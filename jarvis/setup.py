"""One-time setup: save API keys and your name to .env without editing it by hand.

Run with:  setup.bat   (or  python -m jarvis.setup)
"""

from __future__ import annotations

import getpass
import re
import sys

from .config import KNOWN_PROVIDERS, PROJECT_ROOT, ProviderConfig
from .providers import Provider, ProviderError

ENV_FILE = PROJECT_ROOT / ".env"
TEMPLATE = PROJECT_ROOT / ".env.example"

# provider -> (key shape, .env variable, where to get one)
KEY_FORMATS = {
    # Older Google keys start with AIza; keys made in AI Studio since 2026 start with AQ.
    "gemini": (re.compile(r"AIza[0-9A-Za-z_\-]{35}|AQ\.[0-9A-Za-z_\-.]{20,}"), "GEMINI_API_KEY", "https://aistudio.google.com/apikey"),
    "groq": (re.compile(r"gsk_[0-9A-Za-z]{20,}"), "GROQ_API_KEY", "https://console.groq.com/keys"),
}


def detect_provider(key: str) -> str | None:
    for name, (pattern, _, _) in KEY_FORMATS.items():
        if pattern.fullmatch(key):
            return name
    return None


def mask(key: str) -> str:
    return f"{key[:4]}…{key[-3:]}"


def apply_env_updates(text: str, updates: dict[str, str]) -> str:
    """Set NAME=value lines in .env text, keeping comments and other settings as they are."""
    lines = text.splitlines()
    remaining = dict(updates)
    for i, line in enumerate(lines):
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        name = line.split("=", 1)[0].strip()
        if name in remaining:
            lines[i] = f"{name}={remaining.pop(name)}"
    lines += [f"{name}={value}" for name, value in remaining.items()]
    return "\n".join(lines) + "\n"


def read_clipboard() -> str:
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        try:
            return root.clipboard_get().strip()
        finally:
            root.destroy()
    except Exception:
        return ""


def check_key(provider_name: str, key: str) -> str | None:
    """Send a tiny test message. Returns None if the key works, else the reason it didn't."""
    base_url, _, _, model = KNOWN_PROVIDERS[provider_name]
    provider = Provider(ProviderConfig(provider_name, base_url, model, key))
    try:
        "".join(provider.stream([{"role": "user", "content": "Reply with the single word: ready"}]))
    except ProviderError as err:
        return err.reason
    return None


def ask_for_keys() -> dict[str, str]:
    saved: dict[str, str] = {}
    print("1. In the browser, click Copy next to your Gemini or Groq API key.")
    print("   Then press Enter here. (You can also paste the key, or type skip.)")
    while True:
        entry = getpass.getpass("   Key: ").strip()
        if entry.lower() == "skip":
            break
        key = entry or read_clipboard()
        provider = detect_provider(key)
        if not provider:
            print("   No API key found. Gemini keys start with AQ. or AIza, Groq keys with gsk_. Copy it and press Enter again.")
            continue

        _, env_var, _ = KEY_FORMATS[provider]
        print(f"   Found a {provider} key ({mask(key)}). Testing it…")
        reason = check_key(provider, key)
        if reason and "rate limit" not in reason:
            print(f"   ✗ It didn't work: {reason}")
            continue
        saved[env_var] = key
        print(f"   ✓ {provider} key works.")

        others = [n for n, (_, var, _) in KEY_FORMATS.items() if var not in saved]
        if not others:
            break
        url = KEY_FORMATS[others[0]][2]
        if input(f"   Add a {others[0]} key too, as a backup brain? ({url}) [y/N] ").strip().lower() != "y":
            break
        print(f"   Copy the {others[0]} key, then press Enter.")
    return saved


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    print("Jarvis setup\n")
    updates = ask_for_keys()
    name = input("\n2. What should Jarvis call you? (Enter to skip) ").strip()
    if name:
        updates["USER_NAME"] = name
    if not updates:
        print("\nNothing changed.")
        return 0

    base = (ENV_FILE if ENV_FILE.exists() else TEMPLATE).read_text(encoding="utf-8")
    ENV_FILE.write_text(apply_env_updates(base, updates), encoding="utf-8")
    print("\nSaved to .env. Start Jarvis with jarvis.bat.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
