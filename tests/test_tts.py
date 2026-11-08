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

    # Discovers installed voices via list_voices
    available = list_voices(engine="windows", sapi_factory=lambda: fake_sapi)
    assert "Microsoft Hazel" in available

    v = WindowsVoice(prefer="George", sapi_factory=lambda: fake_sapi)
    assert "George" in v.label

    # Switching selects the target voice from the list
    v.set_voice("Hazel")
    assert fake_sapi.Voice == token2
    assert "Hazel" in v.label



def test_is_british_recognition() -> None:
    from jarvis.tts import _is_british
    assert _is_british("Microsoft George - English (United Kingdom)")
    assert _is_british("Hazel - Great Britain")
    assert not _is_british("Microsoft David - English (United States)")


def test_mouth_queue_and_wait() -> None:
    from jarvis.tts import Mouth

    class FakeVoice:
        label = "fake"
        def __init__(self):
            self.spoken = []
        def speak(self, sentence: str) -> None:
            self.spoken.append(sentence)
        def stop(self) -> None:
            pass

    fake_voice = FakeVoice()
    mouth = Mouth(lambda: fake_voice)
    assert mouth.label == "fake"
    assert mouth._thread.daemon is True

    mouth.say("hello")
    mouth.say("world")
    mouth.wait()
    assert fake_voice.spoken == ["hello", "world"]

    mouth.close()


def test_mouth_interrupt() -> None:
    from jarvis.tts import Mouth
    import time

    stopped = []
    class FakeVoice:
        label = "fake"
        def speak(self, sentence: str) -> None:
            time.sleep(0.05)
        def stop(self) -> None:
            stopped.append(True)

    mouth = Mouth(FakeVoice)
    for i in range(10):
        mouth.say(f"sentence {i}")
    mouth.interrupt()
    assert len(stopped) > 0
    mouth.close()


def test_kokoro_default_play_audio() -> None:
    fake_kokoro = MagicMock()
    voice = KokoroVoice(
        voice="bm_george",
        kokoro_factory=lambda m, v: fake_kokoro,
    )
    assert voice._play_audio is True

def test_mouth_set_voice_and_set_speed() -> None:
    from jarvis.tts import Mouth

    class FakeVoice:
        def __init__(self):
            self.label = 'fake-default'
            self.speed = 1.0

        def speak(self, text: str) -> None:
            pass

        def stop(self) -> None:
            pass

        def set_speed(self, speed: float) -> None:
            self.speed = speed

        def set_voice(self, name: str) -> None:
            self.label = f'fake-{name}'

    fake_voice = FakeVoice()
    mouth = Mouth(lambda: fake_voice)
    try:
        assert mouth.label == 'fake-default'
        mouth.set_speed(1.5)
        assert fake_voice.speed == 1.5
        mouth.set_voice('Hazel')
        assert fake_voice.label == 'fake-Hazel'
        assert mouth.label == 'fake-Hazel'
    finally:
        mouth.close()
