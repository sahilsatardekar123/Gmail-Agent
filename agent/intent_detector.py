from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from agent.llm_engine import LlmEngine


@dataclass(frozen=True)
class Intent:
    name: str  # read_latest | reply_draft | sign_out | help | unknown
    message_index: Optional[int] = None  # 1-based index from the list shown to user
    max_results: Optional[int] = None  # for read_latest: user-requested count


_REPLY_RE = re.compile(r"\b(reply|respond)\b.*?\b(\d+)\b", re.IGNORECASE)
_READ_LAST_N_RE = re.compile(
    r"\b(?:fetch|get|show|read)\b.*?\b(?:last|latest)\b.*?\b(\d+)\b.*?\b(?:mail|mails|email|emails|message|messages)\b",
    re.IGNORECASE,
)


def detect_intent(text: str) -> Intent:
    t = (text or "").strip()
    if not t:
        return Intent(name="unknown")

    low = t.lower()
    if "sign out" in low or "logout" in low:
        return Intent(name="sign_out")
    if "help" in low or "what can you do" in low:
        return Intent(name="help")

    if "read" in low or "latest" in low or "inbox" in low:
        m = _READ_LAST_N_RE.search(t)
        if m:
            try:
                return Intent(name="read_latest", max_results=int(m.group(1)))
            except Exception:
                return Intent(name="read_latest")
        return Intent(name="read_latest")

    m = _READ_LAST_N_RE.search(t)
    if m:
        try:
            return Intent(name="read_latest", max_results=int(m.group(1)))
        except Exception:
            return Intent(name="read_latest")

    m = _REPLY_RE.search(t)
    if m:
        idx = int(m.group(2))
        return Intent(name="reply_draft", message_index=idx)

    # Fallback: "reply 2"
    m2 = re.search(r"\breply\s+(\d+)\b", low)
    if m2:
        return Intent(name="reply_draft", message_index=int(m2.group(1)))

    return Intent(name="unknown")


class IntentDetector:
    """
    Hybrid intent detection:
    - fast rule-based pass
    - optional offline LLM fallback to produce structured args
    """

    def __init__(self, llm: Optional[LlmEngine] = None) -> None:
        self.llm = llm

    def detect(self, text: str) -> Intent:
        base = detect_intent(text)
        if base.name != "unknown" or self.llm is None:
            return base

        inferred = self.llm.infer_intent(text)
        if not inferred:
            return base

        name = str(inferred.get("intent", "unknown"))
        if name == "reply_draft":
            mi = inferred.get("message_index")
            if isinstance(mi, int):
                return Intent(name="reply_draft", message_index=mi)
            return Intent(name="unknown")
        if name == "read_latest":
            mr = inferred.get("max_results")
            if isinstance(mr, int):
                return Intent(name="read_latest", max_results=mr)
            return Intent(name="read_latest")
        if name in {"help", "sign_out"}:
            return Intent(name=name)
        return Intent(name="unknown")

