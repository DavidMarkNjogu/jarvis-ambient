"""Speech to text: on this computer (faster-whisper) or Groq's free Whisper service."""

from __future__ import annotations

from typing import Protocol

import httpx
import numpy as np

from .listen import to_wav_bytes
from .providers import ProviderError


class Transcriber(Protocol):
    label: str

    def transcribe(self, audio: np.ndarray) -> str: ...


class GroqTranscriber:
    """Fast and accurate even on a weak laptop, because the work happens in the cloud."""

    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo", language: str = "", client: httpx.Client | None = None):
        self.label = f"groq {model}"
        self._model = model
        self._language = language
        self._client = client or httpx.Client(
            base_url="https://api.groq.com/openai/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(30.0, connect=5.0),
        )

    def transcribe(self, audio: np.ndarray) -> str:
        data = {"model": self._model, "response_format": "json"}
        if self._language:
            data["language"] = self._language
        files = {"file": ("speech.wav", to_wav_bytes(audio), "audio/wav")}
        try:
            response = self._client.post("audio/transcriptions", data=data, files=files)
        except httpx.TransportError as exc:
            raise ProviderError("groq-stt", "could not connect (check your internet)") from exc
        if response.status_code == 429:
            raise ProviderError("groq-stt", "free-tier rate limit reached; try again in a minute")
        if response.status_code in (401, 403):
            raise ProviderError("groq-stt", "the Groq API key was rejected")
        if response.status_code != 200:
            raise ProviderError("groq-stt", f"HTTP {response.status_code}")
        return response.json().get("text", "").strip()


class LocalWhisperTranscriber:
    """Fully offline. On a dual-core laptop, base.en takes roughly a second per sentence."""

    def __init__(self, model_size: str = "base.en", language: str = ""):
        from faster_whisper import WhisperModel

        self.label = f"local whisper {model_size}"
        self._language = language or None
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(audio, language=self._language, beam_size=1)
        return " ".join(segment.text.strip() for segment in segments).strip()
