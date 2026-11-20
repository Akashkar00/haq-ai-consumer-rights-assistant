import streamlit as st

from haq import policy
from haq.llm.base import get_client
from haq.orchestrator import Session

st.set_page_config(page_title="Haq: consumer rights helper", page_icon="⚖️")
st.title("Haq (हक़)")
st.caption("A consumer-refund helper for India. " + policy.DISCLAIMER)
st.warning("Do not share Aadhaar, card numbers or passwords. Phone numbers, emails and card/Aadhaar-like numbers are masked automatically.")

if "session" not in st.session_state:
    st.session_state.session = Session(get_client())
    st.session_state.chat = [("assistant", "Tell me what happened with your order, in your own words.")]
    st.session_state.draft = None
s: Session = st.session_state.session

for role, msg in st.session_state.chat:
    st.chat_message(role).markdown(msg)

if prompt := st.chat_input("Describe your problem or reply here"):
    st.session_state.chat.append(("user", prompt))
    with st.spinner("Thinking..."):
        try:
            r = s.handle(prompt)
            st.session_state.chat.append(("assistant", r.text))
            if r.draft:
                st.session_state.draft = r.draft
        except Exception as e:  # LLM outage or malformed output: never crash the chat
            st.session_state.chat.append(("assistant", f"Sorry, something went wrong on my side ({type(e).__name__}). Please try again."))
    st.rerun()

with st.sidebar:
    st.subheader("Case file (live)")
    st.json(s.case.model_dump(mode="json", exclude_none=True), expanded=False)
    st.caption(f"State: {s.state}")
    if st.session_state.draft:
        st.subheader("Draft")
        st.text_area("Editable draft", st.session_state.draft, height=350)
        st.download_button("Download draft (.txt)", st.session_state.draft, file_name="haq_complaint_draft.txt")
