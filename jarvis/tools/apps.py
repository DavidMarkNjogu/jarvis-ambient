"""Launching allowlisted applications and opening allowlisted folders without shell."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import ToolError

ALLOWED_APPS: dict[str, list[str]] = {
    "chrome": ["chrome"],
    "msedge": ["msedge"],
    "notepad": ["notepad.exe"],
    "calc": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "code": ["code"],
}


def _get_allowed_folders() -> list[Path]:
    userprofile = Path(os.path.expandvars(r"%USERPROFILE%")).resolve()
    project_root = Path(__file__).resolve().parent.parent.parent
    return [
        (userprofile / "Desktop").resolve(),
        (userprofile / "Downloads").resolve(),
        (userprofile / "Documents").resolve(),
        project_root,
    ]


def open_app(app_name: str, target: str | None = None) -> str:
    """Launch an application from the strict allowlist without using a shell."""
    name_clean = app_name.strip().lower()
    if name_clean.endswith(".exe"):
        name_clean = name_clean[:-4]

    if name_clean not in ALLOWED_APPS:
        allowed_list = ", ".join(sorted(ALLOWED_APPS.keys()))
        raise ToolError(f"App '{app_name}' is not allowed. Allowed apps are: {allowed_list}")

    cmd = list(ALLOWED_APPS[name_clean])
    if target:
        cmd.append(target)

    try:
        subprocess.Popen(cmd, shell=False)
        return f"Opened {app_name}"
    except Exception as exc:
        raise ToolError(f"Failed to launch app '{app_name}': {exc}") from exc


def open_folder(folder_path: str) -> str:
    """Open a folder in Windows Explorer, refusing any paths outside allowed roots."""
    if ".." in folder_path:
        raise ToolError(f"Path traversal '..' in '{folder_path}' is not allowed.")

    try:
        resolved = Path(folder_path).resolve()
    except Exception as exc:
        raise ToolError(f"Invalid path '{folder_path}': {exc}") from exc

    allowed_roots = _get_allowed_folders()
    is_allowed = any(resolved == root or root in resolved.parents for root in allowed_roots)

    if not is_allowed:
        raise ToolError(f"Folder '{folder_path}' is outside allowed locations and is not allowed.")

    try:
        subprocess.Popen(["explorer.exe", str(resolved)], shell=False)
        return f"Opened folder: {resolved}"
    except Exception as exc:
        raise ToolError(f"Failed to open folder '{folder_path}': {exc}") from exc
