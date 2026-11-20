"""NeMo actions: thin wrappers over the deterministic modules. Policy lives in the modules."""
from contextvars import ContextVar

from nemoguardrails.actions import action

from haq import policy, redact, safety, verifier

# Per-turn corpus context for the verifier, set by haq.guard before each output check.
TURN_IDS: ContextVar[set[str]] = ContextVar("turn_ids", default=set())
TURN_REFS: ContextVar[set[str]] = ContextVar("turn_refs", default=set())


@action(name="mask_sensitive")
async def mask_sensitive(text: str) -> str:
    return redact.redact(text)


@action(name="check_urgent")
async def check_urgent(text: str) -> bool:
    return safety.check_urgent(text) is not None


@action(name="check_injection")
async def check_injection(text: str) -> bool:
    return policy.looks_like_injection(text)


@action(name="verify_citations")
async def verify_citations(text: str) -> str:
    return verifier.verify(text, TURN_IDS.get(), TURN_REFS.get()).text


@action(name="check_outcome_promise")
async def check_outcome_promise(text: str) -> bool:
    return policy.promises_outcome(text)


@action(name="check_impersonation")
async def check_impersonation(text: str) -> bool:
    return policy.impersonates_lawyer(text)


@action(name="add_disclaimer")
async def add_disclaimer(text: str) -> str:
    return policy.with_disclaimer(text)
