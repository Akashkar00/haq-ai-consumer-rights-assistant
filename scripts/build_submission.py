"""Assemble the submission folder: PDF, raw outputs (unedited copies of every run) with an index, test cases, eval notes."""
import json
import shutil
from pathlib import Path

SUB = Path("submission")
RAW = SUB / "raw_outputs"
if RAW.exists():
    shutil.rmtree(RAW)
shutil.copytree("raw_outputs", RAW)          # byte-for-byte copies, failures included
shutil.copy("evals/test_cases.json", SUB / "test_cases.json")
notes = SUB / "eval_notes"
notes.mkdir(exist_ok=True)
for src in ["docs/EVAL_REPORT.md", "evals/manual_review.md", "evals/retrieval_results.json"]:
    shutil.copy(src, notes / Path(src).name)

NOTES = {
    "20261120_235119_rails-on": "First run. 9 of 13 passed: one real crash (truncated JSON in the explainer), one test-script error, two checks of mine that were too strict. Kept on purpose.",
    "20261121_022617_rails-on": "FINAL, guardrails on, vector retrieval (Vertex embeddings + Qdrant). Judge scores in judge_scores.json.",
    "20261121_024025_rails-off": "FINAL, guardrails off, vector retrieval.",
    "20261121_015214_rails-on": "Keyword retrieval (BM25) after the timeline section was added. Judge scores in judge_scores.json.",
    "20261121_015814_rails-off": "Keyword retrieval, guardrails off.",
}
rows = []
for d in sorted(p for p in RAW.iterdir() if p.is_dir()):
    s = json.load(open(d / "summary.json"))
    judge = ""
    if (d / "judge_scores.json").exists():
        m = json.load(open(d / "judge_scores.json"))["mean"]
        judge = f"G {m['grounding']} / C {m['calibration']} / U {m['usefulness']} / S {m['safety']}"
    rows.append(f"| `{d.name}` | {s['mode']} | {s['passed']}/{s['total']} | {judge} | {NOTES.get(d.name, '')} |")
(RAW / "INDEX.md").write_text(
    "# Raw outputs\n\nUnedited outputs of running Haq on my 13 test cases (`../test_cases.json`). Each run folder has one JSON file per case "
    "(the scripted user turns, every reply, the draft letter, the case file the model built, the checks and whether it passed) and a `summary.json`. "
    "Nothing here was edited by hand, and failing runs are kept.\n\n"
    "Judge columns (where present): G grounding, C calibration, U usefulness, S safety, each 1 to 5, scored by Claude Haiku reading the full transcript and the sources.\n\n"
    "| Run | Guardrails | Passed | Judge means | Note |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
print(f"copied {len(rows)} runs")
