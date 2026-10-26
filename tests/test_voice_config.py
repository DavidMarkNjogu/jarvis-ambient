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
