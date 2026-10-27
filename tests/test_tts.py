from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from jarvis.tts import KokoroVoice, WindowsVoice, list_voices


def test_windows_rate_maps_to_sapi_bounds() -> None:
    # 1.0 maps to Rate 0
    fake_sapi_1 = MagicMock()
    v1 = WindowsVoice(speed=1.0, sapi_factory=lambda: fake_sapi_1)
    assert fake_sapi_1.Rate == 0

    # 1.5 maps to a positive Rate
    fake_sapi_15 = MagicMock()
    v15 = WindowsVoice(speed=1.5, sapi_factory=lambda: fake_sapi_15)
    assert fake_sapi_15.Rate > 0

    # Out-of-range high clamped to 10
    fake_sapi_high = MagicMock()
    v_high = WindowsVoice(speed=5.0, sapi_factory=lambda: fake_sapi_high)
    assert fake_sapi_high.Rate == 10

    # Out-of-range low clamped to -10
    fake_sapi_low = MagicMock()
    v_low = WindowsVoice(speed=-2.0, sapi_factory=lambda: fake_sapi_low)
    assert fake_sapi_low.Rate == -10


def test_kokoro_speed_reaches_synthesis() -> None:
    fake_kokoro = MagicMock()
    fake_kokoro.create.return_value = (MagicMock(), 24000)

    voice = KokoroVoice(
        voice="bm_george",
        speed=1.25,
        kokoro_factory=lambda model, voices: fake_kokoro,
        play_audio=False,
    )
    voice.speak("Testing speed reaching synthesis.")

    assert fake_kokoro.create.called
    _, kwargs = fake_kokoro.create.call_args
    assert kwargs.get("speed") == 1.25


def test_list_voices_names_installed_voices() -> None:
    fake_sapi = MagicMock()
    token1 = MagicMock()
    token1.GetDescription.return_value = "Microsoft George"
    token2 = MagicMock()
    token2.GetDescription.return_value = "Microsoft Hazel"

    tokens = MagicMock()
    tokens.Count = 2
    tokens.Item.side_effect = lambda i: [token1, token2][i]
    fake_sapi.GetVoices.return_value = tokens

    voices = list_voices(engine="windows", sapi_factory=lambda: fake_sapi)
    assert "Microsoft George" in voices
    assert "Microsoft Hazel" in voices


def test_switching_voice_changes_the_active_voice() -> None:
    fake_sapi = MagicMock()
    token1 = MagicMock()
    token1.GetDescription.return_value = "Microsoft George"
    token2 = MagicMock()
    token2.GetDescription.return_value = "Microsoft Hazel"

    tokens = MagicMock()
    tokens.Count = 2
    tokens.Item.side_effect = lambda i: [token1, token2][i]
    fake_sapi.GetVoices.return_value = tokens

    v = WindowsVoice(prefer="George", sapi_factory=lambda: fake_sapi)
    assert "George" in v.label

    v.set_voice("Hazel")
    assert fake_sapi.Voice == token2
    assert "Hazel" in v.label
