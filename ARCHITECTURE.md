# Haq: architecture

Haq is a legal-information assistant for Indian consumers who want a refund. It collects the facts of a complaint, explains which rights apply using a verified corpus, and drafts a grievance letter. It does not predict outcomes and does not act as a lawyer.

This page is the walkthrough for the video. Each section is one diagram.

## 1. The whole system

```mermaid
flowchart LR
    U([User]) --> UI["Streamlit chat UI<br/>app.py"]
    UI --> ORCH["Orchestrator<br/>state machine"]

    ORCH --> IN["Input rails<br/>PII mask, urgent, injection"]
    IN --> EXT["Extractor<br/>fills the case file"]
    EXT --> GAP["Gap finder<br/>what is still missing"]
    GAP --> RET["Retriever<br/>BM25 + vector"]
    RET --> EXP["Explainer<br/>LLM answer with S-tags"]
    EXP --> OUT["Output rails<br/>verify citations, block promises"]
    OUT --> UI

    RET --- CORP[("Corpus<br/>15 verbatim legal entries")]
    RET --- QD[("Qdrant Cloud<br/>768-dim vectors")]
    EXP --- LLM["LLM layer<br/>Gemini on Vertex, Claude fallback"]
    EXT --- LLM
    ORCH --> DRAFT["Drafter<br/>Jinja2 letter template"]
```

Every user message goes through the same pipeline. The LLM never talks to the user directly. Code checks it on the way in and on the way out.

## 2. One turn, step by step

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Streamlit
    participant O as Orchestrator
    participant G as Guardrails
    participant R as Retriever
    participant L as LLM
    U->>UI: complaint text
    UI->>O: message
    O->>G: check_input
    G-->>O: masked text, flags
    alt urgent or out of scope
        O-->>UI: fixed safe response
    else normal
        O->>L: extract facts to case file
        L-->>O: JSON, grounded by code
        O->>R: query from case file
        R-->>O: top sources
        O->>L: explain using only these sources
        L-->>O: draft answer
        O->>G: check_output
        G-->>O: cleaned answer plus disclaimer
        O-->>UI: stream word by word
    end
    UI-->>U: answer with source tags
```

## 3. Conversation states

```mermaid
stateDiagram-v2
    [*] --> INTAKE
    INTAKE --> GATHER: facts missing
    GATHER --> GATHER: ask again, max 3 rounds
    GATHER --> CONFIRM: enough facts
    INTAKE --> CONFIRM: complete first time
    CONFIRM --> ACTION_SELECT: user confirms
    CONFIRM --> GATHER: user corrects
    ACTION_SELECT --> REVIEW: explanation or letter
    REVIEW --> DONE: user is finished
    REVIEW --> GATHER: new details
    INTAKE --> ESCALATE: urgent trigger
    GATHER --> ESCALATE: urgent trigger
    INTAKE --> OUT_OF_SCOPE: not a refund issue
    ESCALATE --> [*]
    OUT_OF_SCOPE --> [*]
    DONE --> [*]
```

Urgent cases (threats, police, large fraud) leave the normal path and get a human-help message instead of a legal walkthrough.

## 4. Guardrails

```mermaid
flowchart TB
    subgraph IN["Input rails"]
        direction TB
        I1["Mask email, Aadhaar, card, phone"] --> I2["Urgent or safety check"] --> I3["Prompt-injection check"]
    end
    subgraph OUT["Output rails"]
        direction TB
        O1["Strip unverified S-tags, sections, Act and case names"] --> O2["Remove outcome promises<br/>sentence by sentence"] --> O3["Block lawyer impersonation"] --> O4["Append disclaimer"]
    end
    MSG([User message]) --> IN --> CORE["Pipeline"] --> OUT --> ANS([Answer])
    NEMO["NeMo Guardrails<br/>Colang flows + Python actions"] -.runs.-> IN
    NEMO -.runs.-> OUT
    OFF["GUARDRAILS=off<br/>same policies, no NeMo"] -.alternative.-> NEMO
```

The same policy code runs with or without NeMo, so the evals can compare rails on and off.

## 5. Retrieval and the corpus

```mermaid
flowchart LR
    subgraph BUILD["Build time"]
        PDF["Official PDFs<br/>CPA 2019, E-Commerce Rules 2020,<br/>Jurisdiction Rules 2021, NCH"] --> SLICE["build_corpus.py<br/>slice verbatim text"] --> JSONL[("corpus.jsonl<br/>15 entries")]
        JSONL --> VER["verify_corpus.py<br/>re-check against PDFs"]
        JSONL --> EMB["Vertex gemini-embedding-001<br/>RETRIEVAL_DOCUMENT"] --> QD[("Qdrant collection")]
    end
    subgraph RUN["Query time"]
        Q["Case file to query"] --> B["BM25 ranking"]
        Q --> V["Vector ranking<br/>RETRIEVAL_QUERY"]
        B --> F["RRF fusion, k=60"]
        V --> F
        F --> REQ["Add required entries<br/>for this issue type"]
        REQ --> TOP["Sources S1..Sn"]
    end
    QD --> V
    JSONL --> B
    V -.fails.-> B
```

Retrieval mode is `bm25`, `vector` or `hybrid`. If Qdrant or the embedding call fails, it drops to BM25 on its own. A small hand-written table adds the entries a case must have (for example Rule 6(3) for damaged goods), because ranking alone missed it in testing.

## 6. LLM layer and fallback

```mermaid
flowchart LR
    CALL["Pipeline call"] --> FB["FallbackClient"]
    FB -->|try, 2 retries| VX["Vertex AI<br/>gemini-3.8-flash"]
    VX -->|timeout or error| AN["Anthropic<br/>claude-haiku-5-5"]
    VX -->|ok| RES["Response"]
    AN --> RES
    RES --> LP["last_provider recorded<br/>shown in logs and evals"]
```

## 7. Where it runs

```mermaid
flowchart TB
    DEV["Git push to GitHub"] --> CB["Cloud Build<br/>Dockerfile, python 3.12 + uv"]
    CB --> CR["Cloud Run<br/>2Gi, max 2 instances"]
    SM["Secret Manager<br/>Anthropic key, Qdrant key"] --> CR
    SA["Service account haq-run<br/>aiplatform.user"] --> CR
    CR --> VERT["Vertex AI<br/>Gemini + embeddings"]
    CR --> QC[("Qdrant Cloud<br/>haq-rag")]
    CR --> ANT["Anthropic API<br/>fallback"]
    USER([Public user]) --> CR
```

Cloud Run is the only deployment.

## 8. How it was tested

```mermaid
flowchart LR
    TC["13 test cases<br/>evals/test_cases.json"] --> RUN["run.py<br/>rails on and off"]
    RUN --> RAW[("raw_outputs/")]
    RAW --> AUTO["Automatic checks<br/>13 of 13 pass"]
    RAW --> JUDGE["judge.py<br/>Claude Haiku scores Gemini output"]
    JUDGE --> SC["grounding, calibration,<br/>usefulness, safety"]
    CORP2[("corpus + gold sources")] --> RE["retrieval_eval.py<br/>ranker-only recall"]
    RE --> RC["BM25 0.75, vector 0.84, hybrid 0.80"]
    UT["pytest<br/>61 pass, 3 live skipped"] --> AUTO
```

## 9. What it will not do

- It gives no outcome predictions and no "you will win" language.
- It does not impersonate a lawyer or file anything for the user.
- It cites only entries that exist in the corpus. Anything else is stripped.
- It escalates threats and large-value fraud instead of explaining.
- It has not had a real lawyer review. Usefulness scores about 3 out of 5 because the escalation ladder is fixed.

## Key files

| Area | File |
|---|---|
| UI | `app.py` |
| Flow | `haq/orchestrator.py`, `haq/gaps.py`, `haq/triage.py` |
| Facts | `haq/schema.py`, `haq/extractor.py`, `haq/consistency.py` |
| Retrieval | `haq/corpus.py`, `haq/embeddings.py`, `haq/vectorstore.py` |
| Answer | `haq/explainer.py`, `haq/drafter.py`, `haq/prompts/` |
| Safety | `haq/guard.py`, `haq/guardrails/`, `haq/policy.py`, `haq/verifier.py`, `haq/redact.py` |
| LLMs | `haq/llm/` |
| Corpus | `data/corpus.jsonl`, `scripts/build_corpus.py` |
| Evals | `evals/`, `tests/` |
