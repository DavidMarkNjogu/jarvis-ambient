# Vision and scope

## What Jarvis is

A personal assistant that runs on David's own Windows laptop, costs nothing to run, and behaves like the one in the films within the limits of physics and a free budget. He says "Hey Jarvis", asks a question in plain speech, and hears a short spoken answer in a British voice. It can also do things for him, remember him, see what he shows it, reach him on his phone, and speak first when it has something useful to say.

The original feasibility study is `jarvis-blueprint.html`. It is the source for the ten phases. Where this repository and the blueprint disagree, [08-DECISIONS.md](08-DECISIONS.md) says why.

## The finished product (what "final implementation" means)

When every phase is done, all of this works on the laptop with no paid service:

| Capability | How it behaves | Phase |
|---|---|---|
| Wake word | "Hey Jarvis" starts listening, a short chime confirms, it goes back to sleep after the answer | 3 |
| Speech in and out | Speaks sentence by sentence while the answer is still being written; speed and voice are adjustable | 2, 3 |
| Conversation | Remembers the current conversation; replies in one to three plain spoken sentences; dry British wit, never fawning | 1 |
| Brain | Gemini free tier first, Groq second, a local Ollama model when offline; switches automatically; never mixes two models in one reply | 1 |
| Actions | Time, weather, web search, open apps and folders, volume, timers, reminders, system stats, play music. Anything that deletes, sends or spends needs a spoken yes first | 4 |
| Memory | Remembers facts David tells it and recalls them after a restart; never stores passwords or keys | 5 |
| Eyes | Describes the screen or the webcam, on request only | 6 |
| Reach | Answers David's own Telegram messages and voice notes from anywhere | 7 |
| Face | A browser HUD with a reactive aperture, live transcript, tool log and system stats; can start with Windows | 8 |
| Initiative | Morning briefing, warnings (low disk, low battery), optional nudges, never during quiet hours and never over David's voice | 9 |

Phases 1 and 2 are built. The speaking visualizer (the first part of phase 8) is built. Run `scripts/verify.py` for the current truth.

## Not in scope, ever

These are limits of physics, law or honesty, not of effort:

- Mid-air holograms, the suit, a conscious AI, "hacking into anything".
- Cloning Paul Bettany's voice or any real person's voice. Use stock voices.
- Letting the model run shell commands it wrote itself. Only named tools with fixed behaviour.
- Anything that needs a paid plan to keep working.

## Not in scope yet (decide later, with David)

Barge-in (interrupting Jarvis mid-sentence), custom wake words trained on David's voice, Swahili and Sheng conversation, Home Assistant smart-home control (needs devices David does not own), running as a Windows service.

## Constraints that shape every decision

| Constraint | Value | Consequence |
|---|---|---|
| Budget | 100% free. Free tools only, and look at every route before saying something is impossible | No paid APIs. Check free-tier limits before relying on one |
| Machine | Windows 10 Pro (build 19045), Intel i5-6300U dual core, no GPU, about 8 GB RAM | Local models must be small. Cloud brain for hard questions |
| Disk | The C: drive is nearly full: about 0.1 GB free at handoff | Every new package needs a size check first. Prefer the standard library. See [07-RUNBOOK.md](07-RUNBOOK.md#disk) |
| Python | 3.12.6, in `.venv` inside the project | Always run `.venv\Scripts\python`, never the system Python |
| Path | `C:\Users\user pc\Desktop\2026\J.A.R.V.I.S` | Keep it short. Windows refuses very long paths during some installs |
| Network | Home or mobile connection, sometimes offline | Everything cloud has an offline fallback or a plain-English error |
| Language | David speaks English, Swahili and Sheng. Time zone Africa/Nairobi | Default Whisper model is English-only (`base.en`). See open decisions |
| Windows 10 | No longer receives regular security updates | An assistant that controls the PC is safer on a supported system; keep tool power small |

## Principles (these decide arguments)

1. **Every phase ends with something that works.** Stop at any phase and David still has a useful assistant.
2. **Honest about itself.** Jarvis must never claim an ability it lacks, nor deny one it has. The "Honesty" paragraph in `jarvis/personality.py` must always match the registered abilities. This is tested.
3. **Named tools, fixed behaviour, confirm first.** Side effects are decided by code, not by the model.
4. **Secrets stay in `.env`.** Never printed, logged, committed or pasted into chat.
5. **Offline fallback early.** Free cloud tiers change without notice.
6. **Small and standard-library first.** Disk is scarce and every dependency is a future breakage.
7. **Plain errors.** A failure says what happened and what to do, in words David can act on.
8. **Verify, do not believe.** See [04-VERIFICATION.md](04-VERIFICATION.md).

## UI rules (apply to every screen, from David)

- No emoji anywhere in a UI. One consistent SVG line-icon set.
- Never Inter, Arial, Roboto or system-ui as the main typeface. Use the loaded pairing in `DESIGN.md`: Archivo for display, IBM Plex Mono for body and telemetry.
- Colours and spacing come from `tokens.json` and `DESIGN.md`. Do not invent new ones.
- Before David approves any new UI plan, show him a review pack: a draft of how it may look plus the inspiration references you picked. His references: threeui.com, tasteskill.dev, 21st.dev, gsap.com, Jitter, LottieFiles, cta.gallery, unsection.com, 60fps.design.
- Check at 1440x900 and 390x844 with real screenshots. No horizontal scrolling on a phone-width screen.
- A single unified HUD, not nested cards.

## The whole-project definition of done

Jarvis is finished when `scripts/verify.py --phase 9` prints `VERIFY: PASS`, which means every automated, live and human check from phase 0 to 9 is satisfied, and David has used it for a normal week without a blocking problem. A week of real use will find things no check does; the last step is his notes, not an agent's opinion.
