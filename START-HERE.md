# Start here

A plain guide to this folder: where Jarvis lives, how to run it, and how to fix it if something breaks. Written so you can follow it without Claude.

Last updated: 21 Oct 2026, end of Phase 2.

## 1. Where it is

```
C:\Users\user pc\Desktop\2026\J.A.R.V.I.S
```

Open File Explorer, go to **Desktop → 2026 → J.A.R.V.I.S**. Everything Jarvis needs is in this one folder.

## 2. How to run it

| Double-click | What happens |
|---|---|
| `voice.bat` | **Talking Jarvis + Visualizer.** A black window opens, and your web browser automatically opens the glowing visual aperture at `http://127.0.0.1:5050`. Press **Enter**, speak, then pause. Jarvis answers out loud while the orb pulses in arc-cyan with live subtitles. You can type instead of speaking. Type `q` and press Enter to quit. The first start takes about 1½ minutes while the speech model loads. |
| `jarvis.bat` | **Typing-only Jarvis.** Faster to start. Type a question, press Enter, and read the answer in the terminal. Type `/quit` to exit. |
| `setup.bat` | Changes or adds your API key, or your name. Copy a key first, then run this. |

Inside `jarvis.bat` you can also type:

| Command | What it does |
|---|---|
| `/reset` | Forget the conversation so far |
| `/brain` | Show which AI brains are in use |
| `/models` | List the models each brain offers |
| `/quit` | Exit |

"Hey Jarvis" doesn't work yet. That's Phase 3 (see `PHASE3-PLAN.md`).

## 3. What's in the folder

| Item | What it is | Touch it? |
|---|---|---|
| `voice.bat`, `jarvis.bat`, `setup.bat` | The buttons you double-click | Use them |
| `START-HERE.md` | This guide | Read it |
| `docs\VISUALIZER-WALKTHROUGH.md` | Complete visualizer guide, screenshots & navigation | Read it |
| `README.md` | The technical guide: settings, models, voices | When changing settings |
| `jarvis-blueprint.html` | The full plan for every phase. Open it in a browser. | Read it |
| `PHASE3-PLAN.md` | The plan for the next phase ("Hey Jarvis"), waiting for your OK | Read it |
| `.env` | **Your secret API key** and your name | Never share or upload it |
| `.env.example` | A blank copy of `.env` showing every setting | Reference |
| `jarvis\` | The program itself (Python code) | Only to change how it works |
| `jarvis\static\` | The visualizer aperture frontend (HTML, CSS, JS) | Safe to inspect |
| `jarvis\personality.py` | How Jarvis talks. Edit this to change its personality. | Safe to edit |
| `tests\` | Automatic checks that the code still works | Leave alone |
| `docs\` | Project documentation and verification screenshots | Reference |
| `.venv\` | Python and all the installed packages (about 300 MB) | Leave alone; rebuild if broken (step 5) |
| `requirements*.txt` | Lists of packages to install | Used when rebuilding |
| `history\` | An old copy of the project and the original chat transcript | Safe to delete if you need space |
| `.pytest_cache`, `pytest.ini`, `.gitignore` | Housekeeping files for the tools | Leave alone |

Some names start with a dot (`.env`, `.venv`). Windows may hide them. To show them: in File Explorer, click **View → Show → Hidden items**.

## 4. How Jarvis works, in one picture

```
your voice ──► microphone ──► Whisper (speech → text, runs on this PC)
                                   │
                                   ▼
                        Gemini (the "brain", online, free)
                                   │
                                   ▼
            Microsoft George voice (text → speech, built into Windows) ──► speakers
```

- **Brain:** Google Gemini, using the key in `.env`. If Gemini is down, Jarvis tries Groq, then Ollama, but only if you've set those up.
- **Ears:** faster-whisper, offline on this PC.
- **Voice:** Microsoft George (British), built into Windows.

## 5. If something breaks

**The window flashes and closes, or says "python not found" / "No module named…"**
The `.venv` folder is broken, usually because the folder was moved or copied. Rebuild it:

1. Open the `J.A.R.V.I.S` folder in File Explorer.
2. Click the address bar, type `cmd` and press Enter. A black window opens in this folder.
3. Paste these lines one at a time, pressing Enter after each:

```
rmdir /s /q .venv
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-voice.txt faster-whisper
```

That needs about 1 GB of free space on C: and takes a few minutes.

**Jarvis says the key is wrong or missing**
Go to https://aistudio.google.com/apikey, sign in, and copy your key (it's in the project "Personal Assistant", named "Jarvis"). Then double-click `setup.bat`.

**"Rate limited" or slow answers**
The free Gemini tier has a per-minute limit. Wait a minute. To add a backup brain, get a free Groq key at https://console.groq.com/keys and run `setup.bat` again.

**Jarvis can't hear you**
Check Windows **Settings → Privacy → Microphone**, and turn on "Allow desktop apps to access your microphone".

**Installs fail with "No space left" or "Write failed"**
Drive C: is full. Free space by clearing your Downloads folder or deleting `history\`.

**Don't move this folder somewhere with a long path.** Windows can't install the voice packages in deeply nested folders. `Desktop\2026\J.A.R.V.I.S` is fine.

## 6. Check that everything still works

In a `cmd` window in this folder (see step 5):

```
.venv\Scripts\python -m pytest -q
```

It should end with "61 passed" (the number grows as phases are added).

## 7. Progress

| Phase | What | Status |
|---|---|---|
| 1 | Text brain (`jarvis.bat`) | Done |
| 2 | Talking and listening (`voice.bat`) | Done |
| 2+ | Reactive speaking visualizer (`http://127.0.0.1:5050`) | Done (see `docs\VISUALIZER-WALKTHROUGH.md`) |
| 3 | "Hey Jarvis" wake word | Planned: `PHASE3-PLAN.md` |
| 4+ | Actions, memory, full HUD… | See `jarvis-blueprint.html` |

When a phase is finished, this file gets updated.
