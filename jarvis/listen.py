"""Recording from the microphone until you stop talking."""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

from typing import Any, Iterable, Iterator

import numpy as np

SAMPLE_RATE = 16_000
BLOCK_SECONDS = 0.03  # 30 ms blocks
FRAME_SAMPLES = 1280  # 80 ms frames at 16 kHz


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
    min_threshold: float = 0.003
    block_seconds: float = BLOCK_SECONDS

    def __post_init__(self) -> None:
        import os
        env_min = os.environ.get('JARVIS_MIC_THRESHOLD')
        if env_min:
            try:
                self.min_threshold = float(env_min)
            except ValueError:
                pass
        self._blocks = 0
        self._noise: list[float] = []
        self._threshold = self.min_threshold
        self._speech_blocks = 0
        self._quiet_blocks = 0
        self.heard_speech = False

    def _to_blocks(self, seconds: float) -> int:
        return round(seconds / self.block_seconds)

    def feed(self, rms: float) -> bool:
        """Feed one block's loudness. Returns True when recording should stop."""
        self._blocks += 1
        if self._blocks <= self._to_blocks(self.calibration_seconds):
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

        if self._blocks >= self._to_blocks(self.max_seconds):
            return True
        if not self.heard_speech:
            return self._blocks >= self._to_blocks(self.start_timeout)
        return self._quiet_blocks >= self._to_blocks(self.silence_seconds)

    def feed_frame(self, frame: np.ndarray) -> bool:
        """Feed an audio frame directly by calculating its RMS energy."""
        rms = float(np.sqrt(np.mean(frame.astype("float32") ** 2)))
        return self.feed(rms)


def _to_blocks(seconds: float) -> int:
    # Whole blocks, so 0.9 s is exactly 30 blocks rather than 0.8999… vs 0.9.
    return round(seconds / BLOCK_SECONDS)


class MicStream:
    """One continuous 16 kHz mono microphone stream yielding fixed-size frames (default 1,280 samples / 80 ms)."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        frame_size: int = FRAME_SAMPLES,
        source: Iterable[np.ndarray] | np.ndarray | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self._source = source
        self._closed = False
        self._stream: Any = None

    def __iter__(self) -> Iterator[np.ndarray]:
        if self._source is not None:
            if isinstance(self._source, np.ndarray):
                for offset in range(0, len(self._source) - self.frame_size + 1, self.frame_size):
                    yield self._source[offset : offset + self.frame_size]
            else:
                for chunk in self._source:
                    yield chunk
            return

        import sounddevice as sd

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.frame_size,
        ) as stream:
            self._stream = stream
            while not self._closed:
                data, _ = stream.read(self.frame_size)
                yield data[:, 0].copy()

    def drain(self) -> None:
        if self._stream is not None:
            try:
                avail = getattr(self._stream, 'read_available', 0)
                if avail > 0:
                    self._stream.read(avail)
            except Exception:
                pass

    def close(self) -> None:
        self._closed = True


def record_utterance(
    endpointer: Endpointer | None = None,
    stream: MicStream | Iterator[np.ndarray] | None = None,
) -> np.ndarray | None:
    """Record one spoken request. Returns 16 kHz mono float32 audio, or None if nobody spoke."""
    if stream is not None:
        endpointer = endpointer or Endpointer(block_seconds=0.08)
        chunks: list[np.ndarray] = []
        for frame in stream:
            mono = frame.astype("float32")
            chunks.append(mono)
            if endpointer.feed_frame(mono):
                break
        if not endpointer.heard_speech:
            return None
        return np.concatenate(chunks)

    import sounddevice as sd

    endpointer = endpointer or Endpointer()
    block = int(SAMPLE_RATE * BLOCK_SECONDS)
    chunks = []
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=block) as sd_stream:
        while True:
            data, _ = sd_stream.read(block)
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
