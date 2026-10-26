"""Recording from the microphone until you stop talking."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

import numpy as np

SAMPLE_RATE = 16_000
BLOCK_SECONDS = 0.03  # 30 ms blocks


@dataclass
class Endpointer:
    """Decides when speech starts and ends from the loudness of each audio block.

    The first blocks measure the room's background noise; speech is anything
    clearly louder than that.
    """

    silence_seconds: float = 0.9
    start_timeout: float = 6.0
    max_seconds: float = 20.0
    calibration_seconds: float = 0.3
    min_threshold: float = 0.008

    def __post_init__(self) -> None:
        self._blocks = 0
        self._noise: list[float] = []
        self._threshold = self.min_threshold
        self._speech_blocks = 0
        self._quiet_blocks = 0
        self.heard_speech = False

    def feed(self, rms: float) -> bool:
        """Feed one block's loudness. Returns True when recording should stop."""
        self._blocks += 1
        if self._blocks <= _to_blocks(self.calibration_seconds):
            self._noise.append(rms)
            self._threshold = max(self.min_threshold, 3.0 * float(np.median(self._noise)))
            return False

        if rms > self._threshold:
            self._speech_blocks += 1
            self._quiet_blocks = 0
            if self._speech_blocks >= 3:  # ~90 ms of sound, not a click
                self.heard_speech = True
        else:
            self._quiet_blocks += 1
            if not self.heard_speech:
                self._speech_blocks = 0

        if self._blocks >= _to_blocks(self.max_seconds):
            return True
        if not self.heard_speech:
            return self._blocks >= _to_blocks(self.start_timeout)
        return self._quiet_blocks >= _to_blocks(self.silence_seconds)


def _to_blocks(seconds: float) -> int:
    # Whole blocks, so 0.9 s is exactly 30 blocks rather than 0.8999… vs 0.9.
    return round(seconds / BLOCK_SECONDS)


def record_utterance(endpointer: Endpointer | None = None) -> np.ndarray | None:
    """Record one spoken request. Returns 16 kHz mono float32 audio, or None if nobody spoke."""
    import sounddevice as sd

    endpointer = endpointer or Endpointer()
    block = int(SAMPLE_RATE * BLOCK_SECONDS)
    chunks: list[np.ndarray] = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=block) as stream:
        while True:
            data, _ = stream.read(block)
            mono = data[:, 0].copy()
            chunks.append(mono)
            if endpointer.feed(float(np.sqrt(np.mean(mono**2)))):
                break
    if not endpointer.heard_speech:
        return None
    return np.concatenate(chunks)


def to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return buffer.getvalue()
