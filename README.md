# Jarvis

A personal assistant built one phase at a time, following the Project Jarvis Blueprint.

**Current stage: Phase 3, "Hey Jarvis" Wake Word & Voice Customization.** Double-click `voice.bat` to launch hands-free voice mode with the browser speaking aperture at `http://127.0.0.1:5050`. Say "Hey Jarvis", hear the chime, speak your query, and hear the answer spoken aloud. Type `/speed <rate>` to adjust voice speed, `/voices` to list voices, and `/voice <name>` to switch. Enter-only push-to-talk mode is available via `voice.bat --push-to-talk`.

## Finish setup (5 minutes, free)

1. Get a free API key (no card needed). Gemini is the main brain and Groq is the backup; one key is enough to start.
   - Gemini: https://aistudio.google.com/apikey
   - Groq: https://console.groq.com/keys
2. Click **Copy** next to the key, then double-click `setup.bat` and press Enter. It reads the key from your clipboard, tests it, and saves it to `.env` together with your name.
3. Double-click `jarvis.bat`. (The first time, if setup hasn't run yet, it runs setup for you.)

Run `setup.bat` again any time to add a backup key or change a key.

Never share `.env` or upload it anywhere. It's already listed in `.gitignore`.

## Using it

Type normally. Commands:

| Command   | What it does                               |
|-----------|--------------------------------------------|
| `/reset`  | Forget the current conversation            |
| `/models` | List the models each brain offers          |
| `/brain`  | Show which brains are in use, in order     |
| `/quit`   | Exit (Ctrl+C also works)                   |

To ask a single question and exit, run `jarvis.bat what is the capital of Japan`.

Under each reply, a grey line shows which brain answered and how long it took.

## Changing things

- **Personality:** edit `jarvis/personality.py`.
- **Which brain and which model:** edit `JARVIS_PROVIDERS` and the `*_MODEL` lines in `.env`. If a model name stops working (providers retire models), type `/models` and pick a new one.
- **Offline brain:** install Ollama from https://ollama.com, run `ollama pull qwen2.5:1.5b`, and Jarvis will use it whenever the cloud brains fail. On an 8 GB laptop without a graphics card, expect it to be slow and noticeably less clever.

## How it's built

| File                    | Job                                                                       |
|-------------------------|---------------------------------------------------------------------------|
| `jarvis/config.py`      | Reads `.env` and decides which brains are available                       |
| `jarvis/providers.py`   | Talks to Gemini, Groq and Ollama, which share the same OpenAI-style API   |
| `jarvis/brain.py`       | Keeps conversation history and falls back between brains                  |
| `jarvis/personality.py` | The system prompt that makes it Jarvis                                    |
| `jarvis/__main__.py`    | The terminal app                                                          |
| `tests/`                | Automated checks, run with `.venv\Scripts\python -m pytest`               |

`Brain.ask()` yields the reply in small pieces as they arrive. Phase 2 will feed those pieces straight into the voice, so Jarvis starts speaking before the whole answer is written.

## Moving this folder

A Python virtual environment can't be moved. If you move or copy this folder, delete `.venv` and rebuild it from inside the folder:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## Phase 2: talking Jarvis (code written, needs the voice packages)

Double-click `voice.bat`. Press Enter and speak; Jarvis stops listening when you pause, then answers out loud, starting before the whole reply has arrived. You can also type instead of speaking.

Install the voice packages once (needs this folder on a short path, see below):

```
.venv\Scripts\python -m pip install -r requirements-voice.txt
```

What it picks automatically:

| Part  | With a Groq key                         | Without                                    |
|-------|-----------------------------------------|--------------------------------------------|
| Ears  | Groq's free Whisper (fast, accurate)    | faster-whisper on this PC (`requirements-offline.txt`) |
| Voice | Kokoro `bm_george` if downloaded, else Windows' built-in **Microsoft George** | same |

Optional natural voice: `.venv\Scripts\python -m pip install -r requirements-offline.txt` then `.venv\Scripts\python -m jarvis.download_voice` (about 115 MB).

Override in `.env` with `JARVIS_STT=groq|local`, `JARVIS_TTS=kokoro|windows`, `WHISPER_MODEL`, `KOKORO_VOICE`, `WINDOWS_VOICE`.

## Reactive Speaking Visualizer (`voice.bat`)

Double-clicking `voice.bat` now automatically boots a zero-dependency local visualizer at:
```
http://127.0.0.1:5050
```
- **Concentric Aperture Rings**: CSS/SVG rotating rings pulse dynamically to indicate Idle (breathing slate), Listening (emerald mic pulse), Thinking (amber orbital spin), and Speaking (cyan amplitude bloom).
- **Live Sentence Captions**: Displays the exact text spoken by Jarvis in real-time.
- **Permanent In-Repo Guide**: See [`docs/VISUALIZER-WALKTHROUGH.md`](docs/VISUALIZER-WALKTHROUGH.md) for full architecture and verification screenshots.
- To run voice mode without opening the browser: `voice.bat --no-visual` or set `JARVIS_VISUAL=0` in `.env`.

**Path length:** Windows refuses files with very long paths unless long-path support is turned on. Keep this folder somewhere short, like `Desktop\2026\Jarvis`, or the voice packages won't install.
