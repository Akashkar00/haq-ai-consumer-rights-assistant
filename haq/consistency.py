"""Every amount, date and ID in a draft must come from the CaseFile (or be today's date)."""
import re
from datetime import date, datetime

from haq.schema import CaseFile

_MONTHS = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_AMOUNT = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d+)?)")
_DATE = re.compile(rf"\b(\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}|\d{{1,2}}\s+(?:{_MONTHS})[a-z]*\.?,?\s+\d{{4}})\b")
_ID = re.compile(r"\b(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]{6,}\b")
_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %B %Y", "%d %b %Y", "%d %b, %Y", "%d %B, %Y", "%d %b. %Y"]


def parse_date(s: str) -> date | None:
    s = re.sub(r"\s+", " ", s.strip())
    for f in _FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


def case_values(case: CaseFile, today: date):
    amounts = set()
    if case.amount_paid_inr is not None:
        amounts.add(float(case.amount_paid_inr))
    dates = {today}
    if case.order_date:
        dates.add(case.order_date)
    dates.update(e.date for e in case.timeline if e.date)
    dates.update(c.date for c in case.complaints_made if c.date)
    ids = {x.lower() for x in ([case.order_id] if case.order_id else [])}
    ids.update(c.ticket_id.lower() for c in case.complaints_made if c.ticket_id)
    return amounts, dates, ids


def check(draft: str, case: CaseFile, today: date) -> list[str]:
    """Return a list of human-readable mismatches (empty = consistent)."""
    amounts, dates, ids = case_values(case, today)
    problems = []
    for m in _AMOUNT.finditer(draft):
        v = float(m.group(1).replace(",", ""))
        if v not in amounts:
            problems.append(f"Amount {m.group(0)} is not in your confirmed facts.")
    for m in _DATE.finditer(draft):
        d = parse_date(m.group(1))
        if d is None or d not in dates:
            problems.append(f"Date '{m.group(1)}' is not in your confirmed facts.")
    stripped = _DATE.sub(" ", draft)
    stripped = re.sub(r"\b(?:\+?91[- ]?)?\d{10}\b", " ", stripped)
    for m in _ID.finditer(stripped):
        tok = m.group(0)
        if tok.lower() not in ids and not tok.isalpha():
            problems.append(f"Reference '{tok}' is not in your confirmed facts.")
    return problems
