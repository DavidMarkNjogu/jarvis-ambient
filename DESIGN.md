# Jarvis UI Design System (HUD & Visualizer)

## 1. Design Direction
A distraction-free, cinematic, retro-futuristic HUD inspired by Iron Man's holographic workshop and technical telemetry consoles. Clean vector line geometry, concentric rings, and audio-reactive amplitude glow.

## 2. Typography
- **Display**: `Archivo` (weight: 600, 800; font-stretch: 112%) for titles, indicators, telemetry headers.
- **Body / Telemetry**: `IBM Plex Mono` (weight: 400, 500) for state indicators, timestamps, live streaming transcripts, and speech metrics.
- **Rules**: Zero system defaults (no Inter, Arial, Roboto, system-ui). Latin subset, WOFF2, `font-display: swap`. Max 2 font families, max 3 weights.

## 3. Color Tokens
- **Base Background**: `#070b0e` (Deepest Void)
- **HUD Surface**: `#0d1419` (Obsidian Blue)
- **Primary Ink**: `#cfe6ee` (High-contrast Pale Cyan)
- **Muted Ink**: `#6f8a95` (Subdued Slate)
- **Accent Glow**: `#59c3e3` (Arc Cyan)
- **Core Glow**: `#bdf0ff` (Luminescent White-Cyan)
- **Status Indicators**:
  - `IDLE`: `#6f8a95` (Muted Slate)
  - `LISTENING`: `#7fd69b` (Soft Emerald)
  - `THINKING`: `#e3b54a` (Warm Amber)
  - `SPEAKING`: `#59c3e3` (Arc Reactor Cyan)
  - `ERROR`: `#ef7d7d` (Muted Crimson)

## 4. Visual Constraints
- **Zero Emoji**: No unicode emojis in UI, states, toasts, or copy.
- **Zero Cardocalypse**: Single unified HUD aperture. Spacing and subtle hairline dividers (`#1f3640`) rather than nested cards.
- **State Orb**:
  - 3 concentric rings + glowing core.
  - Idle: slow gentle breathing (3.2s cycle).
  - Listening: active emerald inward pulse reacting to mic RMS.
  - Thinking: amber orbital rotation.
  - Speaking: dynamic arc-cyan expansion modulated by audio chunk playback.
