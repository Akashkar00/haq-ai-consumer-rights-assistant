"""Offline tests for the vector path: fake embedder + in-memory Qdrant, no network."""
import hashlib

import pytest

from haq.corpus import Corpus
from haq.vectorstore import VectorRetriever, make_client

DIM = 64


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder: shared words give similar vectors."""
    model, dim = "fake", DIM

    def _vec(self, text):
        v = [0.0] * DIM
        for w in "".join(c.lower() if c.isalnum() else " " for c in text).split():
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
        return v

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


@pytest.fixture
def vr():
    c = Corpus(mode="bm25")
    return VectorRetriever(c.entries, FakeEmbedder(), client=make_client(":memory:")), c


def test_index_is_idempotent_and_search_finds_related_entry(vr):
    v, c = vr
    assert v.client.count(v.collection).count == len(c.entries)
    assert v.ensure_indexed() is False  # already indexed: no re-embedding
    top = [eid for eid, _ in v.search("limitation period two years complaint filed cause of action", 3)]
    assert "CPA2019-69" in top


def test_hybrid_ranking_uses_both_and_reports_mode(vr):
    v, c = vr
    hybrid = Corpus(vector=v.__class__(c.entries, FakeEmbedder(), client=v.client), mode="hybrid")
    chunks = hybrid.retrieve("refund defective goods seller", "defective_item", k=6, method="hybrid")
    assert hybrid.last_mode_used == "hybrid" and len(chunks) == 6


def test_vector_failure_falls_back_to_bm25(vr):
    v, c = vr

    class Broken(FakeEmbedder):
        def embed_query(self, text):
            raise RuntimeError("Vertex down")

    broken = VectorRetriever(c.entries, FakeEmbedder(), client=v.client)
    broken.embedder = Broken()
    corpus = Corpus(vector=broken, mode="hybrid")
    chunks = corpus.retrieve("refund for undelivered order", "non_delivery", k=6)
    assert corpus.last_mode_used == "bm25" and chunks


def test_default_mode_is_bm25_and_needs_no_network():
    c = Corpus()
    assert c.vector is None
    c.retrieve("refund", None)
    assert c.last_mode_used == "bm25"


def test_vector_mode_uses_vector_ranking(vr):
    v, c = vr
    corpus = Corpus(vector=VectorRetriever(c.entries, FakeEmbedder(), client=v.client), mode="vector")
    corpus.retrieve("limitation period two years", None, k=5)
    assert corpus.last_mode_used == "vector"
