"""rag.py - Embeddings (sentence-transformers), storage and retrieval (ChromaDB)."""
import json
import os

import chromadb
from sentence_transformers import SentenceTransformer

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")
COLLECTION = "emails"
URGENCY_ORDER = {"High": 0, "Medium": 1, "Low": 2}

db = chromadb.PersistentClient(path=DB_PATH)  # data survives app restarts
_model = None


def get_model():
    """Load the embedding model once (it is downloaded on first use)."""
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(texts):
    """Embedding step: turn text into 384-number vectors that capture meaning."""
    return get_model().encode(texts).tolist()


def get_collection():
    # Cosine distance: smaller distance = more similar meaning.
    return db.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def chunk_text(text, size=150, overlap=30):
    """Split long text into overlapping word chunks so each embedding stays focused."""
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - overlap, 1), step)]


def email_exists(email_id):
    return bool(get_collection().get(ids=[f"{email_id}-summary"])["ids"])


def add_email(mail, summary):
    """Store one summary document plus body chunks for an email in ChromaDB."""
    header = f"From: {mail['sender']} | To: {mail['receiver']} | Subject: {mail['subject']} | Date: {mail['date']}"
    summary_text = (
        f"{header}\nUrgency: {summary['urgency']} | Action required: {summary['action_required']}\n"
        f"Summary: {summary.get('main_topic', '')}\nKey points: {summary.get('key_points', [])}\n"
        f"Deadlines: {summary.get('dates_deadlines', [])}\nActions: {summary.get('required_actions', [])}\n"
        f"Decisions: {summary.get('decisions', [])}"
    )
    docs = [summary_text] + [f"{header}\n{chunk}" for chunk in chunk_text(mail["body"])]
    ids = [f"{mail['id']}-summary"] + [f"{mail['id']}-{i}" for i in range(len(docs) - 1)]
    base = {"file_name": mail["file_name"], "subject": mail["subject"]}
    metas = [{**base, "type": "chunk"} for _ in docs]
    # The summary document also keeps the full email so the dashboard can be rebuilt.
    metas[0] = {**base, "type": "summary", "email_json": json.dumps(mail), "summary_json": json.dumps(summary)}
    get_collection().add(ids=ids, documents=docs, embeddings=embed(docs), metadatas=metas)


def list_emails():
    """Return all processed emails (with summaries), most urgent first."""
    result = get_collection().get(where={"type": "summary"})
    emails = [{**json.loads(m["email_json"]), "summary": json.loads(m["summary_json"])}
              for m in result["metadatas"]]
    return sorted(emails, key=lambda e: URGENCY_ORDER.get(e["summary"]["urgency"], 1))


def search(question, top_k=3):
    """Retrieval step: find the top_k chunks most similar to the question."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    res = collection.query(query_embeddings=embed([question]), n_results=min(top_k, collection.count()))
    return [
        {"text": doc, "file_name": meta["file_name"], "subject": meta["subject"],
         "score": round(1 - dist, 3)}  # similarity = 1 - cosine distance
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def clear_database():
    try:
        db.delete_collection(COLLECTION)
    except Exception:
        pass  # collection did not exist yet
