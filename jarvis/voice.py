"""Talking Jarvis (Phase 2). Run with:  voice.bat   (or  python -m jarvis.voice)

Press Enter and speak; Jarvis stops listening when you pause, then answers out loud.
You can also type a message instead of pressing Enter on an empty line.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from rich.console import Console

from .brain import AllProvidersFailed, Brain
from .config import load_settings, voice_settings_from_env
from .memory import Memory
from .personality import system_prompt
from .providers import Provider, ProviderError
from .speech import SentenceBuffer
from .tts import KOKORO_MODEL, KOKORO_VOICES, KokoroVoice, Mouth, WindowsVoice, list_voices
from .visual import VisualServer
from .wake import make_chime


def build_transcriber(vs, console: Console):
    if vs.stt_engine == "groq":
        from .stt import GroqTranscriber

        return GroqTranscriber(vs.groq_key, language=vs.language)
    from .stt import LocalWhisperTranscriber

    with console.status(f"[dim]loading speech recognition ({vs.whisper_model}); the first run downloads it…[/dim]"):
        return LocalWhisperTranscriber(vs.whisper_model, language=vs.language)


def build_mouth(vs) -> Mouth:
    speed = getattr(vs, "voice_speed", 1.1)
    if vs.tts_engine == "kokoro":
        return Mouth(lambda: KokoroVoice(vs.kokoro_voice, speed=speed))
    return Mouth(lambda: WindowsVoice(vs.windows_voice, speed=speed))


def init_wake_detector(vs, console: Console | None = None):
    if not getattr(vs, "wake_enabled", True):
        return None
    try:
        from .wake import WakeDetector

        threshold = getattr(vs, "wake_threshold", 0.5)
        return WakeDetector(threshold=threshold, load_model=True)
    except Exception as err:
        if console:
            console.print(f"[dim]wake word detector disabled ({err}); falling back to press-Enter mode.[/dim]")
        return None


def main(argv: list[str] | None = None, console: Console | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="jarvis-voice", description="Talking Jarvis (Phase 3).")
    parser.add_argument("--no-visual", action="store_true", help="run without browser visualizer")
    parser.add_argument("--port", type=int, default=5050, help="port for the visualizer server")
    parser.add_argument("--push-to-talk", action="store_true", help="force press-Enter mode (skip wake word)")
    args = parser.parse_args(argv)

    console = console or Console(highlight=False)
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

    wake_detector = None
    if not args.push_to_talk and getattr(vs, "wake_enabled", True):
        wake_detector = init_wake_detector(vs, console)

    visual: VisualServer | None = None
    if not args.no_visual and os.environ.get("JARVIS_VISUAL", "1") != "0":
        try:
            visual = VisualServer(port=args.port)
            url = visual.start()
            console.print(f"[dim]aperture: {url}[/dim]")
        except Exception as err:
            console.print(f"[dim]visualizer failed to start ({err}), continuing voice-only[/dim]")
            visual = None

    from .tools import default_registry
    tools = default_registry()

    memory = Memory()
    brain = Brain(
        [Provider(cfg) for cfg in settings.providers],
        system_prompt=lambda: system_prompt(
            settings.user_name,
            mode="voice",
            voice_name=mouth.label,
            tools=[t.name for t in tools.list_tools()],
            profile_facts=memory.get_profile_facts(),
        ),
        history_turns=settings.history_turns,
        on_failure=lambda err: console.print(f"[dim]  ✗ {err.provider}: {err.reason}[/dim]"),
        tools=tools,
    )
    from .listen import MicStream, record_utterance

    mode_label = "hands-free 'Hey Jarvis'" if wake_detector else "press-Enter"
    console.print(f"[bold cyan]J.A.R.V.I.S.[/bold cyan] [dim]online · voice mode ({mode_label})[/dim]")
    console.print(f"[dim]ears: {transcriber.label} · voice: {mouth.label} · brain: {settings.providers[0].name}[/dim]")
    if wake_detector:
        console.print("[dim]Say 'Hey Jarvis' to speak hands-free, or type a command (/speed, /voices, /voice, q).[/dim]")
    else:
        console.print("[dim]Press Enter and speak. Type a message to skip the mic. Type q to quit.[/dim]")
    greet(mouth, console, visual=visual)

    mic_stream: MicStream | None = None
    stream_iter = None
    if wake_detector:
        try:
            mic_stream = MicStream()
            stream_iter = iter(mic_stream)
        except Exception as err:
            console.print(f"[dim]Could not open continuous mic ({err}); falling back to press-Enter mode.[/dim]")
            wake_detector = None

    try:
        while True:
            if visual:
                visual.set_state("idle")

            typed = ""
            heard_wake = False

            if wake_detector and stream_iter is not None:
                # Check for keyboard input on Windows without blocking
                try:
                    import msvcrt

                    while True:
                        if msvcrt.kbhit():
                            typed = console.input("\n[bold]›[/bold] ").strip()
                            break
                        # Poll next frame from stream
                        frame = next(stream_iter)
                        if wake_detector.process_frame(frame):
                            heard_wake = True
                            break
                except (ImportError, StopIteration):
                    try:
                        typed = console.input("\n[bold]›[/bold] ").strip()
                    except (EOFError, KeyboardInterrupt):
                        break
                except (EOFError, KeyboardInterrupt):
                    break
            else:
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

            if typed.startswith("/speed"):
                parts = typed.split()
                if len(parts) > 1:
                    try:
                        new_speed = float(parts[1])
                        mouth.set_speed(new_speed)
                        console.print(f"[dim]Voice speed set to {new_speed}x.[/dim]")
                    except ValueError:
                        console.print("[dim]Usage: /speed <number between 0.5 and 2.5>[/dim]")
                else:
                    console.print(f"[dim]Current voice speed: {getattr(vs, 'voice_speed', 1.1)}x. Usage: /speed <number>[/dim]")
                continue

            if typed.startswith("/voices"):
                voices = list_voices(vs.tts_engine)
                console.print("[bold]Available voices:[/bold]")
                for v in voices:
                    console.print(f"  • {v}")
                continue

            if typed.startswith("/voice"):
                parts = typed.split(maxsplit=1)
                if len(parts) > 1:
                    new_voice = parts[1].strip()
                    mouth.set_voice(new_voice)
                    console.print(f"[dim]Active voice switched to: {mouth.label}[/dim]")
                else:
                    console.print(f"[dim]Current voice: {mouth.label}. Usage: /voice <name>[/dim]")
                continue

            text = typed
            if heard_wake or (not typed and not wake_detector):
                if heard_wake:
                    import sounddevice as sd

                    sd.play(make_chime(), 16000)
                    sd.wait()
                    if mic_stream is not None:
                        mic_stream.drain()

                if visual:
                    visual.set_state("listening", "Listening...")
                with console.status("[bold green]listening…[/bold green] [dim](pause to finish)[/dim]"):
                    audio = record_utterance(stream=stream_iter if heard_wake else None)
                if audio is None:
                    console.print("[dim]I didn't hear anything.[/dim]")
                    continue

                if wake_detector:
                    wake_detector.pause()

                started = time.perf_counter()
                try:
                    if visual:
                        visual.set_state("thinking", "Transcribing speech...")
                    with console.status("[dim]transcribing…[/dim]"):
                        text = transcriber.transcribe(audio)
                except ProviderError as err:
                    console.print(f"[red]Couldn't transcribe:[/red] {err.reason}")
                    if wake_detector:
                        wake_detector.resume()
                    continue

                if not text:
                    console.print("[dim]I couldn't make that out.[/dim]")
                    if wake_detector:
                        wake_detector.resume()
                    continue
                console.print(f"[dim]you said[/dim] {text} [dim]({time.perf_counter() - started:.1f}s)[/dim]")

            if not text or not text.strip():
                continue

            try:
                if visual:
                    visual.set_state("thinking", "Synthesizing answer...")
                respond(brain, mouth, console, text, visual=visual)
            except KeyboardInterrupt:
                mouth.interrupt()
                if visual:
                    visual.set_state("idle", "")
                console.print(" [dim](interrupted)[/dim]")
            finally:
                if wake_detector:
                    wake_detector.resume()
    finally:
        mouth.interrupt()
        mouth.close()
        if visual:
            visual.stop()
        try:
            user_turns = [m.get("content", "") for m in brain.history if m.get("role") == "user"]
            if user_turns:
                summary = f"Voice session: {len(user_turns)} turns. Queries: {'; '.join(user_turns[:5])}"
                memory.save_session_summary(summary)
        except Exception:
            pass
        memory.close()
        console.print("[dim]Jarvis offline.[/dim]")
    return 0


def greet(mouth: Mouth, console: Console, visual: VisualServer | None = None) -> None:
    hour = time.localtime().tm_hour
    part = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
    line = f"Good {part}. Systems online."
    console.print(f"[bold cyan]jarvis ›[/bold cyan] {line}")
    if visual:
        visual.set_state("speaking", line)
    mouth.say(line)
    mouth.wait()
    if visual:
        visual.set_state("idle")


def respond(brain: Brain, mouth: Mouth, console: Console, text: str, visual: VisualServer | None = None) -> None:
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
                if visual:
                    visual.set_state("speaking", sentence)
                mouth.say(sentence)
    except AllProvidersFailed:
        if visual:
            visual.set_state("error", "No brain available.")
        console.print("\n[red]I can't reach any brain right now.[/red]")
        return
    for sentence in sentences.flush():
        first_sound = first_sound or time.perf_counter()
        if visual:
            visual.set_state("speaking", sentence)
        mouth.say(sentence)
    used = brain.last_provider
    to_voice = f"{first_sound - started:.1f}s to first words" if first_sound else "no speech"
    console.print(f"\n[dim]  {used.name} · {to_voice}[/dim]")
    mouth.wait()
    if visual:
        visual.set_state("idle")
    if mouth.error:
        console.print(f"[dim]  voice problem: {mouth.error}[/dim]")
        mouth.error = None


if __name__ == "__main__":
    sys.exit(main())
