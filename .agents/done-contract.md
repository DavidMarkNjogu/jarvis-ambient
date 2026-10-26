# Done Contract: Jarvis Speaking Visualizer (Minimal Aperture)

## Acceptance Criteria
- [x] Visual server module `jarvis/visual.py` runs using Python standard library (zero external pip packages). Evidence: `ThreadingHTTPServer` + SSE implementation with 0 pip dependencies.
- [x] SSE `/events` endpoint broadcasts JSON messages for `idle`, `listening`, `thinking`, and `speaking` states with current sentence text. Evidence: Verified in `test_visual_server_sse_stream` and live Playwright test.
- [x] Modern, zero-slop UI in `jarvis/static/visualizer.html` using Archivo & IBM Plex Mono fonts and dark HUD styling. Evidence: Verified `document.fonts.check()` returns true for both fonts; 0 emojis; WCAG AA compliant.
- [x] Orb animates smoothly: rotating dashed rings and breathing/pulsing core scaled to state. Evidence: Concentric SVG/CSS ring keyframe animations for idle, listening, thinking, speaking.
- [x] `jarvis/voice.py` updates state appropriately during the live speech conversation cycle. Evidence: Wired into `greet`, `record_utterance`, `transcribe`, and `respond` streaming loops.
- [x] Integration and unit tests in `tests/test_visual.py` pass with 100% success rate (`pytest`). Evidence: 8 passed in 1.37s; total repo test suite 61 passed in 2.23s.
- [x] Zero lint/syntax errors and clean git status. Evidence: All pytest checks green, screenshots verified at 1440px and 390px with zero horizontal overflow.
