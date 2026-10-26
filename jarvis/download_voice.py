"""Download the Kokoro voice model (about 115 MB) into models/. Optional upgrade over the Windows voice.

Run with:  python -m jarvis.download_voice
"""

from __future__ import annotations

import sys

import httpx

from .tts import KOKORO_MODEL, KOKORO_VOICES, MODELS_DIR

RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
FILES = [(f"{RELEASE}/{KOKORO_MODEL.name}", KOKORO_MODEL), (f"{RELEASE}/{KOKORO_VOICES.name}", KOKORO_VOICES)]


def download(url: str, target) -> None:
    partial = target.with_suffix(target.suffix + ".part")
    with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        done = 0
        with partial.open("wb") as out:
            for chunk in response.iter_bytes(1 << 16):
                out.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r  {target.name}: {done / total:5.1%} of {total / 1e6:.0f} MB", end="", flush=True)
    partial.replace(target)
    print()


def main() -> int:
    MODELS_DIR.mkdir(exist_ok=True)
    for url, target in FILES:
        if target.exists():
            print(f"  {target.name}: already downloaded")
            continue
        try:
            download(url, target)
        except httpx.HTTPError as err:
            print(f"\n  Download failed for {target.name}: {err}")
            return 1
    print("Kokoro voice ready. Jarvis will use it automatically next time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
