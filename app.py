import os
import re
import time

import streamlit as st

# Streamlit Cloud keeps keys in st.secrets, not .env. Copy them into the environment BEFORE importing haq
# (haq.config's load_dotenv never overrides variables that are already set).
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float, bool)):
            os.environ.setdefault(str(_k), str(_v))
except Exception:  # no secrets file locally: .env is used instead
    pass

from haq import policy
from haq.corpus import Corpus
from haq.llm.base import get_client
from haq.orchestrator import Session

st.set_page_config(page_title="Haq: consumer rights helper", page_icon="⚖️")
st.title("Haq (हक़)")
st.caption("A consumer-refund helper for India. " + policy.DISCLAIMER)
st.warning("Do not share Aadhaar, card numbers or passwords. Phone numbers, emails and card/Aadhaar-like numbers are masked automatically.")

@st.cache_resource
def get_corpus():
    """One Corpus (BM25 index + Qdrant connection) shared by all sessions."""
    return Corpus()


if "session" not in st.session_state:
    st.session_state.session = Session(get_client(), get_corpus())
    st.session_state.chat = [("assistant", "Tell me what happened with your order, in your own words.")]
    st.session_state.draft = None
s: Session = st.session_state.session

for role, msg in st.session_state.chat:
    st.chat_message(role).markdown(msg)

MAX_USER_MESSAGES = int(os.getenv("MAX_USER_MESSAGES", "30"))  # per session, so a public link cannot run up the LLM bill
if "n_user" not in st.session_state:
    st.session_state.n_user = 0

def stream_words(text: str, total_seconds: float = 3.0):
    """Reveal an already-complete reply piece by piece. (The model's answer is produced in one go and then
    checked by the guardrails, so this is a display effect, not live token streaming.)"""
    parts = re.split(r"(\s+)", text)
    delay = min(0.02, total_seconds / max(len(parts), 1))
    for part in parts:
        yield part
        if part.strip():
            time.sleep(delay)


if prompt := st.chat_input("Describe your problem or reply here"):
    st.session_state.chat.append(("user", prompt))
    with st.chat_message("user"):  # show the question immediately, not after the answer arrives
        st.markdown(prompt)
    reply = None
    if st.session_state.n_user >= MAX_USER_MESSAGES:
        reply = "This session has reached its message limit. Please refresh the page to start a new one."
    else:
        st.session_state.n_user += 1
    with st.chat_message("assistant"):
        if reply is None:
            with st.spinner("Thinking..."):
                try:
                    r = s.handle(prompt)
                    reply = r.text
                    if r.draft:
                        st.session_state.draft = r.draft
                except Exception as e:  # LLM outage or malformed output: never crash the chat
                    reply = f"Sorry, something went wrong on my side ({type(e).__name__}). Please try again."
        st.write_stream(stream_words(reply))
    st.session_state.chat.append(("assistant", reply))

with st.sidebar:
    st.subheader("Case file (live)")
    st.json(s.case.model_dump(mode="json", exclude_none=True), expanded=False)
    st.caption(f"State: {s.state}")
    st.caption(f"Retrieval: {s.corpus.last_mode_used or 'not used yet'} (configured: {s.corpus.mode}, vector store: {'on' if s.corpus.vector else 'off'})")
    if st.session_state.draft:
        st.subheader("Draft")
        st.text_area("Editable draft", st.session_state.draft, height=350)
        st.download_button("Download draft (.txt)", st.session_state.draft, file_name="haq_complaint_draft.txt")
