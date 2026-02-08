from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    # Point these at locally-downloaded model folders (no runtime downloads)
    qwen_model_dir: Path = Path("models") / "qwen"
    # For strict offline use, set this to a local faster-whisper model directory.
    # If you set it to a built-in name like "small", faster-whisper may download weights the first time.
    whisper_model: str = str(Path("models") / "whisper")

    # Generation
    temperature: float = 0.4
    max_new_tokens: int = 220

    # VRAM safety
    max_input_chars: int = 6000

