# Verification: how "done" is proven

## The problem

A coding agent can say a phase is done when it is not. It can tick a checklist, write a test that asserts nothing, paste "evidence" it never produced, delete a failing test, or quietly weaken a requirement. Claude did not want David to depend on its word, and neither should he depend on yours.

The earlier `.agents/done-contract.md` shows the weakness: boxes ticked by hand, with prose "Evidence" lines that nothing checks. This system replaces that with checks a script runs.

## The idea in one paragraph

What "done" means is written **before** the build, in `acceptance/spec.json`, and locked with a hash. Whether each check is met is **computed** by `scripts/verify.py` from real test runs, never recorded by hand. Tests are guarded against being hollow, and can be attacked with mutation testing. What software cannot judge (does the voice sound right, does the wake word work across the room) is signed by David himself.

```
   spec.json (locked)         tests/ + code           David's ears and room
        |                          |                          |
        v                          v                          v
   named checks  ------>  verify.py runs everything  <---  signoffs.md
                                   |
                     PASS / PENDING / FAIL per check, per phase
```

## What an agent could do, and what stops it

| Cheat | Why it is tempting | What stops it |
|---|---|---|
| Tick a box or write "done" | Fastest way to finish | There is no status field to write. Status is computed |
| Weaken or delete a requirement | The check is hard to pass | `spec.json` is hash-locked; a changed spec fails `verify.py`; `--audit` lists every change to it |
| Delete or rename a failing test | Makes the suite green | Each check names exact tests, so a missing one shows as PENDING or PARTIAL; a floor on total tests (`min_total_tests`); `--audit` shows the test count per commit |
| A test with no assertion, or `assert True` | Looks like coverage | The hollow-test scan fails any test function with no real assertion |
| Skip or xfail a test | Hides a failure | Skip and xfail decorators fail the scan; skipped tests at run time must be 0 |
| A test that never calls the real code (everything mocked) | Passes easily | `covers`: each test must mention the real class or function it claims to cover; mutation testing finds code that tests do not pin |
| A test that copies the code's current output as the expected value | Always passes, proves nothing | `must_assert` states what the test must prove, in plain English, written before the build; the fresh reviewer checks it; mutation testing exposes some |
| Run only the easy tests, report the count from memory | Saves time | `verify.py` runs the whole suite itself. The report must paste its output. David can re-run |
| Claim a live check passed | Needs network and models | `verify.py --live` runs the scripts and requires an exact output line; David can re-run |
| Create the approval or sign-off itself | Skips waiting for David | `--approve` and `--lock` refuse to run without a real keyboard; approval is bound to the plan's hash; `--audit` shows who changed what (see Limits) |
| Import a package that is not declared | It worked on its machine | The declared-imports check compares every import in `jarvis/` against `requirements*.txt` |
| Commit a key, or track `.env` | Careless `git add -A` | The secret scan and the `.gitignore` check |
| `shell=True`, `eval`, `exec`, `os.system` | Quick way to run a command | AST scan fails the build |
| Docs that drift from reality | Nobody re-reads them | The check register is generated from the spec and compared byte for byte; a document naming a check ID that does not exist fails; broken links fail |

## Commands

Run all of these from the project folder with the project's Python: `.venv\Scripts\python`.

| Command | What it does | When |
|---|---|---|
| `scripts\verify.py` | Offline gate: disk, lock, spec shape, hollow tests, hygiene, full test suite, status per phase | After every meaningful change |
| `scripts\verify.py --live` | The same, plus the live checks (network, models, speakers) | Before reporting a phase finished |
| `scripts\verify.py --phase N` | The phase gate. Implies `--live`. Fails unless every check from phase 0 to N is satisfied, including David's sign-offs | The final gate |
| `scripts\verify.py --mutate jarvis\FILE.py` | Breaks the file on purpose in a temporary copy and checks the tests notice. `--sample N`, `--min-score X` | For every module you wrote or changed |
| `scripts\verify.py --gate N` | Is there a plan for phase N that David approved and that has not changed since? | Before writing any code |
| `scripts\verify.py --audit` | History of spec, lock, approvals, sign-offs, deleted tests and test counts | David's spot check |
| `scripts\verify.py --render-register` | Rewrites `docs/09-CHECK-REGISTER.md` from the spec | Only after David changes the spec |
| `scripts\verify.py --approve N` | **David only.** Reads `plans/PHASE-N.md` and records approval | After he reads the plan |
| `scripts\verify.py --lock` | **David only.** Re-locks the spec after a change he approved | After a spec change |

The last line of a normal run is `VERIFY: PASS` or `VERIFY: FAIL (n problems)` followed by each problem. Exit code 0 means pass.

## Reading the status of a check

| Status | Meaning | What to do |
|---|---|---|
| `PASS` | Every named test exists and passed (or the live command printed its line) | Nothing |
| `PENDING` | None of its tests exist yet | Build it. Write the tests first |
| `PARTIAL` | Some named tests exist, some do not | Write the missing ones |
| `FAIL` | A named test failed, or `covers` found a test that never touches the real code | Fix the code (or the test, if the test is wrong, and say why) |
| `NOT-RUN` | A live check, and `--live` was not used | Run with `--live` |
| `AWAITING-HUMAN` | A human check with no sign-off | Ask David (see below) |
| `SIGNED` | David signed `PASS` in `acceptance/signoffs.md` | Nothing |
| `FAIL-SIGNED` | David signed `FAIL` | Fix what he reported, ask him to try again |

## Messages you may see, and the right response

| Message | The right fix. Never: edit the spec, delete the test, or add a skip |
|---|---|
| `spec.json no longer matches spec.lock` | You changed the requirements. Revert your edit. If a requirement is genuinely wrong, write the case to David and wait |
| `hollow test (no real assertion)` | Add an assertion that checks behaviour, not `assert True` |
| `never touches [...]` | The test does not exercise the real class. Make it import and call the real thing, using fakes only for the outside world (network, clock, microphone) |
| `only N tests passed but the floor is M` | Tests were removed or are not collected. Restore them |
| `tests were skipped` | Install what the skipped test needs, or fix the test. A skipped test proves nothing |
| `imports 'x' but no requirements*.txt declares` | Add the package to the right requirements file after checking its size, and say so in the report |
| `disk almost full` | Stop. Ask David to free space ([07-RUNBOOK.md](07-RUNBOOK.md#disk)) |
| `mutation score ... below` | Tests do not pin the behaviour. Read the survivors it printed and write tests that fail when each one changes |

## Writing tests that cannot lie

1. **Name tests as sentences** about behaviour. Use the exact names in the register for the phase's checks; add more if useful.
2. **Fake only the outside world:** network (an injected `httpx.Client` with a transport), the clock (inject a function), the microphone (feed arrays), the voice engine (a fake `Voice`). Never fake the class under test.
3. **Assert on observable results,** such as the text yielded, the events emitted, the file contents, the exception message. Asserting that a mock was called is the weakest kind; prefer it only when there is no observable result.
4. **Test boundaries and failure paths,** not just the happy path: threshold minus one, empty input, an exception halfway.
5. **No sleeping, no real time, no real network, no real audio** in automated tests. Those belong in live checks.
6. **Red first.** Write the test, run it, and see it fail for the right reason before you write the code. Paste that failure in your report. A test you never saw fail may be testing nothing.
7. **One behaviour per test.** When one fails, the name says what broke.

## Mutation testing

`--mutate` copies the code, changes one thing at a time (a `>` becomes `<=`, `and` becomes `or`, `True` becomes `False`, a `+` becomes a `-`, a `not` is removed), and runs the tests. If every test still passes, the tests never noticed the change. Default sample is 15 changes and the file must score 60 percent or more. Some survivors are harmless (the change does not alter behaviour), so read each one; a survivor that matters needs a new test. Do this on every module you write or change, and put the scores and your reading of the survivors in the report. Mutation testing runs only the offline suite, so it is cheap. It does not cover code the tests cannot reach, such as the live microphone.

### Known gaps

Measured on 26 Oct 2026 with `--sample 12` on `jarvis/listen.py`: 9 of 12 changes caught. The survivors were:

- `listen.py` line 52, the `not` in `if not self.heard_speech:` that resets the sound counter during silence. No test shows that two separate clicks must not add up to speech.
- `listen.py` lines 71 and 75, inside `record_utterance`, the real microphone loop. No automated test runs it. The Phase 3 shared stream replaces this loop and must be tested (P3-06).

`jarvis/speech.py` scored 3 of 3 on the sites it offered.

## Human sign-off protocol

Some checks (the `H` ones) can only be judged by David, such as 8 wake-ups out of 10 from two metres, or "the voice sounds right". For each one:

1. When your own checks pass, write `plans/PHASE-N-handoff.md`: for each human check, the exact steps, how to count, and what counts as a pass. Copy them from the register; make them doable by someone who does not read code.
2. Tell David to try them. Report only what he tells you. Never guess how it went.
3. David adds a line to `acceptance/signoffs.md` (format in that file). Agents never write there.
4. If it fails, he writes `FAIL` with his numbers. Use them. When fixed, he tries again and writes a newer line, which replaces the old one.

## Limits (honest)

- The script cannot hear. It can show that audio was produced without error; only David can say it sounds right. That is why human checks exist.
- Wake-word accuracy depends on his voice, microphone and room. Synthetic speech proves the wiring, not the accuracy.
- The spec only checks what was thought of in advance. A bug nobody imagined passes every check. Real use and David's notes find those.
- The human-only commands refuse to run without a real keyboard (`stdin` and `stdout` must be a terminal). An agent running commands through a terminal emulator could get past that check. It is a speed bump plus an audit trail, not a wall. The real protection is `--audit` and David reading it. An agent that fakes an approval or a sign-off has broken the rules in [AGENTS.md](../AGENTS.md); report it.
- The initial lock was written by Claude at handoff, not by David (the lock file says so). If he wants it to be his, he can read `docs/09-CHECK-REGISTER.md` and run `--lock`.
- Mutation results use a fixed random sample so they are repeatable; a different sample may find other survivors.

## David's five-minute check (no programming needed)

Open a terminal in the project folder (File Explorer, click the address bar, type `cmd`, Enter) and run:

```
.venv\Scripts\python scripts\verify.py --live
```

1. **Read the last line.** `VERIFY: PASS` is good. If the agent said "done" and this says `FAIL`, the agent is wrong. Paste the failure to it.
2. **Read the table above it.** Each phase shows how many checks are satisfied. A phase is done only when the number is complete, including your own sign-offs.
3. Run `.venv\Scripts\python scripts\verify.py --audit`. Every line under "changes to the spec, lock, approvals and sign-offs" should be something you did or agreed to. If you do not recognise one, ask.
4. Open `acceptance\signoffs.md`. Every entry must be yours.
5. Try the human steps yourself. No script replaces your ears.
