# Phase 3 Human Handoff: Verification Steps for David

All automated and live machine checks for Phase 3 are passing (`11/15`).
Per AGENTS.md Rule 5, only you can judge the physical environment, microphone pickup, and voice audio quality.

Below are the exact steps to verify the 4 human checks (`P3-H1` through `P3-H4`).

---

## 1. P3-H1: Wake Detection Rate (8 out of 10)
- **Claim:** From about 2 metres in a quiet room, saying "Hey Jarvis" wakes it at least 8 times out of 10.
- **Steps:**
  1. Double-click `voice.bat` in `C:\Users\user pc\Desktop\2026\J.A.R.V.I.S`.
  2. Stand or sit about 2 metres from the laptop in a quiet room.
  3. Say "Hey Jarvis" 10 times, waiting about 5 seconds between attempts (listen for the chime).
  4. Note how many times the chime sounded and Jarvis entered the listening state.
  *(Tip: If it misses your natural cadence or accent, you can lower `WAKE_THRESHOLD=0.35` in `.env`).*

---

## 2. P3-H2: False Trigger Resistance
- **Claim:** With background TV or music playing for one hour, it wakes by itself fewer than about once.
- **Steps:**
  1. Leave `voice.bat` running in the background.
  2. Turn on normal music or TV in the room for 1 hour.
  3. Count any unprompted wake chimes. (Target: 0 to 1).

---

## 3. P3-H3: Self-Trigger Suppression
- **Claim:** Jarvis never wakes on its own voice while speaking a long answer.
- **Steps:**
  1. Say: "Hey Jarvis, explain the history of the Apollo space program in detail."
  2. While Jarvis is speaking the long multi-sentence answer out loud through the laptop speakers, observe if any chime or interruption occurs.
  3. Verify that the wake detector remains paused until speech finishes.

---

## 4. P3-H4: Voice Speed, Voice Switching, and Prompt Honesty
- **Claim:** Speed and voice can be changed by command and the difference is audible; asking "how do I change your voice?" gets a correct answer.
- **Steps:**
  1. In the terminal window, type `/speed 1.4` and press Enter. Ask a question and verify the speech is noticeably faster.
  2. Type `/speed 1.0` to return to normal speed.
  3. Type `/voices` and press Enter. Verify the list of installed Windows voices (and Kokoro options) is printed.
  4. Type `/voice Hazel` (or another voice from the list). Ask a question and hear the new voice.
  5. Say aloud: "Hey Jarvis, how do I change your voice?"
  6. Verify Jarvis explains the `/voice` and `/speed` commands clearly instead of claiming the feature does not exist.

---

## 5. Signing Off

When satisfied with the real-world checks, record your sign-offs in `acceptance/signoffs.md` by checking off `[x]` on `P3-H1` through `P3-H4`.
