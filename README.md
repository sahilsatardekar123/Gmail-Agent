# Local Voice-Controlled Gmail AI Agent (V1)

Runs locally on Windows. Speech-to-text + LLM inference are **offline**; only Gmail API calls require internet.

## What this does (V1)
- Push-to-talk voice input (or text fallback)
- Read latest Gmail emails (sender/subject/snippet)
- Draft a reply with a local LLM (or a template fallback)
- **Never sends** without explicit confirmation

## Google/Gmail API setup (personal use)
1. Create a Google Cloud project and enable **Gmail API**.
2. Configure **OAuth consent screen** and add yourself as a **test user**.
3. Create OAuth Client ID: **Desktop app**.
4. Download the client JSON and save it as:
   - `secrets/oauth_client.json`

This app uses these scopes (least privilege for V1):
- `https://www.googleapis.com/auth/gmail.readonly`
- `https://www.googleapis.com/auth/gmail.send`

## Install
Create a venv and install deps:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

### Optional (offline voice + offline LLM)
For **full V1** (voice + local model), install extras (recommended on Python **3.11/3.12**):

```bash
pip install -r requirements-voice.txt
pip install -r requirements-llm.txt
```

## Run

```bash
python main.py
```

## Local-only model weights
Put your local model folders under `models/` (no runtime downloads). Configure paths in `config/model_config.py`.

## Security notes
- `secrets/oauth_client.json` and `secrets/token.json` are sensitive; do not share.
- Logs are redacted; tokens are never printed.

