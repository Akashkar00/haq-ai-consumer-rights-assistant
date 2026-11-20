"""Single entry point for guardrails. GUARDRAILS=off runs the same policies without NeMo."""
import os
from dataclasses import dataclass
from pathlib import Path

from haq import policy, redact, safety, verifier

_CONFIG = Path(__file__).parent / "guardrails"
_BLOCK_TEXT = {"injection": None, "outcome": policy.NO_PREDICTION, "impersonation": None}
_rails = None


@dataclass
class Verdict:
    status: str  # passed | modified | blocked
    text: str
    rail: str | None = None


def _enabled() -> bool:
    return os.getenv("GUARDRAILS", "on").lower() != "off"


def _get_rails():
    global _rails
    if _rails is None:
        from nemoguardrails import LLMRails, RailsConfig

        from haq.guardrails import actions

        _rails = LLMRails(RailsConfig.from_path(str(_CONFIG)))
        for name in dir(actions):
            fn = getattr(actions, name)
            if hasattr(fn, "action_meta"):
                _rails.register_action(fn, fn.action_meta["name"])
    return _rails


def _blocked_text(rail: str | None, original: str) -> str:
    if rail and "urgent" in rail:
        return safety.escalation_message(safety.check_urgent(original) or "urgent matter")
    if rail and "injection" in rail:
        return "I can't follow instructions that change my rules or ask me to cite material outside my verified sources, such as case law. Tell me about your refund problem and I will help."
    if rail and "outcome" in rail:
        return policy.NO_PREDICTION
    return "I can't share that wording. I can give general information from the official sources shown."


def check_input(text: str) -> Verdict:
    if not _enabled():
        masked = redact.redact(text)
        if (cat := safety.check_urgent(masked)):
            return Verdict("blocked", safety.escalation_message(cat), "check urgent matter")
        if policy.looks_like_injection(masked):
            return Verdict("blocked", _blocked_text("injection", masked), "check prompt injection")
        return Verdict("modified" if masked != text else "passed", masked)
    from nemoguardrails.rails.llm.options import RailStatus, RailType

    r = _get_rails().check([{"role": "user", "content": text}], rail_types=[RailType.INPUT])
    if r.status == RailStatus.BLOCKED:
        return Verdict("blocked", _blocked_text(r.rail, text), r.rail)
    return Verdict(r.status.value, r.content)


def check_output(text: str, retrieved_ids: set[str], allowed_refs: set[str]) -> Verdict:
    if not _enabled():
        v = verifier.verify(text, retrieved_ids, allowed_refs)
        if policy.promises_outcome(v.text):
            return Verdict("blocked", policy.NO_PREDICTION, "block outcome promises")
        if policy.impersonates_lawyer(v.text):
            return Verdict("blocked", _blocked_text("impersonation", v.text), "block lawyer impersonation")
        out = policy.with_disclaimer(v.text)
        return Verdict("modified" if out != text else "passed", out)
    from nemoguardrails.rails.llm.options import RailStatus, RailType

    from haq.guardrails.actions import TURN_IDS, TURN_REFS

    t1, t2 = TURN_IDS.set(retrieved_ids), TURN_REFS.set(allowed_refs)
    try:
        r = _get_rails().check(
            [{"role": "user", "content": "x"}, {"role": "assistant", "content": text}],
            rail_types=[RailType.OUTPUT],
        )
    finally:
        TURN_IDS.reset(t1)
        TURN_REFS.reset(t2)
    if r.status == RailStatus.BLOCKED:
        return Verdict("blocked", _blocked_text(r.rail, text), r.rail)
    return Verdict(r.status.value, r.content)
