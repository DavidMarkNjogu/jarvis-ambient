from __future__ import annotations

import io
from unittest.mock import MagicMock

import pytest
from rich.console import Console

import jarvis.__main__ as main_mod
from jarvis.brain import AllProvidersFailed
from jarvis.config import ProviderConfig
from jarvis.providers import ProviderError


def test_main_cli_question(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_settings = MagicMock()
    fake_settings.providers = [ProviderConfig("groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "key")]
    fake_settings.user_name = "David"
    fake_settings.history_turns = 12

    monkeypatch.setattr(main_mod, "load_settings", lambda: fake_settings)
    called = []
    monkeypatch.setattr(main_mod, "answer", lambda c, b, text: called.append(text) or True)

    code = main_mod.main(argv=["what", "is", "the", "time"])
    assert code == 0
    assert called == ["what is the time"]


def test_main_setup_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main_mod, "load_settings", MagicMock(side_effect=ValueError("bad config")))
    assert main_mod.main(argv=[]) == 1

    fake_settings = MagicMock()
    fake_settings.providers = []
    monkeypatch.setattr(main_mod, "load_settings", lambda: fake_settings)
    assert main_mod.main(argv=[]) == 1


def test_main_repl_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_settings = MagicMock()
    fake_settings.providers = [ProviderConfig("groq", "https://api.groq.com/openai/v1", "llama", "key")]
    fake_settings.user_name = "David"
    fake_settings.skipped = ["ollama (not running)"]
    monkeypatch.setattr(main_mod, "load_settings", lambda: fake_settings)

    mock_brain = MagicMock()
    monkeypatch.setattr(main_mod, "Brain", lambda *a, **kw: mock_brain)

    mock_console = MagicMock()
    mock_console.input.side_effect = ["", "/help", "/reset", "/brain", "/models", "test question", "exit"]
    monkeypatch.setattr(main_mod, "Console", lambda highlight=False: mock_console)

    mock_answer = MagicMock(return_value=True)
    monkeypatch.setattr(main_mod, "answer", mock_answer)

    code = main_mod.main(argv=[])
    assert code == 0
    mock_brain.reset.assert_called_once()
    mock_answer.assert_called_once_with(mock_console, mock_brain, "test question")


def test_answer_flow() -> None:
    out = io.StringIO()
    c = Console(file=out)
    brain = MagicMock()
    brain.ask.return_value = iter(["Hello", " world"])
    fake_provider = MagicMock()
    fake_provider.name = "groq"
    fake_provider.model = "llama"
    brain.last_provider = fake_provider

    res = main_mod.answer(c, brain, "hi")
    assert res is True
    assert "groq" in out.getvalue()
    assert "llama" in out.getvalue()

    # Provider failure
    def failing_gen(t):
        if False:
            yield ""
        raise AllProvidersFailed("down")

    brain.ask.side_effect = failing_gen
    out.truncate(0)
    out.seek(0)
    res_fail = main_mod.answer(c, brain, "hi")
    assert res_fail is False
    assert "can't reach any brain" in out.getvalue()

    # Keyboard interrupt
    class InterruptingGen:
        def __iter__(self):
            return self
        def __next__(self):
            raise KeyboardInterrupt()
        def close(self):
            pass

    brain.ask.side_effect = None
    brain.ask.return_value = InterruptingGen()
    out.truncate(0)
    out.seek(0)
    res_int = main_mod.answer(c, brain, "hi")
    assert res_int is True
    assert "interrupted" in out.getvalue()


def test_show_brain_and_models() -> None:
    out = io.StringIO()
    c = Console(file=out)

    prov = MagicMock()
    prov.name = "groq"
    prov.model = "llama"
    prov.list_models.return_value = ["llama", "mixtral"]

    main_mod.show_brain(c, [prov], ["ollama (offline)"])
    text = out.getvalue()
    assert "brain order: groq (llama)" in text
    assert "skipped ollama (offline)" in text

    out.truncate(0)
    out.seek(0)
    main_mod.show_models(c, [prov])
    m_text = out.getvalue()
    assert "groq" in m_text
    assert "2 models" in m_text
    assert "llama" in m_text

    # Provider error during list_models
    prov.list_models.side_effect = ProviderError("groq", "network down")
    out.truncate(0)
    out.seek(0)
    main_mod.show_models(c, [prov])
    assert "network down" in out.getvalue()
