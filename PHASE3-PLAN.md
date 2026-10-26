# Phase 3 plan: "Hey Jarvis" Wake Word & Voice Customization

Status: **plan updated with voice customization (speed, voice switching, flair), waiting for David's approval. Nothing below has been built.**

## Goal

1. **Hands-free wake word:** Run `voice.bat` and leave it running. Say "Hey Jarvis", hear a short chime, ask your question, and hear the answer. Then it goes back to listening for the wake word, with no Enter key needed. The current press-Enter mode stays available as a fallback.
2. **Voice speed control:** Adjust how fast Jarvis speaks (e.g., 1.0x to 1.5x) via `JARVIS_VOICE_SPEED` in `.env` or in-session commands, so answers feel snappier.
3. **Voice switching & selection:** List installed Windows and Kokoro voices (`/voices`), switch voices (`/voice <name>`), and have Jarvis accurately explain its voice settings when asked.
4. **Natural voice & flair:** Easy activation of Kokoro neural voice (natural British & American inflections with realistic cadence, moving away from robotic Windows monotone).

**Done when:**
- It wakes from normal speaking distance (about 2 m) at least 8 times out of 10 in a quiet room.
- It wakes by itself fewer than about once an hour with the TV or music on.
- It never wakes from its own voice while it is speaking.
- Spoken voice speed can be adjusted smoothly (both Windows SAPI rate and Kokoro speed).
- Jarvis can list available voices and accurately answer "how do I change your voice?" without claiming the feature does not exist.

## How it will work

```
mic (16 kHz) ──► wake detector (openWakeWord "hey_jarvis") ──► chime
                                                              │
         ◄── back to wake detector ◄── speak reply ◄── brain ◄┘ record until pause ◄─┘
```

1. **One microphone stream.** Today `record_utterance()` opens the mic each time it's called. Phase 3 opens the mic once and feeds 80 ms frames (1,280 samples) to whichever part is listening: the wake detector, or the recorder after a wake. This avoids the gap, and the risk of missing the first word, that reopening the mic would cause.
2. **Wake detector** (`jarvis/wake.py`, new): a `WakeDetector` class wrapping openWakeWord's pre-trained `hey_jarvis` model through ONNX. It scores each frame and fires when the score passes a threshold (default 0.5, set in `.env`). After firing it ignores the next 2 seconds, so one "Hey Jarvis" can't trigger twice.
3. **Chime:** a short tone made in code with numpy, so there's no sound file to ship. It plays as soon as the wake word is heard, so you know it's listening.
4. **Recording after the wake:** reuse the existing `Endpointer` from Phase 2, fed from the shared stream. It stops when you pause and gives up after 6 seconds of silence.
5. **No self-triggering:** the wake detector is paused while Jarvis is speaking, and its buffer is cleared when speech ends. This is the simple, reliable choice for a laptop, where the speakers feed straight back into the mic.
6. **Interrupting Jarvis mid-sentence ("barge-in"):** not in this phase. Ctrl+C still cuts it off. Hearing your voice over its own needs echo cancellation, which is unreliable on built-in laptop audio, so it gets its own phase (3b) once 3a is solid.

## Files that change

| File | Change |
|---|---|
| `jarvis/wake.py` | New: `WakeDetector` (model loading, scoring, threshold, cooldown) and `make_chime()` |
| `jarvis/listen.py` | Add a shared `MicStream` that yields frames; `record_utterance()` can take frames from it instead of opening its own stream |
| `jarvis/voice.py` | New wake loop (`voice.bat`); add `/speed`, `/voices`, and `/voice` interactive commands |
| `jarvis/tts.py` | Expose speech rate/speed in `WindowsVoice` (SAPI `Rate`) and `KokoroVoice` (`speed`); add `list_voices()` |
| `jarvis/config.py` | `JARVIS_WAKE` (`on`/`off`), `WAKE_THRESHOLD` (default 0.5), `JARVIS_VOICE_SPEED` (default 1.1) |
| `jarvis/personality.py` | Give Jarvis context on its voice capabilities so it can explain how to change voices/speed accurately |
| `.env.example`, `README.md` | Document wake word and voice speed/switching settings |
| `requirements-voice.txt` | Add `openwakeword` |
| `tests/test_wake.py` | Automated wake tests |
| `tests/test_tts.py` | Tests for rate/speed adjustments and voice switching |

`brain.py`, `providers.py`, `setup.py` and `.env` are not touched.

## Tests

All of these use fake score streams, mock engines, or recorded numbers with no mic needed:

- **Wake Detector**:
  - Fires once when scores cross threshold; cooldown ignores subsequent spikes for 2s.
  - Never fires below threshold.
  - Paused while Jarvis speaks; clears buffer immediately after speech finishes.
  - Invalid `WAKE_THRESHOLD` produces a clean, descriptive error.
  - `make_chime()` generates 16 kHz audio without external asset files.
- **Voice Customization & Speed**:
  - `WindowsVoice` rate maps properly to SAPI Rate bounds (-10 to +10).
  - `KokoroVoice` propagates speed factor (e.g. 1.25x) to ONNX synthesis.
  - Voice switching accurately selects between installed Windows voices and Kokoro neural voice profiles.
  - Jarvis prompt accurately reflects voice settings when user asks "how do I change your voice".
- **Shared Stream Recorder**:
  - `Endpointer` accurately segments silence/speech when fed continuous frames from `MicStream`.

**Live check, run once on your PC:** Windows speaks "Hey Jarvis, what time is it?" into a WAV file (the same trick used to test Phase 2). The file goes through the real detector and recorder, and must wake and transcribe correctly. Then you try it with your own voice, which is the only part I can't check for you.

## Disk and install (needs your decision)

C: has **0.85 GB free**.

- openWakeWord itself is tiny. Its model files (wake word, mel-spectrogram and embedding models) are about 5 MB.
- `onnxruntime`, which it runs on, is **already installed** (faster-whisper brought it in).
- A normal install also adds **scipy and scikit-learn, roughly 150–200 MB**. Those are mainly used for training custom wake words, not for detecting the built-in one.

Option A (recommended): install `openwakeword --no-deps` and test that detecting "hey_jarvis" works without scipy and scikit-learn. If it does, Phase 3 costs about 10 MB. If an import fails, stop and ask before installing the extras.
Option B: a normal install, about 200 MB, leaving roughly 0.65 GB free.

## Risks

- **Accent and mic quality:** the stock model is trained mostly on synthetic US and UK voices. If it misses your "Hey Jarvis" too often, lower `WAKE_THRESHOLD` to 0.3–0.4. A custom model trained on your voice is a later option, and it's heavy to train on this PC.
- **CPU:** the detector uses about 5–10% of one core continuously on an i5-6300U. That's acceptable, but it keeps the laptop busier on battery.
- **openWakeWord on Python 3.12 / Windows:** version 0.6.0 is the current release and ships a pure-Python wheel. Its last release is older, so if it breaks against the installed `onnxruntime` 1.31, the fallback is calling the three ONNX models directly (about 80 extra lines).
- **The Windows mic permission** has to allow desktop apps. Phase 2 already confirmed the mic is detected.

## Not in this phase

Barge-in (3b), custom wake words, starting automatically with Windows, and the HUD (Phase 8).

## Critic review of this plan (self-review)

Checked against correctness, failure paths and setup:

1. **Fixed in the plan:** the first draft reopened the mic after each wake, which would cut off the first word ("Hey Jarvis, *what*…"). Changed to one shared stream (point 1 above).
2. **Fixed in the plan:** the first draft had no way to stop Jarvis waking on its own voice. Added pausing during speech (point 5).
3. **Failure path:** if the wake model fails to load (missing download, broken install), `voice.bat` must fall back to Enter mode with a one-line explanation, not crash. Added to the `voice.py` change.
4. **Failure path:** openWakeWord downloads its model files on first use, which needs internet once. The plan downloads them during install (`openwakeword.utils.download_models(["hey_jarvis"])`) so the first run doesn't stall without explanation.
5. **Open question, not resolved:** the 8-out-of-10 target can only be measured with David's real voice. Synthetic-speech tests prove the wiring, not the accuracy.

## Decisions for David

1. Approve this updated plan, or change it.
2. Disk for Wake Word: Option A (try a ~10 MB install first, recommended) or Option B (normal ~200 MB install).
3. Should wake mode become the default for `voice.bat`, with Enter mode behind `--push-to-talk`, or the other way round?
4. Preferred default voice speed: Standard 1.0x or slightly accelerated 1.15x–1.2x?
5. Voice flair: Shall we add a quick one-step setup for the natural Kokoro offline voice (British George / Lewis) to replace the robotic Windows SAPI default?
