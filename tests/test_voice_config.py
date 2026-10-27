import pytest

from jarvis.config import voice_settings_from_env


def test_auto_prefers_groq_ears_when_key_present_and_windows_voice_without_kokoro():
    vs = voice_settings_from_env({"GROQ_API_KEY": "gsk_x"}, kokoro_installed=False)
    assert (vs.stt_engine, vs.tts_engine, vs.windows_voice) == ("groq", "windows", "George")
    assert vs.groq_key == "gsk_x"


def test_auto_goes_offline_without_groq_and_uses_kokoro_when_downloaded():
    vs = voice_settings_from_env({}, kokoro_installed=True)
    assert (vs.stt_engine, vs.whisper_model, vs.tts_engine, vs.kokoro_voice) == (
        "local", "base.en", "kokoro", "bm_george",
    )


def test_explicit_choices_win():
    vs = voice_settings_from_env(
        {"GROQ_API_KEY": "k", "JARVIS_STT": "local", "JARVIS_TTS": "windows", "WINDOWS_VOICE": "Hazel"},
        kokoro_installed=True,
    )
    assert (vs.stt_engine, vs.tts_engine, vs.windows_voice) == ("local", "windows", "Hazel")


def test_groq_ears_without_key_is_a_clear_error():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        voice_settings_from_env({"JARVIS_STT": "groq"}, kokoro_installed=False)


def test_unknown_engine_is_a_clear_error():
    with pytest.raises(ValueError, match="JARVIS_TTS"):
        voice_settings_from_env({"JARVIS_TTS": "elevenlabs"}, kokoro_installed=False)


def test_wake_defaults():
    vs = voice_settings_from_env({}, kokoro_installed=False)
    assert vs.wake_enabled is True
    assert vs.wake_threshold == 0.5
    assert vs.voice_speed == 1.1


def test_bad_wake_threshold_is_a_clear_error():
    # String non-number
    with pytest.raises(ValueError) as exc1:
        voice_settings_from_env({"WAKE_THRESHOLD": "high"}, kokoro_installed=False)
    assert "WAKE_THRESHOLD" in str(exc1.value)
    assert "high" in str(exc1.value)

    # Out of range (1.7)
    with pytest.raises(ValueError) as exc2:
        voice_settings_from_env({"WAKE_THRESHOLD": "1.7"}, kokoro_installed=False)
    assert "WAKE_THRESHOLD" in str(exc2.value)
    assert "1.7" in str(exc2.value)


def test_bad_voice_speed_is_a_clear_error():
    # String non-number
    with pytest.raises(ValueError) as exc1:
        voice_settings_from_env({"JARVIS_VOICE_SPEED": "fast"}, kokoro_installed=False)
    assert "JARVIS_VOICE_SPEED" in str(exc1.value)
    assert "fast" in str(exc1.value)

    # Out of range (e.g. 5.0)
    with pytest.raises(ValueError) as exc2:
        voice_settings_from_env({"JARVIS_VOICE_SPEED": "5.0"}, kokoro_installed=False)
    assert "JARVIS_VOICE_SPEED" in str(exc2.value)
    assert "5.0" in str(exc2.value)

