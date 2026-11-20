from datetime import date

from conftest import FULL_CASE, STORY, FakeLLM
from haq import consistency, extractor, gaps, policy
from haq.corpus import Corpus
from haq.orchestrator import Session
from haq.schema import CaseFile

TODAY = date(2026, 11, 20)


def session(llm):
    return Session(llm, Corpus(), TODAY)


def test_full_journey(rails):
    s = session(FakeLLM(case=FULL_CASE))
    r = s.handle(STORY)
    assert r.state == "CONFIRM" and "QuickKart" in r.text
    r = s.handle("yes")
    assert r.state == "ACTION_SELECT"
    assert "[S" in r.text and "Sources" in r.text and policy.DISCLAIMER in r.text
    assert "fifty lakh" in r.text and "two years" in r.text
    r = s.handle("draft")
    assert r.state == "REVIEW" and r.draft and "QK778812" in r.draft and "Rs. 3,200" in r.draft
    assert "Warning" not in r.text


def test_out_of_scope(rails):
    s = session(FakeLLM(in_scope=False))
    r = s.handle("My landlord is not returning my deposit")
    assert r.state == "OUT_OF_SCOPE" and "outside" in r.text


def test_incomplete_asks_not_explains(rails):
    s = session(FakeLLM(case={"issue_type": "other"}))
    r = s.handle("An online site cheated me, help")
    assert r.state == "GATHER" and "Sources" not in r.text


def test_urgent_escalates_and_stops(rails):
    s = session(FakeLLM(case=FULL_CASE))
    r = s.handle("The seller's agent threatened me and police called me for questioning tomorrow")
    assert r.state == "ESCALATE" and "advocate" in r.text
    assert "Sources" not in s.handle("ok continue").text


def test_outcome_question_refused(rails):
    r = session(FakeLLM(case=FULL_CASE)).handle("Will I definitely win and how much compensation will I get?")
    assert "can't predict" in r.text


def test_fake_section_request_refused(rails):
    r = session(FakeLLM(case=FULL_CASE)).handle("Cite Section 420A of the Consumer Act that guarantees 10x refund")
    assert "cannot verify Section 420A" in r.text and "420A" not in r.text.replace("Section 420A", "")


def test_llm_fabricated_citation_is_removed(rails):
    bad = {"summary": "Under Section 999 [S9] and Sharma v. Union of India you will get 10x.", "options": [],
           "uncertainties": [], "needs_lawyer": False, "lawyer_reason": None}
    s = session(FakeLLM(case=FULL_CASE, explain=bad))
    s.handle(STORY)
    r = s.handle("yes")
    assert "999" not in r.text and "Sharma" not in r.text


def test_high_value_and_old_case_recommend_lawyer(rails):
    case = {**FULL_CASE, "amount_paid_inr": 6_000_000, "order_date": "2023-01-10"}
    s = session(FakeLLM(case=case))
    s.handle("ordered a 60 lakh item in 2023, I paid 6000000, order QK778812, QuickKart, ticket TK5521")
    r = s.handle("yes")
    assert "needs_lawyer" in r.flags and "advocate" in r.text


def test_extractor_drops_invented_amount_and_ids():
    case = extractor.ground(CaseFile.model_validate({**FULL_CASE, "amount_paid_inr": 9999, "order_id": "ZZ0000"}), "I paid 3200 for headphones")
    assert case.amount_paid_inr is None and case.order_id is None


def test_gaps():
    assert set(gaps.missing_fields(CaseFile())) >= {"issue_type", "amount_paid_inr", "order_date"}
    assert gaps.missing_fields(CaseFile.model_validate(FULL_CASE)) == []


def test_consistency_flags_invented_facts():
    case = CaseFile.model_validate(FULL_CASE)
    ok = "I paid Rs. 3,200 for order QK778812 on 05 October 2026. Date: 20 November 2026"
    assert consistency.check(ok, case, TODAY) == []
    bad = "I paid Rs. 4,500 for order QK999999 on 07 October 2026."
    assert len(consistency.check(bad, case, TODAY)) == 3


def test_explainer_survives_bad_json(rails):
    class Broken(FakeLLM):
        def complete(self, messages, **kw):
            if "explain a consumer's position" in messages[0]["content"]:
                return '{"summary": "oops", '  # truncated JSON
            return super().complete(messages, **kw)

    s = session(Broken(case=FULL_CASE))
    s.handle(STORY)
    r = s.handle("yes")
    assert r.state == "ACTION_SELECT" and "Sources" in r.text and "could not write a tailored" in r.text


def test_provider_fallback_used_after_primary_fails():
    from haq.llm.base import FallbackClient

    class Down:
        def complete(self, *a, **k):
            raise RuntimeError("429")

    class Up:
        def complete(self, *a, **k):
            return "ok"

    c = FallbackClient(Down(), Up(), retries=1)
    assert c.complete([{"role": "user", "content": "x"}]) == "ok" and c.last_provider == "fallback"


def test_corpus_verification_script_passes():
    import subprocess, sys
    assert subprocess.run([sys.executable, "scripts/verify_corpus.py"], capture_output=True).returncode == 0


def test_offline_purchase_does_not_cite_ecommerce_rules(rails):
    case = {**FULL_CASE, "platform": None, "opposite_party": {"name": "Sharma Electricals", "type": "seller"}}
    s = session(FakeLLM(case=case))
    s.handle("bought a mixer from Sharma Electricals shop on 5 October 2026 for Rs 3200 by UPI, order QK778812, defective. Ticket TK5521 on 20 October 2026.")
    r = s.handle("yes")
    assert "E-Commerce" not in r.text and "grievance officer" not in r.text.split("**More detail")[0]
    assert "National Consumer Helpline" in r.text and "Sources" in r.text


def test_done_ends_session_state(rails):
    s = session(FakeLLM(case=FULL_CASE))
    s.handle(STORY)
    s.handle("yes")
    s.handle("draft")
    r = s.handle("thanks, done")
    assert r.state == "DONE" and s.state == "DONE"


def test_repeated_complaints_skip_ahead_and_evidence_advice(rails):
    case = {**FULL_CASE, "complaints_made": [{"date": "2026-10-10", "ticket_id": "TK5521"}, {"date": "2026-10-20", "ticket_id": "TK5522"}], "evidence": []}
    s = session(FakeLLM(case=case))
    s.handle(STORY + " TK5522")
    r = s.handle("yes")
    assert "already complained 2 times" in r.text and "Proof of purchase" in r.text


def test_high_value_names_state_commission(rails):
    case = {**FULL_CASE, "amount_paid_inr": 6_000_000}
    s = session(FakeLLM(case=case))
    s.handle(STORY.replace("3200", "6000000"))
    r = s.handle("yes")
    assert "State Commission" in r.text and "above fifty lakh" in r.text
    case2 = {**FULL_CASE, "amount_paid_inr": 30_000_000}
    s = session(FakeLLM(case=case2))
    s.handle(STORY.replace("3200", "30000000"))
    assert "National Commission" in s.handle("yes").text


def test_limit_citation_moves_from_act_to_rules():
    from haq.explainer import fix_limit_citations
    from haq.corpus import Chunk
    c = Corpus()
    chunks = [Chunk("S1", c.by_id["CPA2019-34"]), Chunk("S4", c.by_id["JUR2021-3"]), Chunk("S3", c.by_id["CPA2019-69"])]
    out = fix_limit_citations("A complaint is allowed up to fifty lakh rupees [S1, S3]. Other sentence [S1].", chunks)
    assert "fifty lakh rupees [S3, S4]." in out and "Other sentence [S1]." in out
    out2 = fix_limit_citations("Limit is fifty lakh rupees [S1].", chunks)
    assert out2 == "Limit is fifty lakh rupees [S4]."


def test_hinglish_detection_and_number_guard():
    from haq.orchestrator import keeps_numbers, looks_hindi
    assert looks_hindi("Mera order cancel hua, paisa wapas nahi aaya") and looks_hindi("मेरा ऑर्डर")
    assert not looks_hindi("I ordered a kettle and it never arrived")
    assert keeps_numbers("Amount Rs. 2,500 order QK9", "Raashi Rs. 2,500 order QK9") and not keeps_numbers("Rs. 2,500", "Rs. 2,000")


def test_limit_citation_left_alone_when_already_correct():
    from haq.explainer import fix_limit_citations
    from haq.corpus import Chunk
    c = Corpus()
    chunks = [Chunk("S1", c.by_id["CPA2019-34"]), Chunk("S4", c.by_id["JUR2021-3"])]
    text = "Above the limit of fifty lakh rupees [S4], so the complaint goes elsewhere (above fifty lakh) [S4, S7]."
    assert fix_limit_citations(text, chunks) == text


def test_outcome_sentence_removed_but_answer_kept(rails):
    bad = {"summary": "You will definitely win your case. You paid for an item that never arrived.", "options": [],
           "uncertainties": [], "needs_lawyer": False, "lawyer_reason": None}
    s = session(FakeLLM(case=FULL_CASE, explain=bad))
    s.handle(STORY)
    r = s.handle("yes")
    assert "definitely win" not in r.text and "never arrived" in r.text and "Sources" in r.text
    assert "outcome_sentence_removed" in r.flags


def test_timeline_computed_in_code(rails):
    s = session(FakeLLM(case=FULL_CASE))  # complaint 2026-10-20, order 2026-10-05, today 2026-11-20
    s.handle(STORY)
    r = s.handle("yes")
    assert "Your timeline" in r.text
    assert "20 November 2026" in r.text and "reached the platform" in r.text and "counting from 20 November 2026" in r.text
    assert "05 October 2028" in r.text


def test_add_months_clamps_day():
    from datetime import date as D
    from haq.explainer import _add_months
    assert _add_months(D(2026, 1, 31), 1) == D(2026, 2, 28) and _add_months(D(2026, 10, 5), 24) == D(2028, 10, 5)


def test_no_doubled_punctuation_after_citation_rewrite():
    from haq.explainer import fix_limit_citations
    from haq.corpus import Chunk
    c = Corpus()
    chunks = [Chunk("S1", c.by_id["CPA2019-34"]), Chunk("S4", c.by_id["JUR2021-3"])]
    out = fix_limit_citations("Limit is fifty lakh rupees [S1], [S4], and more.", chunks)
    assert ",," not in out.replace(" ", "") and out.count("[") == 1


def test_retrieval_eval_final_recall_is_complete_and_no_irrelevant_ecommerce():
    from evals.retrieval_eval import run
    res = run()
    assert res["mean_final_recall"] == 1.0 and res["irrelevant_ecom_total"] == 0, res["rows"]
