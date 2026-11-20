"""Deterministic urgency rules. Run before any LLM; the LLM cannot downgrade a hit."""
import re

_URGENT = {
    "police_or_arrest": r"\b(police|fir|arrest(ed)?|custody|cyber ?crime)\b",
    "court_or_hearing": r"\b(court summons|summons|hearing (date|tomorrow|on)|legal notice (received|from)|contempt)\b",
    "threat_or_violence": r"\b(threaten(ed|ing)?|threat|beat|assault(ed)?|violence|blackmail(ed|ing)?)\b",
    "injury": r"\b(injur(y|ed)|hospital(i[sz]ed)?|burn(t|ed)|bleeding)\b",
    "self_harm": r"\b(suicide|kill myself|end my life|self[- ]harm)\b",
}

ESCALATION_MESSAGE = (
    "This sounds urgent, so I am stopping the normal refund flow. "
    "Please speak to a qualified advocate now. If you cannot afford one, your District Legal "
    "Services Authority (NALSA) can arrange free legal aid. If you are in danger, call 112. "
    "These are general pointers, not from my verified sources. I am not a lawyer and this is not legal advice."
)


def check_urgent(text: str) -> str | None:
    """Return the matched category (e.g. 'police_or_arrest') or None."""
    for category, pattern in _URGENT.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            return category
    return None


def escalation_message(category: str) -> str:
    return ESCALATION_MESSAGE
