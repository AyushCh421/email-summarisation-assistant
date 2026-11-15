"""app.py - Streamlit UI for the AI Email Summarisation Assistant.
Run with:  streamlit run app.py
"""
import streamlit as st

import email_processor
import rag
import summarizer

st.set_page_config(page_title="Email Summarisation Assistant", page_icon="📧", layout="wide")
st.title("📧 AI Email Summarisation Assistant")
st.caption("Upload → Extract → Clean → Summarise → Detect urgency → Embed → Store → Ask → Retrieve → Answer")

if "messages" not in st.session_state:
    st.session_state.messages = []  # chat history


def process_uploads(files):
    """Full pipeline for each uploaded file: parse → summarise → embed and store."""
    for f in files:
        with st.spinner(f"Processing {f.name}..."):
            try:
                mail = email_processor.process_file(f.name, f.getvalue())
                if rag.email_exists(mail["id"]):
                    st.info(f"{f.name}: duplicate email, already processed.")
                    continue
                summary = summarizer.summarize_email(mail)
                rag.add_email(mail, summary)
                st.success(f"{f.name}: processed successfully.")
            except ValueError as e:  # empty file, invalid format, bad AI output
                st.error(f"{f.name}: {e}")
            except Exception as e:  # network / Gemini API errors
                st.error(f"{f.name}: API error - {e}")


def show_list(title, items):
    st.markdown(f"**{title}**")
    for item in items or ["None mentioned"]:
        st.markdown(f"- {item}")


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("📂 Upload Emails")
    files = st.file_uploader("Choose .eml or .txt files", type=["eml", "txt"], accept_multiple_files=True)
    if st.button("Process Emails", type="primary", use_container_width=True):
        if not files:
            st.warning("Please upload at least one email file first.")
        elif not summarizer.has_api_key():
            st.error("GEMINI_API_KEY is missing. Add it to your .env file and restart the app.")
        else:
            process_uploads(files)
    if st.button("Clear Database", use_container_width=True):
        rag.clear_database()
        st.session_state.messages = []
        st.success("Database cleared.")
    emails = rag.list_emails()
    st.metric("Processed emails", len(emails))

# ---------------- Email Dashboard ----------------
st.header("📊 Email Dashboard")
if not emails:
    st.info("No emails processed yet. Upload files in the sidebar and click **Process Emails**.")
else:
    st.dataframe(
        [{"Sender": e["sender"], "Subject": e["subject"], "Date": e["date"],
          "Urgency": e["summary"]["urgency"], "Action Required": e["summary"]["action_required"],
          "Summary": e["summary"].get("main_topic", "")} for e in emails],
        hide_index=True,
    )
    icons = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
    for e in emails:
        s = e["summary"]
        st.subheader(f"{icons.get(s['urgency'], '⚪')} {e['subject']}")
        st.caption(f"From: {e['sender']} | To: {e['receiver']} | Date: {e['date']} | File: {e['file_name']}")
        st.write(f"**Urgency:** {s['urgency']} ({s.get('urgency_reason', '')}) | "
                 f"**Action required:** {s['action_required']}")
        with st.expander("🤖 AI Summary"):
            st.markdown(f"**Main topic:** {s.get('main_topic', '')}")
            show_list("Key points", s.get("key_points"))
            show_list("Important dates and deadlines", s.get("dates_deadlines"))
            show_list("Required actions", s.get("required_actions"))
            show_list("Decisions or requests", s.get("decisions"))
            st.markdown(f"**Conclusion:** {s.get('conclusion', '')}")
        with st.expander("📄 Email Details (original content)"):
            st.text(e["body"])

# ---------------- Chat Assistant ----------------
st.header("💬 Email Chat Assistant")
st.caption("Try: What deadlines are mentioned in my emails? / Which emails require an immediate response?")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        chunks = msg.get("chunks")
        if chunks:
            if msg["content"] != summarizer.NOT_FOUND:
                sources = {f"{c['file_name']} — {c['subject']}" for c in chunks}
                st.markdown("**Sources:** " + "; ".join(sorted(sources)))
            with st.expander("🔎 Retrieved Context"):
                for c in chunks:
                    st.markdown(f"**File:** {c['file_name']} | **Subject:** {c['subject']} | "
                                f"**Similarity:** {c['score']}")
                    st.text(c["text"])

question = st.chat_input("Ask a question about your uploaded emails...")
if question:
    st.session_state.messages.append({"role": "user", "content": question})
    chunks = []
    if not summarizer.has_api_key():
        answer = "GEMINI_API_KEY is missing. Add it to your .env file and restart the app."
    else:
        with st.spinner("Searching your emails..."):
            chunks = rag.search(question, top_k=3)  # RAG: retrieve top 3 chunks
            if not chunks:
                answer = summarizer.NOT_FOUND  # nothing stored / nothing relevant
            else:
                try:
                    answer = summarizer.answer_question(question, chunks)  # RAG: generate
                except Exception as e:
                    answer = f"API error: {e}"
    st.session_state.messages.append({"role": "assistant", "content": answer, "chunks": chunks})
    st.rerun()
