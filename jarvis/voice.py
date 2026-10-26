"""Talking Jarvis (Phase 2). Run with:  voice.bat   (or  python -m jarvis.voice)

Press Enter and speak; Jarvis stops listening when you pause, then answers out loud.
You can also type a message instead of pressing Enter on an empty line.
"""

from __future__ import annotations

import os
import sys
import time

from rich.console import Console

from .brain import AllProvidersFailed, Brain
from .config import load_settings, voice_settings_from_env
from .personality import system_prompt
from .providers import Provider, ProviderError
from .speech import SentenceBuffer
from .tts import KOKORO_MODEL, KOKORO_VOICES, KokoroVoice, Mouth, WindowsVoice


def build_transcriber(vs, console: Console):
    if vs.stt_engine == "groq":
        from .stt import GroqTranscriber

        return GroqTranscriber(vs.groq_key, language=vs.language)
    from .stt import LocalWhisperTranscriber

    with console.status(f"[dim]loading speech recognition ({vs.whisper_model}); the first run downloads it…[/dim]"):
        return LocalWhisperTranscriber(vs.whisper_model, language=vs.language)


def build_mouth(vs) -> Mouth:
    if vs.tts_engine == "kokoro":
        return Mouth(lambda: KokoroVoice(vs.kokoro_voice))
    return Mouth(lambda: WindowsVoice(vs.windows_voice))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    console = Console(highlight=False)
    try:
        settings = load_settings()
        kokoro_ready = KOKORO_MODEL.exists() and KOKORO_VOICES.exists()
        vs = voice_settings_from_env(os.environ, kokoro_installed=kokoro_ready)
    except ValueError as err:
        console.print(f"[red]Setup problem:[/red] {err}")
        return 1
    if not settings.providers:
        console.print("[red]No brain configured.[/red] Run setup.bat first.")
        return 1

    try:
        transcriber = build_transcriber(vs, console)
        mouth = build_mouth(vs)
    except ImportError as err:
        console.print(f"[red]Voice parts aren't installed:[/red] {err.name}. See README.md, Phase 2.")
        return 1

    brain = Brain(
        [Provider(cfg) for cfg in settings.providers],
        system_prompt=lambda: system_prompt(settings.user_name),
        history_turns=settings.history_turns,
        on_failure=lambda err: console.print(f"[dim]  ✗ {err.provider}: {err.reason}[/dim]"),
    )
    from .listen import record_utterance

    console.print("[bold cyan]J.A.R.V.I.S.[/bold cyan] [dim]online · voice mode[/dim]")
    console.print(f"[dim]ears: {transcriber.label} · voice: {mouth.label} · brain: {settings.providers[0].name}[/dim]")
    console.print("[dim]Press Enter and speak. Type a message to skip the mic. Type q to quit.[/dim]")
    greet(mouth, console)

    while True:
        try:
            typed = console.input("\n[bold]›[/bold] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if typed.lower() in {"q", "quit", "exit", "/quit"}:
            break
        if typed == "/reset":
            brain.reset()
            console.print("[dim]Conversation forgotten.[/dim]")
            continue

        text = typed
        if not text:
            with console.status("[bold green]listening…[/bold green] [dim](pause to finish)[/dim]"):
                audio = record_utterance()
            if audio is None:
                console.print("[dim]I didn't hear anything.[/dim]")
                continue
            started = time.perf_counter()
            try:
                with console.status("[dim]transcribing…[/dim]"):
                    text = transcriber.transcribe(audio)
            except ProviderError as err:
                console.print(f"[red]Couldn't transcribe:[/red] {err.reason}")
                continue
            if not text:
                console.print("[dim]I couldn't make that out.[/dim]")
                continue
            console.print(f"[dim]you said[/dim] {text} [dim]({time.perf_counter() - started:.1f}s)[/dim]")

        try:
            respond(brain, mouth, console, text)
        except KeyboardInterrupt:
            mouth.interrupt()
            console.print(" [dim](interrupted)[/dim]")

    mouth.interrupt()
    mouth.close()
    console.print("[dim]Jarvis offline.[/dim]")
    return 0


def greet(mouth: Mouth, console: Console) -> None:
    hour = time.localtime().tm_hour
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    line = f"Good {part}. Systems online."
    console.print(f"[bold cyan]jarvis ›[/bold cyan] {line}")
    mouth.say(line)


def respond(brain: Brain, mouth: Mouth, console: Console, text: str) -> None:
    sentences = SentenceBuffer()
    started = time.perf_counter()
    first_sound = None
    console.print("[bold cyan]jarvis ›[/bold cyan] ", end="")
    try:
        for piece in brain.ask(text):
            sys.stdout.write(piece)
            sys.stdout.flush()
            for sentence in sentences.feed(piece):
                first_sound = first_sound or time.perf_counter()
                mouth.say(sentence)
    except AllProvidersFailed:
        console.print("\n[red]I can't reach any brain right now.[/red]")
        return
    for sentence in sentences.flush():
        first_sound = first_sound or time.perf_counter()
        mouth.say(sentence)
    used = brain.last_provider
    to_voice = f"{first_sound - started:.1f}s to first words" if first_sound else "no speech"
    console.print(f"\n[dim]  {used.name} · {to_voice}[/dim]")
    mouth.wait()
    if mouth.error:
        console.print(f"[dim]  voice problem: {mouth.error}[/dim]")
        mouth.error = None


if __name__ == "__main__":
    sys.exit(main())
