from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def make_chime(sample_rate: int = 16000) -> np.ndarray:
    """Generate a clean two-tone chime in 16 kHz audio without external asset files.

    Tone 1: 587.33 Hz (D5) for 120 ms
    Tone 2: 880.00 Hz (A5) for 160 ms
    Total: 280 ms (4,480 samples), well within the 1,600 - 9,600 sample bounds.
    """
    t1 = np.linspace(0, 0.12, int(sample_rate * 0.12), endpoint=False)
    tone1 = np.sin(2 * np.pi * 587.33 * t1)
    # Cosine taper for tone1
    env1 = np.sin(np.pi * np.linspace(0, 1, len(t1))) ** 2
    tone1 = tone1 * env1

    t2 = np.linspace(0, 0.16, int(sample_rate * 0.16), endpoint=False)
    tone2 = np.sin(2 * np.pi * 880.00 * t2)
    # Cosine taper for tone2
    env2 = np.sin(np.pi * np.linspace(0, 1, len(t2))) ** 2
    tone2 = tone2 * env2

    chime = np.concatenate([tone1, tone2]) * 0.25
    return chime.astype(np.float32)


class WakeDetector:
    """Detects 'Hey Jarvis' wake word using openWakeWord with cooldown and speech-pause safety."""

    def __init__(
        self,
        threshold: float = 0.5,
        cooldown_seconds: float = 2.0,
        model_name: str = "hey_jarvis",
        load_model: bool = False,
    ) -> None:
        self.threshold = float(threshold)
        self.cooldown_seconds = float(cooldown_seconds)
        self.model_name = model_name
        self._paused = False
        self._last_fire_time = -1e9
        self._model: Any = None

        if load_model:
            self._ensure_model_loaded()

    def _ensure_model_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import openwakeword
            self._model = openwakeword.Model(wakeword_models=[self.model_name])
        except Exception as exc:
            logger.error("Failed to load wake word model '%s': %s", self.model_name, exc)
            raise RuntimeError(f"Could not load wake word model '{self.model_name}': {exc}") from exc

    def pause(self) -> None:
        """Pause detection while Jarvis is speaking."""
        self._paused = True

    def resume(self) -> None:
        """Resume detection and flush internal buffers so residual speech cannot wake."""
        self._paused = False
        if self._model is not None:
            try:
                self._model.reset()
            except Exception:
                pass

    def process_score(self, score: float, timestamp: float | None = None) -> bool:
        """Evaluate a wake score with threshold and cooldown filtering."""
        if self._paused:
            return False

        current_time = time.monotonic() if timestamp is None else timestamp
        if current_time - self._last_fire_time < self.cooldown_seconds:
            return False

        if score >= self.threshold:
            self._last_fire_time = current_time
            return True

        return False

    def process_frame(self, frame: np.ndarray, timestamp: float | None = None) -> bool:
        """Feed an audio frame (16kHz 16-bit mono) and return True if wake detected."""
        if self._paused:
            return False

        self._ensure_model_loaded()
        prediction = self._model.predict(frame)
        score = float(prediction.get(self.model_name, 0.0))
        return self.process_score(score, timestamp=timestamp)
