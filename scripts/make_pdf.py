from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

ss = getSampleStyleSheet()
H = ParagraphStyle("h", parent=ss["Heading2"], fontSize=11, spaceBefore=6, spaceAfter=2)
B = ParagraphStyle("b", parent=ss["BodyText"], fontSize=8.8, leading=11.2, spaceAfter=2)
doc = SimpleDocTemplate("submission/solution.pdf", pagesize=A4, leftMargin=16*mm, rightMargin=16*mm, topMargin=13*mm, bottomMargin=12*mm,
                        title="Haq: AI consumer-rights assistant (Kuku Problem 2)", author="Akash Kar")
S = [Paragraph("Haq (हक़): an AI assistant for consumer refund disputes in India", ss["Title"])]
sections = [
 ("Problem and scope", "Problem 2 asks for an AI lawyer. A general one would hallucinate law, so Haq does one thing: it helps a person with an everyday "
  "consumer refund dispute (not delivered, damaged, defective, wrong item, cancelled without refund, return refused). It turns their story into a "
  "confirmed case file, explains their position from a small verified set of official sources, lays out an escalation path, and drafts a grievance letter. "
  "It says what it does not know, and sends the user to an advocate when the facts call for it."),
 ("How it works", "Streamlit chat over a state machine: intake, triage, up to three rounds of follow-up questions, confirmation, explanation, optional draft. "
  "LLM: Gemini 3.8 Flash on Vertex AI, with an automatic Anthropic fallback (tested live). The model only extracts facts, phrases questions, writes an explanation "
  "from retrieved sources and a short facts paragraph; everything that must be right is produced or checked by code."),
 ("Knowledge base", "15 entries sliced verbatim from the saved official texts: Consumer Protection Act 2019 (ss. 2(7), 2(10), 2(11), 2(47), 34, 35, 69), "
  "E-Commerce Rules 2020 (rr. 4(4), 4(5), 4(10), 6(3)), the 2021 Jurisdiction Rules (50 lakh / 2 crore limits, cross-checked against the PIB release) and the "
  "National Consumer Helpline page. Each entry has a URL, retrieval date and a volatile flag. Anything unverified (filing fees, e-Jagriti, the 2026 e-commerce "
  "amendment's commencement date) is excluded and listed in EXCLUDED.md. No case law is included."),
 ("Hallucination and safety controls", "(1) Code-level verifier strips any section, Act or case name not in the retrieved set. (2) Source list and escalation ladder are rendered from corpus "
  "metadata, not by the model. (3) Extractor drops any amount, order ID or ticket ID the user never wrote. (4) Draft is template-first and every amount, date and ID is "
  "checked against the confirmed facts. (5) Urgent signals (police, FIR, threats, injury, self-harm) escalate by fixed rules and cannot be downgraded by the model. "
  "(6) Outcome questions are refused by rule; requests to cite unknown sections are refused. (7) PII masked before any LLM call. "
  "(8) NeMo Guardrails wraps every turn with input and output rails (Colang flows calling the same Python checks); GUARDRAILS=off runs the same policies without it."),
 ("Evaluation (13 cases, raw outputs saved)", "Final code: 13/13 automatic checks with the NeMo rails on and 13/13 with rails off (no fallback calls). An independent-model judge (Claude Haiku reading full "
  "transcripts and sources) scored grounding 4.15, calibration 4.00, usefulness 2.77, safety 4.54 out of 5; my own earlier self-review was higher, so the judge is the conservative number. "
  "Checks found and fixed real bugs: explain step crashed on truncated JSON; the Anthropic fallback call was broken; e-commerce rules were cited for an offline purchase; a stalled Vertex call hung the UI (60s timeouts added); "
  "one bad sentence used to replace a whole answer. 50 offline tests pass; the UI was driven in Chrome through the full journey and the edge cases; Hindi, long and concurrent sessions were stress-tested."),
 ("Honest limits", "13 rule-based cases and no second reviewer: this shows the flows work, not that the system is reliable in general. No human or lawyer has reviewed it. Usefulness is the weakest area (generic next steps). Rails on vs off made no measurable difference here "
  "(same functions underneath). The verifier is regex-based and will not catch a paraphrased wrong claim. One domain, English-first, not lawyer-reviewed, values can change, drafts need "
  "human review, no persistence. NeMo's LLMRails class is deprecated in 0.25 (works, pinned)."),
 ("Run it", "uv sync; cp .env.example .env; gcloud auth application-default login; uv run streamlit run app.py. Tests: uv run python -m pytest. Evals: uv run python -m evals.run on. "
  "Files: README.md, docs/EVAL_REPORT.md, raw_outputs/, data/SOURCES.md."),
]
for h, t in sections:
    S += [Paragraph(h, H), Paragraph(t, B)]
doc.build(S)
