# Runbook

Exact commands for this machine (Windows 10 Pro, Windows PowerShell 5.1, project at `C:\Users\user pc\Desktop\2026\J.A.R.V.I.S`). Run everything from the project folder. The project's Python is `.venv\Scripts\python`; never use the system `python`.

## Everyday commands

| Task | Command |
|---|---|
| Talking Jarvis | `voice.bat` (or `.venv\Scripts\python -m jarvis.voice`) |
| Typing Jarvis | `jarvis.bat`; one question: `jarvis.bat what time is it` |
| Set or change the key or the name | `setup.bat` (copy the key first; it reads the clipboard) |
| Run the tests | `.venv\Scripts\python -m pytest -q` |
| Full verification | `.venv\Scripts\python scripts\verify.py` |
| With live checks | `.venv\Scripts\python scripts\verify.py --live` |
| Phase gate | `.venv\Scripts\python scripts\verify.py --phase N` |
| Mutation test a file | `.venv\Scripts\python scripts\verify.py --mutate jarvis\listen.py` |
| One live check | `.venv\Scripts\python scripts\live_checks.py e2e` |

`voice.bat` options: `--no-visual` (no browser HUD), `--port 5051`. Environment: `JARVIS_VISUAL=0` turns the HUD off, `JARVIS_NO_BROWSER=1` starts the HUD server without opening a browser tab.

## Desktop app & autostart

Jarvis can run as a standalone desktop app with a custom arc-reactor emblem, headless background listener, and dedicated aperture HUD.

| Task | Command |
|---|---|
| Install/Update Desktop shortcut | `.venv\Scripts\python scripts\setup_desktop.py --desktop` |
| Launch on Windows startup | `.venv\Scripts\python scripts\setup_desktop.py --autostart` |
| Remove Windows startup | `.venv\Scripts\python scripts\setup_desktop.py --remove-autostart` |
| Hardware mic diagnostics | `.venv\Scripts\python scripts\test_mic.py` |

The desktop shortcut launches `.venv\Scripts\pythonw.exe -m jarvis.voice` directly. `pythonw.exe` suppresses the black console window without requiring Windows Script Host (`.vbs`), ensuring compatibility with security policies and antivirus tools.

## Settings (`.env`)

Never print the file; it holds the key. List the names only:

```
Select-String '^[A-Z_]+=' .env | ForEach-Object { $_.Line.Split('=')[0] }
```

| Setting | Default | Meaning |
|---|---|---|
| `GEMINI_API_KEY`, `GROQ_API_KEY` | none | Free keys. Gemini keys start `AIza` or `AQ.`; Groq keys start `gsk_` |
| `USER_NAME` | empty | What Jarvis calls David |
| `JARVIS_PROVIDERS` | `gemini,groq,ollama` | Brains to try, in order |
| `GEMINI_MODEL`, `GROQ_MODEL`, `OLLAMA_MODEL`, `OLLAMA_URL` | see `.env.example` | Model per brain |
| `JARVIS_HISTORY_TURNS` | 12 | Exchanges kept in mind |
| `JARVIS_STT` | auto | `auto`, `groq` or `local`. Auto uses Groq if a Groq key exists |
| `WHISPER_MODEL` | `base.en` | English-only. Use `base` or `small` for other languages (larger download) |
| `JARVIS_LANGUAGE` | empty | Force a language code for Whisper |
| `JARVIS_TTS` | auto | `auto`, `kokoro` or `windows`. Auto uses Kokoro only if its files are downloaded |
| `KOKORO_VOICE`, `WINDOWS_VOICE` | `bm_george`, `George` | Voice names |

## Disk

The C: drive is the main enemy of this project. At handoff it had about 0.1 GB free. `verify.py` warns under 1 GB and fails under 0.15 GB.

Check free space:

```
Get-PSDrive C | ForEach-Object { "{0:N2} GB free" -f ($_.Free/1GB) }
```

What was using space on 26 Oct 2026 (measured; sizes change):

| Folder | Size | Safe to clear? |
|---|---|---|
| `C:\Users\user pc\Downloads` | about 11 GB | David's own files. His decision only |
| `C:\Users\user pc\AppData\Local\Google\Chrome` | about 7 GB | Browser data. His decision |
| `C:\Users\user pc\AppData\Local\Temp` | about 2.7 GB | Temporary files; normally safe, close programs first |
| `C:\Users\user pc\AppData\Local\ms-playwright` | about 1.9 GB | Browser downloads for automation tools; they re-download on use |
| `C:\Users\user pc\AppData\Local\npm-cache` | about 1.4 GB | Cache; it refills whenever `npx` runs |
| `C:\Users\user pc\AppData\Roaming\Claude` | about 1.1 GB | Claude desktop app data. Leave |
| `.venv` | about 0.3 GB | Needed |
| `C:\Users\user pc\.cache\huggingface` | about 0.14 GB | The Whisper model. Re-download is about 80 seconds |
| `history\` | tiny | Old copy; safe to delete |

**Root cause found on 26 Oct 2026 (a feedback loop).** Between 12:52 and 19:35 something ran `pip install` of `claude_agent_sdk` (with `cryptography`, `pydantic_core` and `pywin32`, for the system Python 3.12, not this project's `.venv`) more than 1,400 times. Each failed or interrupted attempt left 100 to 400 MB behind in `AppData\Local\Temp` as folders named `pip-unpack-*` and `pip-build-tracker-*`: 2.6 GB in total and still growing. The disk is full, so pip fails, so the leftovers keep the disk full. Free space fell from 0.29 GB to 3 MB during one afternoon. The program that starts these installs was not identified (the packages point to Claude's own tooling, but that is a guess). The `pip-*` folders in Temp are pip's own scratch space and are the first thing to delete, with David's yes. If they reappear afterwards, find the process: Task Manager, Details tab, or `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'pip install' }`.

If there is a second drive or a large USB stick, moving the npm cache and `Downloads` there is the lasting fix. Also: Windows Settings, System, Storage, and "Storage Sense". **Never delete anything without David's yes for that action;** a yes earlier does not cover a later deletion.

Before installing any package: check free space, install with `pip install --no-cache-dir`, then see what it cost:

```
(Get-ChildItem .venv -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
```

Write the before and after in the plan and the report.

## Rebuild the virtual environment

Needed if the project folder was moved or copied, or `.venv` is broken. About 1 GB free needed, a few minutes:

```
rmdir /s /q .venv
python -m venv .venv
.venv\Scripts\python -m pip install --no-cache-dir -r requirements.txt -r requirements-voice.txt faster-whisper
```

Then `.venv\Scripts\python scripts\verify.py`.

## Optional: the natural Kokoro voice (about 115 MB plus a package)

```
.venv\Scripts\python -m pip install --no-cache-dir -r requirements-offline.txt
.venv\Scripts\python -m jarvis.download_voice
```

After that `voice.bat` uses Kokoro automatically (`JARVIS_TTS=auto`). Needs about 250 MB free. `models/` is git-ignored.

## Optional: the offline brain (Ollama)

Install from https://ollama.com (a few hundred MB), then `ollama pull qwen2.5:1.5b`. Jarvis uses it when the cloud brains fail. On this laptop expect it to be slow and not very clever.

## Testing voice without a human

Windows can speak into a WAV file, which the real transcriber then hears. `scripts/live_checks.py stt` and `e2e` do exactly that. It proves the pipeline, not the sound quality or the room. `tts` proves the voice engine ran without error, not that it was audible.

## Git

- The repository is local, branch `master`. Check `git remote -v` before assuming there is a remote. **Do not push, merge, force, delete branches or rewrite history unless David says so.**
- One branch per phase: `git switch -c phase-3-wake-word`. David merges.
- Commit messages follow the existing log: `feat(scope): ...`, `fix(scope): ...`, `docs: ...`, `test(scope): ...`.
- Before every commit: `git status` and `git diff --stat`. Nothing from `.env`, `models/`, `data/`, `.venv/`.

## When something is wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `No module named ...` or the window closes at once | `.venv` broken or moved | Rebuild it (above) |
| "Setup problem: ... must be ..." | A bad value in `.env` | The message names the setting; fix the line |
| "No brain configured" | No key | `setup.bat` |
| "API key was rejected" | Wrong or revoked key | New key at https://aistudio.google.com/apikey, then `setup.bat` |
| "rate limit" | Free tier limit | Wait a minute; add a Groq key as a second brain |
| "model ... was not found" | The provider retired a model name | `jarvis.bat`, `/models`, set `GEMINI_MODEL` |
| Nothing recorded, "I didn't hear anything" | Microphone blocked or wrong device | Settings, Privacy, Microphone, allow desktop apps; `sounddevice.query_devices()` |
| Spoken reply cut off or silent | Voice engine error | The loop prints "voice problem: ..."; try `WINDOWS_VOICE`; run `live_checks.py tts` |
| "There is no script engine for file extension '.vbs'" | Windows Script Host disabled | Re-run `.venv\Scripts\python scripts\setup_desktop.py --desktop` to use native `pythonw.exe` |
| HUD does not open | Port busy or browser blocked | It tries the next free port; open the printed address by hand |
| First start takes over a minute | Whisper model loading or downloading | Normal the first time |
| `pip` or `pytest` errors about writing files | Disk full | See Disk |
| A tracked file with a key was found | A secret was committed | Stop. Tell David. The key must be revoked and replaced; deleting the file is not enough |

## Antigravity or another agent: first five minutes

```
cd "C:\Users\user pc\Desktop\2026\J.A.R.V.I.S"
git status
Get-PSDrive C | ForEach-Object { "{0:N2} GB free" -f ($_.Free/1GB) }
.venv\Scripts\python scripts\verify.py
```

Then read [AGENTS.md](../AGENTS.md) and [00-INDEX.md](00-INDEX.md).
