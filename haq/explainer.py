import re
from dataclasses import dataclass, field
from datetime import date

from pydantic import ValidationError

from haq import guard, policy
from haq.config import PROMPTS
from haq.corpus import Chunk, Corpus
from haq.llm.base import parse_json
from haq.schema import CaseFile, Explanation

_LADDER_IDS = ["NCH-HOWTO", "JUR2021-3", "CPA2019-69", "CPA2019-35"]
# Hand-written, per issue type: entries a good answer needs even when BM25 ranks them below the top 7.
# BM25 alone missed these in the retrieval eval (evals/retrieval_eval.py).
_ISSUE_REQUIRED = {
    "non_delivery": ["CPA2019-2-11"], "cancelled_not_refunded": ["CPA2019-2-11"], "return_refused": ["CPA2019-2-11"],
    "damaged_item": ["CPA2019-2-10"], "defective_item": ["CPA2019-2-10"], "wrong_item": ["CPA2019-2-10"],
}
_ISSUE_REQUIRED_PLATFORM = {
    "non_delivery": ["ECOM2020-6-3"], "cancelled_not_refunded": ["ECOM2020-4-10"], "return_refused": ["ECOM2020-6-3", "ECOM2020-4-10"],
    "damaged_item": ["ECOM2020-6-3"], "defective_item": ["ECOM2020-6-3"], "wrong_item": ["ECOM2020-6-3"],
}
_HIGH_VALUE_IDS = ["JUR2021-4", "JUR2021-5"]
STATE_LIMIT_INR = 20_000_000  # two crore, from JUR2021-4/5 (volatile)
_ECOM_LADDER_IDS = ["ECOM2020-4-5"]  # only for purchases made through a platform
DISTRICT_LIMIT_INR = 5_000_000  # fifty lakh, from JUR2021-3 (volatile; re-check before relying on it)


@dataclass
class ExplainResult:
    text: str
    chunks: list[Chunk]
    flags: list[str] = field(default_factory=list)
    needs_lawyer: bool = False


def lawyer_triggers(case: CaseFile, today: date) -> list[str]:
    """Deterministic reasons to recommend an advocate, independent of the LLM."""
    why = []
    if case.amount_paid_inr and case.amount_paid_inr > DISTRICT_LIMIT_INR:
        why.append("The amount is above the District Commission's value limit in the sources, so a different "
                   "Commission would apply and the claim needs professional handling.")
    if case.order_date and (today - case.order_date).days > 730:
        why.append("More than two years have passed since the order date. The sources set a two-year limit from "
                   "when the cause of action arose, so a lawyer should check whether the complaint is still in time.")
    if any("physical injury" in n.lower() or "fraud" in n.lower() for n in case.notes_uncertain):
        why.append("Injury or fraud was mentioned, which needs an advocate.")
    return why


def _render_chunks(chunks: list[Chunk]) -> str:
    return "\n\n".join(
        f"[{c.sid}] {c.entry['title']} ({c.entry['reference']})\nOfficial text: {c.entry['verbatim_text']}\n"
        f"Plain summary (Haq's paraphrase): {c.entry['plain_summary']}" for c in chunks)


def _ladder(case: CaseFile, chunks: list[Chunk]) -> list[str]:
    by_id = {c.entry["id"]: c.sid for c in chunks}
    tag = lambda eid: f" [{by_id[eid]}]" if eid in by_id else ""
    if case.platform:
        step1 = ("1. Write to the seller/platform grievance officer and keep the ticket number. For e-commerce entities "
                 "the Rules require acknowledgement within 48 hours and resolution within one month" + tag("ECOM2020-4-5") + ".")
    else:
        step1 = "1. Write to the seller in writing (email or letter), keep proof that you sent it, and ask for a reply by a fixed date."
    n = len(case.complaints_made)
    if n >= 2:
        step1 += (f" You have already complained {n} times; if those were closed without a resolution, you can move "
                  "straight to the next step instead of repeating this one.")
    steps = [
        step1,
        "2. If that does not work, register a grievance with the National Consumer Helpline (1915 or 1800114000)"
        + tag("NCH-HOWTO") + ".",
        "3. Optionally send a written legal notice. An advocate can draft this; I do not cover its legal content.",
    ]
    if case.amount_paid_inr is not None and case.amount_paid_inr <= DISTRICT_LIMIT_INR:
        steps.append("4. File a complaint with the District Commission. The value limit is up to fifty lakh rupees"
                     + tag("JUR2021-3") + " and a complaint should be filed within two years of the cause of action"
                     + tag("CPA2019-69") + ". It may be filed electronically" + tag("CPA2019-35") + ".")
    else:
        if case.amount_paid_inr is not None and case.amount_paid_inr <= STATE_LIMIT_INR:
            which = "the State Commission (above fifty lakh and up to two crore rupees)" + tag("JUR2021-4")
        elif case.amount_paid_inr is not None:
            which = "the National Commission (above two crore rupees)" + tag("JUR2021-5")
        else:
            which = "a Commission that depends on the value you paid" + tag("JUR2021-3")
        steps.append(f"4. The amount is above the District Commission's limit of fifty lakh rupees{tag('JUR2021-3')}, so the complaint "
                     f"would go to {which}. Please confirm the amount and consult an advocate before filing.")
    return steps


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    import calendar
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def timeline_notes(case: CaseFile, today: date, chunks: list[Chunk]) -> list[str]:
    """Dates computed in code from the user's own facts and the cited rules (never by the model)."""
    by_id = {c.entry["id"]: c.sid for c in chunks}
    tag = lambda eid: f" [{by_id[eid]}]" if eid in by_id else ""
    notes = []
    if case.platform and "ECOM2020-4-5" in by_id:
        for c in case.complaints_made:
            if c.date:
                due = _add_months(c.date, 1)
                if today > due:
                    notes.append(f"If your complaint of {c.date:%d %B %Y} reached the platform's grievance officer, the one-month period ended on {due:%d %B %Y}"
                                 f"{tag('ECOM2020-4-5')}. As of {today:%d %B %Y} that date has passed, so you can move to the next step.")
                else:
                    notes.append(f"If your complaint of {c.date:%d %B %Y} reached the platform's grievance officer, it should be resolved by {due:%d %B %Y}"
                                 f"{tag('ECOM2020-4-5')}. If it is not, move to the next step. (A message to the seller alone may not start this clock.)")
                break  # the earliest dated complaint sets the clock
    if case.order_date:
        last = _add_months(case.order_date, 24)
        left = (last - today).days
        when = f"{left} days from today" if left >= 0 else f"{-left} days ago"
        notes.append(f"Two years from your order date ({case.order_date:%d %B %Y}) is {last:%d %B %Y}, which is {when} (counting from {today:%d %B %Y})"
                     f"{tag('CPA2019-69')}. The limit runs from when the cause of action arose, which may be later (for example "
                     "the promised delivery date), so treat this as a rough guide and check with an advocate if it is close.")
    return notes


def _evidence_advice(case: CaseFile) -> str | None:
    have = {e.type for e in case.evidence if e.available}
    if "invoice" in have:
        return None
    return ("Before you start, gather proof of the purchase. Without an invoice, a bank or UPI statement, the payment "
            "SMS or email, the order confirmation, or your chat with the seller can help show what you bought and paid.")


_TAGS = re.compile(r"\[S\d+(?:\s*,\s*S\d+)*\]")
_LIMIT = re.compile(r"fifty lakh|50 lakh", re.I)


def fix_limit_citations(text: str, chunks: list[Chunk]) -> str:
    """A sentence stating the fifty-lakh limit must cite the 2021 Rules entry, not Section 34(1) (base text: one crore)."""
    by_id = {c.entry["id"]: c.sid[1:] for c in chunks}
    rule, act = by_id.get("JUR2021-3"), by_id.get("CPA2019-34")
    if not rule:
        return text

    def fix_sentence(sent: str) -> str:
        if not _LIMIT.search(sent):
            return sent
        nums: list[str] = []

        def collect(m: re.Match) -> str:
            nums.extend(re.findall(r"\d+", m.group(0)))
            return ""

        stripped = _TAGS.sub(collect, sent).rstrip()
        if act not in nums and rule in nums:
            return sent  # already cites the Rules entry and not the Act: leave untouched
        stripped = re.sub(r"\s+([,.;:)])", r"\1", stripped)
        stripped = re.sub(r"([,;:])(\s*[,;:])+", r"\1", stripped)  # tag removal can leave doubled punctuation
        keep = [n for n in dict.fromkeys(nums) if n != act]
        if rule not in keep:
            keep.append(rule)
        tag = "[" + ", ".join(f"S{n}" for n in keep) + "]"
        m = re.search(r"([.;:]?)$", stripped)
        return stripped[: m.start()].rstrip() + f" {tag}" + m.group(1)

    lines = []
    for line in text.split("\n"):
        sents = re.split(r"(?<=[.;])\s+(?=[A-Z0-9])", line)
        lines.append(" ".join(fix_sentence(x) for x in sents))
    return "\n".join(lines)


def _llm_explanation(llm, messages) -> Explanation:
    """Parse the model's JSON with one repair retry; degrade to a source-only answer instead of crashing."""
    for _ in range(2):
        raw = None
        try:
            raw = llm.complete(messages, json_mode=True, temperature=0.1, max_tokens=8000)
            return Explanation.model_validate(parse_json(raw))
        except (ValueError, ValidationError) as e:
            messages = messages + ([{"role": "assistant", "content": raw}] if raw else []) + [
                {"role": "user", "content": f"That was not valid JSON for the schema ({str(e)[:200]}). Return the JSON only."}]
    return Explanation(summary="I could not write a tailored explanation this time, so below are the standard steps "
                               "and the official sources that apply.",
                       uncertainties=["The automatic explanation step failed; please check the sources directly."])


def retrieve_for_case(corpus: Corpus, case: CaseFile, bm25_only: bool = False) -> list[Chunk]:
    """BM25 retrieval, plus the entries the options ladder cites (unless bm25_only, used to measure BM25 alone)."""
    issue = case.issue_type.value if case.issue_type else None
    query = " ".join(filter(None, [issue and issue.replace("_", " "), case.product_or_service, case.remedy_sought,
                                   "refund consumer complaint e-commerce grievance"]))
    on_platform = bool(case.platform)  # the E-Commerce Rules apply to platform purchases, not a local shop
    chunks = corpus.retrieve(query, issue, k=7, exclude_tag=None if on_platform else "ecommerce")
    if bm25_only:
        return chunks
    have = {c.entry["id"] for c in chunks}
    high_value = bool(case.amount_paid_inr and case.amount_paid_inr > DISTRICT_LIMIT_INR)
    required = _ISSUE_REQUIRED.get(issue, []) + (_ISSUE_REQUIRED_PLATFORM.get(issue, []) if on_platform else [])
    for eid in _LADDER_IDS + (_ECOM_LADDER_IDS if on_platform else []) + required + (_HIGH_VALUE_IDS if high_value else []):
        if eid not in have:
            chunks.append(Chunk(f"S{len(chunks) + 1}", corpus.by_id[eid]))
    return chunks


def explain(llm, corpus: Corpus, case: CaseFile, today: date) -> ExplainResult:
    chunks = retrieve_for_case(corpus, case)
    messages = [
        {"role": "system", "content": (PROMPTS / "explain.md").read_text()},
        {"role": "user", "content": f"CASE FILE:\n{case.model_dump_json()}\n\nSOURCES:\n{_render_chunks(chunks)}"}]
    exp = _llm_explanation(llm, messages)

    triggers = lawyer_triggers(case, today)
    needs_lawyer = exp.needs_lawyer or bool(triggers)
    parts = [exp.summary.strip()]
    if (ev := _evidence_advice(case)):
        parts.append("\n**Proof of purchase**\n" + ev)
    if (tl := timeline_notes(case, today, chunks)):
        parts += ["\n**Your timeline**", *[f"- {t}" for t in tl]]
    parts += ["\n**Your options (in the usual order)**", *_ladder(case, chunks)]
    if exp.options:
        parts.append("\n**More detail on these options**")
        parts += [f"- {o.step.rstrip('. ')}: {o.why}" for o in exp.options]
    unsure = list(exp.uncertainties) + [f"Not confirmed: {n}" for n in case.notes_uncertain]
    if unsure:
        parts.append("\n**What I'm not sure about**")
        parts += [f"- {u}" for u in unsure]
    if needs_lawyer:
        parts.append("\n**Please consider speaking to an advocate**")
        parts += [f"- {w}" for w in triggers] or [f"- {exp.lawyer_reason or 'The facts are complex enough that professional advice helps.'}"]
    draft = fix_limit_citations("\n".join(parts), chunks)
    draft, dropped = policy.strip_outcome_sentences(draft)  # drop only the offending sentence, not the whole answer

    cited = {c.sid[1:] for c in chunks}
    verdict = guard.check_output(draft, cited, corpus.allowed_refs([c.entry for c in chunks]))
    flags = ["outcome_sentence_removed"] if dropped else []
    if verdict.status == "blocked":
        flags.append(f"blocked:{verdict.rail}")
    elif "[unverified reference removed]" in verdict.text:
        flags.append("unverified_reference_removed")
    sources = "\n".join(
        f"[{c.sid}] {c.entry['title']} – {c.entry['reference']} – {c.entry['source_url']} (retrieved {c.entry['retrieved_on']}"
        + (", may change" if c.entry["volatile"] else "") + ")" for c in chunks)
    final = verdict.text if verdict.status == "blocked" else f"{verdict.text}\n\n**Sources**\n{sources}"
    if verdict.status != "blocked":
        final = policy.with_disclaimer(final)
    return ExplainResult(final, chunks, flags, needs_lawyer)
