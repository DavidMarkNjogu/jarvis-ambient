"""The conversation: history, personality and falling back between providers."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Protocol

from .providers import ProviderError

CUT_OFF_NOTICE = " [connection lost]"


class ChatProvider(Protocol):
    name: str
    model: str

    def stream(self, messages: list[dict]) -> Iterator[str]: ...


class AllProvidersFailed(Exception):
    def __init__(self, failures: list[ProviderError]):
        super().__init__("No brain available: " + "; ".join(str(f) for f in failures))
        self.failures = failures


class Brain:
    def __init__(
        self,
        providers: list[ChatProvider],
        system_prompt: Callable[[], str],
        history_turns: int = 12,
        on_failure: Callable[[ProviderError], None] | None = None,
    ):
        if not providers:
            raise ValueError("Brain needs at least one provider.")
        self.providers = providers
        self.history: list[dict] = []
        self.last_provider: ChatProvider | None = None
        self._system_prompt = system_prompt
        self._history_turns = history_turns
        self._on_failure = on_failure

    def reset(self) -> None:
        self.history.clear()

    def ask(self, text: str) -> Iterator[str]:
        """Stream a reply, trying each provider in order until one starts answering.

        Falls back only before the first piece of text arrives, so a reply is never
        stitched together from two different models.
        """
        text = text.strip()
        if not text:
            return
        messages = [
            {"role": "system", "content": self._system_prompt()},
            *self.history[-2 * self._history_turns:],
            {"role": "user", "content": text},
        ]
        failures: list[ProviderError] = []
        for provider in self.providers:
            stream = provider.stream(messages)
            try:
                first = next(stream, "")
            except ProviderError as err:
                failures.append(err)
                if self._on_failure:
                    self._on_failure(err)
                continue
            if not first:
                err = ProviderError(provider.name, "returned an empty reply")
                failures.append(err)
                if self._on_failure:
                    self._on_failure(err)
                continue

            self.last_provider = provider
            reply = [first]
            try:
                yield first
                for piece in stream:
                    reply.append(piece)
                    yield piece
            except ProviderError:
                reply.append(CUT_OFF_NOTICE)
                yield CUT_OFF_NOTICE
            finally:
                stream.close()
                self._remember(text, "".join(reply))
            return

        raise AllProvidersFailed(failures)

    def _remember(self, user_text: str, reply: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})
        # Keep a little more than we send so /reset is the only thing that truly forgets.
        excess = len(self.history) - 4 * self._history_turns
        if excess > 0:
            del self.history[:excess]
