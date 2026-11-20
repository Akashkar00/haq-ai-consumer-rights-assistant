"""Retrieval-only evaluation (no LLM). Gold sets are my own judgment of which corpus entries a good answer needs.

Reports recall of the gold entries for (a) BM25 alone (k=7) and (b) the final retrieval used by the explainer
(BM25 plus the entries the options ladder always cites), and counts irrelevant e-commerce entries on non-platform cases.
"""
import json
import sys

from haq.corpus import Corpus
from haq.explainer import retrieve_for_case
from haq.schema import CaseFile

CORE = {"CPA2019-34", "CPA2019-35", "CPA2019-69", "JUR2021-3", "NCH-HOWTO"}
SCENARIOS = [
    ("T01 non-delivery, platform", {"issue_type": "non_delivery", "platform": "QuickKart", "product_or_service": "headphones", "amount_paid_inr": 3200},
     CORE | {"CPA2019-2-11", "ECOM2020-4-5", "ECOM2020-6-3"}),
    ("T02 damaged, platform", {"issue_type": "damaged_item", "platform": "ShopEasy", "product_or_service": "dinner set", "amount_paid_inr": 4500},
     CORE | {"CPA2019-2-10", "ECOM2020-6-3", "ECOM2020-4-5"}),
    ("T03 cancelled, no refund, platform", {"issue_type": "cancelled_not_refunded", "platform": "QuickKart", "product_or_service": "backpack", "amount_paid_inr": 1800},
     CORE | {"CPA2019-2-11", "ECOM2020-4-10", "ECOM2020-4-5"}),
    ("T04 defective, local shop", {"issue_type": "defective_item", "platform": None, "product_or_service": "mixer grinder", "amount_paid_inr": 6500},
     CORE | {"CPA2019-2-10"}),
    ("T06 non-delivery, platform, 5 tickets", {"issue_type": "non_delivery", "platform": "QuickKart", "product_or_service": "phone", "amount_paid_inr": 15000},
     CORE | {"CPA2019-2-11", "ECOM2020-4-5", "ECOM2020-6-3"}),
    ("T12 high value, seller", {"issue_type": "non_delivery", "platform": None, "product_or_service": "car accessory package", "amount_paid_inr": 6_000_000},
     CORE | {"CPA2019-2-11", "JUR2021-4"}),
    ("T13 cancelled, platform (Hinglish)", {"issue_type": "cancelled_not_refunded", "platform": "QuickKart", "product_or_service": "shirt", "amount_paid_inr": 2500},
     CORE | {"CPA2019-2-11", "ECOM2020-4-10", "ECOM2020-4-5"}),
]


def run() -> dict:
    corpus, rows = Corpus(), []
    for name, facts, gold in SCENARIOS:
        case = CaseFile.model_validate(facts)
        final = {c.entry["id"] for c in retrieve_for_case(corpus, case)}
        bm25 = {c.entry["id"] for c in retrieve_for_case(corpus, case, bm25_only=True)}
        ecom_irrelevant = sorted(i for i in final if i.startswith("ECOM") and not case.platform)
        rows.append({"scenario": name, "gold": len(gold), "bm25_recall": len(gold & bm25) / len(gold),
                     "final_recall": len(gold & final) / len(gold), "missing_final": sorted(gold - final),
                     "missing_bm25": sorted(gold - bm25), "irrelevant_ecom": ecom_irrelevant})
    n = len(rows)
    return {"rows": rows, "mean_bm25_recall": sum(r["bm25_recall"] for r in rows) / n,
            "mean_final_recall": sum(r["final_recall"] for r in rows) / n,
            "irrelevant_ecom_total": sum(len(r["irrelevant_ecom"]) for r in rows)}


if __name__ == "__main__":
    res = run()
    for r in res["rows"]:
        print(f"{r['scenario']:42s} BM25 recall {r['bm25_recall']:.2f}  final {r['final_recall']:.2f}  missing_final={r['missing_final']} irrelevant_ecom={r['irrelevant_ecom']}")
    print(f"MEAN BM25 recall {res['mean_bm25_recall']:.2f} | final recall {res['mean_final_recall']:.2f} | irrelevant e-commerce entries {res['irrelevant_ecom_total']}")
    if "--json" in sys.argv:
        json.dump(res, open("evals/retrieval_results.json", "w"), indent=2)
