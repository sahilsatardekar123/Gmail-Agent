from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any


_TOKEN_RE = re.compile(r"(ya29\.[0-9A-Za-z\-_]+|1//[0-9A-Za-z\-_]+)")


def _redact(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        v = _TOKEN_RE.sub("[REDACTED_TOKEN]", value)
        # avoid dumping huge content (emails/audio)
        if len(v) > 2000:
            return v[:2000] + "...[TRUNCATED]"
        return v
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items() if k.lower() not in {"access_token", "refresh_token"}}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


@dataclass(frozen=True)
class Logger:
    name: str = "dior"
    level: int = logging.INFO

    def build(self) -> logging.Logger:
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        logger.propagate = False
        return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.info(json.dumps(_redact(payload), ensure_ascii=False))

