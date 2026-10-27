"""Text to speech: Kokoro (natural British voice, offline) or the voice built into Windows."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from .config import PROJECT_ROOT

MODELS_DIR = PROJECT_ROOT / "models"
KOKORO_MODEL = MODELS_DIR / "kokoro-v1.0.int8.onnx"
KOKORO_VOICES = MODELS_DIR / "voices-v1.0.bin"


class Voice(Protocol):
    label: str

    def speak(self, text: str) -> None: ...

    def stop(self) -> None: ...

    def set_speed(self, speed: float) -> None: ...

    def set_voice(self, name: str) -> None: ...


def _speed_to_sapi_rate(speed: float) -> int:
    """Map speed multiplier (e.g. 1.0x -> 0, 1.5x -> 5) to SAPI Rate bounds (-10 to +10, clamped)."""
    rate = int(round((speed - 1.0) * 10.0))
    return max(-10, min(10, rate))


class KokoroVoice:
    def __init__(
        self,
        voice: str = "bm_george",
        speed: float = 1.05,
        model: Path = KOKORO_MODEL,
        voices: Path = KOKORO_VOICES,
        kokoro_factory: Callable[[str, str], Any] | None = None,
        play_audio: bool = True,
    ):
        self.label = f"kokoro {voice}"
        self._voice = voice
        self._speed = speed
        self._play_audio = play_audio
        self._lang = "en-gb" if voice.startswith("b") else "en-us"
        if kokoro_factory is not None:
            self._kokoro = kokoro_factory(str(model), str(voices))
        else:
            from kokoro_onnx import Kokoro
            self._kokoro = Kokoro(str(model), str(voices))

    def set_speed(self, speed: float) -> None:
        self._speed = speed

    def set_voice(self, voice: str) -> None:
        self._voice = voice
        self._lang = "en-gb" if voice.startswith("b") else "en-us"
        self.label = f"kokoro {voice}"

    def speak(self, text: str) -> None:
        samples, sample_rate = self._kokoro.create(text, voice=self._voice, speed=self._speed, lang=self._lang)
        if self._play_audio:
            import sounddevice as sd
            sd.play(samples, sample_rate)
            sd.wait()

    def stop(self) -> None:
        if self._play_audio:
            import sounddevice as sd
            sd.stop()


class WindowsVoice:
    """Uses the speech voices that come with Windows. No download needed."""

    def __init__(
        self,
        prefer: str = "George",
        speed: float = 1.0,
        sapi_factory: Callable[[], Any] | None = None,
    ):
        if sapi_factory is not None:
            self._sapi = sapi_factory()
        else:
            import comtypes.client
            self._sapi = comtypes.client.CreateObject("SAPI.SpVoice")

        self._voices = _windows_voices(self._sapi)
        self.label = "windows"
        self.set_voice(prefer)
        self.set_speed(speed)

    def set_speed(self, speed: float) -> None:
        self._speed = speed
        self._sapi.Rate = _speed_to_sapi_rate(speed)

    def set_voice(self, name: str) -> None:
        chosen = next((v for v, d in self._voices if name and name.lower() in d.lower()), None)
        chosen = chosen or next((v for v, d in self._voices if _is_british(d)), None)
        if chosen is not None:
            self._sapi.Voice = chosen
            self.label = f"windows {chosen.GetDescription()}"
        else:
            try:
                self.label = f"windows {self._sapi.Voice.GetDescription()}"
            except Exception:
                self.label = "windows"

    def speak(self, text: str) -> None:
        self._sapi.Speak(text)

    def stop(self) -> None:
        self._sapi.Speak("", 2)  # SVSFPurgeBeforeSpeak


def list_voices(
    engine: str = "auto",
    sapi_factory: Callable[[], Any] | None = None,
) -> list[str]:
    """List available voices for the specified or auto-detected engine."""
    results: list[str] = []
    if engine in {"windows", "auto"}:
        try:
            if sapi_factory is not None:
                sapi = sapi_factory()
            else:
                import comtypes.client
                sapi = comtypes.client.CreateObject("SAPI.SpVoice")
            tokens = _windows_voices(sapi)
            for _, desc in tokens:
                if desc not in results:
                    results.append(desc)
        except Exception:
            pass

    if engine in {"kokoro", "auto"}:
        kokoro_voices = [
            "bm_george (British male)",
            "bm_lewis (British male)",
            "bf_emma (British female)",
            "bf_isabella (British female)",
            "am_adam (American male)",
            "am_michael (American male)",
            "af_bella (American female)",
            "af_nicole (American female)",
        ]
        results.extend(kokoro_voices)

    return results


class Mouth:
    """Speaks sentences one after another on a background thread.

    The reply keeps streaming in while earlier sentences are being spoken. The voice
    engine is created on the speaking thread because the Windows voice requires it.
    """

    def __init__(self, make_voice: Callable[[], Voice]):
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._ready = threading.Event()
        self._voice: Voice | None = None
        self.error: Exception | None = None
        self._thread = threading.Thread(target=self._run, args=(make_voice,), daemon=True)
        self._thread.start()
        self._ready.wait()
        if self.error:
            raise self.error

    @property
    def label(self) -> str:
        return self._voice.label if self._voice else "none"

    def say(self, sentence: str) -> None:
        self._queue.put(sentence)

    def wait(self) -> None:
        """Block until everything queued so far has been spoken."""
        self._queue.join()

    def interrupt(self) -> None:
        """Drop everything not yet spoken and cut off the current sentence."""
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
        if self._voice:
            self._voice.stop()

    def close(self) -> None:
        self._queue.put(None)

    def _run(self, make_voice: Callable[[], Voice]) -> None:
        try:
            _init_com()
            self._voice = make_voice()
        except Exception as exc:  # reported to the caller in __init__
            self.error = exc
            self._ready.set()
            return
        self._ready.set()
        while True:
            sentence = self._queue.get()
            if sentence is None:
                self._queue.task_done()
                return
            try:
                self._voice.speak(sentence)
            except Exception as exc:
                self.error = exc
            finally:
                self._queue.task_done()


ONECORE_VOICES = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices"


def _windows_voices(sapi) -> list[tuple[object, str]]:
    """Classic desktop voices plus the newer OneCore ones (where George lives)."""
    import comtypes.client

    found = []
    tokens = sapi.GetVoices()
    found += [(tokens.Item(i), tokens.Item(i).GetDescription()) for i in range(tokens.Count)]
    try:
        category = comtypes.client.CreateObject("SAPI.SpObjectTokenCategory")
        category.SetId(ONECORE_VOICES, False)
        tokens = category.EnumerateTokens()
        found += [(tokens.Item(i), tokens.Item(i).GetDescription()) for i in range(tokens.Count)]
    except Exception:
        pass
    return found


def _is_british(description: str) -> bool:
    text = description.lower()
    return "united kingdom" in text or "great britain" in text


def _init_com() -> None:
    try:
        import comtypes

        comtypes.CoInitialize()
    except Exception:
        pass
