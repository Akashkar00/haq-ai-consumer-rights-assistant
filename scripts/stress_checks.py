"""Live robustness checks beyond the eval set: Hindi script, long conversation, concurrent sessions."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from haq import config  # noqa: F401
from haq.corpus import Corpus
from haq.llm.base import get_client
from haq.orchestrator import Session

TODAY, corpus, llm = date(2026, 11, 21), Corpus(), get_client()


def hindi():
    s = Session(llm, corpus, TODAY)
    r = s.handle("मैंने 5 अक्टूबर 2026 को QuickKart से 2500 रुपये का जूता मंगवाया, UPI से भुगतान किया, ऑर्डर नंबर QK9001 है। डिलीवरी नहीं हुई। मैंने अभी तक कोई शिकायत नहीं की है।")
    print("HINDI  state:", r.state, "| amount:", s.case.amount_paid_inr, "| order:", s.case.order_id, "| date:", s.case.order_date, "| issue:", s.case.issue_type)
    return s.case.amount_paid_inr == 2500 and s.state in ("CONFIRM", "GATHER")


def long_conversation():
    s = Session(llm, corpus, TODAY)
    turns = ["help, my order has a problem", "I bought a shirt from QuickKart", "It was Rs 900", "No, sorry it was Rs 1200",
             "ordered on 1 October 2026", "it never arrived", "not complained yet", "actually the seller is ShirtHub on QuickKart",
             "no, the amount was Rs 1200 as I said", "yes", "draft", "change the remedy to replacement", "done"]
    states = []
    for t in turns:
        r = s.handle(t)
        states.append(s.state)
    print("LONG   states:", states)
    print("LONG   final amount:", s.case.amount_paid_inr, "| seller:", s.case.opposite_party.name, "| turns kept:", len(s.user_texts))
    return s.case.amount_paid_inr == 1200 and states[-1] == "DONE" and s.last_draft is not None


def concurrent():
    amounts = [1111, 2222, 3333, 4444]

    def run(a):
        s = Session(llm, corpus, TODAY)
        s.handle(f"I ordered a gadget{a} from Shop{a} on 3 October 2026 for Rs {a} by UPI, order ORD{a}, never delivered. No complaint yet.")
        s.handle("yes")
        r = s.handle("draft")
        return a, r.draft or ""

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(run, amounts))
    ok = True
    for a, d in results:
        others = [str(x) for x in amounts if x != a]
        leaked = [x for x in others if x in d or f"{int(x):,}" in d]
        mine = f"{a:,}" in d and f"ORD{a}" in d
        print(f"CONC   session {a}: own facts present={mine} leaked_from_others={leaked}")
        ok &= mine and not leaked
    return ok


if __name__ == "__main__":
    t0 = time.time()
    res = {"hindi": hindi(), "long": long_conversation(), "concurrent": concurrent()}
    print(res, f"{time.time()-t0:.0f}s", "GUARDRAILS=" + os.getenv("GUARDRAILS", "on"))
