from haq.schema import CaseFile


def missing_fields(c: CaseFile) -> list[str]:
    miss = []
    if c.issue_type is None:
        miss.append("issue_type")
    if not c.opposite_party.name:
        miss.append("opposite_party")
    if c.amount_paid_inr is None:
        miss.append("amount_paid_inr")
    if c.order_date is None:
        miss.append("order_date")
    if not c.complaints_made and not c.no_complaint_yet:
        miss.append("complaints_made")
    return miss


def evidence_gaps(c: CaseFile) -> list[str]:
    have = {e.type for e in c.evidence if e.available}
    gaps = []
    if "invoice" not in have and "bank_statement" not in have:
        gaps.append("No invoice or bank statement mentioned: proof of payment may be needed.")
    if not have:
        gaps.append("No evidence mentioned yet (screenshots, emails, photos, chats).")
    return gaps


QUESTION_TOPICS = {
    "issue_type": "what went wrong (not delivered, damaged, wrong item, cancelled without refund, return refused)",
    "opposite_party": "who you bought from (the seller and/or the platform name)",
    "amount_paid_inr": "how much you paid, in rupees",
    "order_date": "the order date (an approximate date is fine)",
    "complaints_made": "whether you have already complained to the seller or platform (when, how, any ticket number), or 'none yet'",
}
