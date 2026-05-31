"""
Read-only IMAP client for the staff portal inbox.
Uses Python's built-in imaplib — no extra packages required.
"""

import imaplib
import email
import email.header
import email.utils
from email import policy
from django.conf import settings


class IMAPError(Exception):
    pass


def _decode_header(value):
    if not value:
        return ""
    parts = email.header.decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                decoded.append(part.decode("utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _get_body(msg):
    """Return (body_text, is_html) from a parsed email message."""
    if msg.is_multipart():
        # Prefer HTML, fall back to plain
        html_part = None
        plain_part = None
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html" and not html_part:
                html_part = part
            elif ct == "text/plain" and not plain_part:
                plain_part = part
        if html_part:
            payload = html_part.get_payload(decode=True)
            charset = html_part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace"), True
        if plain_part:
            payload = plain_part.get_payload(decode=True)
            charset = plain_part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace"), False
        return "", False
    else:
        payload = msg.get_payload(decode=True)
        if not payload:
            return "", False
        charset = msg.get_content_charset() or "utf-8"
        is_html = msg.get_content_type() == "text/html"
        return payload.decode(charset, errors="replace"), is_html


def _connect():
    host = settings.IMAP_HOST.strip()
    port = settings.IMAP_PORT
    user = settings.IMAP_USER.strip()
    password = settings.IMAP_PASSWORD.strip()

    if not user or not password:
        raise IMAPError("IMAP credentials are not configured.")

    try:
        conn = imaplib.IMAP4_SSL(host, port)
        conn.login(user, password)
        return conn
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"IMAP login failed: {e}")
    except OSError as e:
        raise IMAPError(f"Cannot connect to mail server: {e}")


def fetch_inbox(limit=50):
    """Return a list of message summary dicts, newest first."""
    conn = _connect()
    try:
        conn.select("INBOX", readonly=True)
        _, data = conn.search(None, "ALL")
        message_ids = data[0].split()
        # Newest first, limited
        message_ids = message_ids[-limit:][::-1]

        messages = []
        for uid in message_ids:
            _, msg_data = conn.fetch(uid, "(RFC822.HEADER FLAGS)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            flags = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
            is_read = "\\Seen" in flags

            messages.append({
                "uid": uid.decode(),
                "subject": _decode_header(msg.get("Subject", "(no subject)")),
                "from": _decode_header(msg.get("From", "")),
                "date": msg.get("Date", ""),
                "is_read": is_read,
            })
        return messages
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"Failed to fetch inbox: {e}")
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def fetch_message(uid):
    """Return a full parsed message dict for the given UID."""
    conn = _connect()
    try:
        conn.select("INBOX", readonly=True)
        _, msg_data = conn.fetch(uid.encode(), "(RFC822)")
        if not msg_data or not msg_data[0]:
            raise IMAPError("Message not found.")

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw, policy=policy.default)

        body, is_html = _get_body(msg)

        return {
            "uid": uid,
            "subject": _decode_header(msg.get("Subject", "(no subject)")),
            "from": _decode_header(msg.get("From", "")),
            "to": _decode_header(msg.get("To", "")),
            "date": msg.get("Date", ""),
            "body": body,
            "is_html": is_html,
        }
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"Failed to fetch message: {e}")
    finally:
        try:
            conn.logout()
        except Exception:
            pass
