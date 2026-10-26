# Jarvis documentation map

Written 26 Oct 2026, when Claude handed this project over to Antigravity (or any other coding agent). Everything an agent needs is in the repository, in plain files. Nothing depends on a particular AI product.

## Read in this order

| # | File | Read it to learn | Time |
|---|---|---|---|
| 1 | [AGENTS.md](../AGENTS.md) | The rules you must never break and the commands you will use | 5 min |
| 2 | [01-VISION-AND-SCOPE.md](01-VISION-AND-SCOPE.md) | What the finished Jarvis is, what it is not, and the constraints | 10 min |
| 3 | [02-ARCHITECTURE.md](02-ARCHITECTURE.md) | How the code works today, where each new feature plugs in, the invariants | 15 min |
| 4 | [03-PHASES.md](03-PHASES.md) | Every phase: goal, files, design, traps. Phase 3 is next | 20 min |
| 5 | [04-VERIFICATION.md](04-VERIFICATION.md) | How "done" is proven without trusting anyone's word, including yours | 10 min |
| 6 | [05-WORKFLOW.md](05-WORKFLOW.md) | The loop to follow for every phase, plus the plan, report and reviewer templates | 10 min |
| 7 | [06-MISTAKES-AND-CHECKS.md](06-MISTAKES-AND-CHECKS.md) | Every mistake an agent can make here, and the command that catches each | 10 min |
| 8 | [07-RUNBOOK.md](07-RUNBOOK.md) | Exact commands, recovery steps, Windows quirks, disk rules | reference |
| 9 | [08-DECISIONS.md](08-DECISIONS.md) | Why things are the way they are, and the questions still waiting for David | 10 min |
| 10 | [09-CHECK-REGISTER.md](09-CHECK-REGISTER.md) | Every acceptance check, generated from the locked spec | reference |

For David (not an agent): read [START-HERE.md](../START-HERE.md) instead.

## The three sources of truth

1. **`acceptance/spec.json`** says what "done" means. It is locked. Only David changes it.
2. **`scripts/verify.py`** decides whether each check is met, by running real tests. Its output is the only status that counts.
3. **`acceptance/signoffs.md`** holds David's own judgement on the things software cannot judge (does the voice sound right).

If a document, a commit message or your own memory disagrees with `verify.py`, `verify.py` is right.

## The next task

Phase 3: "Hey Jarvis" wake word and voice control. Start with [03-PHASES.md](03-PHASES.md#phase-3) and the existing draft [PHASE3-PLAN.md](../PHASE3-PLAN.md). That draft has five open questions for David; they must be answered before any code is written (see [05-WORKFLOW.md](05-WORKFLOW.md)).

Before anything else, free some disk space. See [07-RUNBOOK.md](07-RUNBOOK.md#disk). At handoff the C: drive had about 0.1 GB free, and `verify.py` fails below 0.15 GB.

## Other files already in the repository

| File | What it is |
|---|---|
| [README.md](../README.md) | Technical guide to settings, commands and voices |
| [PHASE3-PLAN.md](../PHASE3-PLAN.md) | Draft plan for Phase 3, waiting for David's answers |
| [DESIGN.md](../DESIGN.md) and `tokens.json` | The UI design system: fonts, colours, rules. Law for any UI work |
| [docs/VISUALIZER-WALKTHROUGH.md](VISUALIZER-WALKTHROUGH.md) | How the speaking visualizer works, with screenshots |
| `docs/vision/dumps/` | David's raw ideas, cleaned up. Read them to understand intent |
| `jarvis-blueprint.html` | The original feasibility study and ten-phase plan. Open in a browser |
| `.agents/` | Earlier agent workflow records (plan, done-contract, approval flag). Kept as history; new work follows [05-WORKFLOW.md](05-WORKFLOW.md) |
| `.visual/` | Wireframes and draft overview for the visualizer |
| `history/` | An old copy of the project and the first chat transcript. Git-ignored. Safe to delete |
