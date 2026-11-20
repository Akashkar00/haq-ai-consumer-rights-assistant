import json
import logging
import os
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from haq.config import CORPUS_PATH

log = logging.getLogger("haq.corpus")
RRF_K = 60  # reciprocal-rank-fusion constant
CORE_TAGS = {"jurisdiction", "limitation", "filing"}


def _tok(s: str) -> list[str]:
    return [w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(w) > 2]


@dataclass
class Chunk:
    sid: str  # "S1".. assigned per retrieval
    entry: dict


class Corpus:
    def __init__(self, path=CORPUS_PATH, vector=None, mode: str | None = None):
        self.entries = [json.loads(l) for l in open(path) if l.strip()]
        self.mode = (mode or os.getenv("RETRIEVAL_MODE", "bm25")).lower()  # bm25 | vector | hybrid
        self.vector = vector
        self.last_mode_used = None  # set by the first retrieval
        if self.vector is None and self.mode in ("vector", "hybrid"):
            try:
                from haq.embeddings import VertexEmbedder
                from haq.vectorstore import VectorRetriever
                self.vector = VectorRetriever(self.entries, VertexEmbedder())
            except Exception as e:  # no credentials, Qdrant unreachable, ...: keep working on BM25
                log.warning("vector retrieval unavailable, using BM25 only: %s", str(e)[:200])
        self.by_id = {e["id"]: e for e in self.entries}
        self._bm25 = BM25Okapi([_tok(e["title"] + " " + e["plain_summary"] + " " + e["verbatim_text"]) for e in self.entries])

    def allowed_refs(self, entries: list[dict] | None = None) -> set[str]:
        refs: set[str] = set()
        for e in entries or self.entries:
            refs.update(e.get("refs", []))
            refs.add(e["title"].split(" – ")[0])  # act / rules name
        return refs

    def bm25_ranking(self, query: str) -> list[int]:
        scores = self._bm25.get_scores(_tok(query))
        return sorted(range(len(self.entries)), key=lambda i: scores[i], reverse=True)

    def vector_ranking(self, query: str) -> list[int]:
        idx = {e["id"]: i for i, e in enumerate(self.entries)}
        return [idx[eid] for eid, _ in self.vector.search(query)]

    def ranking(self, query: str, method: str = "auto") -> list[int]:
        """method: bm25 | vector | hybrid | auto (follow RETRIEVAL_MODE; BM25 whenever no vector store is available)."""
        if method == "auto":
            method = "bm25" if self.vector is None else ("hybrid" if self.mode == "hybrid" else "vector")
        if method == "bm25" or self.vector is None:
            self.last_mode_used = "bm25"
            return self.bm25_ranking(query)
        try:
            v = self.vector_ranking(query)
        except Exception as e:  # embedding or Qdrant call failed at query time
            log.warning("vector search failed, falling back to BM25: %s", str(e)[:200])
            self.last_mode_used = "bm25"
            return self.bm25_ranking(query)
        if method == "vector":
            self.last_mode_used = "vector"
            return v
        b = self.bm25_ranking(query)
        fused: dict[int, float] = {}
        for ranking in (b, v):
            for rank, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
        self.last_mode_used = "hybrid"
        return sorted(fused, key=fused.get, reverse=True)

    def retrieve(self, query: str, issue_type: str | None, k: int = 6, exclude_tag: str | None = None,
                 method: str = "auto") -> list[Chunk]:
        ranked = [i for i in self.ranking(query, method) if not (exclude_tag and exclude_tag in self.entries[i]["tags"])]
        picked: list[int] = []
        for i, e in enumerate(self.entries):  # core jurisdiction / limitation / filing entries always included
            if CORE_TAGS & set(e["tags"]) and (issue_type is None or issue_type in e["tags"]) and not e["id"].startswith(("JUR2021-4", "JUR2021-5")):
                picked.append(i)
        for i in ranked:
            e = self.entries[i]
            if i not in picked and (issue_type is None or issue_type in e["tags"]):
                picked.append(i)
            if len(picked) >= k:
                break
        return [Chunk(f"S{n}", self.entries[i]) for n, i in enumerate(picked[:k], start=1)]
