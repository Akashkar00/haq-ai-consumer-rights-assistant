"""Embed the corpus with Vertex AI and (re)index it into Qdrant. Safe to re-run (skips if already indexed).

Qdrant Cloud/server: set QDRANT_URL and QDRANT_API_KEY. Otherwise a local on-disk store in data/qdrant_local is used.
"""
from haq import config  # noqa: F401
from haq.corpus import Corpus
from haq.embeddings import VertexEmbedder
from haq.vectorstore import VectorRetriever, make_client
import os

corpus = Corpus(mode="bm25")
emb = VertexEmbedder()
vr = VectorRetriever(corpus.entries, emb, client=make_client())
where = os.getenv("QDRANT_URL") or "local on-disk (data/qdrant_local)"
print(f"collection {vr.collection} at {where}: {vr.client.count(vr.collection).count} vectors, model {emb.model}, dim {emb.dim}")
for q in ["seller refuses to refund a defective product", "how long do I have to file a complaint"]:
    print(q, "->", [(i, round(s, 3)) for i, s in vr.search(q, 3)])
