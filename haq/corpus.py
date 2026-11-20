import json
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from haq.config import CORPUS_PATH

CORE_TAGS = {"jurisdiction", "limitation", "filing"}


def _tok(s: str) -> list[str]:
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(w) > 2]


@dataclass
class Chunk:
    sid: str  # "S1".. assigned per retrieval
    entry: dict


class Corpus:
    def __init__(self, path=CORPUS_PATH):
        self.entries = [json.loads(l) for l in open(path) if l.strip()]
        self.by_id = {e["id"]: e for e in self.entries}
        self._bm25 = BM25Okapi([_tok(e["title"] + " " + e["plain_summary"] + " " + e["verbatim_text"]) for e in self.entries])

    def allowed_refs(self, entries: list[dict] | None = None) -> set[str]:
        refs: set[str] = set()
        for e in entries or self.entries:
            refs.update(e.get("refs", []))
            refs.add(e["title"].split(" – ")[0])  # act / rules name
        return refs

    def retrieve(self, query: str, issue_type: str | None, k: int = 6, exclude_tag: str | None = None) -> list[Chunk]:
        scores = self._bm25.get_scores(_tok(query))
        for i, e in enumerate(self.entries):
            if exclude_tag and exclude_tag in e["tags"]:
                scores[i] = -1e9
        ranked = sorted(range(len(self.entries)), key=lambda i: scores[i], reverse=True)
        picked: list[int] = []
        for i, e in enumerate(self.entries):  # core jurisdiction / limitation / filing entries always included
            if CORE_TAGS & set(e["tags"]) and (issue_type is None or issue_type in e["tags"]) and not e["id"].startswith(("JUR2021-4", "JUR2021-5")):
                picked.append(i)
        for i in ranked:
            e = self.entries[i]
            if i not in picked and scores[i] > -1e8 and (issue_type is None or issue_type in e["tags"]):
                picked.append(i)
            if len(picked) >= k:
                break
        return [Chunk(f"S{n}", self.entries[i]) for n, i in enumerate(picked[:k], start=1)]
