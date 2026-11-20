# Architecture

```
user → [NeMo input rails: mask PII · urgent · injection] → orchestrator (state machine)
     → extractor / gaps / triage / retriever / explainer / drafter (LLM via FallbackClient)
     → [NeMo output rails: verify citations · no outcome promise · no lawyer impersonation · disclaimer] → UI
```

- **Rails** are Colang flows that call Python actions wrapping `safety.py`, `verifier.py`, `redact.py`, `policy.py`.
  The same functions run when `GUARDRAILS=off`, so every safety property is unit-testable without the framework.
- **Orchestrator** states: INTAKE → GATHER (≤3 question rounds) → CONFIRM → ACTION_SELECT → REVIEW; plus ESCALATE and
  OUT_OF_SCOPE. Urgency is re-checked on every message. Outcome questions and requests to cite unknown sections are
  answered by fixed rules before any LLM call.
- **Extractor** validates model JSON with Pydantic (one repair retry) and drops any amount, order ID or ticket ID the
  user never wrote (`extractor.ground`).
- **Retriever**: BM25 over 15 corpus entries plus the entries the options ladder cites. **Explainer**: the LLM writes
  the summary and detail; the ladder and the source list are produced by code from corpus metadata; the whole text goes
  through the verifier, which strips any section, Act or case name not in the retrieved set.
- **Drafter**: Jinja2 template fills facts from the `CaseFile`; the LLM writes only the facts paragraph;
  `consistency.py` checks every amount, date and ID in the draft against the `CaseFile`.
- **LLM layer**: `VertexClient` (gemini-3.8-flash, global endpoint) → `AnthropicClient` fallback.
