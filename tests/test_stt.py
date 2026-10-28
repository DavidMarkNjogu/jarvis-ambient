from __future__ import annotations

from unittest.mock import MagicMock
import httpx
import numpy as np
import pytest

from jarvis.stt import GroqTranscriber, LocalWhisperTranscriber
from jarvis.providers import ProviderError


def test_groq_transcriber_success() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": " hello world "}
    mock_client.post.return_value = mock_resp

    audio = np.zeros(16000, dtype=np.float32)
    transcriber = GroqTranscriber(api_key="gsk_fake", client=mock_client, language="en")
    text = transcriber.transcribe(audio)

    assert text == "hello world"
    assert transcriber.label == "groq whisper-large-v3-turbo"
    assert mock_client.post.called
    data = mock_client.post.call_args[1]["data"]
    assert data["model"] == "whisper-large-v3-turbo"
    assert data["language"] == "en"


def test_groq_transcriber_handles_rate_limit_429() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_client.post.return_value = mock_resp

    audio = np.zeros(16000, dtype=np.float32)
    transcriber = GroqTranscriber(api_key="gsk_fake", client=mock_client)

    with pytest.raises(ProviderError) as exc_info:
        transcriber.transcribe(audio)
    assert "rate limit" in str(exc_info.value).lower()


def test_groq_transcriber_handles_rejected_key_401() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_client.post.return_value = mock_resp

    audio = np.zeros(16000, dtype=np.float32)
    transcriber = GroqTranscriber(api_key="bad_key", client=mock_client)

    with pytest.raises(ProviderError) as exc_info:
        transcriber.transcribe(audio)
    assert "rejected" in str(exc_info.value).lower()


def test_groq_transcriber_handles_connection_error() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = httpx.ConnectError("Network unreachable")

    audio = np.zeros(16000, dtype=np.float32)
    transcriber = GroqTranscriber(api_key="gsk_fake", client=mock_client)

    with pytest.raises(ProviderError) as exc_info:
        transcriber.transcribe(audio)
    assert "could not connect" in str(exc_info.value).lower()


def test_groq_transcriber_handles_generic_http_error() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 502
    mock_client.post.return_value = mock_resp

    audio = np.zeros(16000, dtype=np.float32)
    transcriber = GroqTranscriber(api_key="gsk_fake", client=mock_client)

    with pytest.raises(ProviderError) as exc_info:
        transcriber.transcribe(audio)
    assert "502" in str(exc_info.value)


def test_local_whisper_transcriber(monkeypatch: pytest.MonkeyPatch) -> None:
    import faster_whisper

    mock_segment_1 = MagicMock()
    mock_segment_1.text = "Hello"
    mock_segment_2 = MagicMock()
    mock_segment_2.text = "Jarvis"

    mock_model_instance = MagicMock()
    mock_model_instance.transcribe.return_value = ([mock_segment_1, mock_segment_2], None)

    monkeypatch.setattr(faster_whisper, "WhisperModel", lambda *a, **kw: mock_model_instance)

    transcriber = LocalWhisperTranscriber(model_size="tiny.en", language="en")
    assert "tiny.en" in transcriber.label
    assert transcriber._language == "en"

    # Default empty language resolves to None
    default_transcriber = LocalWhisperTranscriber(model_size="tiny.en", language="")
    assert default_transcriber._language is None

    audio = np.zeros(16000, dtype=np.float32)
    text = transcriber.transcribe(audio)
    assert text == "Hello Jarvis"
