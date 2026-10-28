# Desktop App, Background Execution & Wake Word Architecture

Date: 2026-10-28  
Topic: Desktop icon, always-listening background execution, and OS-level wake bypass options.

---

## 1. Cleaned and Arranged Thoughts

### The Desired Experience
1. **Desktop App / Clickable Icon**:
   - Double-clicking an icon on the Windows desktop launches Jarvis seamlessly.
   - It should not leave an intrusive, ugly black terminal window (`cmd.exe`) open on the screen.
   - It should bring up a sleek, frameless desktop aperture HUD window displaying state and real-time telemetry.

2. **Always-Available Spoken Interaction ("Hey Jarvis")**:
   - Marcus wants to talk to Jarvis anytime hands-free by simply calling out "Hey Jarvis".
   - Concern: Does this require Jarvis to run continuously in the background, consuming CPU/battery, or can the operating system itself hear the microphone and invoke Jarvis on demand?

3. **Industry Standard Architectural Options**:
   - Marcus explicitly requested the industry-standard approach used by modern AI voice assistants (Siri, Alexa, Google Assistant, Windows Copilot).

---

## 2. What It Means (Technical Analysis & Options)

### Can the OS wake Jarvis without Jarvis running?
- **No pure OS-level microphone trigger exists in Windows for custom third-party wake words** without a running background process. Windows only has a proprietary hardware keyword spotter for Microsoft Cortana/Copilot baked into specific Realtek/Intel Smart Sound Technology (SST) DSP firmware chips.
- Therefore, to hear "Hey Jarvis", a process **must be running** to read the audio stream.

### The 3 Architecture Options Evaluated

| Option | Architecture | CPU / RAM Cost | User Experience | Recommendation |
|---|---|---|---|---|
| **Option 1 (Current & Industry Standard)**: Lightweight Headless Background Daemon | Python runs headless via `pythonw.exe` in background. `openWakeWord` processes 80ms audio frames on CPU (~1-2% CPU usage, ~45 MB RAM). Opens HUD aperture via Chrome/Edge `--app` mode. | ~1-2% CPU, ~45 MB RAM | Zero black terminal window. Always hears "Hey Jarvis". Instant response. Can be added to Windows Startup. | **Recommended & Built** |
| **Option 2**: Push-to-Talk Global Hotkey (`Win + Space` or `Ctrl + Shift + J`) | A tiny keyboard hook listener waits for a hotkey. Audio mic is completely OFF until the key combination is pressed. | < 0.1% CPU, ~15 MB RAM | 100% microphone privacy when not speaking. Requires physical keyboard press instead of hands-free calling. | **Available as secondary mode** |
| **Option 3**: Windows System Tray (Systray) Minimizer | Jarvis runs with an icon in the Windows notification area (system tray next to the clock). Right-click menu for Mute, Wake, Settings, and Quit. | ~1-2% CPU, ~50 MB RAM | Standard utility pattern on Windows. Visually unobtrusive. | **Planned for Phase 8** |

### Fix Applied for Desktop Shortcut
- Double-clicking the `.vbs` shortcut previously failed on systems where Windows Script Host is blocked (`There is no script engine for file extension ".vbs"`).
- The shortcut was re-engineered in `scripts/setup_desktop.py` to point directly to `.venv\Scripts\pythonw.exe -m jarvis.voice`.
- `pythonw.exe` is native to Python on Windows, suppresses the console window completely, requires no VBScript engine, and is immune to antivirus script blocks.

---

## 3. Original (as sent)

```text
cant you turn it into a desktop app or icon i click. i was to tell you that just calling it should wake it up but the issue is that it will require having it always running in the background or can we bypass that and just having the mic on will make the os hear and execute 

get industry satndard approach

also i would need you to log the whole desktop app thing and the options you gave me
```
