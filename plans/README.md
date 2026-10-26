# plans/

One file per phase, written by the agent before any code, approved by David.

| File | Written by | Purpose |
|---|---|---|
| `PHASE-N.md` | the agent | The plan, using the template in [docs/05-WORKFLOW.md](../docs/05-WORKFLOW.md). David approves it with `scripts\verify.py --approve N` |
| `PHASE-N-review.md` | a fresh reviewer, saved unedited | The reviewer's findings and verdict |
| `PHASE-N-handoff.md` | the agent | Exact steps for David's human checks |
| `BLOCKED-N.md` | the agent | Written after three failed attempts; asks David for help |

The first plan to write is `PHASE-3.md`, starting from [PHASE3-PLAN.md](../PHASE3-PLAN.md) once David has answered its questions.
