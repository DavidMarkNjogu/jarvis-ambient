from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest
from rich.console import Console

import jarvis.voice as voice


def test_falls_back_to_enter_mode_when_wake_model_fails(monkeypatch) -> None:
    # 1. Force the wake model loader to raise an exception
    def failing_wake_detector(*args, **kwargs):
        raise RuntimeError("Model file 'hey_jarvis' missing or corrupt")

    monkeypatch.setattr("jarvis.wake.WakeDetector", failing_wake_detector)

    # 2. Capture console output
    captured_output = io.StringIO()
    test_console = Console(file=captured_output, highlight=False)

    # 3. Mock voice settings with wake enabled
    fake_vs = MagicMock()
    fake_vs.wake_enabled = True
    fake_vs.wake_threshold = 0.5
    fake_vs.stt_engine = "local"
    fake_vs.tts_engine = "windows"
    fake_vs.whisper_model = "base.en"
    fake_vs.windows_voice = "George"
    fake_vs.language = ""
    fake_vs.groq_key = None

    from jarvis.config import ProviderConfig

    fake_settings = MagicMock()
    fake_settings.providers = [ProviderConfig("ollama", "http://localhost:11434/v1", "qwen", None)]
    fake_settings.user_name = "David"
    fake_settings.history_turns = 12

    monkeypatch.setattr(voice, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(voice, "voice_settings_from_env", lambda *a, **kw: fake_vs)
    monkeypatch.setattr(voice, "build_transcriber", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "build_mouth", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "greet", lambda *a, **kw: None)

    # Simulate user typing 'q' on the first prompt
    test_console.input = MagicMock(return_value="q")

    # Run main with --no-visual
    exit_code = voice.main(argv=["--no-visual"], console=test_console)

    # Must return normally (code 0)
    assert exit_code == 0

    # Output must contain the reason for the fallback
    output = captured_output.getvalue()
    assert "falling back to press-Enter mode" in output
    assert "missing or corrupt" in output
