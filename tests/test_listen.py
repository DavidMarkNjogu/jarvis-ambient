import io
import wave

import pytest

np = pytest.importorskip("numpy")

from jarvis.listen import BLOCK_SECONDS, Endpointer, to_wav_bytes  # noqa: E402


def blocks(level, seconds):
    return [level] * round(seconds / BLOCK_SECONDS)


def run(endpointer, levels):
    for i, rms in enumerate(levels):
        if endpointer.feed(rms):
            return i + 1
    return None


def test_stops_after_a_pause_following_speech():
    e = Endpointer(silence_seconds=0.9)
    levels = blocks(0.002, 0.3) + blocks(0.1, 1.5) + blocks(0.002, 2.0)
    stopped_at = run(e, levels)
    assert e.heard_speech
    assert stopped_at == round(1.8 / BLOCK_SECONDS) + round(0.9 / BLOCK_SECONDS)


def test_gives_up_if_nobody_speaks():
    e = Endpointer(start_timeout=2.0)
    stopped_at = run(e, blocks(0.002, 5.0))
    assert not e.heard_speech
    assert stopped_at == round(2.0 / BLOCK_SECONDS)


def test_a_single_click_is_not_speech():
    e = Endpointer(start_timeout=2.0)
    run(e, blocks(0.002, 0.3) + [0.5] + blocks(0.002, 3.0))
    assert not e.heard_speech


def test_noisy_room_raises_the_threshold():
    e = Endpointer(start_timeout=2.0)
    run(e, blocks(0.05, 0.3) + blocks(0.08, 3.0))  # fan noise, slightly louder
    assert not e.heard_speech


def test_stops_at_max_length_even_mid_speech():
    e = Endpointer(max_seconds=3.0)
    assert run(e, blocks(0.002, 0.3) + blocks(0.1, 10.0)) == round(3.0 / BLOCK_SECONDS)


def test_wav_is_16khz_mono_16bit():
    data = to_wav_bytes(np.zeros(16_000, dtype="float32"))
    with wave.open(io.BytesIO(data)) as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth(), wav.getnframes()) == (16_000, 1, 2, 16_000)
