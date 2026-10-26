# Done Contract: Jarvis Speaking Visualizer (Minimal Aperture)

## Acceptance Criteria
- [ ] Visual server module `jarvis/visual.py` runs using Python standard library (zero external pip packages).
- [ ] SSE `/events` endpoint broadcasts JSON messages for `idle`, `listening`, `thinking`, and `speaking` states with current sentence text.
- [ ] Modern, zero-slop UI in `jarvis/static/visualizer.html` using Archivo & IBM Plex Mono fonts and dark HUD styling.
- [ ] Orb animates smoothly: rotating dashed rings and breathing/pulsing core scaled to state.
- [ ] `jarvis/voice.py` updates state appropriately during the live speech conversation cycle.
- [ ] Integration and unit tests in `tests/test_visual.py` pass with 100% success rate (`pytest`).
- [ ] Zero lint/syntax errors and clean git status.
