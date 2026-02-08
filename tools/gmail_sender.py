from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import parseaddr

from tools.gmail_reader import EmailFull


@dataclass(frozen=True)
class SendResult:
    id: str
    thread_id: str


def _strip_re(subject: str) -> str:
    s = subject.strip()
    if not s:
        return s
    # Collapse multiple Re:
    s2 = re.sub(r"^(?:(?:re|fw|fwd)\s*:\s*)+", "", s, flags=re.IGNORECASE).strip()
    return f"Re: {s2}" if s2 else "Re:"


def send_reply(service, original: EmailFull, reply_text: str) -> SendResult:
    # Prefer Reply-To (if present), otherwise From:
    reply_to = original.reply_to or original.from_
    _, addr = parseaddr(reply_to)
    to_addr = addr or reply_to

    msg = MIMEText(reply_text, _charset="utf-8")
    msg["To"] = to_addr
    msg["Subject"] = _strip_re(original.subject)

    if original.message_id:
        msg["In-Reply-To"] = original.message_id
        msg["References"] = (original.references + " " + original.message_id).strip() if original.references else original.message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    sent = (
        service.users()
        .messages()
        .send(userId="me", body={"raw": raw, "threadId": original.thread_id})
        .execute()
    )
    return SendResult(id=sent.get("id", ""), thread_id=sent.get("threadId", ""))

