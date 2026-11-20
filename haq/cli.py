from haq.llm.base import get_client
from haq.orchestrator import Session


def main():
    s = Session(get_client())
    print("Haq: tell me about your refund problem (Ctrl+C to quit).")
    while s.state != "DONE":
        r = s.handle(input("\nyou> "))
        print(f"\nhaq> {r.text}")
        if r.draft:
            print("\n----- DRAFT -----\n" + r.draft)


if __name__ == "__main__":
    main()
