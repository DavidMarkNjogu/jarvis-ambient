# Mistakes an agent can make here, and how to check each

Use this as a checklist at the end of every phase (step 6 of [05-WORKFLOW.md](05-WORKFLOW.md)) and as the reviewer's list. "Check" is something you run or read, not something you believe. Items marked **(script)** are already enforced by `scripts/verify.py`. When you find a new mistake, add a row.

## A. Claiming and proving

| # | Mistake | Check |
|---|---|---|
| A1 | Says "done" without running the gate | Paste the real output of `verify.py --phase N` |
| A2 | Quotes a test count from memory | The count in the report equals the "passed" line of the run **(script)** |
| A3 | Edits `acceptance/` or a test to make it pass | `verify.py --audit`; the lock fails if the spec changes **(script)** |
| A4 | Treats a mocked pass as proof that the real thing works (mocks Gemini, says the brain works) | Live checks (`--live`) call the real service |
| A5 | Claims it heard the audio or saw the screen | Agents cannot hear. Audio and look are human checks. For UI, save real screenshots from the running page |
| A6 | Declares a human check passed | Only David's line in `acceptance/signoffs.md` counts **(script)** |
| A7 | Writes "Evidence:" prose instead of command output | Evidence is pasted output, never a sentence |
| A8 | Counts `PENDING`, `NOT-RUN` or `AWAITING-HUMAN` as done | The phase gate fails on them **(script)** |
| A9 | Reads half a file or log and concludes | Read the whole relevant file; search the rest |
| A10 | Re-runs a flaky test until it is green | Run it three times. Flaky is failing: find the nondeterminism (clock, thread, ordering) and inject it |
| A11 | Treats "all checks pass" as "it works for David" | Write the handoff steps; he tries them |
| A12 | Changes behaviour but leaves old tests green by editing their expectations | Diff the tests: every changed expectation needs a stated reason in the report |

## B. Inventing things

| # | Mistake | Check |
|---|---|---|
| B1 | Invents a library's functions or arguments (openWakeWord, kokoro-onnx, faster-whisper, sounddevice) | After installing, read the real thing: `.venv\Scripts\python -c "import x; help(x)"` or open the file in `.venv\Lib\site-packages\x\` |
| B2 | Invents model, voice or device names | Ask the system: `/models` for brains, `list_voices()` for voices, `sounddevice.query_devices()` for microphones, `openwakeword.MODELS` for wake models |
| B3 | Invents or mistypes a package name | Look it up on pypi.org first; prefer well-known, maintained packages; check the size before installing; never install an unverified package |
| B4 | Invents a Windows command, registry path or setting | Run it on this machine in a throwaway way, or say it is untested |
| B5 | Invents free-tier limits | Read the provider's current page; write the date next to the number |
| B6 | Invents abilities in Jarvis's prompt | Test P4-08 compares the prompt to the registered tools |
| B7 | Links or paths in docs that do not exist | Link check **(script)** |

## C. This machine and Windows

| # | Mistake | Check |
|---|---|---|
| C1 | Installs while the disk is full. A failed `pip install` leaves 100 to 400 MB of leftovers in Temp, which keeps the disk full and made a runaway loop on 26 Oct | Disk check **(script)**; look at free space before every install; if an install fails, check Temp for `pip-*` folders before retrying |
| C2 | Long paths (over 260 characters) break installs | Keep the project at `Desktop\2026\J.A.R.V.I.S`; do not nest folders deeply |
| C3 | Uses the system Python | Always `.venv\Scripts\python`; `verify.py` prints the interpreter it uses |
| C4 | Moves or copies `.venv` | A venv cannot move. Rebuild ([07-RUNBOOK.md](07-RUNBOOK.md#rebuild-the-virtual-environment)) |
| C5 | pytest collects the duplicate tests under `history\` | `pytest.ini` sets `testpaths = tests`. Do not remove it |
| C6 | PowerShell 5.1 pitfalls: no `&&`; `Set-Content` and `>` pick surprising encodings; quotes inside here-strings | Write files with the editor tool or Python with `encoding="utf-8"`; chain commands with `;` and `if ($?)` |
| C7 | Prints a symbol the Windows console cannot encode and crashes | Programs call `stream.reconfigure(encoding="utf-8", errors="replace")`; do not print emoji; do not remove that |
| C8 | Creates the Windows voice on the wrong thread | Invariant 3 in [02-ARCHITECTURE.md](02-ARCHITECTURE.md) |
| C9 | pip's cache fills the disk | `pip install --no-cache-dir` |
| C10 | First Whisper start takes about 80 seconds and needs the internet once | Warn David; models cache in `%USERPROFILE%\.cache\huggingface` |
| C11 | Port 5050 is taken | Use `find_free_port`; never hard-code a port |
| C12 | Microphone blocked or busy | Windows Settings, Privacy, Microphone, allow desktop apps; only one reader of the mic at a time |
| C13 | Laptop sleeps or lid closes and Jarvis stops | Tell David; do not try to defeat power settings |
| C14 | Windows Defender or antivirus blocks a download | Ask David. Never disable security software |
| C15 | Wrong time zone in answers | Use local time (`datetime.now()`); the machine is on Africa/Nairobi |

## D. Security and privacy

| # | Mistake | Check |
|---|---|---|
| D1 | Prints or logs an API key | Mask keys (`setup.mask`); secret scan **(script)**. Never `cat .env`. To see which settings exist, print names only: `Select-String '^[A-Z_]+=' .env \| ForEach-Object { $_.Line.Split('=')[0] }` |
| D2 | Commits `.env`, `models/` or `data/` | `.gitignore` check and `.env`-tracked check **(script)**; read `git status` before every commit |
| D3 | Lets the model run free shell commands | `shell=True`, `eval`, `exec`, `os.system` fail the build **(script)**; tools take argument lists |
| D4 | Treats web or file content as instructions | Wrap tool results as untrusted data (P4-05); side effects need a spoken yes regardless of what the model says |
| D5 | Lets the model decide that David said yes | Confirmation is a plain matcher in code (P4-02) |
| D6 | Allowlist bypass: `..`, another drive letter, a shortcut, a name like `cmd` | Path and app tests (P4-04) try each of these |
| D7 | Answers strangers on Telegram | Allowlist test (P7-01) |
| D8 | A server reachable from the network | Servers bind `127.0.0.1` only **(script)** |
| D9 | Leaves the camera or microphone open | Camera test (P6-02); open only on request |
| D10 | Puts personal facts into prompts without telling David they go to the cloud | Say it in the plan; keep secrets out of memory (P5-05) |
| D11 | Creates accounts, bots or tokens, or types credentials, on David's behalf | Never. Give David the manual steps |
| D12 | Pushes, force-pushes, merges, deletes branches or files, or changes payments or auth without being asked | Never without David's explicit yes in this conversation |
| D13 | Uses scraped or pooled "free" API keys, or unverified packages | Never. Use David's own free keys and known packages |

## E. Product behaviour

| # | Mistake | Check |
|---|---|---|
| E1 | Replies in voice mode with markdown, bullet lists, emoji or long paragraphs | Read three real replies; `clean_for_speech` tests; keep the Style paragraph of the prompt |
| E2 | The prompt's Honesty paragraph is out of date after a new ability | Change `personality.py` in the same commit; the registry-versus-prompt test (P4-08) |
| E3 | Addresses David by the wrong name | `.env` has `USER_NAME=David`; David's global notes say he goes by Marcus. Open question in [08-DECISIONS.md](08-DECISIONS.md); ask, do not change `.env` yourself |
| E4 | Latency gets worse without anyone noticing | Report the numbers printed by `live_checks.py e2e` before and after |
| E5 | The voice reads URLs, code or symbols aloud | Tests in `tests/test_speech.py`; add one for every new case |
| E6 | The HUD stays on "speaking" after Ctrl+C or an error | Returns to idle in `voice.py`; test it when you touch that loop |
| E7 | A silent fallback hides an outage | Keep the grey line that shows which brain answered |
| E8 | Wake word fires too often or too rarely | Human checks P3-H1 and P3-H2 with real numbers; tune `WAKE_THRESHOLD` |

## F. Code and process

| # | Mistake | Check |
|---|---|---|
| F1 | One giant change | Small commits, one concern each, on a branch; `git log --oneline` reads like a story |
| F2 | Refactors nobody asked for | Compare the diff to the plan; anything outside the plan goes in the report or is removed |
| F3 | Adds a dependency without measuring | Declared-imports check **(script)**; size before and after in the plan and the report |
| F4 | Parses settings in a second place | All settings in `config.py` with a clear `ValueError` |
| F5 | Breaks an existing function's signature or behaviour | The full suite must stay green; never delete or loosen an old test |
| F6 | Docs not updated | Register freshness and link checks **(script)**; update START-HERE, README, architecture and decisions |
| F7 | Ignores the existing style | Match the module you are in: type hints, frozen dataclasses, `Protocol`s, plain messages, short comments |
| F8 | Edits `history/` or the old `.agents/` records | Leave them; they are the record |
| F9 | Leaves debug prints or experiments behind | `git diff` before committing |
| F10 | Starts the next phase before this one is signed | Do not. Each phase ends with something that works |

## G. UI (David's rules, plus what went wrong before)

| # | Mistake | Check |
|---|---|---|
| G1 | Emoji or dingbat symbols in a UI | Scan of `jarvis/static/` **(script)** |
| G2 | Inter, Arial, Roboto or system-ui as the main font | Font scan **(script)**; use Archivo and IBM Plex Mono |
| G3 | New colours, spacing or fonts invented | Take them from `tokens.json` and `DESIGN.md` |
| G4 | No screenshots at both sizes | Real screenshots at 1440x900 and 390x844 of the running page, saved under `docs/images/` |
| G5 | Horizontal scroll at phone width | Check at 390 px |
| G6 | Nested cards instead of one unified HUD | Compare to `DESIGN.md` |
| G7 | A new UI plan without the review pack | No approval request until the draft and references are shown |
| G8 | A mock-up presented as the real page | The screenshot must come from the page that `voice.bat` serves |
