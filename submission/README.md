# Haq: an AI helper for refund disputes in India

Kuku AI Generalist assignment, Problem 2 (Build an AI Lawyer).

## Form fields

| Field | Value |
|---|---|
| Name | Akash Kar |
| Roll number | (fill in) |
| Branch | (fill in) |
| Problem chosen | Problem 2: Build an AI Lawyer |
| Solution doc | `solution.pdf` (2 pages) |
| Prototype, live app | https://haq-1056072922203.us-central1.run.app |
| Prototype, code | https://github.com/Akashkar00/haq-ai-consumer-rights-assistant |
| Raw outputs | `raw_outputs/` in this folder (also in the repo under `submission/raw_outputs`) |
| Walkthrough video | not recorded |

The live app runs on Google Cloud Run with Gemini 3.8 Flash on Vertex AI, Vertex embeddings and Qdrant Cloud. There is also a lighter copy on Streamlit Community Cloud
(https://haq-consumer-rights-india.streamlit.app/) that uses Claude Haiku and keyword search only, because that host has no Google credentials. Each session is capped at 30 messages.
The first request after the app has been idle can take 20 to 40 seconds.

## What is in this folder

- `solution.pdf`: the write-up.
- `raw_outputs/`: unedited outputs of every evaluation run, failures included. Start with `raw_outputs/INDEX.md`.
- `test_cases.json`: the 13 test cases I wrote (inputs and what each one should do).
- `eval_notes/`: the evaluation report, my review notes with the judge's per-case issues, and the retrieval comparison.

## Run it yourself

```bash
git clone https://github.com/Akashkar00/haq-ai-consumer-rights-assistant && cd haq-ai-consumer-rights-assistant
uv sync && cp .env.example .env     # add ANTHROPIC_API_KEY; Vertex uses your gcloud login
uv run streamlit run app.py
```

Swapping the model is two lines in `.env` (`LLM_PROVIDER`, `LLM_MODEL`). `uv run python -m pytest` runs the 61 offline tests and `uv run python -m evals.run on` re-runs the 13 cases.

## Limits, in one place

Covers one kind of problem (online purchase refunds). No lawyer has reviewed the corpus or the answers. Next steps come from a fixed ladder, so usefulness is the weakest part (about 3 of 5 from the judge).
The corpus has 15 entries from the Consumer Protection Act 2019, the E-Commerce Rules 2020 and the 2021 Jurisdiction Rules. It has no filing fees, no e-Jagriti, and no case law.
