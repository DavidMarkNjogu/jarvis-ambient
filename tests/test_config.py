from datetime import datetime

import pytest

from jarvis.config import settings_from_env
from jarvis.personality import system_prompt


def test_defaults_skip_cloud_providers_without_keys():
    s = settings_from_env({})
    assert [p.name for p in s.providers] == ["ollama"]
    assert s.providers[0].base_url == "http://localhost:11434/v1"
    assert s.skipped == ["gemini: no GEMINI_API_KEY in .env", "groq: no GROQ_API_KEY in .env"]
    assert s.history_turns == 12


def test_keys_enable_providers_in_configured_order():
    s = settings_from_env({
        "JARVIS_PROVIDERS": "groq, gemini",
        "GEMINI_API_KEY": "g-key",
        "GROQ_API_KEY": "q-key",
        "GROQ_MODEL": "openai/gpt-oss-20b",
        "USER_NAME": "David",
    })
    assert [(p.name, p.model, p.api_key) for p in s.providers] == [
        ("groq", "openai/gpt-oss-20b", "q-key"),
        ("gemini", "gemini-flash-lite-latest", "g-key"),
    ]
    assert s.user_name == "David"


def test_blank_values_fall_back_to_defaults():
    s = settings_from_env({"GEMINI_API_KEY": "k", "GEMINI_MODEL": "  ", "JARVIS_PROVIDERS": "gemini"})
    assert s.providers[0].model == "gemini-flash-lite-latest"


def test_unknown_provider_is_a_clear_error():
    with pytest.raises(ValueError, match="openai"):
        settings_from_env({"JARVIS_PROVIDERS": "gemini,openai"})


def test_bad_history_setting_is_a_clear_error():
    with pytest.raises(ValueError, match="whole number"):
        settings_from_env({"JARVIS_HISTORY_TURNS": "lots"})


def test_system_prompt_includes_name_and_time():
    prompt = system_prompt("David", datetime(2026, 10, 20, 19, 5))
    assert "You work for David" in prompt
    assert "Tuesday 20 October 2026, 19:05" in prompt


def test_voice_prompt_mentions_voice_commands():
    voice_prompt = system_prompt("David", mode="voice", voice_name="Microsoft George")
    assert "/voice" in voice_prompt
    assert "/speed" in voice_prompt
    assert "Microsoft George" in voice_prompt

    text_prompt = system_prompt("David", mode="text")
    assert "/voice" not in text_prompt
    assert "/speed" not in text_prompt



def test_prompt_lists_exactly_the_registered_tools():
    tools = ["get_time", "get_weather", "open_app"]
    prompt = system_prompt("David", tools=tools)
    for t in tools:
        assert t in prompt
    assert "not connected" in prompt.lower()

    empty_prompt = system_prompt("David", tools=[])
    assert "get_time" not in empty_prompt
    assert "not connected" in empty_prompt.lower()


def test_prompt_includes_profile_facts() -> None:
    facts = ["David's sister is called Amina", "David prefers tea over coffee"]
    prompt = system_prompt("David", profile_facts=facts)
    for f in facts:
        assert f in prompt
