import json
import logging
import os
import re
import time
from typing import Protocol

from haq import config  # noqa: F401  (loads .env)

log = logging.getLogger("haq.llm")


class LLMClient(Protocol):
    def complete(self, messages: list[dict], *, json_mode: bool = False,
                 temperature: float = 0.1, max_tokens: int = 4000) -> str: ...


def parse_json(text: str):
    """Parse model output as JSON, tolerating code fences and leading prose."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.IGNORECASE)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))


class VertexClient:
    def __init__(self, model: str, project: str, location: str):
        from google import genai

        self.model = model
        from google.genai import types

        # A stalled request must fail so the fallback provider can answer (no timeout = the UI hangs forever).
        self.client = genai.Client(vertexai=True, project=project, location=location,
                                   http_options=types.HttpOptions(timeout=int(os.getenv("LLM_TIMEOUT_S", "60")) * 1000))

    def complete(self, messages, *, json_mode=False, temperature=0.1, max_tokens=4000) -> str:
        from google.genai import types

        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            types.Content(role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["content"])])
            for m in messages if m["role"] != "system"
        ]
        cfg = types.GenerateContentConfig(
            system_instruction=system or None, temperature=temperature,
            # Gemini 3.x spends part of this budget on hidden reasoning; a small cap can return empty text.
            max_output_tokens=max(max_tokens, 2000),
            response_mime_type="application/json" if json_mode else None)
        r = self.client.models.generate_content(model=self.model, contents=contents, config=cfg)
        if not r.text:
            raise RuntimeError("empty response from Vertex")
        return r.text


class AnthropicClient:
    def __init__(self, model: str):
        import anthropic

        self.model = model
        self.client = anthropic.Anthropic(timeout=float(os.getenv("LLM_TIMEOUT_S", "60")))

    def complete(self, messages, *, json_mode=False, temperature=0.1, max_tokens=4000) -> str:
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        if json_mode:
            system += "\nReturn only one valid JSON object, no prose, no code fences."
        turns = [{"role": m["role"], "content": m["content"]} for m in messages if m["role"] != "system"]
        # temperature is deliberately not sent: the current SDK/model rejects it for this provider.
        r = self.client.messages.create(model=self.model, system=system, messages=turns, max_tokens=max_tokens)
        return "".join(b.text for b in r.content if b.type == "text")


class FallbackClient:
    """Tries the primary provider (with retries), then the fallback. Records which one answered."""

    def __init__(self, primary, fallback=None, retries: int = 2):
        self.primary, self.fallback, self.retries = primary, fallback, retries
        self.last_provider = None

    def complete(self, messages, **kw) -> str:
        err = None
        for attempt in range(self.retries):
            try:
                out = self.primary.complete(messages, **kw)
                self.last_provider = "primary"
                return out
            except Exception as e:  # provider errors: rate limit, 5xx, empty output
                err = e
                log.warning("primary LLM failed (attempt %d): %s", attempt + 1, str(e)[:200])
                time.sleep(1.5 * (attempt + 1))
        if self.fallback is None:
            raise err
        out = self.fallback.complete(messages, **kw)
        self.last_provider = "fallback"
        return out


def _make(provider: str, model: str):
    if provider == "vertex":
        return VertexClient(model, os.environ["GOOGLE_CLOUD_PROJECT"], os.getenv("GOOGLE_CLOUD_LOCATION", "global"))
    if provider == "anthropic":
        return AnthropicClient(model)
    raise ValueError(f"unknown provider {provider}")


def get_client() -> FallbackClient:
    primary = _make(os.getenv("LLM_PROVIDER", "vertex"), os.getenv("LLM_MODEL", "gemini-3.8-flash"))
    fb_provider = os.getenv("LLM_FALLBACK_PROVIDER")
    fallback = _make(fb_provider, os.environ["LLM_FALLBACK_MODEL"]) if fb_provider else None
    return FallbackClient(primary, fallback)
