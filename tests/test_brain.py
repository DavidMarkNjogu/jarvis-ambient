import pytest

from jarvis.brain import CUT_OFF_NOTICE, AllProvidersFailed, Brain
from jarvis.providers import ProviderError


class FakeProvider:
    def __init__(self, name, chunks=(), fail=None, fail_after=None):
        self.name = name
        self.model = f"{name}-model"
        self.chunks = list(chunks)
        self.fail = fail
        self.fail_after = fail_after
        self.calls = []

    def stream(self, messages):
        self.calls.append(messages)
        if self.fail and self.fail_after is None:
            raise ProviderError(self.name, self.fail)
        for i, chunk in enumerate(self.chunks):
            if self.fail_after == i:
                raise ProviderError(self.name, self.fail)
            yield chunk


def make_brain(*providers, turns=12, failures=None):
    return Brain(
        list(providers),
        system_prompt=lambda: "SYSTEM",
        history_turns=turns,
        on_failure=failures.append if failures is not None else None,
    )


def test_streams_reply_and_remembers_it():
    p = FakeProvider("gemini", ["Good ", "evening."])
    brain = make_brain(p)

    assert "".join(brain.ask("hello")) == "Good evening."
    assert brain.history == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "Good evening."},
    ]
    assert brain.last_provider is p


def test_sends_system_prompt_then_history_then_new_message():
    p = FakeProvider("gemini", ["ok"])
    brain = make_brain(p)
    "".join(brain.ask("first"))
    "".join(brain.ask("second"))

    sent = p.calls[-1]
    assert sent[0] == {"role": "system", "content": "SYSTEM"}
    assert [m["content"] for m in sent[1:]] == ["first", "ok", "second"]


def test_falls_back_to_next_provider_before_any_text():
    failures = []
    gemini = FakeProvider("gemini", fail="rate limit")
    groq = FakeProvider("groq", ["From groq."])
    brain = make_brain(gemini, groq, failures=failures)

    assert "".join(brain.ask("hi")) == "From groq."
    assert brain.last_provider is groq
    assert [f.provider for f in failures] == ["gemini"]


def test_empty_reply_counts_as_failure():
    brain = make_brain(FakeProvider("gemini", []), FakeProvider("groq", ["ok"]))
    assert "".join(brain.ask("hi")) == "ok"


def test_raises_when_every_provider_fails():
    brain = make_brain(FakeProvider("gemini", fail="bad key"), FakeProvider("ollama", fail="not running"))

    with pytest.raises(AllProvidersFailed) as info:
        "".join(brain.ask("hi"))
    assert [f.provider for f in info.value.failures] == ["gemini", "ollama"]
    assert brain.history == []


def test_mid_reply_failure_keeps_partial_text_and_does_not_switch():
    gemini = FakeProvider("gemini", ["Half a ", "thought", "never"], fail="dropped", fail_after=2)
    groq = FakeProvider("groq", ["should not be used"])
    brain = make_brain(gemini, groq)

    assert "".join(brain.ask("hi")) == "Half a thought" + CUT_OFF_NOTICE
    assert groq.calls == []
    assert brain.history[-1]["content"] == "Half a thought" + CUT_OFF_NOTICE


def test_stopping_early_still_remembers_what_was_said():
    brain = make_brain(FakeProvider("gemini", ["one ", "two ", "three"]))
    reply = brain.ask("count")
    next(reply)
    reply.close()

    assert brain.history[-1] == {"role": "assistant", "content": "one "}


def test_only_recent_turns_are_sent():
    p = FakeProvider("gemini", ["ok"])
    brain = make_brain(p, turns=2)
    for i in range(5):
        "".join(brain.ask(f"q{i}"))

    sent = [m["content"] for m in p.calls[-1][1:]]
    assert sent == ["q2", "ok", "q3", "ok", "q4"]


def test_reset_forgets_history():
    brain = make_brain(FakeProvider("gemini", ["ok"]))
    "".join(brain.ask("hi"))
    brain.reset()
    assert brain.history == []


def test_needs_a_provider():
    with pytest.raises(ValueError):
        Brain([], system_prompt=lambda: "")


def test_empty_or_whitespace_message_is_ignored():
    p = FakeProvider("gemini", ["should not be called"])
    brain = make_brain(p)
    assert list(brain.ask("")) == []
    assert list(brain.ask("   \n\t  ")) == []
    assert p.calls == []
    assert brain.history == []


def test_brain_executes_tool_and_feeds_result_back():
    from jarvis.tools import ToolRegistry, ToolDef

    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="get_time",
            description="Get current time",
            parameters={"type": "object", "properties": {}},
            handler=lambda: {"time": "14:30:00"},
            risk="safe",
        )
    )

    class ToolCallingProvider:
        name = "gemini"
        model = "gemini-model"

        def __init__(self):
            self.calls = []
            self.last_tool_calls = []
            self._step = 0

        def stream(self, messages, tools=None):
            self.calls.append(messages)
            self._step += 1
            if self._step == 1:
                self.last_tool_calls = [
                    {"id": "call_t1", "type": "function", "function": {"name": "get_time", "arguments": "{}"}}
                ]
                return iter([])
            else:
                self.last_tool_calls = []
                return iter(["It is ", "2:30 PM."])

    provider = ToolCallingProvider()
    brain = Brain(
        [provider],
        system_prompt=lambda: "SYS",
        tools=registry,
    )

    reply = "".join(brain.ask("what time is it"))
    assert reply == "It is 2:30 PM."
    assert len(provider.calls) == 2
    # Verify second call included the tool output
    second_call_messages = provider.calls[1]
    assert any(m.get("role") == "tool" and "14:30:00" in str(m.get("content")) for m in second_call_messages)


def test_tool_loop_stops_after_max_steps():
    from jarvis.tools import ToolRegistry, ToolDef

    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="ping",
            description="ping",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "pong",
            risk="safe",
        )
    )

    class InfiniteToolProvider:
        name = "gemini"
        model = "gemini-model"

        def __init__(self):
            self.calls = []
            self.last_tool_calls = [
                {"id": "call_loop", "type": "function", "function": {"name": "ping", "arguments": "{}"}}
            ]

        def stream(self, messages, tools=None):
            self.calls.append(messages)
            return iter([])

    provider = InfiniteToolProvider()
    brain = Brain([provider], system_prompt=lambda: "SYS", tools=registry, max_tool_steps=5)

    reply = "".join(brain.ask("start loop"))
    assert len(provider.calls) == 5
    assert "maximum" in reply.lower() or "limit" in reply.lower() or "stopped" in reply.lower()


def test_brain_requires_confirmation_for_confirm_risk_tools():
    from jarvis.tools import ToolRegistry, ToolDef

    deleted = []
    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="delete_file",
            description="Deletes a file",
            parameters={"type": "object", "properties": {"filename": {"type": "string"}}},
            handler=lambda filename: deleted.append(filename) or "deleted",
            risk="confirm",
        )
    )

    class ConfirmToolProvider:
        name = "gemini"
        model = "gemini-model"

        def __init__(self):
            self.calls = []
            self.last_tool_calls = []
            self._step = 0

        def stream(self, messages, tools=None):
            self.calls.append(messages)
            self._step += 1
            if self._step == 1:
                self.last_tool_calls = [
                    {"id": "c1", "type": "function", "function": {"name": "delete_file", "arguments": '{"filename": "test.txt"}'}}
                ]
                return iter([])
            else:
                self.last_tool_calls = []
                return iter(["File has been deleted."])

    provider = ConfirmToolProvider()
    brain = Brain([provider], system_prompt=lambda: "SYS", tools=registry)

    # 1. First ask: user says "delete test.txt". Brain must ask for confirmation and NOT run the tool
    q1 = "".join(brain.ask("delete test.txt"))
    assert "confirm" in q1.lower()
    assert deleted == []
    assert brain.pending_confirmation is not None

    # 2. User says "yes": Brain must execute the tool and provide final response
    q2 = "".join(brain.ask("yes"))
    assert deleted == ["test.txt"]
    assert "File has been deleted" in q2
    assert brain.pending_confirmation is None


def test_brain_cancels_confirm_risk_tool_when_user_says_no():
    from jarvis.tools import ToolRegistry, ToolDef

    deleted = []
    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="delete_file",
            description="Deletes a file",
            parameters={"type": "object", "properties": {"filename": {"type": "string"}}},
            handler=lambda filename: deleted.append(filename) or "deleted",
            risk="confirm",
        )
    )

    class ConfirmToolProvider:
        name = "gemini"
        model = "gemini-model"

        def __init__(self):
            self.calls = []
            self.last_tool_calls = [
                {"id": "c1", "type": "function", "function": {"name": "delete_file", "arguments": '{"filename": "test.txt"}'}}
            ]

        def stream(self, messages, tools=None):
            self.calls.append(messages)
            return iter([])

    provider = ConfirmToolProvider()
    brain = Brain([provider], system_prompt=lambda: "SYS", tools=registry)

    q1 = "".join(brain.ask("delete test.txt"))
    assert "confirm" in q1.lower()
    assert deleted == []

    # User says "no"
    q2 = "".join(brain.ask("no"))
    assert "cancel" in q2.lower()
    assert deleted == []
    assert brain.pending_confirmation is None


def test_is_affirmative_and_negative_matching():
    from jarvis.brain import is_affirmative, is_negative

    # Multi-word exact phrases
    assert is_affirmative("do it")
    assert is_affirmative("go ahead")
    assert is_negative("never mind")

    # Word contained in sentence
    assert is_affirmative("yes please")
    assert is_affirmative("yeah, sure!")
    assert is_negative("no thanks")
    assert is_negative("don't do that")

    # Neutral or unrelated
    assert not is_affirmative("maybe tomorrow")
    assert not is_negative("tell me a joke")


def test_brain_clarification_on_ambiguous_confirmation():
    from jarvis.tools import ToolRegistry, ToolDef

    registry = ToolRegistry()
    registry.register(
        ToolDef(
            name="delete_file",
            description="Deletes a file",
            parameters={"type": "object", "properties": {"filename": {"type": "string"}}},
            handler=lambda filename: "deleted",
            risk="confirm",
        )
    )

    class ConfirmToolProvider:
        name = "gemini"
        model = "gemini-model"
        calls = []
        last_tool_calls = [
            {"id": "c1", "type": "function", "function": {"name": "delete_file", "arguments": '{"filename": "test.txt"}'}}
        ]

        def stream(self, messages, tools=None):
            return iter([])

    brain = Brain([ConfirmToolProvider()], system_prompt=lambda: "SYS", tools=registry)
    _ = "".join(brain.ask("delete test.txt"))
    assert brain.pending_confirmation is not None

    # Ambiguous reply
    clarification = "".join(brain.ask("what is the weather today?"))
    assert "please say yes or no" in clarification.lower()
    assert brain.pending_confirmation is not None

