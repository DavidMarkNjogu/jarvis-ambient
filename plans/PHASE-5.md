# Phase 5 plan: Memory (It knows who you are)

Owner's words (verbatim):
> "whatever is industry standard . i also wanna start talking nd handing off tsasks to him" (28 Oct 2026)
> "proceed" (29 Oct 2026)

---

## Goal and done
Done = these checks: **P5-01, P5-02, P5-03, P5-04, P5-05, P5-06, P5-L1, P5-H1**. Nothing else counts.

1. **Persistent personal memory across restarts:** David can tell Jarvis a fact ("my sister is called Amina", "I prefer tea over coffee"), quit Jarvis, restart, and Jarvis remembers without being retold.
2. **Deterministic SQLite storage:** Storage lives in `data/jarvis.db` using Python's standard library `sqlite3`. Zero external databases, zero paid vectors, zero memory bloat.
3. **Secret & PII filter:** Memory refuses to store API keys (`AIza...`, `gsk_...`, `sk-...`), passwords, or 16-digit credit card numbers. Rejection is hard and tested.
4. **Fast keyword recall:** Exact and tokenized keyword search retrieves relevant facts without returning unrelated ones or hallucinating old state.
5. **Prompt integration:** Profile facts are formatted into the system prompt at startup so Jarvis naturally knows David's preferences and context on every turn.
6. **Session summary:** At exit, key session context/summary is persisted so future sessions can recall prior topics and discussions.

---

## Decisions for David

1. **Approve this plan:** Run `.venv\Scripts\python scripts\verify.py --approve 5`.
2. **Database location:** `data/jarvis.db` (existing database initialized in Phase 4).
3. **Keyword matching:** SQLite FTS5 (Full-Text Search) with standard library `LIKE` / token fallback, guaranteeing 0 MB package footprint.
4. **Secret rejection policy:** Explicitly raise `ValueError` / `ToolError` when text contains API keys (`AIza`, `gsk_`, `sk-`), credit cards (`\b(?:\d{4}[ -]?){3}\d{4}\b`), or password declarations (`my password is ...`).

---

## Files

- **New:**
  - `jarvis/memory.py` (`Memory` class, SQLite schema, `remember`, `recall`, `forget`, session summaries, secret validation)
  - `tests/test_memory.py` (P5-01, P5-02, P5-03, P5-05, P5-06)
- **Changed:**
  - `jarvis/tools/__init__.py` (register `remember`, `recall`, `forget` tools for the Brain)
  - `jarvis/config.py` (load profile facts from `Memory` into prompt generation)
  - `jarvis/personality.py` (inject profile facts into system prompt under a designated User Profile section)
  - `jarvis/__main__.py` (save session summary on exit)
  - `jarvis/voice.py` (save session summary on exit)
  - `scripts/live_checks.py` (implement `check_memory` across separate subprocesses for P5-L1)
  - `tests/test_config.py` (P5-04 prompt includes profile facts)
- **Untouched on purpose:**
  - `acceptance/spec.json`, `acceptance/spec.lock`, `acceptance/signoffs.md`, `.agents/approvals/`
  - `.env`

---

## Design

### 1. SQLite Schema (`jarvis/memory.py`)
Table `facts`:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `fact` TEXT NOT NULL
- `category` TEXT DEFAULT 'profile'  # 'profile', 'preference', 'general'
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

Table `session_summaries`:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `summary` TEXT NOT NULL
- `created_at` TEXT NOT NULL

### 2. Secret & Credential Filtering
Before writing any fact to SQLite, `Memory.remember()` executes strict regex scanning:
- Google API keys: `AIza[0-9A-Za-z_\-]{35}`
- Groq / OpenAI keys: `gsk_[0-9A-Za-z]{20,}`, `sk-[0-9A-Za-z]{20,}`
- Passwords: `(?i)\b(my\s+password\s+is|password\s*[:=])\s*\S+`
- Credit card numbers: `\b(?:\d{4}[ -]?){3}\d{4}\b`
If matched, the write is aborted and raises `ValueError("Memory refuses to store credentials, passwords, or credit card numbers.")`.

### 3. Recall & Forgetting
- `recall(keyword: str) -> list[str]`: Queries SQLite for entries containing the keywords (case-insensitive substring and word-boundary matching).
- `forget(keyword: str) -> int`: Deletes facts matching the keyword, returning count of forgotten entries. Reopening the database confirms zero trace remains.

### 4. System Prompt Profile Loading
- At startup, `system_prompt(...)` queries `memory.get_profile_facts()`.
- Formats facts into a concise profile block:
  ```
  User Profile (remembered facts):
  • David's sister is called Amina.
  • David prefers tea over coffee.
  ```

### 5. Session Summaries
- On clean exit (Ctrl+C, quit, exit), `Memory.save_session_summary(...)` persists a summary record.
- Searchable by keywords in subsequent sessions.

---

## Cost
- **Disk:** 0 MB (uses Python's standard library `sqlite3`).
- **RAM/CPU:** < 2 ms per query; zero vector database overhead.

---

## Order of work

1. **Approval gate:** David runs `.venv\Scripts\python scripts\verify.py --approve 5`.
2. **Branch:** Create `phase-5-memory`.
3. **Step 1 (P5-01, P5-02, P5-03, P5-05):** Write `tests/test_memory.py` tests first (TDD), watch them fail, then implement `jarvis/memory.py`.
4. **Step 2 (P5-04):** Write `tests/test_config.py` for prompt profile injection and update `jarvis/config.py` & `jarvis/personality.py`.
5. **Step 3 (P5-06):** Add session summary test and implementation.
6. **Step 4 (P5-L1):** Implement `scripts/live_checks.py memory` and verify with `--live`.
7. **Step 5 (Mutation testing):** Run `scripts/verify.py --mutate jarvis/memory.py` and ensure score >= 70%.
8. **Step 6 (Full verification):** Run `scripts/verify.py --phase 5` and provide report for human sign-off `P5-H1`.
