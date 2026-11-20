from haq.config import PROMPTS
from haq.llm.base import parse_json


def triage(llm, text: str) -> dict:
    messages = [{"role": "system", "content": (PROMPTS / "triage.md").read_text()},
                {"role": "user", "content": text}]
    try:
        out = parse_json(llm.complete(messages, json_mode=True, temperature=0.0, max_tokens=600))
        return {"in_scope": bool(out.get("in_scope")), "domain": str(out.get("domain", "other")),
                "reason": str(out.get("reason", ""))}
    except Exception:  # if classification fails, stay in scope and let extraction ask questions
        return {"in_scope": True, "domain": "unknown", "reason": "triage unavailable"}


OUT_OF_SCOPE_MESSAGE = (
    "This looks like it is outside everyday consumer refund disputes ({domain}), which is the only thing I can help "
    "with, so I will not give advice on it. For legal help you can contact your District Legal Services Authority "
    "(free legal aid may be available if you qualify; this is a general pointer, not from my verified sources) or consult a qualified advocate. If your problem is about a "
    "purchase that was not delivered, was faulty, or was not refunded, tell me about it and I will help."
)
