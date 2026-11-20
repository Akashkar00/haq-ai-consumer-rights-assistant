import json
import re

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


def extract(llm, case: CaseFile, user_text: str, all_user_text: str) -> CaseFile:
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
            return ground(updated, all_user_text)
        except (ValueError, ValidationError) as e:
            last_err = e
            messages = messages + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That was not valid for the schema ({str(e)[:300]}). Return corrected JSON only."}]
    raise ValueError(f"extraction failed: {last_err}")
