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
