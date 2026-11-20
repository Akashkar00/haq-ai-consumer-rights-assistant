"""Run the eval cases through the real pipeline and save every raw output (including failures)."""
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

from haq import guard
from haq.corpus import Corpus
from haq.llm.base import get_client
from haq.orchestrator import Session
from haq.verifier import verify

TODAY = date(2026, 11, 20)


def judge(case, replies, draft, final_state, flags, corpus, per_turn_flags):
    e, text = case["expect"], "\n".join(replies)
    checks = {}
    checks["final_state"] = final_state in e["final_state"]
    for s in e.get("must_contain", []):
        checks[f"contains:{s}"] = s.lower() in text.lower() or (draft and s in draft)
    if e.get("must_contain_any"):
        checks["contains_any"] = any(s.lower() in text.lower() for s in e["must_contain_any"])
    for pat in e.get("must_not_match", []):
        checks[f"absent:{pat}"] = not re.search(pat, text, re.I)
    if e.get("flags_any"):
        checks["flags_any"] = any(f in flags for f in e["flags_any"])
    if "max_question_marks" in e:
        checks["<=3 questions"] = text.count("?") <= e["max_question_marks"]
    # Citation integrity: any [S#] / Section / Act mention in replies must survive the verifier with all
    # corpus refs allowed. "[S" tags are checked for range separately (S1..S12).
    ids = {str(i) for i in range(1, 13)}
    # Refusals that quote the user's own request (flag unverified_section_request) are not claims by Haq.
    checkable = "\n".join(r for r, f in zip(replies, per_turn_flags) if "unverified_section_request" not in f)
    checks["no_unverified_citation"] = not verify(checkable, ids, corpus.allowed_refs()).modified
    return checks


def main(mode):
    import os
    os.environ["GUARDRAILS"] = mode
    corpus, llm = Corpus(), get_client()
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_rails-{mode}"
    out = Path("raw_outputs") / run_id
    out.mkdir(parents=True)
    cases = json.load(open("evals/test_cases.json"))
    rows = []
    for c in cases:
        s, replies, flags, per_turn, t0, err = Session(llm, corpus, TODAY), [], [], [], time.time(), None
        try:
            for turn in c["turns"]:
                r = s.handle(turn)
                replies.append(r.text)
                flags += r.flags
                per_turn.append(r.flags)
        except Exception as ex:
            err = f"{type(ex).__name__}: {ex}"
        draft = s.last_draft
        checks = judge(c, replies, draft, s.state, flags, corpus, per_turn) if not err else {"no_crash": False}
        passed = all(checks.values())
        rec = {"id": c["id"], "name": c["name"], "turns": c["turns"], "replies": replies, "draft": draft,
               "final_state": s.state, "flags": flags, "case_file": json.loads(s.case.model_dump_json()),
               "checks": checks, "passed": passed, "error": err, "seconds": round(time.time() - t0, 1),
               "provider": llm.last_provider}
        (out / f"{c['id']}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False))
        rows.append(rec)
        print(f"{c['id']} {'PASS' if passed else 'FAIL'} state={s.state} {rec['seconds']}s "
              + ("" if passed else str([k for k, v in checks.items() if not v] or err)))
    summary = {"run_id": run_id, "mode": mode, "passed": sum(r["passed"] for r in rows), "total": len(rows),
               "fallback_used": sum(r["provider"] == "fallback" for r in rows)}
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(summary)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "on")
