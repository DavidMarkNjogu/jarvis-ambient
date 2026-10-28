from __future__ import annotations

import numpy as np
import pytest

from jarvis.wake import make_chime, WakeDetector


def test_make_chime_is_short_non_silent_16khz() -> None:
    chime = make_chime()
    assert isinstance(chime, np.ndarray)
    # 16 kHz sample rate: between 0.1s (1600 samples) and 0.6s (9600 samples)
    assert 1600 <= len(chime) <= 9600
    # Must not be silent: max absolute amplitude > 0.05
    assert np.max(np.abs(chime)) > 0.05


def test_fires_once_when_score_crosses_threshold() -> None:
    detector = WakeDetector(threshold=0.5, cooldown_seconds=2.0)
    # Feed scores: baseline zeros, then one crossing above 0.5
    assert not detector.process_score(0.1, timestamp=0.0)
    assert not detector.process_score(0.4, timestamp=0.1)
    assert detector.process_score(0.65, timestamp=0.2)
    assert not detector.process_score(0.4, timestamp=0.3)


def test_cooldown_ignores_a_second_spike_within_two_seconds() -> None:
    detector = WakeDetector(threshold=0.5, cooldown_seconds=2.0)
    # First spike fires at t=1.0s
    assert detector.process_score(0.8, timestamp=1.0)
    # Second spike at t=2.0s (1.0s later, within 2s cooldown) must be ignored
    assert not detector.process_score(0.9, timestamp=2.0)


def test_fires_again_after_cooldown() -> None:
    detector = WakeDetector(threshold=0.5, cooldown_seconds=2.0)
    # First spike at t=1.0s fires
    assert detector.process_score(0.8, timestamp=1.0)
    # Second spike at t=3.5s (2.5s later, after 2s cooldown) must fire
    assert detector.process_score(0.85, timestamp=3.5)


def test_never_fires_below_threshold() -> None:
    detector = WakeDetector(threshold=0.5)
    for t in [0.0, 0.5, 1.0, 1.5, 2.0]:
        assert not detector.process_score(0.49, timestamp=t)


def test_single_low_spike_does_not_fire() -> None:
    detector = WakeDetector(threshold=0.5)
    assert not detector.process_score(0.0, timestamp=0.0)
    assert not detector.process_score(0.49, timestamp=0.1)
    assert not detector.process_score(0.0, timestamp=0.2)


def test_scores_while_paused_are_ignored() -> None:
    detector = WakeDetector(threshold=0.5)
    detector.pause()
    assert not detector.process_score(0.95, timestamp=1.0)
    assert not detector.process_score(0.99, timestamp=1.5)
    # process_frame while paused must also be ignored immediately
    dummy = np.zeros(1280, dtype=np.int16)
    assert not detector.process_frame(dummy, timestamp=2.0)


def test_resume_clears_the_buffer() -> None:
    detector = WakeDetector(threshold=0.5)
    detector.pause()
    # High score while paused is ignored
    assert not detector.process_score(0.95, timestamp=1.0)
    detector.resume()
    # Buffer is cleared on resume, fresh low score does not fire
    assert not detector.process_score(0.2, timestamp=2.0)
    # Fresh high score after resume fires
    assert detector.process_score(0.9, timestamp=2.5)


def test_process_frame_converts_float32_to_int16() -> None:
    detector = WakeDetector(threshold=0.5)
    captured: dict = {}

    class FakeModel:
        def predict(self, frame: np.ndarray) -> dict[str, float]:
            captured["dtype"] = frame.dtype
            captured["max"] = int(np.max(frame))
            return {"hey_jarvis": 0.8}

    detector._model = FakeModel()
    float_frame = np.array([0.5, -0.5], dtype=np.float32)
    assert detector.process_frame(float_frame)
    assert captured["dtype"] == np.int16
    assert captured["max"] == int(0.5 * 32767)
