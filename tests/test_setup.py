from jarvis.setup import apply_env_updates, detect_provider, mask

GEMINI_KEY = "AIza" + "x" * 35
GROQ_KEY = "gsk_" + "A1b2" * 13


def test_detects_provider_from_key_shape():
    assert detect_provider(GEMINI_KEY) == "gemini"
    assert detect_provider(GROQ_KEY) == "groq"
    assert detect_provider("AQ." + "Ab3_x-" * 8) == "gemini"
    assert detect_provider("hello world") is None
    assert detect_provider("AIza-too-short") is None
    assert detect_provider("") is None


def test_mask_hides_the_middle():
    assert mask(GEMINI_KEY) == "AIza…xxx"
    assert GEMINI_KEY[5:30] not in mask(GEMINI_KEY)


def test_updates_existing_lines_and_keeps_comments():
    template = "# Free keys:\nGEMINI_API_KEY=\nGROQ_API_KEY=\n# What Jarvis calls you.\nUSER_NAME=\n"
    result = apply_env_updates(template, {"GEMINI_API_KEY": "abc", "USER_NAME": "David"})
    assert result == "# Free keys:\nGEMINI_API_KEY=abc\nGROQ_API_KEY=\n# What Jarvis calls you.\nUSER_NAME=David\n"


def test_replaces_old_value_and_appends_missing_settings():
    result = apply_env_updates("GEMINI_API_KEY=old\n", {"GEMINI_API_KEY": "new", "GROQ_API_KEY": "q"})
    assert result == "GEMINI_API_KEY=new\nGROQ_API_KEY=q\n"


def test_ignores_commented_out_settings():
    result = apply_env_updates("# GEMINI_API_KEY=example\n", {"GEMINI_API_KEY": "real"})
    assert result == "# GEMINI_API_KEY=example\nGEMINI_API_KEY=real\n"
