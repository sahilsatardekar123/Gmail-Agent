from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class EmailSummary:
    id: str
    thread_id: str
    from_: str
    subject: str
    date: str
    snippet: str


@dataclass(frozen=True)
class EmailFull:
    id: str
    thread_id: str
    from_: str
    reply_to: str
    to: str
    subject: str
    date: str
    message_id: str
    references: str
    body_text: str


def _header(headers: list[dict[str, str]], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def list_latest(service, max_results: int, query: str) -> list[EmailSummary]:
    resp = (
        service.users()
        .messages()
        .list(userId="me", maxResults=max_results, q=query)
        .execute()
    )
    msgs = resp.get("messages", []) or []

    out: list[EmailSummary] = []
    for m in msgs:
        msg_id = m["id"]
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
                fields="id,threadId,snippet,payload/headers",
            )
            .execute()
        )
        headers = (msg.get("payload") or {}).get("headers") or []
        out.append(
            EmailSummary(
                id=msg.get("id", ""),
                thread_id=msg.get("threadId", ""),
                from_=_header(headers, "From"),
                subject=_header(headers, "Subject"),
                date=_header(headers, "Date"),
                snippet=msg.get("snippet", ""),
            )
        )
    return out


def get_full_message(service, message_id: str) -> EmailFull:
    msg = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = msg.get("payload") or {}
    headers = payload.get("headers") or []

    body_text = _extract_best_text(payload)
    return EmailFull(
        id=msg.get("id", ""),
        thread_id=msg.get("threadId", ""),
        from_=_header(headers, "From"),
        reply_to=_header(headers, "Reply-To"),
        to=_header(headers, "To"),
        subject=_header(headers, "Subject"),
        date=_header(headers, "Date"),
        message_id=_header(headers, "Message-ID"),
        references=_header(headers, "References"),
        body_text=body_text,
    )


def _extract_best_text(payload: dict[str, Any]) -> str:
    # Prefer text/plain; fallback to first decodable part; fallback empty.
    parts = payload.get("parts")
    if not parts:
        return _decode_body(payload.get("body"))

    plain = _find_part(parts, "text/plain")
    if plain is not None:
        return _decode_body((plain.get("body") or {}))

    # try any text/* part
    any_text = _find_part_prefix(parts, "text/")
    if any_text is not None:
        return _decode_body((any_text.get("body") or {}))

    # fallback to first part with data
    for p in parts:
        text = _decode_body(p.get("body"))
        if text.strip():
            return text
        subparts = p.get("parts") or []
        if subparts:
            text2 = _extract_best_text({"parts": subparts})
            if text2.strip():
                return text2
    return ""


def _find_part(parts: list[dict[str, Any]], mime_type: str) -> Optional[dict[str, Any]]:
    for p in parts:
        if p.get("mimeType") == mime_type:
            return p
        sub = p.get("parts") or []
        if sub:
            found = _find_part(sub, mime_type)
            if found is not None:
                return found
    return None


def _find_part_prefix(parts: list[dict[str, Any]], prefix: str) -> Optional[dict[str, Any]]:
    for p in parts:
        mt = p.get("mimeType") or ""
        if mt.startswith(prefix):
            return p
        sub = p.get("parts") or []
        if sub:
            found = _find_part_prefix(sub, prefix)
            if found is not None:
                return found
    return None


def _decode_body(body: Optional[dict[str, Any]]) -> str:
    if not body:
        return ""
    data = body.get("data")
    if not data:
        return ""
    try:
        raw = base64.urlsafe_b64decode(data.encode("utf-8"))
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""

