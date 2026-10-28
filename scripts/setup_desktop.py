"""Setup native desktop shortcut and optional Windows autostart for Jarvis.

Usage:
    .venv\\Scripts\\python scripts\\setup_desktop.py --desktop
    .venv\\Scripts\\python scripts\\setup_desktop.py --autostart
    .venv\\Scripts\\python scripts\\setup_desktop.py --remove-autostart
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = ROOT / "jarvis.ico"
PYTHONW_PATH = ROOT / ".venv" / "Scripts" / "pythonw.exe"


def create_shortcut(target_path: Path, name: str = "Jarvis") -> bool:
    """Create a Windows .lnk shortcut pointing directly to pythonw.exe (no VBScript dependency)."""
    lnk_path = target_path / f"{name}.lnk"

    ps_script = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{lnk_path}'); "
        f"$s.TargetPath = '{PYTHONW_PATH}'; "
        f"$s.Arguments = '-m jarvis.voice'; "
        f"$s.WorkingDirectory = '{ROOT}'; "
        f"$s.Description = 'J.A.R.V.I.S. Voice Assistant'; "
        f"$s.IconLocation = '{ICON_PATH}, 0'; "
        f"$s.Save()"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
    return result.returncode == 0 and lnk_path.exists()


def install_desktop() -> int:
    desktop = Path(os.path.expandvars(r"%USERPROFILE%\Desktop"))
    if create_shortcut(desktop, "Jarvis"):
        print(f"Created Desktop shortcut: {desktop / 'Jarvis.lnk'}")
        return 0
    print("Failed to create Desktop shortcut.")
    return 1


def install_autostart() -> int:
    startup = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
    if create_shortcut(startup, "Jarvis"):
        print(f"Enabled Windows Autostart: {startup / 'Jarvis.lnk'}")
        return 0
    print("Failed to enable Windows Autostart.")
    return 1


def remove_autostart() -> int:
    startup = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
    lnk = startup / "Jarvis.lnk"
    if lnk.exists():
        lnk.unlink()
        print("Removed Jarvis from Windows Startup.")
    else:
        print("Jarvis is not in Windows Startup.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Desktop and Autostart setup for Jarvis.")
    parser.add_argument("--desktop", action="store_true", help="Create Desktop shortcut")
    parser.add_argument("--autostart", action="store_true", help="Enable launch on Windows startup")
    parser.add_argument("--remove-autostart", action="store_true", help="Remove launch on Windows startup")
    args = parser.parse_args()

    if args.autostart:
        return install_autostart()
    if args.remove_autostart:
        return remove_autostart()

    # Default to creating the desktop shortcut
    return install_desktop()


if __name__ == "__main__":
    sys.exit(main())
