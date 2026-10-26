import jarvis.setup as setup

GEMINI_KEY = "AIza" + "y" * 35
GROQ_KEY = "gsk_" + "Q9" * 20


def run_setup(monkeypatch, tmp_path, *, secrets, answers, clipboard="", bad_keys=()):
    env_file = tmp_path / ".env"
    template = tmp_path / ".env.example"
    template.write_text("GEMINI_API_KEY=\nGROQ_API_KEY=\nUSER_NAME=\n", encoding="utf-8")
    secrets, answers = iter(secrets), iter(answers)
    checked = []

    def fake_check(provider, key):
        checked.append(provider)
        return "the API key was rejected; check it in .env" if key in bad_keys else None

    monkeypatch.setattr(setup, "ENV_FILE", env_file)
    monkeypatch.setattr(setup, "TEMPLATE", template)
    monkeypatch.setattr(setup.getpass, "getpass", lambda prompt="": next(secrets))
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(setup, "read_clipboard", lambda: clipboard)
    monkeypatch.setattr(setup, "check_key", fake_check)
    assert setup.main() == 0
    return env_file, checked


def test_enter_reads_key_from_clipboard_and_saves(monkeypatch, tmp_path):
    env_file, checked = run_setup(
        monkeypatch, tmp_path, secrets=[""], answers=["n", "David"], clipboard=GEMINI_KEY
    )
    assert checked == ["gemini"]
    assert env_file.read_text(encoding="utf-8") == f"GEMINI_API_KEY={GEMINI_KEY}\nGROQ_API_KEY=\nUSER_NAME=David\n"


def test_rejected_key_is_not_saved_and_asks_again(monkeypatch, tmp_path):
    env_file, checked = run_setup(
        monkeypatch, tmp_path, secrets=[GEMINI_KEY, "skip"], answers=[""], bad_keys={GEMINI_KEY}
    )
    assert checked == ["gemini"]
    assert not env_file.exists()


def test_can_add_backup_key(monkeypatch, tmp_path):
    env_file, checked = run_setup(
        monkeypatch, tmp_path, secrets=[GEMINI_KEY, GROQ_KEY], answers=["y", ""]
    )
    assert checked == ["gemini", "groq"]
    text = env_file.read_text(encoding="utf-8")
    assert f"GEMINI_API_KEY={GEMINI_KEY}" in text and f"GROQ_API_KEY={GROQ_KEY}" in text


def test_clipboard_without_a_key_asks_again(monkeypatch, tmp_path):
    env_file, checked = run_setup(
        monkeypatch, tmp_path, secrets=["", "skip"], answers=[""], clipboard="some copied sentence"
    )
    assert checked == []
    assert not env_file.exists()
