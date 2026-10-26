# Implementation Plan: Jarvis Speaking Visualizer (Minimal Aperture)

## 1. Owner's Words (Verbatim)
> "what ofthe visual of Jarvis speaking? /plan"
> "I just wanted to know where we are at. Optionally then we can maybe have option 2 from the previous step"
> "Okay"

## 2. Who, Where, On What
- **Target User**: Marcus operating Jarvis on Windows laptop.
- **Platform**: Local browser window (Edge / Chrome) displaying the minimalist reactive HUD aperture alongside the console.
- **Performance Budget**: Zero external pip dependencies; CPU usage < 1%; local SSE streaming latency < 50ms.
- **Success Metric**: Within 100ms of Jarvis generating voice output, the orb transitions to `SPEAKING` with reactive pulse and sentence captions, returning smoothly to `IDLE` when playback finishes.

## 3. User Flows (Before Screens)
```
[User starts voice.bat] 
         │
         ▼
[Visualizer server initializes on localhost:5050] ──► [Browser opens / displays HUD Aperture]
         │
         ├── User speaks / mic active ───────────────► State: LISTENING (Emerald pulse)
         ├── LLM generating tokens ──────────────────► State: THINKING (Amber orbital spin)
         ├── Kokoro / Windows voice speaks ──────────► State: SPEAKING (Arc-Cyan bloom + subtitle)
         └── Speech completes ───────────────────────► State: IDLE (Breathing slate/cyan rings)
```

## 4. Page & State Inventory
| View / Component | Purpose | Empty / Idle | Active / Speaking | Error |
|---|---|---|---|---|
| **Aperture Orb** | Visual feedback of Jarvis presence | 3 concentric rings, gentle breathing (3.2s) | Dynamic radial scaling + core bloom | Crimson ring flicker |
| **Telemetry Header** | Identifies system status | "SYSTEM IDLE" | "SPEAKING" / "LISTENING" | "BRAIN OFFLINE" |
| **Subtitle Bar** | Real-time transcript of current sentence | Muted ellipsis / instructions | Live sentence text as spoken | Error description |

## 5. References & AI Ingestion
- **Reference**: `jarvis-blueprint.html` (lines 95–115 & 239–262). Concentric SVG/CSS rings with dashed SVG borders and radial gradients.
- **Anti-Slop Audit**:
  - No purple-to-blue neon gradients.
  - Zero unicode emojis.
  - No bloated desktop frameworks (Electron / PySide6 avoided to save 300MB+ disk space).
  - No default system fonts (Inter/Arial/Roboto strictly avoided).

## 6. Design Decisions (Locked in Plan)
- **Display Font**: `Archivo` (bold technical geometry).
- **Telemetry & Body**: `IBM Plex Mono` (crisp typewriter monospace).
- **Color Palette**:
  - Background: `#070b0e` (Deep Void)
  - Surface: `#0d1419` (Obsidian)
  - Accent: `#59c3e3` (Arc Reactor Cyan)
  - Status: `#6f8a95` (Idle), `#7fd69b` (Listening), `#e3b54a` (Thinking), `#59c3e3` (Speaking).
- **Design Tokens**: Written and locked in [tokens.json](file:///c:/Users/user pc/Desktop/2026/J.A.R.V.I.S/tokens.json) and [DESIGN.md](file:///c:/Users/user pc/Desktop/2026/J.A.R.V.I.S/DESIGN.md).

## 7. Wireframes & Visual Draft Overview
- Low-fidelity wireframes created in [.visual/wireframes/index.html](file:///c:/Users/user pc/Desktop/2026/J.A.R.V.I.S/.visual/wireframes/index.html).
- Visual Draft Overview preview assembled in [.visual/DRAFT_OVERVIEW.html](file:///c:/Users/user pc/Desktop/2026/J.A.R.V.I.S/.visual/DRAFT_OVERVIEW.html).

## 8. Technical Plan
- **Architecture**: Zero-dependency Python standard library HTTP + Server-Sent Events (SSE) server in `jarvis/visual.py`.
- **Event Broadcaster**: Thread-safe event bus that broadcasts state changes (`idle`, `listening`, `thinking`, `speaking`) and streaming sentence captions to connected browser clients.
- **Frontend**: Clean single-file static HTML/CSS/JS served from `jarvis/static/visualizer.html`, connecting to `/events` via standard `EventSource`.
- **Integration**:
  - `jarvis/voice.py`: Hook into utterance recording (`listening`), provider query (`thinking`), sentence playback (`speaking`), and return to `idle`.
  - Provide `--visual` flag and automatic launch in `voice.bat`.
- **Out of Scope**: Full Phase 8 multi-panel HUD (tool telemetry, system RAM/CPU monitors, multi-turn history log) which depend on Phases 4 & 5.

## 9. Question Batch (ONE Round)
1. **Window Mode**: Should `voice.bat` automatically open the visualizer tab in your default browser on start?
   *(Recommended: Yes, automatically launch `http://localhost:5050`)*
2. **Port**: Is `5050` acceptable for the local visualizer server?
   *(Recommended: Yes, 5050 with fallback to next free port)*

## 10. Approval Gate (IMMUTABLE HARD RULE)
- Inspect the visual design at [.visual/DRAFT_OVERVIEW.html](file:///c:/Users/user pc/Desktop/2026/J.A.R.V.I.S/.visual/DRAFT_OVERVIEW.html) and [.visual/wireframes/index.html](file:///c:/Users/user pc/Desktop/2026/J.A.R.V.I.S/.visual/wireframes/index.html).
- Execution is completely blocked until Marcus creates `.agents/APPROVED`.
- The assistant is forbidden from creating `.agents/APPROVED`.

## 11. Convert Plan into Done-Contract Checks
Checks mapped to `.agents/done-contract.md`:
- [ ] Visualizer server starts cleanly on localhost with zero external dependencies.
- [ ] SSE `/events` endpoint streams state transitions without connection leaks.
- [ ] Browser aperture renders concentric rings and reacts to state changes (`idle`, `listening`, `thinking`, `speaking`).
- [ ] Captions display synchronized with spoken output.
- [ ] Unit tests in `tests/test_visual.py` pass with 0 failures.
