"""Qdrant vector store for the corpus. Qdrant Cloud/server if QDRANT_URL is set, else local on-disk mode."""
import hashlib
import logging
import os
from pathlib import Path

from haq import config

log = logging.getLogger("haq.vectorstore")
LOCAL_PATH = config.ROOT / "data" / "qdrant_local"


def doc_text(entry: dict) -> str:
    """What gets embedded for a corpus entry (kept short: title, my summary, then the official text)."""
    return f"{entry['title']}\n{entry['plain_summary']}\n{entry['verbatim_text']}"[:3000]


def make_client(path: str | None = None):
    from qdrant_client import QdrantClient

    if path == ":memory:":
        return QdrantClient(":memory:")
    url = os.getenv("QDRANT_URL")
    if url:
        return QdrantClient(url=url, api_key=os.getenv("QDRANT_API_KEY") or None, timeout=30)
    Path(path or LOCAL_PATH).mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(path or LOCAL_PATH))


class VectorRetriever:
    def __init__(self, entries: list[dict], embedder, client=None):
        self.entries, self.embedder = entries, embedder
        self.client = client or make_client()
        digest = hashlib.sha1("".join(doc_text(e) for e in entries).encode()).hexdigest()[:8]
        base = os.getenv("QDRANT_COLLECTION", "haq_corpus")
        self.collection = f"{base}_{getattr(embedder, 'model', 'embed').replace('/', '_')}_{embedder.dim}_{digest}"
        self.ensure_indexed()

    def ensure_indexed(self) -> bool:
        """Create and fill the collection if it does not exist for this corpus + model. Returns True if it indexed."""
        from qdrant_client.models import Distance, PointStruct, VectorParams

        if self.client.collection_exists(self.collection) and self.client.count(self.collection).count == len(self.entries):
            return False
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(self.collection, vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE))
        vecs = self.embedder.embed_documents([doc_text(e) for e in self.entries])
        self.client.upsert(self.collection, points=[
            PointStruct(id=i, vector=v, payload={"entry_id": e["id"]}) for i, (e, v) in enumerate(zip(self.entries, vecs))])
        log.info("indexed %d corpus entries into Qdrant collection %s", len(self.entries), self.collection)
        return True

    def search(self, query: str, k: int | None = None) -> list[tuple[str, float]]:
        """Return (entry_id, cosine score) best first."""
        qv = self.embedder.embed_query(query)
        res = self.client.query_points(self.collection, query=qv, limit=k or len(self.entries), with_payload=True)
        return [(p.payload["entry_id"], p.score) for p in res.points]
