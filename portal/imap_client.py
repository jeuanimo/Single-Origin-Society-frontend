"""
IMAP client for the staff portal inbox.
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


# ── IMAP flag constants ───────────────────────────────────────────────────────
FLAG_SEEN = "\\Seen"
FLAG_FLAGGED = "\\Flagged"
FLAG_DELETED = "\\Deleted"
FLAGS_ADD = "+FLAGS"
FLAGS_REMOVE = "-FLAGS"

ORDER_SUBJECT_MARKER = "Order"


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _decode_part(part):
    """Decode a MIME part payload to a string."""
    payload = part.get_payload(decode=True)
    if not payload:
        return ""
    charset = part.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="replace")


def _get_body(msg):
    """Return (body_text, is_html) from a parsed email message."""
    if not msg.is_multipart():
        payload = msg.get_payload(decode=True)
        if not payload:
            return "", False
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace"), msg.get_content_type() == "text/html"

    html_part = None
    plain_part = None
    for part in msg.walk():
        ct = part.get_content_type()
        if ct == "text/html" and html_part is None:
            html_part = part
        elif ct == "text/plain" and plain_part is None:
            plain_part = part

    if html_part:
        return _decode_part(html_part), True
    if plain_part:
        return _decode_part(plain_part), False
    return "", False


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
        raise IMAPError(f"IMAP login failed: {e}") from e
    except OSError as e:
        raise IMAPError(f"Cannot connect to mail server: {e}") from e


def _logout(conn):
    try:
        conn.logout()
    except Exception as e:  # noqa: BLE001
        import logging
        logging.getLogger(__name__).debug("IMAP logout error (ignored): %s", e)


def _is_order_email(subject):
    return ORDER_SUBJECT_MARKER in subject


def _auto_flag_orders(conn, message_ids):
    """Flag any unflagged order notification emails."""
    for uid in message_ids:
        _, msg_data = conn.fetch(uid, "(RFC822.HEADER FLAGS)")
        if not msg_data or not msg_data[0]:
            continue
        flags_str = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
        msg = email.message_from_bytes(msg_data[0][1])
        subject = _decode_header(msg.get("Subject", ""))
        if _is_order_email(subject) and FLAG_FLAGGED not in flags_str:
            conn.store(uid, FLAGS_ADD, FLAG_FLAGGED)


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_inbox(limit=50):
    """Return a list of message summary dicts, newest first."""
    conn = _connect()
    try:
        conn.select("INBOX")
        _, data = conn.search(None, "ALL")
        message_ids = data[0].split()
        message_ids = message_ids[-limit:][::-1]

        _auto_flag_orders(conn, message_ids)

        result = []
        for uid in message_ids:
            _, msg_data = conn.fetch(uid, "(RFC822.HEADER FLAGS)")
            if not msg_data or not msg_data[0]:
                continue
            flags = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
            msg = email.message_from_bytes(msg_data[0][1])
            result.append({
                "uid": uid.decode(),
                "subject": _decode_header(msg.get("Subject", "(no subject)")),
                "from": _decode_header(msg.get("From", "")),
                "date": msg.get("Date", ""),
                "is_read": FLAG_SEEN in flags,
                "is_important": FLAG_FLAGGED in flags,
            })
        return result
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"Failed to fetch inbox: {e}") from e
    finally:
        _logout(conn)


def fetch_message(uid):
    """Return a full parsed message dict for the given UID."""
    conn = _connect()
    try:
        conn.select("INBOX", readonly=True)
        _, msg_data = conn.fetch(uid.encode(), "(RFC822)")
        if not msg_data or not msg_data[0]:
            raise IMAPError("Message not found.")
        msg = email.message_from_bytes(msg_data[0][1], policy=policy.default)
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
        raise IMAPError(f"Failed to fetch message: {e}") from e
    finally:
        _logout(conn)


def mark_unread(uid):
    conn = _connect()
    try:
        conn.select("INBOX")
        conn.store(uid.encode(), FLAGS_REMOVE, FLAG_SEEN)
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"Failed to mark message unread: {e}") from e
    finally:
        _logout(conn)


def toggle_important(uid, flagged):
    conn = _connect()
    try:
        conn.select("INBOX")
        action = FLAGS_ADD if flagged else FLAGS_REMOVE
        conn.store(uid.encode(), action, FLAG_FLAGGED)
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"Failed to update flag: {e}") from e
    finally:
        _logout(conn)


def delete_message(uid):
    conn = _connect()
    try:
        conn.select("INBOX")
        conn.store(uid.encode(), FLAGS_ADD, FLAG_DELETED)
        conn.expunge()
    except imaplib.IMAP4.error as e:
        raise IMAPError(f"Failed to delete message: {e}") from e
    finally:
        _logout(conn)
