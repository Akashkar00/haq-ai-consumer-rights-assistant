"""Build submission/solution.pdf (max 2 pages). Plain characters only: Helvetica cannot draw the rupee sign."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK, MUTED, RULE = colors.HexColor("#1b1f24"), colors.HexColor("#5a6270"), colors.HexColor("#c9ced6")
body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.3, leading=12.2, textColor=INK, alignment=TA_LEFT, spaceAfter=2.6)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=9, bulletIndent=0, spaceAfter=1.6)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=INK, spaceAfter=1)
sub = ParagraphStyle("sub", parent=body, textColor=MUTED, fontSize=8.8, leading=11.5, spaceAfter=3)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.8, leading=13.5, textColor=INK, spaceBefore=7, spaceAfter=2.5)
cell = ParagraphStyle("cell", parent=body, fontSize=8.7, leading=11, spaceAfter=0)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold")

P = lambda t, s=body: Paragraph(t, s)
B = lambda t: Paragraph(t, bullet, bulletText="•")


def table(rows, widths, header=True):
    t = Table([[Paragraph(c, cellb if (header and i == 0) else cell) for c in r] for i, r in enumerate(rows)], colWidths=widths, repeatRows=1)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f5")))
    t.setStyle(TableStyle(st))
    return t


W = A4[0] - 30 * mm - 12  # the page frame pads 6pt on each side; tables must fit inside it
S = []
S += [P("Haq: an AI helper for refund disputes in India", h1),
      P("Kuku AI Generalist assignment, Problem 2 (Build an AI Lawyer). Akash Kar.<br/>"
        "Live app: https://haq-1056072922203.us-central1.run.app<br/>"
        "Code: https://github.com/Akashkar00/haq-ai-consumer-rights-assistant", sub)]

S += [P("What I picked and why", h2),
      P("I picked Problem 2 and cut it down to one kind of problem: an online order that never arrived, came broken, or was cancelled without a refund. "
        "I chose it because it happens to almost everyone, the law behind it is short and public (the Consumer Protection Act 2019 and the E-Commerce Rules 2020), "
        "and the way up is clear: the seller, then the National Consumer Helpline, then the Consumer Commission. "
        "A small scope also meant I could check every legal claim against a source instead of trusting what a model remembers about Indian law. "
        "Haq does not cover tenancy, salary or criminal matters. If someone brings one, it says so and points to legal aid.")]

S += [P("Assumptions I made", h2),
      B("English first. I tried one Hindi (Devanagari) story and one Hinglish story; the facts were extracted correctly, and the confirmation step adds a Hinglish version."),
      B("The law is as it stood in the official copies I saved on 20 November 2026. The District Commission limit of Rs 50 lakh comes from the 2021 Jurisdiction Rules. Anything that can change is marked in the answer."),
      B("\"Today\" is the server date. Haq counts two years from the order date, but the Act counts from when the cause of action arose, so it labels that date a rough guide."),
      B("No case law at all. The corpus has 15 entries, so \"my sources don't cover that\" is a normal answer.")]

S += [P("How it works", h2),
      P("A message passes input checks, then a scope check, then the model turns the story into a structured case file. Haq asks for what is missing (at most three rounds), "
        "shows the case file, and waits for the user to confirm it. Only then does it retrieve sources, write the explanation and offer a complaint letter.")]
steps = ["Message", "Input checks", "Scope", "Case file", "Questions", "Confirm", "Sources", "Explain", "Output checks", "Letter"]
flow_cells, flow_w = [], []
for i, name in enumerate(steps):
    flow_cells.append(Paragraph(name, ParagraphStyle("f", parent=cell, fontSize=7.4, leading=9, alignment=1)))
    flow_w.append((W - 9 * 2 * mm) / 10)
    if i < len(steps) - 1:
        flow_cells.append(Paragraph(">", ParagraphStyle("a", parent=cell, fontSize=8, alignment=1, textColor=MUTED)))
        flow_w.append(2 * mm)
flow = Table([flow_cells], colWidths=flow_w)
flow.setStyle(TableStyle([("BACKGROUND", (i, 0), (i, 0), colors.HexColor("#eef1f5")) for i in range(0, len(flow_cells), 2)]
                         + [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1)]))
S += [Spacer(1, 2), flow, Spacer(1, 5)]
S += [table([
    ["The model does", "Code and rules do"],
    ["Decides if the message is a consumer refund problem. Fills the case file from the story. Words the follow-up questions. "
     "Writes the plain-language explanation and one facts paragraph of the letter.",
     "Stops the flow on police, threat, injury or self-harm words. Masks phone, card and Aadhaar-like numbers before any model call. "
     "Refuses \"will I win?\" and requests to cite a section it cannot verify. Builds the list of options, the dates and the source list. "
     "Strips any section, Act or case name that is not in the retrieved sources. Fills the letter from a template and checks every amount, date and ID in it against the case file."],
], [W * 0.40, W * 0.60])]
S += [Spacer(1, 3),
      P("<b>How it avoids invented law.</b> The corpus is 15 entries cut word for word from the official PDFs by a script and re-checked by a second one, "
        "each with its URL and retrieval date. The model sees only the entries retrieved for the case, tagged [S1], [S2] and so on. "
        "Afterwards the verifier removes anything it cites that is not in those entries, and the source list shown to the user is built from the corpus, not from the model's text. "
        "The case-file step drops any amount or order number the user never typed. NeMo Guardrails runs the input and output checks."),
      P("<b>Retrieval and swapping models.</b> Entries are embedded with Vertex AI gemini-embedding-001 and searched in Qdrant Cloud, with keyword search (BM25) as an automatic fallback. "
        "The model is two environment variables: Gemini 3.8 Flash on Vertex is the default and Claude Haiku takes over when it fails. "
        "I tested the fallback with a real call, not only a mock.")]

S += [P("How it would scale", h2),
      B("<b>More topics.</b> Each area (tenancy, salary) needs its own verified corpus. The slicing and checking scripts make an entry cheap to add. "
        "The slow part is a qualified person confirming it, and that, not the model, is the bottleneck."),
      B("<b>More languages.</b> The pipeline ran on the Hindi text I tried, but I would add test cases per language before claiming support."),
      B("<b>Cost.</b> A conversation is about 4 to 8 model calls and 1 or 2 embedding calls. I did not price it. At volume I would use a cheaper model for scope and extraction, "
        "cache embeddings for common queries, and keep the per-session cap (30 messages, 2 instances). A three-turn case usually took 10 to 60 seconds in my runs, mostly the explanation step (one slow Vertex period pushed single cases to about 250)."),
      B("<b>Humans.</b> The user confirms the facts before any advice and reviews the letter before sending. Haq tells the user to see an advocate when the claim is above Rs 50 lakh, "
        "the order is over two years old, or injury or fraud comes up. A real launch also needs a lawyer to review the corpus and sample conversations.")]

S += [KeepTogether([P("How I checked it", h2),
      P("I wrote 13 test cases: normal disputes, a missing invoice, a vague message, five unresolved complaints, a made-up section, \"will I win?\", "
        "a landlord case, an urgent police case, a prompt injection, a Rs 60 lakh claim from 2023, and Hinglish. The first run passed 9 of 13. "
        "One was a real crash (the explainer received cut-off JSON), one was a mistake in my test script, and two were checks of mine that were too strict. "
        "After fixing them, 13 of 13 pass with the guardrails on and with them off. Every run, failures included, is in raw_outputs. 61 offline tests also pass.")])]
S += [table([
    ["Check", "Result"],
    ["Automatic checks (state reached, required and banned text, citation integrity)", "13/13 guardrails on, 13/13 off (after the first run's 9/13)"],
    ["Second opinion: Claude Haiku reads each full transcript against the sources (1 to 5)", "grounding 3.9, calibration 3.9, usefulness 3.2, safety 4.5"],
    ["Retrieval alone, 7 scenarios, the entries a good answer needs (my judgment)", "keyword 75%, Vertex embeddings 84%, mixed 80%"],
], [W * 0.62, W * 0.38])]
S += [Spacer(1, 3),
      P("I scored the outputs myself too, and my scores were higher than the judge's, so I trust the judge's numbers more. "
        "Across seven judge runs usefulness stayed between 2.8 and 3.2, and the gaps between runs are small enough to be noise.")]

S += [P("Where it fails", h2),
      B("<b>Usefulness is the weak spot.</b> Next steps come from a fixed ladder, so two different cases get similar advice."),
      B("<b>Citations.</b> The judge caught the model citing Section 34(1), which says one crore, for the Rs 50 lakh limit. Code now fixes that citation. "
        "The verifier is pattern-based, so a wrongly paraphrased claim with no section number can slip through."),
      B("<b>Refusals are blunt</b> and carry no source tags."),
      B("<b>Gaps in the sources.</b> No filing fees, no e-Jagriti (the site would not load), and I could not confirm when the 2026 e-commerce amendment takes effect."),
      B("<b>No lawyer has reviewed the corpus or the answers.</b> Haq says plainly that it is not a lawyer.")]

S += [P("Tools I used, and where they got it wrong", h2),
      P("I built this with Claude Code, with Gemini 3.8 Flash and Claude Haiku inside the app, Vertex AI embeddings, Qdrant, NeMo Guardrails, Streamlit and Cloud Run. "
        "I used Firecrawl to find the official PDFs and a second model as the judge. Two places the tools were wrong. "
        "First, the assistant told me a \"sources don't cover this\" answer was the model ignoring a source. A retrieval-only test showed the entry was never retrieved, "
        "so the fix was in retrieval, not in the prompt. Second, the Anthropic fallback passed its mocked tests and then crashed on its first real call, "
        "because the SDK rejected an argument. That is why the live provider tests exist.")]

doc = SimpleDocTemplate("submission/solution.pdf", pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=11 * mm,
                        title="Haq: an AI helper for refund disputes in India (Kuku assignment, Problem 2)", author="Akash Kar")
doc.build(S)
