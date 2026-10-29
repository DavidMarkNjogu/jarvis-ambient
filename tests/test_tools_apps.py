from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from jarvis.tools.apps import open_app, open_folder
from jarvis.tools import ToolError


def test_only_allowlisted_apps_open(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_run)

    # Allowed apps and aliases should succeed
    for app in ["chrome", "msedge", "notepad", "calc", "explorer", "code", "calculator", "google chrome", "vscode"]:
        res = open_app(app)
        assert "opened" in res.lower()

    # Non-allowlisted apps must be refused with ToolError
    for forbidden in ["powershell", "cmd", "malware.exe", "bash", "format"]:
        with pytest.raises(ToolError) as exc_info:
            open_app(forbidden)
        assert "not allowed" in str(exc_info.value).lower()


def test_no_shell_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_popen = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)

    open_app("notepad")
    assert mock_popen.called
    _, kwargs = mock_popen.call_args
    assert kwargs.get("shell") is not True

    # Check open_folder also never uses shell=True
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    open_folder(str(desktop))
    _, kwargs = mock_popen.call_args
    assert kwargs.get("shell") is not True


def test_paths_outside_allowed_folders_are_refused(tmp_path: Path) -> None:
    # Traversal using .. must be rejected
    with pytest.raises(ToolError) as exc_info:
        open_folder(r"..\Windows\System32")
    assert "not allowed" in str(exc_info.value).lower()

    # Forbidden root (e.g. C:\Windows or arbitrary tmp outside allowed roots)
    with pytest.raises(ToolError) as exc_info:
        open_folder(r"C:\Windows\System32")
    assert "not allowed" in str(exc_info.value).lower()
