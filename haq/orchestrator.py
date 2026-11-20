"""Conversation state machine (plan §10.4). Guardrails run on every turn."""
import re
from dataclasses import dataclass, field
from datetime import date

from haq import drafter, explainer, extractor, gaps, guard, policy, triage
from haq.config import PROMPTS
from haq.corpus import Corpus
from haq.schema import CaseFile

YES = re.compile(r"^\s*(yes|y|yeah|yep|correct|confirm(ed)?|right|that'?s (right|correct)|looks good|ok(ay)?|sure)\b", re.I)
WANT_DRAFT = re.compile(r"\b(draft|letter|complaint|yes|ok|sure|please|go ahead)\b", re.I)
_HINGLISH = re.compile(r"\b(mera|meri|maine|nahi|nahin|paisa|wapas|hua|kharab|rupaye|rupaiye|mahine|abhi tak|shikayat|mangwaya|kiya|hai)\b", re.I)
_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def looks_hindi(text: str) -> bool:
    return bool(_DEVANAGARI.search(text)) or len(set(m.group(0).lower() for m in _HINGLISH.finditer(text))) >= 2


def keeps_numbers(english: str, translated: str) -> bool:
    """A translation is only shown if every number and ID-like token of the English summary survives in it."""
    return all(tok in translated for tok in set(re.findall(r"[A-Za-z]*\d[\w,.-]*", english)))


DONE = re.compile(r"\b(thanks|thank you|done|bye|that'?s all)\b", re.I)


@dataclass
class Reply:
    text: str
    state: str
    flags: list[str] = field(default_factory=list)
    draft: str | None = None


class Session:
    def __init__(self, llm, corpus: Corpus | None = None, today: date | None = None):
        self.llm, self.corpus, self.today = llm, corpus or Corpus(), today or date.today()
        self.state, self.case, self.rounds = "INTAKE", CaseFile(), 0
        self.user_texts: list[str] = []
        self.last_draft: str | None = None

    # -- helpers ---------------------------------------------------------------------------
    def _summary(self) -> str:
        c = self.case
        lines = [f"- Issue: {c.issue_type.value.replace('_', ' ') if c.issue_type else 'not stated'}",
                 f"- Seller/platform: {c.opposite_party.name or 'not stated'}{' via ' + c.platform if c.platform and c.platform != c.opposite_party.name else ''}",
                 f"- Item/service: {c.product_or_service or 'not stated'}",
                 f"- Order ID / date: {c.order_id or 'not stated'} / {c.order_date.isoformat() if c.order_date else 'not stated'}",
                 f"- Amount paid: {f'Rs. {c.amount_paid_inr:,.0f}' if c.amount_paid_inr is not None else 'not stated'}",
                 f"- Earlier complaints: {len(c.complaints_made) or ('none yet' if c.no_complaint_yet else 'not stated')}",
                 f"- Evidence: {', '.join(e.type for e in c.evidence if e.available) or 'none mentioned'}"]
        gap = gaps.evidence_gaps(c) + [f"Missing: {m}" for m in gaps.missing_fields(c)]
        return "Here is what I understood:\n" + "\n".join(lines) + ("\n\nGaps: " + "; ".join(gap) if gap else "") + \
            "\n\nIs this correct? Reply 'yes' to continue, or tell me what to change."

    def _ask(self, missing: list[str]) -> str:
        topics = [gaps.QUESTION_TOPICS[m] for m in missing][:3]
        try:
            msg = self.llm.complete(
                [{"role": "system", "content": (PROMPTS / "followup.md").read_text()},
                 {"role": "user", "content": "Missing information:\n" + "\n".join(f"- {t}" for t in topics)}],
                temperature=0.3, max_tokens=500).strip()
            if msg:
                return msg
        except Exception:
            pass
        return "To help you, please tell me:\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(topics, 1))

    def _gather(self, text: str) -> Reply:
        self.case = extractor.extract(self.llm, self.case, text, " ".join(self.user_texts))
        missing = gaps.missing_fields(self.case)
        if missing and self.rounds < 3:
            self.rounds += 1
            self.state = "GATHER"
            return Reply(self._ask(missing), self.state)
        self.state = "CONFIRM"
        summary = self._summary()
        if looks_hindi(" ".join(self.user_texts)):
            try:
                hi = self.llm.complete(
                    [{"role": "system", "content": "Translate the user's text into simple Hinglish (Hindi in Roman script). Do not change any "
                      "number, name, date or ID. Return only the translation."}, {"role": "user", "content": summary}],
                    temperature=0.0, max_tokens=1500).strip()
                if hi and keeps_numbers(summary, hi):
                    summary += "\n\n(Hindi/Hinglish version; the English above is the one I will use.)\n" + hi
            except Exception:
                pass
        return Reply(summary, self.state)

    def _explain(self) -> Reply:
        self.case.user_confirmed = True
        res = explainer.explain(self.llm, self.corpus, self.case, self.today)
        self.state = "ACTION_SELECT"
        flags = res.flags + (["needs_lawyer"] if res.needs_lawyer else [])
        return Reply(res.text + "\n\nWould you like a complaint letter drafted from these confirmed facts? (reply 'draft')",
                     self.state, flags)

    # -- main entry ------------------------------------------------------------------------
    def handle(self, user_text: str) -> Reply:
        verdict = guard.check_input(user_text)
        if verdict.status == "blocked":
            if "urgent" in (verdict.rail or ""):
                self.state = "ESCALATE"
            return Reply(verdict.text, self.state, [f"blocked:{verdict.rail}"])
        if self.state == "ESCALATE":
            return Reply(verdict.text and "This conversation was stopped because it needs an advocate. " + policy.DISCLAIMER, self.state)
        text = verdict.text  # masked
        self.user_texts.append(text)

        if policy.asks_outcome(text):
            return Reply(policy.NO_PREDICTION + " What usually matters: your evidence of payment and delivery failure, "
                         "any written complaints you made, and the seller's reply.", self.state, ["outcome_refused"])
        bad = [s for s in policy.sections_mentioned(text) if s not in self.corpus.allowed_refs()]
        if bad:
            secs = sorted({r for r in self.corpus.allowed_refs() if r.startswith("Section") and "(" not in r})
            return Reply(f"I cannot verify {', '.join(bad)} in my sources, so I will not cite it. I only rely on specific provisions "
                         f"of the Consumer Protection Act, 2019 ({', '.join(secs)}), the Consumer Protection (E-Commerce) Rules, 2020 "
                         "and the 2021 Jurisdiction Rules. Tell me about your refund problem and I will explain which of these apply.",
                         self.state, ["unverified_section_request"])

        if self.state == "INTAKE":
            t = triage.triage(self.llm, text)
            if not t["in_scope"]:
                self.state = "OUT_OF_SCOPE"
                return Reply(triage.OUT_OF_SCOPE_MESSAGE.format(domain=t["domain"].replace("_", " ")), self.state, ["out_of_scope"])
            return self._gather(text)
        if self.state == "OUT_OF_SCOPE":
            self.state = "INTAKE"
            return self.handle(user_text)
        if self.state == "GATHER":
            return self._gather(text)
        if self.state == "CONFIRM":
            if YES.match(text):
                return self._explain()
            return self._gather(text)  # correction
        if self.state == "ACTION_SELECT":
            if WANT_DRAFT.search(text):
                return self._draft()
            return Reply("Say 'draft' if you would like a complaint letter, or tell me if something needs correcting.", self.state)
        if self.state == "REVIEW":
            if DONE.search(text):
                self.state = "DONE"
                return Reply("Good luck. " + policy.DISCLAIMER, self.state)
            self.case = extractor.extract(self.llm, self.case, text, " ".join(self.user_texts))
            self.case.user_confirmed = True
            return self._draft()
        return Reply("This conversation has ended. Start a new one to continue.", self.state)

    def _draft(self) -> Reply:
        text, problems = drafter.draft_letter(self.llm, self.case, self.today)
        self.last_draft, self.state = text, "REVIEW"
        warn = ("\n\nWarning: " + " ".join(problems) + " Please check these before sending.") if problems else ""
        return Reply("Here is your draft. Review every line before sending." + warn
                     + "\n\nTell me what to change, or say 'done'.", self.state, ["consistency_warning"] if problems else [], text)
