from __future__ import annotations

import queue
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class AudioCaptureConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    hotkey: str = "space"  # hold-to-record


class PushToTalk:
    """
    Hold-to-record audio capture.

    Uses `keyboard` for key state; if that fails (permissions), callers should fall back to text mode.
    """

    def __init__(self, cfg: AudioCaptureConfig) -> None:
        self.cfg = cfg

    def record_while_held(self, out_wav_path: Path, max_seconds: int = 20) -> bool:
        import sounddevice as sd
        import keyboard  # type: ignore

        out_wav_path.parent.mkdir(parents=True, exist_ok=True)

        q: "queue.Queue[np.ndarray]" = queue.Queue()

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                return
            q.put(indata.copy())

        started = False
        start_t = time.time()

        with sd.InputStream(
            samplerate=self.cfg.sample_rate,
            channels=self.cfg.channels,
            dtype=self.cfg.dtype,
            callback=callback,
        ):
            # Wait for initial press
            while time.time() - start_t < 10:
                if keyboard.is_pressed(self.cfg.hotkey):
                    started = True
                    break
                time.sleep(0.01)

            if not started:
                return False

            frames: list[np.ndarray] = []
            press_t = time.time()
            while keyboard.is_pressed(self.cfg.hotkey) and (time.time() - press_t) < max_seconds:
                try:
                    frames.append(q.get(timeout=0.25))
                except queue.Empty:
                    pass

        if not frames:
            return False

        audio = np.concatenate(frames, axis=0)
        # Ensure int16 PCM
        if audio.dtype != np.int16:
            audio = (audio * 32767.0).astype(np.int16)

        with wave.open(str(out_wav_path), "wb") as wf:
            wf.setnchannels(self.cfg.channels)
            wf.setsampwidth(2)  # int16
            wf.setframerate(self.cfg.sample_rate)
            wf.writeframes(audio.tobytes())

        return True

