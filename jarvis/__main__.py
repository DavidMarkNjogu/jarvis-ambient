"""Terminal Jarvis. Run with:  python -m jarvis   (or double-click jarvis.bat)"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from rich.console import Console

from .brain import AllProvidersFailed, Brain
from .config import load_settings
from .personality import system_prompt
from .providers import Provider, ProviderError

HELP = """[dim]/reset   forget this conversation
/models  list models each provider offers
/brain   show which providers are in use
/quit    exit (or Ctrl+C)[/dim]"""


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="jarvis", description="Text-mode Jarvis (Phase 1).")
    parser.add_argument("question", nargs="*", help="ask one question and exit")
    args = parser.parse_args(argv)
    console = Console(highlight=False)

    try:
        settings = load_settings()
    except ValueError as err:
        console.print(f"[red]Setup problem:[/red] {err}")
        return 1
    if not settings.providers:
        console.print(
            "[red]No brain configured.[/red] Copy [bold].env.example[/bold] to [bold].env[/bold] "
            "and paste in a free Gemini or Groq API key. See README.md."
        )
        return 1

    providers = [Provider(cfg) for cfg in settings.providers]
    brain = Brain(
        providers,
        system_prompt=lambda: system_prompt(settings.user_name, mode="text"),
        history_turns=settings.history_turns,
        on_failure=lambda err: console.print(f"[dim]  ✗ {err.provider}: {err.reason}[/dim]"),
    )

    if args.question:
        return 0 if answer(console, brain, " ".join(args.question)) else 1

    console.print("[bold cyan]J.A.R.V.I.S.[/bold cyan] [dim]online · text mode · type /help[/dim]")
    show_brain(console, providers, settings.skipped)
    while True:
        try:
            text = console.input("\n[bold]you ›[/bold] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not text:
            continue
        command = text.lower()
        if command in {"/quit", "/exit", "quit", "exit"}:
            break
        if command == "/help":
            console.print(HELP)
        elif command == "/reset":
            brain.reset()
            console.print("[dim]Conversation forgotten.[/dim]")
        elif command == "/brain":
            show_brain(console, providers, settings.skipped)
        elif command == "/models":
            show_models(console, providers)
        else:
            answer(console, brain, text)
    console.print("[dim]Jarvis offline.[/dim]")
    return 0


def answer(console: Console, brain: Brain, text: str) -> bool:
    started = time.perf_counter()
    reply = brain.ask(text)
    thinking = console.status("[dim]thinking…[/dim]", spinner="dots")
    thinking.start()
    waiting = True
    try:
        for piece in reply:
            if waiting:
                thinking.stop()
                waiting = False
                console.print("[bold cyan]jarvis ›[/bold cyan] ", end="")
            sys.stdout.write(piece)
            sys.stdout.flush()
    except AllProvidersFailed:
        console.print("[red]I can't reach any brain right now.[/red] See the reasons above.")
        console.print("[dim]  Fix: add a free Gemini or Groq key to .env (see README.md), or install Ollama.[/dim]")
        return False
    except KeyboardInterrupt:
        reply.close()
        console.print(" [dim](interrupted)[/dim]")
        return True
    finally:
        thinking.stop()
    used = brain.last_provider
    console.print(f"\n[dim]  {used.name} · {used.model} · {time.perf_counter() - started:.1f}s[/dim]")
    return True


def show_brain(console: Console, providers: list[Provider], skipped: list[str]) -> None:
    order = " → ".join(f"{p.name} ({p.model})" for p in providers)
    console.print(f"[dim]brain order: {order}[/dim]")
    for reason in skipped:
        console.print(f"[dim]skipped {reason}[/dim]")


def show_models(console: Console, providers: list[Provider]) -> None:
    for provider in providers:
        try:
            models = provider.list_models()
        except ProviderError as err:
            console.print(f"[dim]{err.provider}: {err.reason}[/dim]")
            continue
        console.print(f"[bold]{provider.name}[/bold] [dim]({len(models)} models)[/dim]")
        console.print("[dim]  " + "\n  ".join(models[:40]) + "[/dim]")


if __name__ == "__main__":
    sys.exit(main())
