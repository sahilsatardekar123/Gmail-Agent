from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

from tools.gmail_reader import EmailFull, EmailSummary, get_full_message, list_latest
from tools.gmail_sender import SendResult, send_reply


T = TypeVar("T")


@dataclass
class RouterState:
    latest: list[EmailSummary]
    selected: Optional[EmailFull] = None
    draft: Optional[str] = None


def _with_backoff(fn: Callable[[], T], max_attempts: int = 4) -> T:
    delay = 0.5
    last_exc: Optional[Exception] = None
    for _ in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            time.sleep(delay)
            delay *= 2
    assert last_exc is not None
    raise last_exc


def gmail_list_latest(service, max_results: int, query: str) -> list[EmailSummary]:
    return _with_backoff(lambda: list_latest(service, max_results=max_results, query=query))


def gmail_get_full(service, message_id: str) -> EmailFull:
    return _with_backoff(lambda: get_full_message(service, message_id=message_id))


def gmail_send_reply(service, original: EmailFull, reply_text: str) -> SendResult:
    return _with_backoff(lambda: send_reply(service, original=original, reply_text=reply_text))

