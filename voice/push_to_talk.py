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
    # Duration (seconds) cap for each voice command recording.
    duration_seconds: int = 5
    # Keyboard key used for push-to-talk (e.g. "space").
    push_key: str = "space"


class PushToTalk:
    """
    Hold-to-record audio capture.

    Uses `keyboard` for key state; if that fails (permissions), callers should fall back to text mode.
    """

    def __init__(self, cfg: AudioCaptureConfig) -> None:
        self.cfg = cfg

    def record_while_held(
        self, out_wav_path: Path, key: Optional[str] = None, max_seconds: int = 20
    ) -> bool:
        """
        Record audio while a keyboard key is held down.

        Returns True if audio was captured and written to `out_wav_path`,
        otherwise False (e.g. no key press detected or no audio frames).
        """
        import sounddevice as sd
        import keyboard

        # Resolve which key to use for push-to-talk.
        effective_key = (key or self.cfg.push_key).lower()

        out_wav_path.parent.mkdir(parents=True, exist_ok=True)

        # Phase 1: wait briefly for the key to be pressed.
        wait_timeout = 5.0
        wait_start = time.time()
        print(
            f"Hold {effective_key.upper()} to talk (or wait for text input prompt)..."
        )
        while time.time() - wait_start < wait_timeout:
            if keyboard.is_pressed(effective_key):
                break
            time.sleep(0.05)
        else:
            # No key press detected within the timeout – fall back to text.
            return False

        # Phase 2: record while the key is held (up to max_seconds/config cap).
        q: "queue.Queue[np.ndarray]" = queue.Queue()

        def callback(indata, frames, time_info, status):  # noqa: ANN001
            if status:
                return
            q.put(indata.copy())

        print("Recording... release key to send.")

        start_t = time.time()
        frames: list[np.ndarray] = []
        max_duration = min(self.cfg.duration_seconds, max_seconds)

        with sd.InputStream(
            samplerate=self.cfg.sample_rate,
            channels=self.cfg.channels,
            dtype=self.cfg.dtype,
            callback=callback,
        ):
            while keyboard.is_pressed(effective_key) and time.time() - start_t < max_duration:
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

