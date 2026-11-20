from datetime import date

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from haq import consistency, policy
from haq.config import PROMPTS, ROOT
from haq.llm.base import parse_json  # noqa: F401
from haq.schema import CaseFile

_env = Environment(loader=FileSystemLoader(str(ROOT / "data" / "templates")), undefined=StrictUndefined,
                   keep_trailing_newline=True)


def fmt_date(d: date) -> str:
    return d.strftime("%d %B %Y")


def _complaint_lines(case: CaseFile) -> list[str]:
    out = []
    for c in case.complaints_made:
        bits = [fmt_date(c.date) if c.date else "date not recorded", f"via {c.channel}" if c.channel else None,
                f"ticket {c.ticket_id}" if c.ticket_id else None, f"response: {c.response}" if c.response else None]
        out.append(", ".join(b for b in bits if b))
    return out


def draft_letter(llm, case: CaseFile, today: date) -> tuple[str, list[str]]:
    facts = case.model_dump(mode="json", exclude={"user_confirmed"})
    narrative = llm.complete(
        [{"role": "system", "content": (PROMPTS / "narrative.md").read_text()},
         {"role": "user", "content": f"CASE FILE JSON:\n{facts}"}], temperature=0.1).strip()
    amount = case.amount_paid_inr
    text = _env.get_template("grievance_letter.j2").render(
        party_name=case.opposite_party.name or "[Seller / platform name]", platform=case.platform,
        today=fmt_date(today), issue_label=(case.issue_type.value if case.issue_type else "my order").replace("_", " "),
        order_id=case.order_id, product=case.product_or_service or "an order",
        order_date=fmt_date(case.order_date) if case.order_date else None,
        amount=f"{amount:,.0f}" if amount is not None and amount == int(amount) else (f"{amount:,.2f}" if amount is not None else None),
        payment_mode=(case.payment_mode.value.upper() if case.payment_mode.value == "upi" else case.payment_mode.value) if case.payment_mode else None,
        narrative=narrative, complaints=_complaint_lines(case), remedy=case.remedy_sought or "a refund",
        evidence=[e.type.replace("_", " ") for e in case.evidence if e.available], disclaimer=policy.DISCLAIMER)
    return text, consistency.check(text, case, today)
