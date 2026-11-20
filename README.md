# Haq (हक़): a consumer-refund helper for India

Haq turns a messy consumer refund story into a structured case file, explains the user's position using
only a small verified corpus of official Indian sources, and drafts a grievance letter from the confirmed
facts. It is general legal information, not legal advice. Scope: one problem type (online/offline purchase
not delivered, faulty, wrong, cancelled without refund, or return refused).

Repo: https://github.com/Akashkar00/haq-ai-consumer-rights-assistant
Live demo: https://haq-consumer-rights-india.streamlit.app/ (Anthropic Haiku, 30-message cap per session)

## Run

```bash
uv sync
cp .env.example .env            # then fill ANTHROPIC_API_KEY; Vertex uses your gcloud login
gcloud auth application-default login   # once, for Vertex AI
uv run streamlit run app.py     # UI
uv run python -m haq.cli        # terminal fallback
```

LLMs: `gemini-3.8-flash` on Vertex AI (primary, `GOOGLE_CLOUD_LOCATION=global`), `claude-haiku-5-5` via the
Anthropic API as automatic fallback after two failed primary attempts. Change either with env vars. Requests time out after 60s (`LLM_TIMEOUT_S`) so a stalled provider hands over to the fallback.
`GUARDRAILS=on|off` toggles the NeMo Guardrails layer (the same policies run either way).

## Verify

```bash
uv run python -m pytest -q                 # 37 offline tests (no API key needed)
RUN_LIVE=1 uv run python -m pytest -q      # + live Vertex and Anthropic calls
uv run python scripts/verify_corpus.py     # corpus verbatim text vs saved official sources
uv run python -m evals.run on              # 13 eval cases, raw outputs in raw_outputs/<run_id>/
```

Retrieval: Vertex AI `gemini-embedding-001` + Qdrant (`RETRIEVAL_MODE=vector|hybrid|bm25`, BM25 fallback). Index with `uv run python scripts/index_corpus.py`; set `QDRANT_URL` (use `:443`) and `QDRANT_API_KEY` for Qdrant Cloud, or leave them unset for a local on-disk store.

Layout: `haq/` app code · `haq/guardrails/` NeMo config, Colang flows, actions · `data/corpus.jsonl` verified
corpus (`SOURCES.md`, `EXCLUDED.md`, `raw_sources/`) · `evals/` · `tests/` · `docs/` · `plan.md`.

## Limits (read before relying on it)

Single domain; English-first (Hindi script and Hinglish stories were tested; the confirmation summary adds a Hinglish version); not reviewed by a lawyer; no case
law; value limits, fees and e-commerce rules can change (entries are flagged `volatile`); the 2026 e-commerce
amendment's commencement date could not be confirmed; drafts need human review; no persistence.
