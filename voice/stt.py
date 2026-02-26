from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SttResult:
    text: str
    used_model: bool


class SpeechToText:
    """
    Offline speech-to-text.

    Prefers faster-whisper if installed. Never downloads at runtime unless you pass a built-in model name
    that faster-whisper needs to fetch; for strict offline usage, point `model` to a local directory.
    """

    def __init__(self, model: str) -> None:
        self.model = model
        self._whisper = None

    def try_load(self) -> bool:
        if self._whisper is not None:
            return True
        try:
            from faster_whisper import WhisperModel  # type: ignore

            # device auto: uses CUDA if available
            self._whisper = WhisperModel(self.model, device="auto", compute_type="int8")
            return True
        except Exception as e:
            # Surface a basic hint in the terminal if the model cannot be loaded.
            print(f"[voice] Failed to load Whisper model '{self.model}': {e}")
            self._whisper = None
            return False

    def transcribe_wav(self, wav_path: str) -> SttResult:
        if not self.try_load():
            return SttResult(text="", used_model=False)
        segments, _info = self._whisper.transcribe(wav_path, vad_filter=True)
        text = " ".join((s.text or "").strip() for s in segments).strip()
        return SttResult(text=text, used_model=True)

