"""Vertex AI text embeddings (google-genai). Documents and queries use different task types."""
import os

from haq import config  # noqa: F401  (loads .env)


class VertexEmbedder:
    def __init__(self, model: str | None = None, dim: int | None = None, location: str | None = None):
        from google import genai
        from google.genai import types

        self.model = model or os.getenv("EMBED_MODEL", "gemini-embedding-001")
        self.dim = dim or int(os.getenv("EMBED_DIM", "768"))
        self._types = types
        # Same project as the LLM; embeddings are served from a regional endpoint.
        self.client = genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                                   location=location or os.getenv("EMBED_LOCATION", "us-central1"),
                                   http_options=types.HttpOptions(timeout=int(os.getenv("LLM_TIMEOUT_S", "60")) * 1000))

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        cfg = self._types.EmbedContentConfig(task_type=task, output_dimensionality=self.dim)
        out = []
        for i in range(0, len(texts), 20):  # stay well under the per-request input limit
            r = self.client.models.embed_content(model=self.model, contents=texts[i : i + 20], config=cfg)
            out += [e.values for e in r.embeddings]
        return out

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]
