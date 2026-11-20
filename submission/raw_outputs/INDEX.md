# Raw outputs

Unedited outputs of running Haq on my 13 test cases (`../test_cases.json`). Each run folder has one JSON file per case (the scripted user turns, every reply, the draft letter, the case file the model built, the checks and whether it passed) and a `summary.json`. Nothing here was edited by hand, and failing runs are kept.

Judge columns (where present): G grounding, C calibration, U usefulness, S safety, each 1 to 5, scored by Claude Haiku reading the full transcript and the sources.

| Run | Guardrails | Passed | Judge means | Note |
|---|---|---|---|---|
| `20261120_235119_rails-on` | on | 9/13 |  | First run. 9 of 13 passed: one real crash (truncated JSON in the explainer), one test-script error, two checks of mine that were too strict. Kept on purpose. |
| `20261120_235546_rails-on` | on | 13/13 |  |  |
| `20261121_000045_rails-off` | off | 13/13 |  |  |
| `20261121_000659_rails-on` | on | 13/13 |  |  |
| `20261121_001103_rails-on` | on | 13/13 |  |  |
| `20261121_001431_rails-off` | off | 13/13 |  |  |
| `20261121_002438_rails-on` | on | 13/13 |  |  |
| `20261121_002740_rails-off` | off | 13/13 |  |  |
| `20261121_003251_rails-on` | on | 13/13 | G 3.54 / C 3.92 / U 2.92 / S 4.15 |  |
| `20261121_003600_rails-off` | off | 13/13 |  |  |
| `20261121_004146_rails-on` | on | 13/13 | G 4.15 / C 4.0 / U 3.0 / S 4.46 |  |
| `20261121_004615_rails-off` | off | 13/13 |  |  |
| `20261121_011447_rails-on` | on | 13/13 | G 4.15 / C 4.0 / U 2.77 / S 4.54 |  |
| `20261121_012448_rails-off` | off | 13/13 |  |  |
| `20261121_013551_rails-on` | on | 13/13 | G 3.92 / C 3.92 / U 3.0 / S 4.38 |  |
| `20261121_014344_rails-off` | off | 13/13 |  |  |
| `20261121_015214_rails-on` | on | 13/13 | G 4.15 / C 4.0 / U 2.92 / S 4.31 | Keyword retrieval (BM25) after the timeline section was added. Judge scores in judge_scores.json. |
| `20261121_015814_rails-off` | off | 13/13 |  | Keyword retrieval, guardrails off. |
| `20261121_020721_rails-on` | on | 13/13 | G 4.0 / C 3.77 / U 3.08 / S 4.62 |  |
| `20261121_021317_rails-off` | off | 13/13 |  |  |
| `20261121_022617_rails-on` | on | 13/13 | G 3.92 / C 3.92 / U 3.23 / S 4.46 | FINAL, guardrails on, vector retrieval (Vertex embeddings + Qdrant). Judge scores in judge_scores.json. |
| `20261121_024025_rails-off` | off | 13/13 |  | FINAL, guardrails off, vector retrieval. |
