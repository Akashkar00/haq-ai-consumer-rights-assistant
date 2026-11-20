import json

import pytest


class FakeLLM:
    """Scripted LLM: routes by the system prompt, so tests need no API key."""

    def __init__(self, in_scope=True, case=None, explain=None, narrative="I ordered an item and it was not delivered."):
        self.in_scope = in_scope
        self.case = case or {}
        self.explain = explain or {"summary": "You paid for an item that was not delivered.", "options": [],
                                   "uncertainties": [], "needs_lawyer": False, "lawyer_reason": None}
        self.narrative = narrative
        self.last_provider = "fake"

    def complete(self, messages, *, json_mode=False, temperature=0.1, max_tokens=4000):
        sys = messages[0]["content"]
        if "classify a message" in sys:
            return json.dumps({"in_scope": self.in_scope, "domain": "consumer_refund" if self.in_scope else "tenancy", "reason": "x"})
        if "extract a structured case file" in sys:
            return json.dumps(self.case)
        if "explain a consumer's position" in sys:
            return json.dumps(self.explain)
        if "facts" in sys and "paragraph" in sys:
            return self.narrative
        return "Please tell me what you bought, how much you paid and whether you complained."


FULL_CASE = {
    "issue_type": "non_delivery", "opposite_party": {"name": "QuickKart", "type": "platform"}, "platform": "QuickKart",
    "product_or_service": "headphones", "order_id": "QK778812", "order_date": "2026-10-05", "amount_paid_inr": 3200,
    "payment_mode": "upi", "complaints_made": [{"date": "2026-10-20", "channel": "app chat", "ticket_id": "TK5521", "response": "wait"}],
    "evidence": [{"type": "screenshot", "available": True}], "remedy_sought": "refund",
}
STORY = "I ordered headphones from QuickKart on 5 October 2026 for Rs 3200 by UPI, order QK778812, never delivered. Ticket TK5521 on 20 October 2026."


@pytest.fixture(params=["on", "off"])
def rails(request, monkeypatch):
    monkeypatch.setenv("GUARDRAILS", request.param)
    return request.param


@pytest.fixture
def FakeLLMCls():
    return FakeLLM
