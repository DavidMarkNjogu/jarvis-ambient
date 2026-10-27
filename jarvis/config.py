"""Settings loaded from the .env file next to the project."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    model: str
    api_key: str | None


@dataclass(frozen=True)
class Settings:
    providers: list[ProviderConfig]
    skipped: list[str]  # human-readable reasons a provider was left out
    user_name: str
    history_turns: int


# name -> (base URL or env var holding it, API key env var, model env var, default model)
KNOWN_PROVIDERS: dict[str, tuple[str, str | None, str, str]] = {
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "gemini-flash-lite-latest",
    ),
    "groq": (
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    ),
    "ollama": (
        "http://localhost:11434/v1",
        None,  # local, no key
        "OLLAMA_MODEL",
        "qwen2.5:1.5b",
    ),
}

DEFAULT_ORDER = "gemini,groq,ollama"


def settings_from_env(env: Mapping[str, str]) -> Settings:
    order = [p.strip().lower() for p in env.get("JARVIS_PROVIDERS", DEFAULT_ORDER).split(",") if p.strip()]
    unknown = [p for p in order if p not in KNOWN_PROVIDERS]
    if unknown:
        raise ValueError(
            f"Unknown provider(s) in JARVIS_PROVIDERS: {', '.join(unknown)}. "
            f"Choose from: {', '.join(KNOWN_PROVIDERS)}."
        )

    providers: list[ProviderConfig] = []
    skipped: list[str] = []
    for name in order:
        base_url, key_var, model_var, default_model = KNOWN_PROVIDERS[name]
        if name == "ollama":
            base_url = env.get("OLLAMA_URL", "").strip() or base_url
        api_key = None
        if key_var:
            api_key = env.get(key_var, "").strip() or None
            if not api_key:
                skipped.append(f"{name}: no {key_var} in .env")
                continue
        model = env.get(model_var, "").strip() or default_model
        providers.append(ProviderConfig(name, base_url, model, api_key))

    raw_turns = env.get("JARVIS_HISTORY_TURNS", "").strip() or "12"
    try:
        history_turns = max(1, int(raw_turns))
    except ValueError:
        raise ValueError(f"JARVIS_HISTORY_TURNS must be a whole number, got '{raw_turns}'.") from None

    return Settings(
        providers=providers,
        skipped=skipped,
        user_name=env.get("USER_NAME", "").strip(),
        history_turns=history_turns,
    )


@dataclass(frozen=True)
class VoiceSettings:
    stt_engine: str  # "groq" or "local"
    whisper_model: str
    language: str
    tts_engine: str  # "kokoro" or "windows"
    kokoro_voice: str
    windows_voice: str
    groq_key: str | None
    wake_enabled: bool = True
    wake_threshold: float = 0.5
    voice_speed: float = 1.1


def voice_settings_from_env(env: Mapping[str, str], kokoro_installed: bool) -> VoiceSettings:
    """Pick sensible engines: Groq's free Whisper if there's a key (fast on any laptop),
    Kokoro if its model files are downloaded, otherwise the voice built into Windows."""
    groq_key = env.get("GROQ_API_KEY", "").strip() or None

    stt = env.get("JARVIS_STT", "auto").strip().lower() or "auto"
    if stt == "auto":
        stt = "groq" if groq_key else "local"
    if stt not in {"groq", "local"}:
        raise ValueError(f"JARVIS_STT must be auto, groq or local, got '{stt}'.")
    if stt == "groq" and not groq_key:
        raise ValueError("JARVIS_STT=groq needs GROQ_API_KEY in .env (run setup.bat).")

    tts = env.get("JARVIS_TTS", "auto").strip().lower() or "auto"
    if tts == "auto":
        tts = "kokoro" if kokoro_installed else "windows"
    if tts not in {"kokoro", "windows"}:
        raise ValueError(f"JARVIS_TTS must be auto, kokoro or windows, got '{tts}'.")

    wake_raw = env.get("JARVIS_WAKE", "on").strip().lower() or "on"
    if wake_raw in {"on", "true", "1", "yes"}:
        wake_enabled = True
    elif wake_raw in {"off", "false", "0", "no"}:
        wake_enabled = False
    else:
        raise ValueError(f"JARVIS_WAKE must be 'on' or 'off', got '{env.get('JARVIS_WAKE')}'.")

    threshold_raw = env.get("WAKE_THRESHOLD", "0.5").strip() or "0.5"
    try:
        threshold = float(threshold_raw)
        if not (0.0 < threshold < 1.0):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(f"WAKE_THRESHOLD must be a float between 0.0 and 1.0, got '{env.get('WAKE_THRESHOLD')}'.")

    speed_raw = env.get("JARVIS_VOICE_SPEED", "1.1").strip() or "1.1"
    try:
        voice_speed = float(speed_raw)
        if not (0.5 <= voice_speed <= 2.5):
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(f"JARVIS_VOICE_SPEED must be a float between 0.5 and 2.5, got '{env.get('JARVIS_VOICE_SPEED')}'.")

    return VoiceSettings(
        stt_engine=stt,
        whisper_model=env.get("WHISPER_MODEL", "").strip() or "base.en",
        language=env.get("JARVIS_LANGUAGE", "").strip(),
        tts_engine=tts,
        kokoro_voice=env.get("KOKORO_VOICE", "").strip() or "bm_george",
        windows_voice=env.get("WINDOWS_VOICE", "").strip() or "George",
        groq_key=groq_key,
        wake_enabled=wake_enabled,
        wake_threshold=threshold,
        voice_speed=voice_speed,
    )


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or PROJECT_ROOT / ".env")
    return settings_from_env(os.environ)
