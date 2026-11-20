"""Live provider checks. Skipped unless RUN_LIVE=1 (they spend API credits)."""
import os

import pytest

from haq.llm.base import _make

pytestmark = pytest.mark.skipif(os.getenv("RUN_LIVE") != "1", reason="set RUN_LIVE=1 to call real providers")


@pytest.mark.parametrize("provider,model_env", [("vertex", "LLM_MODEL"), ("anthropic", "LLM_FALLBACK_MODEL")])
def test_provider_answers(provider, model_env):
    out = _make(provider, os.environ[model_env]).complete([{"role": "user", "content": "Reply with the word OK"}], max_tokens=50)
    assert "ok" in out.lower()


def test_clients_have_timeouts():
    v = _make("vertex", os.environ["LLM_MODEL"])
    a = _make("anthropic", os.environ["LLM_FALLBACK_MODEL"])
    assert v.client._api_client._http_options.timeout == 60_000
    assert a.client.timeout == 60.0
