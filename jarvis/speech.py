"""Turning streamed reply text into speakable sentences."""

from __future__ import annotations

import re

_ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "st", "vs", "etc", "e.g", "i.e", "no", "approx"}
_BOUNDARY = re.compile(r"[.!?…]+[\"')\]]*\s+|\n+")
_MARKDOWN = re.compile(r"[*_#`>|]+")
_URL = re.compile(r"https?://\S+")


def clean_for_speech(text: str) -> str:
    """Remove things that sound wrong read aloud: markdown symbols and raw links."""
    text = _URL.sub("the link on screen", text)
    text = _MARKDOWN.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


class SentenceBuffer:
    """Collects streamed text and releases whole sentences as soon as they are complete.

    Speaking sentence by sentence lets Jarvis start talking while the rest of the
    reply is still arriving.
    """

    def __init__(self, min_chars: int = 12):
        self._pending = ""
        self._min_chars = min_chars

    def feed(self, text: str) -> list[str]:
        self._pending += text
        sentences: list[str] = []
        start = 0
        for match in _BOUNDARY.finditer(self._pending):
            candidate = self._pending[start:match.end()]
            if self._ends_with_abbreviation(candidate) or len(candidate.strip()) < self._min_chars:
                continue
            sentences.append(candidate)
            start = match.end()
        self._pending = self._pending[start:]
        return [s for s in (clean_for_speech(s) for s in sentences) if s]

    def flush(self) -> list[str]:
        rest = clean_for_speech(self._pending)
        self._pending = ""
        return [rest] if rest else []

    @staticmethod
    def _ends_with_abbreviation(candidate: str) -> bool:
        words = candidate.strip().rstrip(".").split()
        return bool(words) and words[-1].lower() in _ABBREVIATIONS and candidate.rstrip().endswith(".")
