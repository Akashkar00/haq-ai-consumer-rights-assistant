"""Verification gate for data/corpus.jsonl. Exit code 1 on any failure."""
import json
import re
import sys
from pathlib import Path

RAW = Path("data/raw_sources")
REQUIRED = ["id", "title", "source_type", "reference", "source_url", "retrieved_on", "verbatim_text",
            "plain_summary", "tags", "verified"]
norm = lambda t: re.sub(r"\s+", "", t).lower()
fails = []

entries = [json.loads(l) for l in open("data/corpus.jsonl")]
ids = [e["id"] for e in entries]
if len(ids) != len(set(ids)):
    fails.append("duplicate ids")
for e in entries:
    for k in REQUIRED:
        if not e.get(k) and e.get(k) is not False:
            fails.append(f"{e['id']}: missing {k}")
    if not e["source_url"].startswith("https://"):
        fails.append(f"{e['id']}: non-https source_url")
    raw = norm((RAW / e["source_file"]).read_text())
    # Verbatim text must appear in the saved raw source (header/margin noise lines are stripped on build).
    body = norm(e["verbatim_text"])
    if body not in raw:
        # tolerate stripped page-header lines inside the slice by checking in 60-char windows
        chunks = [body[i : i + 60] for i in range(0, len(body), 60)]
        missing = [c for c in chunks if len(c) > 20 and c not in raw]
        if missing:
            fails.append(f"{e['id']}: verbatim text not found in {e['source_file']}")

# Independent cross-check of the values most likely to be quoted to a user.
by_id = {e["id"]: e for e in entries}
pib = norm((RAW / "pib_jurisdiction_2021.txt").read_text())
for eid, phrase in [("JUR2021-3", "fifty lakh"), ("JUR2021-4", "two crore"), ("JUR2021-5", "two crore")]:
    if norm(phrase) not in norm(by_id[eid]["verbatim_text"]):
        fails.append(f"{eid}: expected '{phrase}'")
for needle in ["50lakhrupees", "2crorerupees"]:
    if needle not in pib:
        fails.append(f"PIB cross-check source missing {needle}")
if "twoyears" not in norm(by_id["CPA2019-69"]["verbatim_text"]):
    fails.append("CPA2019-69: expected 'two years'")
if "forty-eighthours" not in norm(by_id["ECOM2020-4-5"]["verbatim_text"]):
    fails.append("ECOM2020-4-5: expected 'forty-eight hours'")
if not all(e["volatile"] for e in entries if e["id"].startswith(("JUR", "NCH"))):
    fails.append("jurisdiction/NCH entries must be volatile")

print(f"{len(entries)} entries checked; {len(fails)} failures")
for f in fails:
    print(" FAIL:", f)
sys.exit(1 if fails else 0)
