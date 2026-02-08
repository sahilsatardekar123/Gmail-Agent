from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GmailConfig:
    # Least-privilege scopes for V1
    scopes: tuple[str, ...] = (
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
    )

    # Secrets live outside source control (see README)
    oauth_client_path: Path = Path("secrets") / "oauth_client.json"
    token_path: Path = Path("secrets") / "token.json"

    # Default query / list size
    list_max_results: int = 5
    list_query: str = "newer_than:7d"

