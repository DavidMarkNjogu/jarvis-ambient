# Decisions, and questions still open

Add an entry whenever you make a real decision (a dependency, an approach, a trade-off), with measured sizes where relevant. Do not rewrite old entries; add a new one that supersedes them.

## Decisions made

| # | Date | Decision | Why | Consequence |
|---|---|---|---|---|
| D-01 | 20 Oct 2026 | Hybrid brain: Gemini free tier first, Groq second, local Ollama third, all through one OpenAI-compatible client | All three speak the same API, so one small `Provider` class serves them. Free. Fast enough on a laptop with no GPU | Free-tier limits and rule changes. Prompts sent to the cloud may be used for training on free tiers. Only Gemini is configured today |
| D-02 | 21 Oct | Default model `gemini-flash-lite-latest` | Fastest and cheapest of the free options; about 1 second per reply | The name can be retired. `/models` lists current ones; set `GEMINI_MODEL` |
| D-03 | 21 Oct | Fall back to the next brain only before the first word of a reply | Never splice one answer from two models | A reply cut midway keeps its partial text and a "[connection lost]" notice |
| D-04 | 21 Oct | Default voice is Windows "Microsoft George", not Kokoro | Kokoro needs about 115 MB plus a package and the disk is full | Less natural voice. Kokoro is a two-command upgrade ([07-RUNBOOK.md](07-RUNBOOK.md)) |
| D-05 | 21 Oct | Local `faster-whisper base.en` for ears when there is no Groq key | Works offline, free | English only; about 1.8 s to transcribe a sentence on this laptop, so the blueprint's 3 second target is missed. A Groq key would help |
| D-06 | 21 Oct | The project lives at a short path, `Desktop\2026\J.A.R.V.I.S`, with the virtual environment rebuilt there | Windows long-path limit blocked `numpy`, `sounddevice` and `comtypes` installs | Keep it short. A venv cannot be moved; rebuild it |
| D-07 | 21 Oct | Accept Gemini keys beginning `AQ.` as well as `AIza` | Google's newer AI Studio keys use the new prefix | `setup.py` and its test were updated |
| D-08 | 21 Oct | `pytest.ini` restricts collection to `tests/` | `history\` held a duplicate copy of the tests that made collection fail | Do not delete `pytest.ini` |
| D-09 | 26 Oct | The HUD uses the standard library only (HTTP plus Server-Sent Events); no FastAPI, no websockets, no Electron | Disk, and nothing in the current needs requires more. The blueprint suggested FastAPI and WebSockets | Phase 8 extends SSE. Frameless window via the browser's app mode |
| D-10 | 26 Oct | The verification system in [04-VERIFICATION.md](04-VERIFICATION.md): locked spec, computed status, test-quality guards, human sign-offs | David is losing access to Claude and must be able to trust a different agent's "done" | Agents cannot tick anything. All "done" claims are re-checkable by running one command |
| D-11 | 26 Oct | Tool confirmation will be decided by code, not by the model (planned for phase 4) | A model can be talked into saying "the user said yes" | A simple yes/no matcher gates every `confirm` tool |
| D-12 | 26 Oct | Memory will start as SQLite with full-text search, not Chroma (planned for phase 5) | Chroma brings many dependencies on a disk with no room | Semantic search later via Gemini embeddings stored in SQLite if keyword search proves weak |
| D-13 | 26 Oct | Documentation is plain Markdown plus Python scripts, in `AGENTS.md` form | Must work with any coding agent and survive the end of David's Claude Pro plan | No Claude-only features anywhere |
| D-14 | 28 Oct | Standalone Desktop App launcher points directly to `pythonw.exe -m jarvis.voice` with custom `jarvis.ico`; zero VBScript dependency | Avoids blocked Windows Script Host (`.vbs`) engines on hardened OS/antivirus setups while running headless without a persistent black console window. Opens HUD aperture in native standalone app mode (`--app=http://127.0.0.1:5050`) | Standard Windows `.lnk` file created via `scripts/setup_desktop.py`. Clean execution on all Windows versions |

## Questions waiting for David

Ask them in one batch when the relevant work starts. Do not answer for him.

| # | Question | Recommendation | Needed for |
|---|---|---|---|
| Q-01 | Approve the Phase 3 plan in `PHASE3-PLAN.md`? | After he reads it | Phase 3 |
| Q-02 | Wake word install: about 10 MB (`openwakeword --no-deps`, try first) or about 200 MB (normal install)? | The small one first | Phase 3 |
| Q-03 | Should `voice.bat` start in wake mode by default, with press-Enter behind `--push-to-talk`? | Yes | Phase 3 |
| Q-04 | Default voice speed: 1.0 or about 1.15? | 1.1 to 1.15 (the draft says 1.1) | Phase 3 |
| Q-05 | Set up the natural Kokoro voice now? (about 250 MB including the package, needs free disk) | Yes, once disk is freed | Phase 3 |
| Q-06 | What should Jarvis call him? `.env` has `USER_NAME=David`, but David's own notes say he goes by Marcus (and uses "David Mark Njogu" in official documents) | Ask him; then `setup.bat` | Now |
| Q-07 | Free disk space. First: may the `pip-*` folders in Temp (2.6 GB of leftovers from a runaway install loop, see [07-RUNBOOK.md](07-RUNBOOK.md#disk)) be deleted? Then: which other folders can go, and is there a second drive or a USB stick? | Yes to the `pip-*` folders; move `Downloads` and the npm cache off C: | Now. Blocks everything. At 3 MB free even saving a file can fail |
| Q-08 | Add a free Groq key as the second brain? | Yes, two minutes at https://console.groq.com/keys | Resilience |
| Q-09 | Install Ollama for a fully offline brain (a few hundred MB plus the model)? | After disk is freed | Phase 0 gap |
| Q-10 | Swahili and Sheng: does he want Jarvis to understand them? That needs a larger multilingual Whisper model and a voice that speaks Swahili | Decide after phase 4 | Later |
| Q-11 | Privacy: facts stored in memory and placed in the prompt go to the cloud brain. Is that acceptable, or should private things stay local only? | Keep sensitive facts out; state it plainly | Phase 5 plan |
| Q-12 | Which second agent or model should act as the fresh reviewer ([05-WORKFLOW.md](05-WORKFLOW.md))? | A different product from the builder | Every phase |
| Q-13 | Is there a remote backup of this repository (GitHub), and may agents push to it? | Ask; the default is no pushing | Now |

## When David is no longer on Claude Pro

Written because he is preparing for that day.

| Part | What happens |
|---|---|
| Jarvis itself | Nothing changes. It uses Gemini, Groq and Ollama, never Claude. Free tiers can change their limits; the fallback chain and the offline brain exist for that |
| These documents and scripts | Plain Markdown and standard-library Python. No Claude feature is used. Any agent that can read files and run commands can continue, including free-tier tools such as Antigravity or the Gemini command-line tool |
| `AGENTS.md` | The open convention for agent instructions. `GEMINI.md` points to it. If another tool looks for a different filename, tell it to read `AGENTS.md` |
| `scripts/verify.py` | Runs with the project's own Python. No network except the optional live checks |
| Claude's saved memory and global notes | Do not travel with the repository. The parts that matter (David's rules for UI, honesty, free-only, idea dumps, naming) are written into [AGENTS.md](../AGENTS.md) and [01-VISION-AND-SCOPE.md](01-VISION-AND-SCOPE.md) |
| The weak point | A weaker agent makes more mistakes. The verification system exists so that it cannot fake "done", but it cannot make a weak agent write good code. Keep phases small, keep the reviewer a different model, and keep David's own sign-offs |
