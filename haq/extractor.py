import calendar
import json
import re
from datetime import date

from pydantic import ValidationError

from haq.config import PROMPTS
from haq.llm.base import parse_json
from haq.schema import CaseFile


def _squash(s: str) -> str:
    return re.sub(r"[\s,]", "", s).lower()


def ground(case: CaseFile, user_text: str) -> CaseFile:
    """Drop any amount / order id / ticket id the user never wrote, so the model cannot invent them."""
    blob = _squash(user_text)
    notes = list(case.notes_uncertain)
    if case.amount_paid_inr is not None:
        n = case.amount_paid_inr
        forms = {str(int(n)) if n == int(n) else str(n), f"{n:.2f}"}
        if not any(f in blob for f in forms) and not re.search(r"lakh|lac|thousand|crore|k\b", user_text, re.I):
            case.amount_paid_inr = None
            notes.append("An amount was not clearly stated; please confirm how much you paid.")
    if case.order_id and _squash(case.order_id) not in blob:
        case.order_id = None
        notes.append("Order ID not found in your messages and was left blank.")
    for c in case.complaints_made:
        if c.ticket_id and _squash(c.ticket_id) not in blob:
            c.ticket_id = None
    case.notes_uncertain = list(dict.fromkeys(notes))
    return case


_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
_MON = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DAY_MON = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MON})\b(?!\s*,?\s*\d{{4}})", re.I)
_MON_DAY = re.compile(rf"\b({_MON})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?!\s*,?\s*\d{{4}})", re.I)


def fill_missing_year(case: CaseFile, user_text: str, today: date) -> CaseFile:
    """"5 March" with no year: take the most recent past 5 March and flag it, so the user can correct it at confirm."""
    if case.order_date is not None:
        return case
    found = {(_MONTHS[m.group(2).lower()], int(m.group(1))) for m in _DAY_MON.finditer(user_text)}
    found |= {(_MONTHS[m.group(1).lower()], int(m.group(2))) for m in _MON_DAY.finditer(user_text)}
    if len(found) != 1:
        return case
    month, day = found.pop()
    for year in (today.year, today.year - 1):
        try:
            d = date(year, month, day)
        except ValueError:
            return case
        if d <= today:
            case.order_date = d
            case.notes_uncertain = list(dict.fromkeys(
                case.notes_uncertain + [f"You gave no year; I assumed {d.isoformat()}. Please correct it if wrong."]))
            return case
    return case


def extract(llm, case: CaseFile, user_text: str, all_user_text: str, today: date | None = None) -> CaseFile:
    system = (PROMPTS / "extract.md").read_text()
    user = f"CURRENT CASE FILE:\n{case.model_dump_json()}\n\nUSER MESSAGE:\n{user_text}"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    last_err = None
    for _ in range(2):  # one repair retry
        raw = llm.complete(messages, json_mode=True, temperature=0.0)
        try:
            data = parse_json(raw)
            updated = CaseFile.model_validate(data)
            updated.user_confirmed = False
            return fill_missing_year(ground(updated, all_user_text), all_user_text, today or date.today())
        except (ValueError, ValidationError) as e:
            last_err = e
            messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That was not valid for the schema ({str(e)[:300]}). Return corrected JSON only."}]
    raise ValueError(f"extraction failed: {last_err}")
