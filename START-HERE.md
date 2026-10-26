# Start here

A plain guide to this folder: where Jarvis lives, how to run it, and how to fix it if something breaks. Written so you can follow it without Claude.

Last updated: 26 Oct 2026, when the project was handed over to Antigravity (see section 8).

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
| `AGENTS.md`, `GEMINI.md` | Instructions for the AI that continues the work (Antigravity or any other) | Read once; do not edit |
| `docs\` | All the documentation (map in `docs\00-INDEX.md`), the visualizer guide and screenshots | Reference |
| `acceptance\` | What "done" means for every phase (`spec.json`, locked) and **your sign-offs** (`signoffs.md`) | `signoffs.md` is yours; leave the rest |
| `scripts\` | `verify.py` (checks the AI's work) and `live_checks.py` | Run `verify.py` yourself (section 9) |
| `plans\` | The AI's written plan for each phase, waiting for your approval | Read, then approve |
| `.agents\`, `.visual\` | Older records from the visualizer work | Leave alone |
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
Drive C: is full. **It is full right now** (3 MB free on the evening of 26 Oct 2026) and the checker refuses to pass below 0.15 GB. A runaway background job keeps trying to install a Python package and leaves about 2.6 GB of half-finished downloads in `AppData\Local\Temp` (folders named `pip-unpack-...`); `docs\07-RUNBOOK.md` explains it. Those folders are safe to delete. Your Downloads folder is about 11 GB, and the caches of other tools (npm, Playwright browsers) add about 3 GB. Free space by clearing Downloads or deleting `history\`; `docs\07-RUNBOOK.md` has the full list with sizes.

**Don't move this folder somewhere with a long path.** Windows can't install the voice packages in deeply nested folders. `Desktop\2026\J.A.R.V.I.S` is fine.

## 6. Check that everything still works

In a `cmd` window in this folder (see step 5):

```
.venv\Scripts\python scripts\verify.py
```

The last line should be `VERIFY: PASS`. (The plain tests alone are `.venv\Scripts\python -m pytest -q`; they end with "62 passed", and the number grows as phases are added.)

## 7. Progress

| Phase | What | Status |
|---|---|---|
| 0 | Tools installed | Done (Ollama, the offline brain, is not installed) |
| 1 | Text brain (`jarvis.bat`) | Done |
| 2 | Talking and listening (`voice.bat`) | Built. **Waiting for you:** sign off P2-H1 and P2-H2 (section 9) |
| 8, first part | Reactive speaking visualizer (`http://127.0.0.1:5050`) | Done (see `docs\VISUALIZER-WALKTHROUGH.md`) |
| 3 | "Hey Jarvis" wake word, voice speed and switching | **Next.** Planned in `PHASE3-PLAN.md`; waiting for your answers |
| 4 to 9 | Tools, memory, eyes, phone, full HUD, speaking first | Not started. Details in `docs\03-PHASES.md` |

The truth about progress is whatever `scripts\verify.py` prints. When a phase is finished, this file gets updated.

## 8. Handing over to Antigravity (or any other AI)

Claude wrote a full set of instructions so another AI can carry on without you having to explain anything. To start it:

1. Open the AI in this folder (`C:\Users\user pc\Desktop\2026\J.A.R.V.I.S`).
2. Tell it: **"Read AGENTS.md and follow it."** (`GEMINI.md` says the same, for tools that look for that name.)
3. Free some disk space first. Nothing will install while the drive is full.

What it will do, in order: read the documents, ask you a short batch of questions, write a plan in `plans\`, wait for your approval, build test-first, check its own work with `verify.py`, ask a second AI to review it, then give you exact steps to try.

**You approve a plan** by reading `plans\PHASE-3.md` and then typing, in a `cmd` window in this folder:

```
.venv\Scripts\python scripts\verify.py --approve 3
```

It shows you the plan and asks you to type `APPROVE PHASE 3`. The AI cannot do this for you (the command refuses to run unless a person is at the keyboard).

The first questions it will ask you are in `docs\08-DECISIONS.md`, marked Q-01 to Q-13. Question Q-06 matters: Jarvis currently calls you "David", but you go by Marcus. Q-07 is the disk.

## 9. How you check an AI's work (five minutes, no coding)

An AI can say "done" when it is not. So its word never counts; the checker's does. In a `cmd` window in this folder:

```
.venv\Scripts\python scripts\verify.py --live
```

1. **Read the last line.** `VERIFY: PASS` is good. If the AI said "done" and this says `FAIL`, the AI is wrong. Paste the failure back to it.
2. **Read the table above it.** Each phase shows how many checks are satisfied.
3. **Do your part.** Some checks only you can judge (does the voice sound right, does "Hey Jarvis" work from across the room). The AI gives you steps; you try them; then you add a line to `acceptance\signoffs.md` in the format shown in that file. The AI is not allowed to write there.
4. **Spot-check for tampering:** `.venv\Scripts\python scripts\verify.py --audit` lists every change to the requirements, approvals and sign-offs. Each one should be something you did.

Two sign-offs are waiting now: **P2-H1** (ask five real questions with your own voice through `voice.bat` and get a spoken answer each time) and **P2-H2** (the voice is audible, British, and nothing is cut off mid-sentence). Add your results to `acceptance\signoffs.md` when you have tried them.

Full explanation: `docs\04-VERIFICATION.md`. The map of all documents: `docs\00-INDEX.md`.
