"""The conversation: history, personality, tools, and falling back between providers."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any, Protocol

from .providers import ProviderError

CUT_OFF_NOTICE = " [connection lost]"


class ChatProvider(Protocol):
    name: str
    model: str
    last_tool_calls: list[dict]

    def stream(self, messages: list[dict], tools: list[dict] | None = None) -> Iterator[str]: ...


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
        tools: Any | None = None,
        max_tool_steps: int = 5,
    ):
        if not providers:
            raise ValueError("Brain needs at least one provider.")
        self.providers = providers
        self.history: list[dict] = []
        self.last_provider: ChatProvider | None = None
        self._system_prompt = system_prompt
        self._history_turns = history_turns
        self._on_failure = on_failure
        self.tools = tools
        self.max_tool_steps = max_tool_steps

    def reset(self) -> None:
        self.history.clear()

    def ask(self, text: str) -> Iterator[str]:
        """Stream a reply, executing tools if requested by the model and feeding results back."""
        text = text.strip()
        if not text:
            return

        messages = [
            {"role": "system", "content": self._system_prompt()},
            *self.history[-2 * self._history_turns:],
            {"role": "user", "content": text},
        ]
        tool_schemas = self.tools.to_openai_tools() if self.tools else None
        failures: list[ProviderError] = []

        for provider in self.providers:
            step = 0
            curr_messages = list(messages)
            provider_failed = False

            while step < self.max_tool_steps:
                step += 1
                try:
                    stream = provider.stream(curr_messages, tools=tool_schemas)
                except TypeError:
                    stream = provider.stream(curr_messages)

                try:
                    first = next(stream, "")
                except ProviderError as err:
                    failures.append(err)
                    if self._on_failure:
                        self._on_failure(err)
                    provider_failed = True
                    break

                tool_calls = getattr(provider, "last_tool_calls", None)
                if not first and tool_calls:
                    # Model emitted tool call(s)
                    for tc in tool_calls:
                        fn = tc.get("function", {})
                        name = fn.get("name", "")
                        raw_args = fn.get("arguments", "{}")
                        try:
                            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        except Exception:
                            args = {}

                        try:
                            result = self.tools.execute(name, args, confirmed=True) if self.tools else "No tools"
                        except Exception as tool_exc:
                            result = {"error": str(tool_exc)}

                        curr_messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tc],
                        })
                        curr_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", "call_1"),
                            "name": name,
                            "content": json.dumps(result, default=str),
                        })
                    continue

                if not first:
                    # Empty response without tool calls
                    err = ProviderError(provider.name, "returned an empty reply")
                    failures.append(err)
                    if self._on_failure:
                        self._on_failure(err)
                    provider_failed = True
                    break

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
                    if hasattr(stream, "close"):
                        stream.close()
                    self._remember(text, "".join(reply))
                return

            if not provider_failed and step >= self.max_tool_steps:
                msg = f"Tool loop stopped: reached maximum {self.max_tool_steps} steps limit."
                self.last_provider = provider
                self._remember(text, msg)
                yield msg
                return

        raise AllProvidersFailed(failures)

    def _remember(self, user_text: str, reply: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply})
        excess = len(self.history) - 4 * self._history_turns
        if excess > 0:
            del self.history[:excess]
