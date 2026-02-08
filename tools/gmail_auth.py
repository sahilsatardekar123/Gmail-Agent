from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.gmail_config import GmailConfig


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_gmail_service(cfg: GmailConfig):
    """
    Returns an authenticated Gmail API service.

    Uses installed-app OAuth flow with a localhost redirect.
    Tokens are stored locally at cfg.token_path.
    """
    # Prevent any accidental model downloads from transformers in this process
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    token_path = Path(cfg.token_path)
    client_path = Path(cfg.oauth_client_path)

    creds: Optional[Credentials] = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes=list(cfg.scopes))

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_path.exists():
                raise FileNotFoundError(
                    f"Missing OAuth client file at '{client_path}'. "
                    f"Download a Desktop OAuth client JSON and save it there."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_path), scopes=list(cfg.scopes))
            creds = flow.run_local_server(port=0, open_browser=True)

        _ensure_parent_dir(token_path)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def sign_out(cfg: GmailConfig) -> bool:
    token_path = Path(cfg.token_path)
    if token_path.exists():
        token_path.unlink()
        return True
    return False

