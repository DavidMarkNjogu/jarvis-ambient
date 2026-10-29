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


def test_build_transcriber_groq_and_local(monkeypatch: pytest.MonkeyPatch) -> None:
    from jarvis import stt
    groq_init = MagicMock()
    local_init = MagicMock()
    monkeypatch.setattr(stt, "GroqTranscriber", groq_init)
    monkeypatch.setattr(stt, "LocalWhisperTranscriber", local_init)

    fake_vs = MagicMock()
    fake_vs.stt_engine = "groq"
    fake_vs.groq_key = "test_key"
    fake_vs.language = "en"
    console = Console(file=io.StringIO())

    voice.build_transcriber(fake_vs, console)
    groq_init.assert_called_once_with("test_key", language="en")

    fake_vs.stt_engine = "local"
    fake_vs.whisper_model = "tiny.en"
    voice.build_transcriber(fake_vs, console)
    local_init.assert_called_once_with("tiny.en", language="en")


def test_build_mouth_kokoro_and_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(voice, "Mouth", lambda fn: fn)

    fake_vs = MagicMock()
    fake_vs.tts_engine = "kokoro"
    fake_vs.kokoro_voice = "af_sky"
    fake_vs.voice_speed = 1.2
    m_fn = voice.build_mouth(fake_vs)
    assert callable(m_fn)

    fake_vs.tts_engine = "windows"
    fake_vs.windows_voice = "David"
    m_fn2 = voice.build_mouth(fake_vs)
    assert callable(m_fn2)


def test_init_wake_detector_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_vs = MagicMock()
    fake_vs.wake_enabled = False
    assert voice.init_wake_detector(fake_vs) is None

    fake_vs.wake_enabled = True
    fake_vs.wake_threshold = 0.6
    from jarvis import wake
    mock_wd = MagicMock()
    monkeypatch.setattr(wake, "WakeDetector", mock_wd)
    res = voice.init_wake_detector(fake_vs)
    assert res is not None
    mock_wd.assert_called_once_with(threshold=0.6, load_model=True)


def test_voice_main_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    out = io.StringIO()
    c = Console(file=out)

    monkeypatch.setattr(voice, "load_settings", MagicMock(side_effect=ValueError("corrupt settings")))
    code = voice.main(argv=["--no-visual"], console=c)
    assert code == 1
    assert "Setup problem" in out.getvalue()

    fake_settings = MagicMock()
    fake_settings.providers = []
    monkeypatch.setattr(voice, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(voice, "voice_settings_from_env", lambda *a, **k: MagicMock())
    out.truncate(0)
    out.seek(0)
    code = voice.main(argv=["--no-visual"], console=c)
    assert code == 1
    assert "No brain configured" in out.getvalue()


def test_voice_main_kokoro_partial_files_pins_and_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    from jarvis.config import ProviderConfig

    fake_settings = MagicMock()
    fake_settings.providers = [ProviderConfig("ollama", "http://localhost:11434/v1", "qwen", None)]
    fake_settings.user_name = "David"
    monkeypatch.setattr(voice, "load_settings", lambda: fake_settings)

    # Model exists but voices do not -> kokoro_installed MUST be False
    fake_model = MagicMock()
    fake_model.exists.return_value = True
    fake_voices = MagicMock()
    fake_voices.exists.return_value = False
    monkeypatch.setattr(voice, "KOKORO_MODEL", fake_model)
    monkeypatch.setattr(voice, "KOKORO_VOICES", fake_voices)

    received_ready = []
    def fake_voice_settings(env, kokoro_installed=False):
        received_ready.append(kokoro_installed)
        vs = MagicMock()
        vs.wake_enabled = False
        vs.tts_engine = "windows"
        return vs

    monkeypatch.setattr(voice, "voice_settings_from_env", fake_voice_settings)
    monkeypatch.setattr(voice, "build_transcriber", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "build_mouth", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "greet", lambda *a, **kw: None)

    c = Console(file=io.StringIO())
    c.input = MagicMock(return_value="q")
    code = voice.main(argv=["--no-visual"], console=c)
    assert code == 0
    assert len(received_ready) == 1
    assert received_ready[0] is False


def test_voice_main_visual_flag_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    from jarvis.config import ProviderConfig

    fake_settings = MagicMock()
    fake_settings.providers = [ProviderConfig("ollama", "http://localhost:11434/v1", "qwen", None)]
    fake_settings.user_name = "David"
    monkeypatch.setattr(voice, "load_settings", lambda: fake_settings)

    fake_vs = MagicMock()
    fake_vs.wake_enabled = False
    fake_vs.tts_engine = "windows"
    monkeypatch.setattr(voice, "voice_settings_from_env", lambda *a, **kw: fake_vs)
    monkeypatch.setattr(voice, "build_transcriber", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "build_mouth", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "greet", lambda *a, **kw: None)

    mock_server = MagicMock()
    monkeypatch.setattr(voice, "VisualServer", mock_server)

    c = Console(file=io.StringIO())
    c.input = MagicMock(return_value="q")

    # With --no-visual, VisualServer must NOT be instantiated
    voice.main(argv=["--no-visual"], console=c)
    assert not mock_server.called


def test_voice_main_slash_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    from jarvis.config import ProviderConfig

    fake_settings = MagicMock()
    fake_settings.providers = [ProviderConfig("ollama", "http://localhost:11434/v1", "qwen", None)]
    fake_settings.user_name = "David"
    fake_settings.history_turns = 12

    fake_vs = MagicMock()
    fake_vs.wake_enabled = False
    fake_vs.tts_engine = "windows"
    fake_vs.voice_speed = 1.1

    mock_mouth = MagicMock()
    mock_mouth.label = "George"
    mock_brain = MagicMock()

    inputs = ["/reset", "/speed 1.5", "/speed", "/voices", "/voice George", "hello", "q"]
    out = io.StringIO()
    c = Console(file=out)
    c.input = MagicMock(side_effect=inputs)

    monkeypatch.setattr(voice, "load_settings", lambda: fake_settings)
    monkeypatch.setattr(voice, "voice_settings_from_env", lambda *a, **kw: fake_vs)
    monkeypatch.setattr(voice, "build_transcriber", lambda *a: MagicMock())
    monkeypatch.setattr(voice, "build_mouth", lambda *a: mock_mouth)
    monkeypatch.setattr(voice, "Brain", lambda *a, **k: mock_brain)
    monkeypatch.setattr(voice, "greet", lambda *a, **kw: None)
    monkeypatch.setattr(voice, "list_voices", lambda *a: ["George", "Hazel"])

    responded = []
    monkeypatch.setattr(voice, "respond", lambda b, m, con, t, **kw: responded.append(t))

    code = voice.main(argv=["--no-visual"], console=c)
    assert code == 0
    mock_brain.reset.assert_called_once()
    mock_mouth.set_speed.assert_called_with(1.5)
    mock_mouth.set_voice.assert_called_with("George")
    text = out.getvalue()
    assert "Conversation forgotten" in text
    assert "Available voices" in text
    assert "George" in text
    assert responded == ["hello"]


def test_respond_and_greet() -> None:
    from jarvis.brain import AllProvidersFailed

    mouth = MagicMock()
    mouth.error = None
    out = io.StringIO()
    c = Console(file=out)
    visual = MagicMock()

    # Test greet
    voice.greet(mouth, c, visual=visual)
    assert mouth.say.called
    assert mouth.wait.called
    assert visual.set_state.called

    # Test respond
    brain = MagicMock()
    brain.ask.return_value = ["Hello", " world.", " How are you?"]
    fake_prov = MagicMock()
    fake_prov.name = "ollama"
    brain.last_provider = fake_prov

    mouth.reset_mock()
    visual.reset_mock()
    out.truncate(0)
    out.seek(0)
    voice.respond(brain, mouth, c, "hi", visual=visual)
    assert mouth.say.called
    assert mouth.wait.called
    assert visual.set_state.called
    console_text = out.getvalue()
    assert "to first words" in console_text
    assert "ollama" in console_text

    # Test respond failure
    brain.ask.side_effect = AllProvidersFailed("down")
    voice.respond(brain, mouth, c, "hi", visual=visual)
    visual.set_state.assert_called_with("error", "No brain available.")
