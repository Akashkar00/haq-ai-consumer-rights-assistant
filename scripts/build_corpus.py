"""Build data/corpus.jsonl by slicing verbatim text out of the saved official PDFs.

Verbatim text is never typed by hand: each entry names a start and end line marker in a raw
source text file, and the slice is copied. scripts/verify_corpus.py re-checks every entry.
"""
import json
import re
from pathlib import Path

RAW = Path("data/raw_sources")
RETRIEVED = "2026-11-20"
CPA_URL = "https://consumeraffairs.gov.in/public/upload/files/CP%20Act%202019_1732700731.pdf"
ECOM_URL = "https://consumeraffairs.gov.in/public/upload/files/E%20commerce%20rules_1732703966.pdf"
JUR_URL = ("https://thc.nic.in/Central%20Governmental%20Rules/Consumer%20Protection%20(Jurisdiction%20of%20the"
           "%20District%20Commission,%20the%20State%20Commission%20and%20the%20National%20Commission)%20Rules,%202021.pdf")
NOISE = re.compile(r"[ऀ-ॿ]|THE GAZETTE OF INDIA", re.I)


def clean(lines: list[str]) -> str:
    kept = [ln.rstrip() for ln in lines if not NOISE.search(ln)]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()


def slice_text(file: str, start: str, end: str, plus: int = 0) -> str:
    lines = (RAW / file).read_text().splitlines()
    s = next(i for i, ln in enumerate(lines) if ln.strip().startswith(start))
    e = next(i for i in range(s, len(lines)) if end in lines[i])
    return clean(lines[s : e + 1 + plus])


# Extra lines to include after the end-marker line, where the sentence wraps onto the next line.
PLUS = {"CPA2019-2-11": 1, "CPA2019-2-47": 2, "CPA2019-35": 1, "CPA2019-69": 1, "JUR2021-4": 1, "ECOM2020-4-5": 1}
E = []


def add(id, title, src_type, ref, refs, file, start, end, url, summary, tags, volatile=False, note=None):
    E.append({
        "id": id, "title": title, "source_type": src_type, "reference": ref, "refs": refs,
        "source_file": file, "source_url": url, "retrieved_on": RETRIEVED,
        "verbatim_text": slice_text(file, start, end, PLUS.get(id, 0)), "plain_summary": summary,
        "tags": tags, "volatile": volatile, "verified": True, "note": note,
    })


CPA = "cpa2019.txt"
ACT = "Consumer Protection Act, 2019"
add("CPA2019-2-7", f"{ACT} – definition of 'consumer'", "statute", "Section 2(7)", ["Section 2", "Section 2(7)"], CPA,
    '(7) "consumer" means', "multi-level marketing", CPA_URL,
    "A consumer is someone who buys goods or hires services for a price paid or promised. Online purchases count. "
    "Buying for resale or a commercial purpose is excluded.", ["definitions", "scope"])
add("CPA2019-2-10", f"{ACT} – definition of 'defect'", "statute", "Section 2(10)", ["Section 2", "Section 2(10)"], CPA,
    '(10) "defect" means', 'and the expression "defective"', CPA_URL,
    "A defect is a fault or shortcoming in quality, quantity or standard required by law, by the contract, or "
    "as claimed by the trader.", ["definitions", "damaged_item", "defective_item", "wrong_item"])
add("CPA2019-2-11", f"{ACT} – definition of 'deficiency'", "statute", "Section 2(11)", ["Section 2", "Section 2(11)"], CPA,
    '(11) "deficiency" means', "(ii) deliberate withholding", CPA_URL,
    "Deficiency covers faults in how a service is performed, including negligence and deliberately withholding "
    "relevant information.", ["definitions", "non_delivery", "cancelled_not_refunded", "return_refused"])
add("CPA2019-2-47", f"{ACT} – 'unfair trade practice' (opening and clause (i) excerpt)", "statute", "Section 2(47)",
    ["Section 2", "Section 2(47)"], CPA, '(47) "unfair trade practice"', "(g) gives to the public any warranty", CPA_URL,
    "An unfair trade practice includes false or misleading statements about goods or services. This is only the "
    "opening and the first group of examples; the full definition has more limbs.",
    ["definitions", "damaged_item", "defective_item", "wrong_item", "other"],
    note="Excerpt: clause (47) continues beyond sub-clause (i)(g) in the Act.")
add("CPA2019-34", f"{ACT} – jurisdiction of the District Commission", "statute", "Section 34(1)-(2)",
    ["Section 34", "Section 34(1)", "Section 34(2)"], CPA, "34. (1)", "(d) the complainant resides or personally works", CPA_URL,
    "A complaint goes to the District Commission where the opposite party is based, or where the cause of action "
    "arose, or where the complainant lives or works. The Act's base text gives a one-crore limit, but see the "
    "2021 Rules entry for the value limit now prescribed.",
    ["jurisdiction", "filing", "non_delivery", "damaged_item", "defective_item", "wrong_item",
     "cancelled_not_refunded", "return_refused", "other"], volatile=True,
    note="Base text says one crore; the Central Government prescribed fifty lakh under the proviso (see JUR2021-3).")
add("CPA2019-35", f"{ACT} – who may file a complaint and how", "statute", "Section 35(1)-(2)",
    ["Section 35", "Section 35(1)", "Section 35(2)"], CPA, "35. (1)", "(2) Every complaint filed under sub-section", CPA_URL,
    "A consumer can file a complaint with the District Commission, and it may be filed electronically. A fee, "
    "as prescribed, is payable.", ["filing", "non_delivery", "damaged_item", "defective_item", "wrong_item",
                                   "cancelled_not_refunded", "return_refused", "other"], volatile=True)
add("CPA2019-69", f"{ACT} – limitation period", "statute", "Section 69(1)-(2)",
    ["Section 69", "Section 69(1)", "Section 69(2)"], CPA, "69. (1)", "records its reasons", CPA_URL,
    "A complaint must be filed within two years from when the cause of action arose. A late complaint can be "
    "entertained only if the Commission accepts there was sufficient cause and records its reasons.",
    ["limitation", "filing", "non_delivery", "damaged_item", "defective_item", "wrong_item",
     "cancelled_not_refunded", "return_refused", "other"])

JUR = "jurisdiction2021.txt"
JR = "Consumer Protection (Jurisdiction of the District Commission, the State Commission and the National Commission) Rules, 2021"
add("JUR2021-3", f"{JR} – District Commission value limit", "rules", "Rule 3", ["Rule 3"], JUR,
    "3.       Jurisdiction of District Commission", "does not exceed fifty lakh rupees", JUR_URL,
    "District Commissions hear complaints where the price paid for the goods or services is up to fifty lakh rupees.",
    ["jurisdiction", "filing", "non_delivery", "damaged_item", "defective_item", "wrong_item",
     "cancelled_not_refunded", "return_refused", "other"], volatile=True)
add("JUR2021-4", f"{JR} – State Commission value limit", "rules", "Rule 4", ["Rule 4"], JUR,
    "4.       Jurisdiction of State Commission", "two", JUR_URL,
    "State Commissions hear complaints above fifty lakh and up to two crore rupees.", ["jurisdiction"], volatile=True)
add("JUR2021-5", f"{JR} – National Commission value limit", "rules", "Rule 5", ["Rule 5"], JUR,
    "5.       Jurisdiction of National Commission", "exceeds  two crore rupees", JUR_URL,
    "The National Commission hears complaints above two crore rupees.", ["jurisdiction"], volatile=True)

EC = "ecom2020.txt"
ER = "Consumer Protection (E-Commerce) Rules, 2020"
EC_TAGS = ["ecommerce", "grievance", "non_delivery", "cancelled_not_refunded", "return_refused",
           "damaged_item", "defective_item", "wrong_item"]
add("ECOM2020-4-4", f"{ER} – grievance mechanism and officer", "rules", "Rule 4(4)", ["Rule 4", "Rule 4(4)"], EC,
    "(4) Every e-commerce entity shall establish", "such officer on its platform", ECOM_URL,
    "Every e-commerce entity must run a grievance mechanism and name a grievance officer on its platform.",
    EC_TAGS, volatile=True, note="Amended by the 2026 Amendment Rules; commencement date not confirmed (see EXCLUDED.md).")
add("ECOM2020-4-5", f"{ER} – grievance officer timelines", "rules", "Rule 4(5)", ["Rule 4", "Rule 4(5)"], EC,
    "(5) Every e-commerce entity shall ensure that the grievance officer", "within forty-eight hours", ECOM_URL,
    "The grievance officer must acknowledge a complaint within 48 hours and resolve it within one month.",
    EC_TAGS, volatile=True, note="Amended by the 2026 Amendment Rules (adds a copy of the recorded complaint); commencement date not confirmed.")
add("ECOM2020-4-10", f"{ER} – refunds on accepted requests", "rules", "Rule 4(10)", ["Rule 4", "Rule 4(10)"], EC,
    "(10) Every e-commerce entity shall effect all payments", "applicable laws.", ECOM_URL,
    "Once a refund request is accepted, the platform must pay it within a reasonable period, as prescribed by "
    "the RBI or other law. The Rules give no fixed number of days.", EC_TAGS + ["refund"], volatile=True)
add("ECOM2020-6-3", f"{ER} – seller duties on refusing returns and refunds", "rules", "Rule 6(3)", ["Rule 6", "Rule 6(3)"], EC,
    "(3) No seller offering goods or services through a marketplace", "force majeure", ECOM_URL,
    "A marketplace seller may not refuse to take back goods or refuse a refund where the goods are defective, "
    "deficient, spurious, not as advertised, or delivered late (except for force majeure).",
    EC_TAGS + ["refund"])

# Government portal guidance: no verbatim statute text, so verbatim_text is a quote from the page.
E.append({
    "id": "NCH-HOWTO", "title": "National Consumer Helpline – how to register a grievance",
    "source_type": "govt_portal_guidance", "reference": "consumerhelpline.gov.in home page", "refs": [],
    "source_file": "nch_home.txt", "source_url": "https://consumerhelpline.gov.in/", "retrieved_on": RETRIEVED,
    "verbatim_text": Path(RAW / "nch_home.txt").read_text().strip(),
    "plain_summary": "You can register a grievance with the National Consumer Helpline by web portal, app, UMANG, "
                     "WhatsApp or call (1915 or 1800114000). NCH forwards it to the company and you can track the response.",
    "tags": ["escalation", "grievance", "non_delivery", "damaged_item", "defective_item", "wrong_item",
             "cancelled_not_refunded", "return_refused", "other"],
    "volatile": True, "verified": True, "note": "Portal text; contact numbers and channels can change."})

Path("data/corpus.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in E) + "\n")
print(f"wrote {len(E)} entries")
