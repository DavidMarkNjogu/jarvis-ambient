# Phase 3 plan: "Hey Jarvis" Wake Word & Voice Customization

Owner's words (verbatim):
> "HANDLE IT AND I HOPE WE CAN GET TO CLAUDE TIER EXECUTION" (27 Oct 2026)
> "how do i change your voice ... rare the steps to change them indicated or saved somewhere ... also i wann aaspeed up your voice ... camnt you add flair to your voice" (26 Oct 2026 live voice session)

---

## Goal and done
Done = these checks: **P3-01, P3-02, P3-03, P3-04, P3-05, P3-06, P3-07, P3-08, P3-09, P3-10, P3-L1, P3-H1, P3-H2, P3-H3, P3-H4**. Nothing else counts.

1. **Hands-free wake word:** Run `voice.bat` and leave it running. Say "Hey Jarvis", hear a short chime, ask a question, and hear the spoken answer. Then it returns to listening for "Hey Jarvis" without touching the keyboard.
2. **Press-Enter fallback:** Press-Enter mode remains available via `--push-to-talk` (or if the wake model fails to load).
3. **Voice speed control:** Adjust speech playback rate smoothly via `JARVIS_VOICE_SPEED` in `.env` or in-session `/speed <rate>` (maps to Windows SAPI Rate -10 to +10, and Kokoro speed multiplier).
4. **Voice switching & selection:** List installed Windows and Kokoro voices via `/voices`, switch via `/voice <name>`, and have Jarvis accurately explain its voice settings when asked aloud.
5. **No self-triggering:** The wake detector pauses while Jarvis speaks and clears its audio buffer on resume so it never wakes on its own voice.

---

## Decisions by David

1. **Approve this plan:** David approves via `.venv\Scripts\python scripts\verify.py --approve 3`.
2. **Disk for openWakeWord:**
   - *Option A (Recommended):* Install `openwakeword --no-deps` (~10 MB, since `onnxruntime` 1.31 is already installed). Verify "hey_jarvis" detection without scipy/scikit-learn.
   - *Option B:* Normal install (~150-200 MB with scipy and scikit-learn).
   - *Decision:* Start with Option A. If any missing import is strictly needed for inference, report exact package size before installing.
3. **Default voice mode in `voice.bat`:**
   - *Decision:* Wake word mode is the default when `JARVIS_WAKE=on`. Enter mode is available via `--push-to-talk` or as an automatic graceful fallback if the wake model fails.
4. **Default voice speed:**
   - *Decision:* Default speed is `1.1` (matching spec P3-05). Valid range 0.5 to 2.0; Windows SAPI Rate maps linearly to [-10, +10].
5. **Kokoro Neural Voice activation:**
   - *Decision:* Support switching to Kokoro dynamically if downloaded; default to Windows Microsoft George when Kokoro files are absent, with clear guidance on how to enable Kokoro.

---

## Files

- **New:**
  - `jarvis/wake.py` (`WakeDetector`, `make_chime`)
  - `tests/test_wake.py` (unit tests for P3-01, P3-02, P3-03, P3-04)
  - `tests/test_voice_loop.py` (unit test for P3-07)
- **Changed:**
  - `jarvis/listen.py` (add `MicStream` yielding 1,280-sample 80ms frames; adapt `Endpointer` to read from stream)
  - `jarvis/tts.py` (support speech speed/rate in `WindowsVoice` and `KokoroVoice`; add `list_voices()` and switching)
  - `jarvis/voice.py` (wake word loop, `/speed`, `/voices`, `/voice <name>` commands, fallback to push-to-talk)
  - `jarvis/config.py` (`WAKE_THRESHOLD`, `JARVIS_WAKE`, `JARVIS_VOICE_SPEED` settings, defaults, and validation; update `system_prompt`)
  - `jarvis/personality.py` (update voice capabilities, honesty section, and command guidance)
  - `.env.example`, `README.md` (document settings and voice commands)
  - `requirements-voice.txt` (add `openwakeword`)
  - `scripts/live_checks.py` (implement `live_wake` for P3-L1)
  - `tests/test_listen.py` (tests for P3-06: `MicStream` and stream-fed `Endpointer`)
  - `tests/test_voice_config.py` (tests for P3-05: defaults and bad value validation)
  - `tests/test_tts.py` (tests for P3-08, P3-09: rate mapping, speed factor, voice listing/switching)
  - `tests/test_config.py` (tests for P3-10: prompt mentions voice commands)
- **Untouched on purpose:**
  - `acceptance/spec.json`, `acceptance/spec.lock`, `acceptance/signoffs.md`, `.agents/approvals/`
  - `jarvis/brain.py`, `jarvis/providers.py`, `jarvis/setup.py`, `.env`

---

## Design

### 1. Shared Audio Stream (`MicStream`)
`listen.py` provides `MicStream`:
- Opens the PyAudio/sounddevice 16 kHz 16-bit mono input stream once.
- Buffers and yields fixed 80 ms chunks (1,280 samples at 16,000 Hz) as NumPy int16 arrays.
- Avoids tearing or missed initial syllables between wake detection and question recording.

### 2. Wake Detector (`WakeDetector` in `jarvis/wake.py`)
- Wraps openWakeWord's `hey_jarvis` ONNX model.
- Processes 1,280-sample frames.
- Fires when prediction score >= `WAKE_THRESHOLD` (default 0.5).
- Enforces a 2.0-second cooldown after firing to prevent duplicate triggers from a single phrase.
- Provides `pause()` and `resume()` methods:
  - When paused (during TTS speech), incoming audio frames are ignored.
  - On `resume()`, internal model buffers are reset so residual echo cannot trigger a false wake.
- If model loading fails, raises an informative exception caught by `voice.py` to trigger graceful fallback.

### 3. Procedural Chime (`make_chime` in `jarvis/wake.py`)
- Pure NumPy synthesis of a two-tone ascending chime (e.g. 587 Hz D5 -> 880 Hz A5, 200 ms).
- Sample rate 16 kHz, float32 or int16, amplitude > 0.05, no external audio files required.

### 4. Voice Speed & Switching (`jarvis/tts.py`)
- `WindowsVoice`: Maps speed ratio (0.5 to 2.0, default 1.1) to SAPI `Rate` (-10 to +10, where 1.0 = 0, clamped).
- `KokoroVoice`: Passes `speed` float directly to synthesis.
- `list_voices()`: Returns list of available voice identifiers and names.
- Active voice switching updates the underlying speech engine immediately.

### 5. Interactive Loop (`jarvis/voice.py`)
- Default mode: `WakeDetector` monitors `MicStream`.
- On wake: plays chime, hands `MicStream` to `Endpointer` to record question, pauses detector, transcribes with Whisper, streams reply through TTS, resumes detector with buffer cleared.
- Commands supported during interactive session: `/speed <val>`, `/voices`, `/voice <name>`.
- Fallback: If `WakeDetector` initialization fails, prints single-line explanation and falls back to press-Enter loop.

---

## Cost

- **Disk:** C: currently has 4.96 GB free. Option A (`openwakeword --no-deps` + 5 MB ONNX model files) costs ~10-15 MB total.
- **CPU:** ~5% to 10% of one core continuously on Intel i5-6300U during listening. Negligible RAM (~30 MB for ONNX session).

---

## Order of work

1. **Gate check:** Wait for David's approval via `.venv\Scripts\python scripts\verify.py --approve 3`, then verify with `verify.py --gate 3`.
2. **Branch:** Create and switch to `phase-3-wake-word`.
3. **Step 1 (P3-04):**
   - Write `tests/test_wake.py::test_make_chime_is_short_non_silent_16khz` (Red).
   - Implement `make_chime()` in `jarvis/wake.py` (Green).
4. **Step 2 (P3-01, P3-02, P3-03):**
   - Write tests for cooldown, threshold filtering, and pause/buffer-clear (Red).
   - Implement `WakeDetector` in `jarvis/wake.py` (Green).
5. **Step 3 (P3-05):**
   - Write tests for wake settings, defaults, and error messages in `tests/test_voice_config.py` (Red).
   - Update `jarvis/config.py` (Green).
6. **Step 4 (P3-06):**
   - Write tests for `MicStream` 1,280-sample frames and `Endpointer` equivalence in `tests/test_listen.py` (Red).
   - Implement `MicStream` and stream-fed `record_utterance` in `jarvis/listen.py` (Green).
7. **Step 5 (P3-08, P3-09):**
   - Write tests for rate mapping, Kokoro speed, and voice switching in `tests/test_tts.py` (Red).
   - Implement rate scaling and voice management in `jarvis/tts.py` (Green).
8. **Step 6 (P3-10):**
   - Write test for voice-mode system prompt containing `/voice` and `/speed` in `tests/test_config.py` (Red).
   - Update `system_prompt` in `jarvis/config.py` and `jarvis/personality.py` (Green).
9. **Step 7 (P3-07):**
   - Write test for fallback to enter mode when wake model fails in `tests/test_voice_loop.py` (Red).
   - Implement wake loop and fallback in `jarvis/voice.py` (Green).
10. **Step 8 (P3-L1):**
    - Implement `live_wake` check in `scripts/live_checks.py`.
    - Run `.venv\Scripts\python scripts\live_checks.py wake`.
11. **Step 9 (Verification & Mutation):**
    - Run `.venv\Scripts\python scripts\verify.py --phase 3`.
    - Run `.venv\Scripts\python scripts\verify.py --mutate jarvis/wake.py`.
    - Run `.venv\Scripts\python scripts\verify.py --mutate jarvis/listen.py`.
12. **Step 10 (Review & Handoff):**
    - Independent review brief saved to `plans/PHASE-3-review.md`.
    - Provide exact steps for David's human checks P3-H1 to P3-H4 in `plans/PHASE-3-handoff.md`.

---

## Risks and traps

- **openWakeWord API compatibility:** Do not guess the API; inspect `openwakeword.Model` signature and input dimensions after installing. It expects int16 audio at 16 kHz in multiples of 1,280 samples.
- **Model downloading:** openWakeWord downloads model files on first invocation. Fetch them at setup time so the first interactive run never hangs silently.
- **Microphone contention:** PyAudio / sounddevice must not be opened concurrently by multiple objects. `MicStream` is the single reader.
- **Self-trigger loop:** Speaker output will bleed into the microphone. Pausing `WakeDetector` during TTS synthesis and clearing audio buffers on resume is mandatory.
- **Accent sensitivity:** If the default model misses David's voice, recommend setting `WAKE_THRESHOLD=0.35` in `.env`.
- **Atomic commits:** Granular commits (`test(wake): ...`, `feat(wake): ...`), zero files left uncommitted.

---

## Not in this phase

- Barge-in / acoustic echo cancellation (Phase 3b).
- Tool execution (Phase 4).
- Full desktop HUD GUI (Phase 8).
