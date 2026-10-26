# Human sign-offs

Some things only a person can judge: whether the voice sounds right, whether "Hey Jarvis" works from across a room. David records those here. Agents must never add lines to this file.

Add one line per check, in this exact format, using the check id from `docs/03-PHASES.md`:

```
P2-H1 | PASS | 2026-10-27 | asked 5 questions, all answered aloud
P3-H1 | FAIL | 2026-11-02 | woke 6 times out of 10 at 2 m; try a lower WAKE_THRESHOLD
```

`PASS` or `FAIL`, then the date, then a short note with the real numbers. A `FAIL` line stops the phase gate until a later `PASS` line replaces it (the newest line for an id wins).

Nothing has been signed yet. Phase 2's human checks (P2-H1, P2-H2) are the first ones waiting.

## Entries

