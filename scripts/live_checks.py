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


def check_tools() -> int:
    import datetime
    import zoneinfo
    from jarvis.config import load_settings
    from jarvis.personality import system_prompt
    from jarvis.providers import Provider
    from jarvis.brain import Brain
    from jarvis.tools import default_registry

    settings = load_settings()
    registry = default_registry()
    try:
        tz = zoneinfo.ZoneInfo("Africa/Nairobi")
    except Exception:
        tz = datetime.timezone(datetime.timedelta(hours=3), name="Africa/Nairobi")
    now_eat = datetime.datetime.now(tz)
    expected_hour_24 = str(now_eat.hour)
    expected_hour_12 = str((now_eat.hour % 12) or 12)

    brain = Brain(
        [Provider(p) for p in settings.providers],
        system_prompt=lambda: system_prompt(settings.user_name, tools=[t.name for t in registry.list_tools()]),
        tools=registry,
    )

    started = time.perf_counter()
    reply = "".join(brain.ask("what time is it right now?"))
    took = time.perf_counter() - started

    hour_words = {
        1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
        7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"
    }
    h12 = (now_eat.hour % 12) or 12
    h_word = hour_words.get(h12, "")
    # Natural British phrasing past :40 often names the upcoming hour (e.g. "ten to three")
    next_h12 = ((now_eat.hour + 1) % 12) or 12
    next_h_word = hour_words.get(next_h12, "")
    next_hour_str = str(next_h12)

    ok = (
        (expected_hour_24 in reply)
        or (expected_hour_12 in reply)
        or (bool(h_word) and h_word in reply.lower())
        or (now_eat.minute >= 40 and ((next_hour_str in reply) or (bool(next_h_word) and next_h_word in reply.lower())))
    )
    return done("tools", ok, f"answered in {took:.1f}s: {reply!r} (expected hour {expected_hour_24} or {expected_hour_12})")


def check_memory() -> int:
    import subprocess
    import tempfile
    import uuid

    db_path = Path(tempfile.gettempdir()) / f"jarvis_live_memory_{uuid.uuid4().hex[:8]}.db"
    test_token = f"live_fact_{uuid.uuid4().hex[:8]}"
    fact_text = f"David's secret hobby is stargazing {test_token}"

    started = time.perf_counter()
    try:
        # Process 1: Write fact
        code1 = subprocess.run(
            [sys.executable, "-c", f"""
from jarvis.memory import Memory
mem = Memory(db_path={str(db_path)!r})
mem.remember({fact_text!r})
mem.close()
"""],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if code1.returncode != 0:
            return done("memory", False, f"process 1 failed: {code1.stderr.strip()}")

        # Process 2: Read fact in fresh process
        code2 = subprocess.run(
            [sys.executable, "-c", f"""
import sys
from jarvis.memory import Memory
mem = Memory(db_path={str(db_path)!r})
facts = mem.recall({test_token!r})
mem.close()
if not facts or {test_token!r} not in facts[0]:
    sys.exit(1)
"""],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if code2.returncode != 0:
            return done("memory", False, f"process 2 failed: {code2.stderr.strip()}")

        took = time.perf_counter() - started
        return done("memory", True, f"persisted fact across 2 processes in {took:.2f}s")
    finally:
        try:
            if db_path.exists():
                db_path.unlink(missing_ok=True)
            for extra in (f"{db_path}-wal", f"{db_path}-shm"):
                Path(extra).unlink(missing_ok=True)
        except Exception:
            pass


CHECKS = {
    "brain": check_brain,
    "stt": check_stt,
    "tts": check_tts,
    "e2e": check_e2e,
    "wake": check_wake,
    "tools": check_tools,
    "memory": check_memory,
}


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
