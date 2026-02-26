from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class LlmResult:
    text: str
    used_model: bool


class LlmEngine:
    """
    Offline local LLM wrapper.

    - Never downloads weights at runtime.
    - If model cannot be loaded, falls back to a safe template drafter.
    """

    def __init__(self, model_dir: str, temperature: float, max_new_tokens: int, max_input_chars: int) -> None:
        self.model_dir = model_dir
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens
        self.max_input_chars = max_input_chars

        self._tokenizer = None
        self._model = None

        # Strongly discourage any network calls by transformers
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_HUB_OFFLINE", "1")

    def try_load(self) -> bool:
        if self._model is not None:
            return True
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            tok = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True, trust_remote_code=True)

            # bitsandbytes 4-bit may not be available on Windows; keep loading robust.
            model = None
            try:
                from transformers import BitsAndBytesConfig  # type: ignore

                bnb = BitsAndBytesConfig(load_in_4bit=True)
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_dir,
                    local_files_only=True,
                    trust_remote_code=True,
                    quantization_config=bnb,
                    device_map="auto",
                )
            except Exception:
                # Fallback to fp16 if available, else cpu fp32
                dtype = torch.float16 if torch.cuda.is_available() else torch.float32
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_dir,
                    local_files_only=True,
                    trust_remote_code=True,
                    dtype=dtype,
                    device_map="auto" if torch.cuda.is_available() else None,
                )

            self._tokenizer = tok
            self._model = model
            return True
        except Exception as e:
            # Surface reason in console so users can debug why local LLM failed.
            print(f"[LLM] Failed to load local model from '{self.model_dir}': {e}")
            self._tokenizer = None
            self._model = None
            return False

    def draft_reply(self, email_from: str, subject: str, email_body: str) -> LlmResult:
        # Safety: cap input size
        body = (email_body or "")[: self.max_input_chars]
        if self.try_load():
            try:
                return LlmResult(text=self._draft_with_model(email_from, subject, body), used_model=True)
            except Exception:
                # Model loaded but generation failed; fallback
                pass
        return LlmResult(text=_template_reply(email_from, subject, body), used_model=False)

    def infer_intent(self, utterance: str) -> Optional[dict[str, Any]]:
        """
        Best-effort intent inference as structured data.

        Returns:
          - {"intent": "read_latest"}
          - {"intent": "read_latest", "max_results": 2}
          - {"intent": "reply_draft", "message_index": 2}
          - {"intent": "help"} / {"intent": "sign_out"}
        """
        u = (utterance or "").strip()
        if not u:
            return None
        if not self.try_load():
            return None
        try:
            return self._infer_intent_with_model(u)
        except Exception:
            return None

    def _infer_intent_with_model(self, utterance: str) -> Optional[dict[str, Any]]:
        assert self._model is not None and self._tokenizer is not None

        system_prompt = (
            "You are an intent classifier for a local Gmail voice assistant.\n"
            "Return ONLY valid JSON. No extra text.\n"
            "Supported intents:\n"
            '- {"intent":"read_latest"} (Use when user wants to read, check, or fetch emails)\n'
            '- {"intent":"read_latest","max_results":2}\n'
            '- {"intent":"reply_draft","message_index":2} (Use when user wants to reply to a specific email)\n'
            '- {"intent":"help"} (Use when user asks what they can do)\n'
            '- {"intent":"sign_out"} (Use when user wants to log out)\n'
            '- {"intent":"chat","chat_response":"Hello! How can I help?"} (CRITICAL: Use this for ANY greeting like "Hello", small talk, or conversational questions. Provide a short, friendly response.)\n'
            '- {"intent":"unknown"} (Use for commands that are completely incomprehensible or unsupported)\n'
            "Rules:\n"
            "- message_index must be an integer if present.\n\n"
            "- max_results must be an integer (1-20) if present.\n\n"
            "- chat_response must be a short string if intent is chat.\n\n"
            "Examples:\n"
            'User: "Read my emails"\nJSON:\n{"intent":"read_latest"}\n\n'
            'User: "Hello, how are you?"\nJSON:\n{"intent":"chat","chat_response":"I\'m doing great, thanks for asking! Need help with your emails?"}\n\n'
            'User: "Reply to message 2"\nJSON:\n{"intent":"reply_draft","message_index":2}\n\n'
            'User: "Hi"\nJSON:\n{"intent":"chat","chat_response":"Hi there! How can I assist you today?"}\n'
        )
        
        # Build chat messages for instruction-tuned models
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": utterance}
        ]
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        
        import torch

        inputs = self._tokenizer(prompt, return_tensors="pt")
        if hasattr(self._model, "device"):
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.0,
                do_sample=False,
                pad_token_id=getattr(self._tokenizer, "eos_token_id", None),
            )

        text = self._tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        # Extract the first JSON object in output
        obj = _extract_first_json_object(text)
        if not obj:
            return None
        data = json.loads(obj)
        if not isinstance(data, dict):
            return None
        intent = str(data.get("intent", "")).strip()
        if intent not in {"read_latest", "reply_draft", "help", "sign_out", "unknown", "chat"}:
            return None
        if intent == "reply_draft":
            mi = data.get("message_index")
            if not isinstance(mi, int):
                return None
        if intent == "read_latest" and "max_results" in data:
            mr = data.get("max_results")
            if not isinstance(mr, int):
                return None
            if mr < 1 or mr > 20:
                return None
        return data

    def _draft_with_model(self, email_from: str, subject: str, email_body: str) -> str:
        assert self._model is not None and self._tokenizer is not None

        prompt = (
            "You are a helpful assistant that drafts professional, friendly email replies.\n"
            "Rules:\n"
            "- Keep it concise.\n"
            "- Do not invent facts.\n"
            "- If details are missing, ask a clear question.\n\n"
            f"Email from: {email_from}\n"
            f"Subject: {subject}\n"
            "Email content:\n"
            f"{email_body}\n\n"
            "Draft a reply:\n"
        )

        import torch

        inputs = self._tokenizer(prompt, return_tensors="pt")
        if hasattr(self._model, "device"):
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}

        with torch.no_grad():
            out = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=True,
                pad_token_id=getattr(self._tokenizer, "eos_token_id", None),
            )
        text = self._tokenizer.decode(out[0], skip_special_tokens=True)
        # Return the part after the prompt
        if "Draft a reply:" in text:
            text = text.split("Draft a reply:", 1)[-1].strip()
        return text.strip()


def _extract_first_json_object(text: str) -> str:
    # naive but robust enough for small outputs
    start = text.find("{")
    if start < 0:
        return ""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return ""


def _template_reply(email_from: str, subject: str, email_body: str) -> str:
    name = email_from.split("<")[0].strip() or "there"
    return (
        f"Hi {name},\n\n"
        "Thanks for your email. I’ve reviewed your message and wanted to follow up.\n\n"
        "Could you please confirm the key details/timeline you prefer? Once I have that, I can proceed.\n\n"
        "Best regards,\n"
        "[Your Name]"
    )

