"""Citation / hallucination gate. Code-level, so prompt injection cannot bypass it."""
import re
from dataclasses import dataclass, field

_SECTION = re.compile(r"\b(?:Section|Sec\.|Rule)\s+\d+[A-Za-z]?(?:\(\d+\))?", re.IGNORECASE)
_ACT = re.compile(r"\b[A-Z][A-Za-z ()-]{2,60}\bAct,? \d{4}")
_PARTY = r"[A-Z]\w*(?:\s+(?:of|and|&)\s+[A-Z]\w*|\s+[A-Z]\w*){0,3}"
_CASE = re.compile(
    rf"\b{_PARTY}\s+(?:v\.?|vs\.?)\s+{_PARTY}"
    r"|\b(?:the )?(?:Supreme Court|High Court)\s+(?:has\s+)?(?:held|ruled|observed)\b",
)
_CITE = re.compile(r"\[S\d+(?:\s*,\s*S\d+)*\]")

REMOVED_MARK = "[unverified reference removed]"


@dataclass
class VerifyResult:
    text: str
    removed: list[str] = field(default_factory=list)

    @property
    def modified(self) -> bool:
        return bool(self.removed)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def verify(text: str, retrieved_ids: set[str], allowed_refs: set[str]) -> VerifyResult:
    """Remove citations and legal references that are not in the retrieved corpus.

    retrieved_ids: citation numbers allowed in this turn, e.g. {"1", "2"} for [S1], [S2].
    allowed_refs:  verbatim reference strings from corpus metadata, e.g. {"Section 35"}.
    """
    allowed = {_norm(r) for r in allowed_refs}
    removed: list[str] = []

    def drop_cite(m: re.Match) -> str:
        nums = re.findall(r"\d+", m.group(0))
        if all(n in retrieved_ids for n in nums):
            return m.group(0)
        removed.append(m.group(0))  # one bad tag removes the whole bracket
        return REMOVED_MARK

    def drop_ref(m: re.Match) -> str:
        if _norm(m.group(0)) in allowed:
            return m.group(0)
        removed.append(m.group(0))
        return REMOVED_MARK

    def drop_always(m: re.Match) -> str:
        removed.append(m.group(0))  # no case law in the corpus, so nothing can match
        return REMOVED_MARK

    text = _CITE.sub(drop_cite, text)
    text = _SECTION.sub(drop_ref, text)
    text = _ACT.sub(drop_ref, text)
    text = _CASE.sub(drop_always, text)
    return VerifyResult(text=text, removed=removed)
