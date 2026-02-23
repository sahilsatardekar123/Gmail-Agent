# Step-by-step guide to complete the Gmail Voice Agent (V1)

Follow these steps in order. You can stop after **Step 4** and use the app in **text-only mode** (no voice, template replies). Steps 5–6 add voice and the local LLM.

---

## Prerequisites

- **Windows** (as per your plan)
- **Python 3.11 or 3.12** (recommended for voice + LLM)
- **Google account** (for Gmail API)
- **NVIDIA GPU (e.g. RTX 3050)** optional but recommended for LLM + faster-whisper

---

## Step 1: Set up the Python environment

1. Open **PowerShell** or **Command Prompt** and go to the project folder:
   ```powershell
   cd c:\Users\sahil\OneDrive\Desktop\dior
   ```

2. Create a virtual environment:
   ```powershell
   python -m venv .venv
   ```

3. Activate it:
   ```powershell
   .venv\Scripts\activate
   ```
   You should see `(.venv)` in the prompt.

4. Install the **base** dependencies (Gmail + auth only):
   ```powershell
   pip install -r requirements.txt
   ```

After this, the app can run in **text-only mode** once Gmail is set up (no voice, no local LLM; replies use a simple template).

---

## Step 2: Google Cloud & Gmail API setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).

2. **Create a project** (or pick an existing one):
   - Top bar: click the project name → **New Project**
   - Name it (e.g. `dior-gmail`) → **Create**

3. **Enable Gmail API**:
   - Left menu: **APIs & Services** → **Library**
   - Search for **Gmail API** → open it → **Enable**

4. **Configure OAuth consent screen**:
   - **APIs & Services** → **OAuth consent screen**
   - User type: **External** → **Create**
   - Fill **App name** (e.g. `Dior Gmail Agent`) and **User support email**
   - **Developer contact**: your email → **Save and Continue**
   - **Scopes**: **Add or Remove Scopes** → add:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
   - **Save and Continue**
   - **Test users**: **Add Users** → add your Gmail address → **Save and Continue**
   - **Back to dashboard**

5. **Create OAuth client (Desktop app)**:
   - **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name (e.g. `Dior Desktop`) → **Create**
   - In the popup: **Download JSON**
   - Save the file somewhere you can find it (e.g. Downloads); you’ll move it in Step 3.

---

## Step 3: Put the secret file in the project

1. In the project folder, create a `secrets` folder if it doesn’t exist:
   ```powershell
   mkdir secrets
   ```

2. Move (or copy) the downloaded JSON into the project and **rename** it exactly to:
   ```
   c:\Users\sahil\OneDrive\Desktop\dior\secrets\oauth_client.json
   ```

3. Confirm the file exists:
   ```powershell
   dir secrets
   ```
   You should see `oauth_client.json`.

**Important:** Never commit `secrets/` to git (it’s in `.gitignore`).

---

## Step 4: Run the app (text-only mode)

1. With the venv still activated, run:
   ```powershell
   python main.py
   ```

2. **First run:** A browser window will open for Google sign-in. Log in with the Gmail account you added as a test user and allow the requested permissions. After that, the app will save a token and won’t ask again (until it expires or you sign out).

3. In the terminal you’ll see something like:
   ```
   Local Gmail Voice Agent (V1)
   Voice mode unavailable (missing optional deps). Using text-only mode.
   Fix: python -m pip install -r requirements-voice.txt
   ```

4. **Test Gmail (read + reply):**
   - Type: `read latest emails` → Enter  
     You should see a short list of recent emails (sender, subject, snippet).
   - Type: `reply 2` (or another number from the list) → Enter  
     The app will draft a reply (template if no LLM), show it, and ask: **Send this reply now? (y/N):**
   - Type `n` to not send, or `y` to send (only if you’re sure).

5. Other commands:
   - `help` – list commands
   - `sign out` – delete the saved token (you’ll re-auth next run)
   - `quit` or `q` – exit

If Step 4 works, **Gmail read & reply with confirmation is done.** The rest is optional (voice and local LLM).

---

## Step 5 (Optional): Add voice (push-to-talk + offline STT)

1. Install voice dependencies (with venv active):
   ```powershell
   pip install -r requirements-voice.txt
   ```

2. **First run:** faster-whisper may download a small model once (e.g. `small` or `base`) if you use a built-in name. For **strict offline** later, you can point to a local model folder in config (see `config/model_config.py` → `whisper_model`).

3. Run again:
   ```powershell
   python main.py
   ```
   You should see: “Tip: hold SPACE to record voice; press Enter to use text instead.”

4. **Test voice:**
   - Hold **Space**, say “read latest emails”, release Space.  
     After a short delay you should see the same list as in text mode.
   - Or press **Enter** and type as before.

If you get errors (e.g. `keyboard` permissions on Windows), you can keep using text input only; the app falls back to “You> ” when voice isn’t used.

---

## Step 6 (Optional): Add local LLM (Qwen for drafting replies)

1. Install LLM dependencies (with venv active):
   ```powershell
   pip install -r requirements-llm.txt
   ```
   This installs PyTorch and Transformers. On Windows with an NVIDIA GPU, PyTorch usually picks up CUDA from pip.

2. **Download Qwen (~2.5B) locally** (no runtime download):
   - Go to [Hugging Face – Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) (or a similar small Qwen2.5 model).
   - Download the full repo (e.g. “Files and versions” → download or use `git lfs clone` from a machine with internet).
   - Put the model folder under your project, e.g.:
     ```
     c:\Users\sahil\OneDrive\Desktop\dior\models\qwen\
     ```
     The folder should contain `config.json`, `tokenizer.json` (or similar), and the weight files (e.g. `.safetensors`).

3. **Check config:** Open `config/model_config.py`. It should have:
   ```python
   qwen_model_dir: Path = Path("models") / "qwen"
   ```
   If you used a different folder name (e.g. `Qwen2.5-1.5B-Instruct`), set:
   ```python
   qwen_model_dir: Path = Path("models") / "Qwen2.5-1.5B-Instruct"
   ```

4. Run the app:
   ```powershell
   python main.py
   ```

5. **Test LLM draft:** Say or type “read latest emails”, then “reply 2”. The draft should now be generated by Qwen instead of the short template. Confirm with `y` only if you want to send.

**If the model doesn’t load** (e.g. out-of-memory on 4GB GPU): the app falls back to the template reply automatically. You can try a smaller model or 4-bit quantization (the code already tries bitsandbytes 4-bit when available).

---

## Step 7: Final checklist

- [ ] Venv created and base deps installed (`requirements.txt`)
- [ ] Google Cloud project created, Gmail API enabled, OAuth consent + test user configured
- [ ] Desktop OAuth client created and JSON saved as `secrets/oauth_client.json`
- [ ] First run: browser login successful, token saved
- [ ] “Read latest emails” works (list appears)
- [ ] “Reply 2” (or any number) shows a draft and asks for confirmation; nothing sends without `y`
- [ ] (Optional) Voice: `requirements-voice.txt` installed, push-to-talk works
- [ ] (Optional) LLM: Qwen in `models/qwen`, draft replies use the model

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| `Missing OAuth client file at 'secrets/oauth_client.json'` | Create `secrets/` and put the downloaded JSON there with that exact name. |
| `No module named 'google...'` | Activate venv and run `pip install -r requirements.txt`. |
| Voice: `No module named 'faster_whisper'` | Run `pip install -r requirements-voice.txt`. |
| Voice: keyboard / sounddevice errors | Run as administrator once for `keyboard`, or use text input only. |
| LLM: out of memory or very slow | Use a smaller Qwen variant or ensure 4-bit is used; app will fall back to template. |
| “No messages found” | Check `config/gmail_config.py` – `list_query` is `newer_than:7d` by default; you can change it (e.g. `in:inbox`). |

---

You’re done when Step 4 works and you’ve tested read + reply with confirmation. Steps 5–6 are optional for voice and smarter drafts.
