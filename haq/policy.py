"""Pure-text output policies shared by the NeMo actions and the GUARDRAILS=off path."""
import re

DISCLAIMER = (
    "Haq gives general legal information based on the official sources shown. It is not a "
    "lawyer and this is not legal advice. Check the sources and consider consulting an "
    "advocate before taking formal action."
)
NO_PREDICTION = (
    "I can't predict whether you will win or how much compensation you may get. That depends on "
    "your evidence, the seller's response and the Commission's view. A qualified advocate can "
    "help value your claim. I do not make such predictions because I only work from verified provisions, not from how a particular Commission will decide."
)

_INJECTION = re.compile(
    r"ignore (all |your |the )?(previous |prior )?(rules|instructions)|disregard .{0,30}(rules|instructions)"
    r"|act as (a |an )?(?!consumer)|reveal (your )?(system )?prompt|you are now|jailbreak",
    re.IGNORECASE,
)
_OUTCOME = re.compile(
    r"\byou (will|would|are certain to|are sure to) (definitely |certainly )?(win|get|receive|succeed)\b"
    r"|\bguarantee[sd]?\b|\bcertain(ly)? to win\b|\b100% (chance|sure)\b",
    re.IGNORECASE,
)
_IMPERSONATION = re.compile(r"\bas your (lawyer|advocate|counsel)\b|\bI advise you to sue\b", re.IGNORECASE)


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(text))


def promises_outcome(text: str) -> bool:
    return bool(_OUTCOME.search(text))


def impersonates_lawyer(text: str) -> bool:
    return bool(_IMPERSONATION.search(text))


def with_disclaimer(text: str) -> str:
    return text if DISCLAIMER in text else f"{text.rstrip()}\n\n{DISCLAIMER}"


_ASKS_OUTCOME = re.compile(
    r"\b(will i (definitely |surely )?(win|get)|am i (sure|certain) to win|how much compensation|"
    r"what are my chances|guarantee)\b", re.IGNORECASE)


def asks_outcome(text: str) -> bool:
    return bool(_ASKS_OUTCOME.search(text))


_SECTION_IN_TEXT = re.compile(r"\bsection\s+(\d+[a-z]?)", re.IGNORECASE)


def sections_mentioned(text: str) -> list[str]:
    return [f"Section {m.group(1)}" for m in _SECTION_IN_TEXT.finditer(text)]


def strip_outcome_sentences(text: str) -> tuple[str, list[str]]:
    """Remove only the sentences that promise an outcome or impersonate a lawyer, keeping the rest of the answer."""
    removed, out = [], []
    for line in text.split("\n"):
        kept = []
        for sent in re.split(r"(?<=[.!?])(?<!\bv\.)(?<!\bvs\.)(?<!\bSec\.)\s+", line):
            if promises_outcome(sent) or impersonates_lawyer(sent):
                removed.append(sent)
            else:
                kept.append(sent)
        out.append(" ".join(kept))
    return "\n".join(out), removed
