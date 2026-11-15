"""email_processor.py - Reads .eml / .txt files and extracts clean email text."""
import email
import hashlib
import html
import re
from email import policy


def clean_text(text):
    """NLP pre-processing: remove HTML tags, decode entities and normalise whitespace."""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)  # drop scripts/styles
    text = re.sub(r"<[^>]+>", " ", text)                       # strip remaining HTML tags
    text = html.unescape(text).replace("\r", "")              # &amp; -> &, remove \r
    text = re.sub(r"[ \t]+", " ", text)                        # collapse spaces/tabs
    text = re.sub(r"\n\s*\n+", "\n\n", text)                   # collapse blank lines
    return text.strip()


def parse_eml(data):
    """Use Python's built-in email package to read headers and the body."""
    msg = email.message_from_bytes(data, policy=policy.default)
    if not any(msg.get(h) for h in ("From", "To", "Subject", "Date")):
        raise ValueError("Invalid email format: no email headers found.")
    body = ""
    part = msg.get_body(preferencelist=("plain", "html"))  # prefer plain text over HTML
    if part is not None:
        try:
            body = part.get_content()
        except Exception:
            body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
    return {
        "sender": str(msg.get("From", "Unknown")),
        "receiver": str(msg.get("To", "Unknown")),
        "subject": str(msg.get("Subject", "(No subject)")),
        "date": str(msg.get("Date", "Unknown")),
        "body": body,
    }


def parse_txt(text):
    """Plain text emails: find 'From:', 'To:', 'Subject:', 'Date:' lines with regex."""
    def header(name, default):
        match = re.search(rf"^{name}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else default

    # Everything that is not a header line is treated as the body.
    body = re.sub(r"^(From|To|Subject|Date)\s*:.*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    return {
        "sender": header("From", "Unknown"),
        "receiver": header("To", "Unknown"),
        "subject": header("Subject", "(No subject)"),
        "date": header("Date", "Unknown"),
        "body": body,
    }


def process_file(file_name, data):
    """Turn an uploaded file (bytes) into a clean email dictionary."""
    if not data or not data.strip():
        raise ValueError("The file is empty.")
    if file_name.lower().endswith(".eml"):
        mail = parse_eml(data)
    else:
        mail = parse_txt(data.decode("utf-8", errors="ignore"))
    mail["body"] = clean_text(mail["body"])
    if not mail["body"]:
        raise ValueError("No readable email body was found.")
    mail["file_name"] = file_name
    mail["id"] = hashlib.md5(data).hexdigest()  # content hash -> detects duplicate uploads
    return mail
