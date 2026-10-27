"""Live checks: the parts of Jarvis that only a real machine can prove (network, models, speakers).

    .venv\\Scripts\\python scripts\\live_checks.py brain|stt|tts|e2e

Each prints one line, "LIVE <name>: PASS" or "LIVE <name>: FAIL (reason)", and exits non-zero on
failure. scripts/verify.py runs these and looks for that exact line. They never print API keys.

What a script cannot prove is whether a human can hear the voice or whether the wake word works in
a living room. Those are the human checks in acceptance/spec.json, signed by David.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PHRASE = "Jarvis, what is the capital of Japan?"
E2E_MAX_SECONDS = 8.0  # speech in, answer text out, on the i5-6300U laptop with local Whisper


def done(name: str, ok: bool, detail: str = "") -> int:
    print(f"LIVE {name}: {'PASS' if ok else 'FAIL'}" + (f" ({detail})" if detail else ""))
    return 0 if ok else 1


def make_wav(path: Path, text: str) -> None:
    """Have Windows speak the text into a 16 kHz mono WAV, the format the recorder produces."""
    script = (
        "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, "
        "[System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono); "
        f"$s.SetOutputToWaveFile('{path}', $f); $s.Speak('{text}'); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True, timeout=60)


def load_audio(path: Path):
    import numpy as np

    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768


def transcribe(text: str) -> tuple[str, float]:
    import os

    from jarvis.stt import LocalWhisperTranscriber

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "phrase.wav"
        make_wav(wav, text)
        ears = LocalWhisperTranscriber(os.environ.get("WHISPER_MODEL") or "base.en")
        started = time.perf_counter()
        heard = ears.transcribe(load_audio(wav))
        return heard, time.perf_counter() - started


def make_brain():
    from jarvis.brain import Brain
    from jarvis.config import load_settings
    from jarvis.personality import system_prompt
    from jarvis.providers import Provider

    settings = load_settings()
    if not settings.providers:
        raise RuntimeError("no brain configured (run setup.bat)")
    return Brain([Provider(c) for c in settings.providers],
                 system_prompt=lambda: system_prompt(settings.user_name, mode="voice"),
                 history_turns=settings.history_turns)


def check_brain() -> int:
    brain = make_brain()
    started = time.perf_counter()
    reply = "".join(brain.ask("Reply with the single word OK."))
    took = time.perf_counter() - started
    return done("brain", "ok" in reply.lower(), f"{brain.last_provider.name} answered in {took:.1f}s")


def check_stt() -> int:
    heard, took = transcribe(PHRASE)
    return done("stt", "japan" in heard.lower(), f"heard {heard!r} in {took:.1f}s")


def check_tts() -> int:
    from jarvis.tts import Mouth, WindowsVoice

    mouth = Mouth(lambda: WindowsVoice("George"))
    label = mouth.label
    mouth.say("Voice check. If you can hear this, the speakers work.")
    mouth.wait()
    err = mouth.error
    mouth.close()
    return done("tts", err is None, f"{label}; the script cannot hear it, so a human must confirm (P2-H2)")


def check_e2e() -> int:
    heard, stt_s = transcribe(PHRASE)
    brain = make_brain()
    started = time.perf_counter()
    reply = "".join(brain.ask(heard))
    brain_s = time.perf_counter() - started
    total = stt_s + brain_s
    ok = "tokyo" in reply.lower() and total <= E2E_MAX_SECONDS
    return done("e2e", ok, f"heard {heard!r}; transcribe {stt_s:.1f}s + answer {brain_s:.1f}s = {total:.1f}s "
                           f"(limit {E2E_MAX_SECONDS:.0f}s); reply {reply[:60]!r}")


def check_wake() -> int:
    import os
    import numpy as np
    from jarvis.stt import LocalWhisperTranscriber
    from jarvis.wake import WakeDetector

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "wake_phrase.wav"
        make_wav(wav, "Hey Jarvis, what is the capital of Japan?")
        with wave.open(str(wav)) as w:
            raw = w.readframes(w.getnframes())
            pcm = np.frombuffer(raw, dtype="<i2")

        detector = WakeDetector(threshold=0.5, load_model=True)
        woke = False
        wake_frame = -1
        frame_size = 1280
        total_frames = len(pcm) // frame_size
        remainder_frames = []

        for i in range(total_frames):
            frame = pcm[i * frame_size : (i + 1) * frame_size]
            if not woke:
                if detector.process_frame(frame):
                    woke = True
                    wake_frame = i
            else:
                remainder_frames.append(frame.astype("float32") / 32768.0)

        if not remainder_frames:
            return done("wake", False, f"woke={woke}, but no audio frames remained for question")

        question_audio = np.concatenate(remainder_frames)
        ears = LocalWhisperTranscriber(os.environ.get("WHISPER_MODEL") or "base.en")
        started = time.perf_counter()
        heard = ears.transcribe(question_audio)
        took = time.perf_counter() - started

        ok = woke and "japan" in heard.lower()
        return done("wake", ok, f"woke={woke} (frame {wake_frame}/{total_frames}); heard {heard!r} in {took:.1f}s")


CHECKS = {"brain": check_brain, "stt": check_stt, "tts": check_tts, "e2e": check_e2e, "wake": check_wake}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        print(f"usage: live_checks.py {'|'.join(CHECKS)}")
        return 2
    name = sys.argv[1]
    try:
        return CHECKS[name]()
    except Exception as err:  # a live check that crashes is a failed check, with the reason shown
        return done(name, False, f"{type(err).__name__}: {err}")


if __name__ == "__main__":
    sys.exit(main())
