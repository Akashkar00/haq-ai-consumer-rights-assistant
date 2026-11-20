"""Regex redaction of sensitive identifiers before text reaches an LLM or a log."""
import re

_PATTERNS = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("AADHAAR", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{9}(?!\d)")),
]


def redact(text: str) -> str:
    # CARD (16 digits) must run before AADHAAR (12 digits) so a card is not half-masked.
    for label, pattern in sorted(_PATTERNS, key=lambda p: p[0] != "CARD"):
        text = pattern.sub(f"[{label}]", text)
    return text
