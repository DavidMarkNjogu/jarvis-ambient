# Architecture

Two halves: how the code works **today** (verified against the files on 26 Oct 2026), and where each **future** feature plugs in. If you change the code, change this file in the same commit.

## Today: one process, a few threads

```
                         voice.bat  ->  python -m jarvis.voice
   microphone                                                      speakers
       |                                                               ^
       v                                                               |
 listen.record_utterance()                                    tts.Mouth (thread)
 (Endpointer decides when                                   speaks queued sentences
  you stopped talking)                                       one at a time
       |                                                               ^
       v  16 kHz mono float32                                          | sentences
 stt.Transcriber  ---- text ---->  brain.Brain.ask()  ---- text pieces ---->  speech.SentenceBuffer
 (local Whisper or Groq)           (providers in order,                         (cuts into sentences,
                                    history, fallback)                           strips markdown)
                                          |
                                          v
                                  providers.Provider.stream()
                                  OpenAI-style SSE over httpx
                                  (Gemini, Groq, Ollama)

 voice.py also pushes state changes to  visual.VisualServer  ->  browser at http://localhost:5050
 (idle, listening, thinking, speaking, error)                      page: jarvis/static/visualizer.*
```

`jarvis.bat` (`python -m jarvis`) is the same brain with typed input and printed output.

## Module map

| Module | Job | Key names |
|---|---|---|
| `jarvis/config.py` | Reads `.env` once. Decides which brains and engines are used. Every bad setting becomes a `ValueError` with a plain message | `Settings`, `ProviderConfig`, `VoiceSettings`, `settings_from_env`, `voice_settings_from_env`, `load_settings`, `KNOWN_PROVIDERS` |
| `jarvis/providers.py` | Talks to one cloud or local model through the OpenAI-compatible chat API, streaming | `Provider.stream`, `Provider.list_models`, `ProviderError(provider, reason)` |
| `jarvis/brain.py` | Conversation history, fallback between providers, partial replies | `Brain.ask`, `Brain.reset`, `AllProvidersFailed`, `CUT_OFF_NOTICE` |
| `jarvis/personality.py` | The system prompt: who Jarvis is, voice or text mode, what it can and cannot do, the time | `system_prompt(user_name, now, mode)` |
| `jarvis/listen.py` | Records from the microphone; decides when you stopped | `Endpointer`, `record_utterance`, `to_wav_bytes`, `SAMPLE_RATE=16000`, `BLOCK_SECONDS=0.03` |
| `jarvis/stt.py` | Speech to text | `GroqTranscriber`, `LocalWhisperTranscriber` (both have `.transcribe(np.ndarray) -> str`) |
| `jarvis/tts.py` | Text to speech | `Voice` protocol, `KokoroVoice`, `WindowsVoice`, `Mouth` |
| `jarvis/speech.py` | Streaming text into speakable sentences | `SentenceBuffer.feed/flush`, `clean_for_speech` |
| `jarvis/voice.py` | The talking loop and its wiring | `main`, `greet`, `respond`, `build_transcriber`, `build_mouth` |
| `jarvis/__main__.py` | The typed loop and `/reset /models /brain /quit` | `main`, `answer` |
| `jarvis/visual.py` | Zero-dependency HTTP and Server-Sent-Events server for the HUD | `VisualBroadcaster`, `VisualServer`, `find_free_port` |
| `jarvis/static/` | The HUD page: `visualizer.html/.css/.js` | Fonts Archivo and IBM Plex Mono |
| `jarvis/setup.py` | `setup.bat`: detects key type from the clipboard, tests it, writes `.env` | `detect_provider`, `KEY_FORMATS`, `apply_env_updates` |
| `jarvis/download_voice.py` | Optional download of the Kokoro voice files (about 115 MB) into `models/` | |
| `scripts/verify.py` | The verification gate | see [04-VERIFICATION.md](04-VERIFICATION.md) |
| `scripts/live_checks.py` | Checks that need the real network, models and speakers | `brain`, `stt`, `tts`, `e2e` today |

## Invariants (things that must stay true; each has a reason)

1. **Fallback only before the first piece of text.** `Brain.ask` moves to the next provider only if nothing has been yielded yet. Otherwise one reply would be stitched from two models. If a reply breaks midway, the partial text is kept and `CUT_OFF_NOTICE` is appended.
2. **An empty reply is a failure.** It triggers fallback like an error does.
3. **The Windows voice is created on the speaking thread.** Windows COM objects are tied to the thread that made them. `Mouth._run` calls `_init_com()` and builds the voice there, and the constructor waits until the voice is ready. Do not move this.
4. **Text is cleaned before it is spoken.** Markdown, URLs and symbols are removed by `clean_for_speech`, otherwise the voice reads "asterisk asterisk".
5. **All settings go through `config.py`.** No module reads `os.environ` for its own settings. Bad values raise `ValueError` with a message that names the setting and the allowed values.
6. **Engines are injected, so tests never touch the network or hardware.** `Provider(config, client=...)`, `Mouth(make_voice)`, transcribers behind the `Transcriber` protocol, `Brain(providers=...)` accepting any object with `.stream`. Keep this pattern for every new engine.
7. **The terminal is UTF-8.** `main()` reconfigures stdout and stderr to UTF-8 with `errors="replace"`, because the Windows console defaults to a codepage that crashes on symbols.
8. **The visualizer degrades quietly.** If it cannot start, voice mode continues without it. A browser closing a tab mid-stream (`WinError 10053`) must never print a traceback.
9. **No secret is ever logged or printed.** `setup.py` masks keys. New logging must mask too. `verify.py` scans tracked files for key shapes.
10. **Only the voice loop touches the microphone.** One reader at a time. (Phase 3 turns this into a shared stream; see [03-PHASES.md](03-PHASES.md#phase-3).)

## Conventions of the existing code (match them)

- `from __future__ import annotations` at the top of every module; type hints on public functions.
- Small modules, one job each; frozen dataclasses for settings; `Protocol` classes for swappable engines.
- Plain-English error text; no stack traces shown to David.
- Tests use fakes and injected clients, one behaviour per test, test names that read as sentences (`test_falls_back_to_next_provider_before_any_text`).
- Comments explain why, not what. Short.
- Standard library first. Third-party packages must be listed in a `requirements*.txt` (`verify.py` enforces this).

## Data and files at run time

| Path | What | Git |
|---|---|---|
| `.env` | David's keys and settings | ignored |
| `models/` | Kokoro voice files, wake-word models, anything downloaded | ignored |
| `data/` | Databases and logs created at run time (`jarvis.db`, `tool-log.jsonl`) | ignored |
| `acceptance/last-report.json` | Output of the last `verify.py` run | ignored |
| `.venv/` | Python and packages | ignored |

## Target architecture (end state)

One process, one `Brain`, several input channels, one set of tools.

```
 inputs                    core                         outputs
 ------                    ----                         -------
 mic + wake (P3) ----+                              +--> Mouth (voice)
 typed (terminal) ---+--> Brain  <--> ToolRegistry  +--> VisualServer (HUD, P8)
 Telegram (P7) ------+      |          (P4)         +--> Telegram replies (P7)
 Scheduler (P9) -----+      |            |
                            |            +--> Memory (P5, SQLite)
                            |            +--> Vision (P6)
                            v
                       Providers (Gemini, Groq, Ollama)
```

Planned modules (names are fixed by the check register; see [09-CHECK-REGISTER.md](09-CHECK-REGISTER.md)):

| Planned file | Phase | Holds |
|---|---|---|
| `jarvis/wake.py` | 3 | `WakeDetector`, `make_chime` |
| `jarvis/listen.py` (extended) | 3 | `MicStream` shared microphone stream |
| `jarvis/tools/` | 4 | `ToolRegistry`, then `apps.py`, `info.py`, `timers.py` |
| `jarvis/memory.py` | 5 | `Memory` on SQLite |
| `jarvis/vision.py` | 6 | `look_at_screen`, `look_through_camera` |
| `jarvis/telegram.py` | 7 | `TelegramBridge` |
| `jarvis/sysstats.py`, `jarvis/autostart.py` | 8 | `system_stats`, `autostart` |
| `jarvis/scheduler.py` | 9 | `Scheduler`, `morning_brief` |

Threads in the finished process: main (loop), mic stream, mouth, visual server, scheduler, Telegram poller. Each owns its resources; they talk through queues and the thread-safe `VisualBroadcaster`, never by sharing mutable state.

## How to extend (recipes)

**Add a brain provider.** It must speak the OpenAI chat API. Add a row to `KNOWN_PROVIDERS` in `config.py` (base URL, key variable, model variable, default model), add its key shape to `KEY_FORMATS` in `setup.py` if it has a recognisable key, add tests in `tests/test_config.py` and `tests/test_setup.py`, document it in `.env.example`.

**Add a voice engine.** Write a class with `label`, `speak(text)` and `stop()` (the `Voice` protocol). Build it inside the `make_voice` factory in `voice.build_mouth`. Add an engine name to `voice_settings_from_env`. Test with a fake.

**Add a tool (Phase 4 onward).** Register a function with a name, a description for the model, a JSON schema for its arguments, and a risk level (`safe` or `confirm`). Write the tests first: wrong arguments refused, confirm-first honoured, call logged. Add the tool to the Honesty paragraph automatically through the registry, never by hand. See [03-PHASES.md](03-PHASES.md#phase-4).

**Add a HUD element.** Publish an event through `VisualBroadcaster`, render it in `static/visualizer.*` following `DESIGN.md`, add a test that the event is broadcast.
