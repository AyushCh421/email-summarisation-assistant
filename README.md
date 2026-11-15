# 📧 AI Email Summarisation Assistant

## Live Link : https://email-summarisation-assistant-ahmi4o8kygfazqsz7rmao7.streamlit.app/

## 1. Introduction
A simple AI-powered assistant, built for an NLP & Generative AI lab, that reads your emails, summarises them,
detects urgency and lets you chat with them. It combines classic **NLP text processing** (parsing, regex
cleaning, chunking), **semantic embeddings** (sentence-transformers), a **vector database** (ChromaDB) and a
**Large Language Model** (Google Gemini) in a small **Retrieval-Augmented Generation (RAG)** pipeline.
It uses plain Python only, with no LangChain.

## 2. Features
- Upload one or more `.eml` or `.txt` email files
- Extracts sender, receiver, subject, date and body
- AI summary for each email: main topic, 3–5 key points, dates and deadlines, required actions, decisions, conclusion
- Urgency classification: **High / Medium / Low**
- Detects whether a reply or action is required (Yes/No)
- Dashboard of all emails, most urgent first
- Chat assistant that answers **only** from your emails, with sources and similarity scores
- Duplicate detection, a persistent local database and a "Clear Database" button
- Resists prompt injection: instructions hidden inside emails are ignored

## 3. Technologies Used
| Purpose | Technology |
|---|---|
| UI | Streamlit |
| Email parsing | Python `email` package (.eml), file reading (.txt) |
| Text processing | Python strings + `re` (regular expressions) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local, free) |
| Vector store | ChromaDB (persistent, `chroma_db/` folder) |
| LLM | Google Gemini (`gemini-3.8-flash`, set with `GEMINI_MODEL` in `.env`) via `google-genai` |
| Config | `python-dotenv` (`.env` file) |

## 4. Project Structure
```
email-summarisation-assistant/
│
├── app.py               # Streamlit UI (sidebar, dashboard, chat)
├── email_processor.py   # Email reading and text extraction/cleaning
├── summarizer.py        # Gemini summarisation, urgency detection, answers
├── rag.py               # Embeddings, ChromaDB storage and retrieval
├── requirements.txt
├── .env.example
├── sample_emails/       # 3 demo emails (.eml plain, .eml HTML, .txt)
└── README.md
```

## 5. Installation
Requires **Python 3.10–3.13**.
```bash
cd email-summarisation-assistant
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
The first run downloads the embedding model (~90 MB), so you need internet access once.

## 6. Configure the Gemini API Key
1. Get a free key from <https://aistudio.google.com/apikey>.
2. Copy the example file: `cp .env.example .env` (Windows: `copy .env.example .env`).
3. Open `.env` and set `GEMINI_API_KEY=your_real_key`.

If the key is missing, the app shows an error message instead of crashing.

## 7. Run the Application
```bash
streamlit run app.py
```
Open <http://localhost:8501>, upload the files from `sample_emails/`, and click **Process Emails**.

## 8. How Email Summarisation Works
1. **Extract**: `email_processor.py` parses `.eml` files with Python's `email` package (preferring the plain-text
   body over HTML). For `.txt` files it uses regex to find the `From:`, `To:`, `Subject:` and `Date:` lines.
2. **Clean**: regex removes HTML tags, decodes HTML entities and collapses extra whitespace.
3. **Summarise**: `summarizer.py` sends the email to Gemini with a **system prompt** (role and rules) and asks for
   **structured JSON** (topic, key points, deadlines, actions, decisions, conclusion).
4. **Classify**: in the same call Gemini assigns urgency (High/Medium/Low) and `action_required` (Yes/No)
   from the email content. A low temperature (0.2) keeps the answers factual.
5. **Safety**: the email text is wrapped in `<email>` tags and treated as data, so instructions inside an email
   are ignored. The sample newsletter contains such an instruction to demonstrate this.

## 9. How the RAG Pipeline Works
```
Upload → Extract → Clean → Summarise → Detect Urgency → Embed → Store in ChromaDB
Question → Embed question → Retrieve top-3 chunks → Gemini answers from context only
```
1. **Chunking**: each email body is split into overlapping 150-word chunks. Every chunk keeps the email header,
   so a question like "emails from Dr. Rao" still matches.
2. **Embedding**: `all-MiniLM-L6-v2` converts each chunk (plus one summary document per email) into a
   384-dimensional vector that represents its meaning.
3. **Storage**: vectors, text and metadata (file name, subject) are saved in a persistent ChromaDB collection
   that uses cosine distance.
4. **Retrieval**: the question is embedded, and ChromaDB returns the **3 most similar chunks**
   (similarity = 1 − cosine distance).
5. **Generation**: Gemini receives only those chunks and must answer from them. Otherwise it replies:
   *"I couldn't find this information in the uploaded emails."*
6. **Transparency**: the UI shows the source file and subject, and the **Retrieved Context** panel shows each
   chunk with its similarity score.

## 10. Sample Questions for Demonstration
- What are the important emails I received?
- Which emails require an immediate response?
- What deadlines are mentioned in my emails?
- Summarise all emails from Dr. Meera Rao.
- Which emails contain assignment or examination information?
- What tasks do I need to complete?
- What are the important decisions mentioned in my emails?
- What is the capital of France? *(should return "I couldn't find this information…")*

## 11. Expected Output Screenshots
Add your screenshots to a `screenshots/` folder and they will appear here:

| Screen | Screenshot |
|---|---|
| Sidebar upload and processing | `![Upload](screenshots/upload.png)` |
| Email dashboard with urgency | `![Dashboard](screenshots/dashboard.png)` |
| AI Summary expander | `![Summary](screenshots/summary.png)` |
| Chat answer with sources | `![Chat](screenshots/chat.png)` |
| Retrieved Context with similarity scores | `![Context](screenshots/context.png)` |
| "Not found" answer | `![Not found](screenshots/not_found.png)` |

**Expected results with the sample emails:** Assignment deadline → **High**, action **Yes**;
Exam timetable → **Medium**; Newsletter → **Low**, action **No** (even though it asks to be marked High).
