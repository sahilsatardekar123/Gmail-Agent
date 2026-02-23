from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    # Point these at locally-downloaded model folders (no runtime downloads)
    qwen_model_dir: Path = Path("models") / "qwen2.5-1.5b-instruct"
    # Use "base" or "small" for auto-download on first use; or a path like "models/whisper" for offline.
    whisper_model: str = "base"

    # Generation
    temperature: float = 0.4
    max_new_tokens: int = 220

    # VRAM safety
    max_input_chars: int = 6000

