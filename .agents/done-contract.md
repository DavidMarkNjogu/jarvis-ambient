# Done Contract: Phase 5 - Memory (It knows who you are)

StartedAt: 2026-10-29T17:29:20+03:00

## Acceptance Criteria
- [x] P5-01: A remembered fact survives closing and reopening the database (tests/test_memory.py::test_remembered_fact_survives_a_new_connection)
- [x] P5-02: Recall finds relevant fact by keyword and does not return unrelated ones (tests/test_memory.py::test_recall_finds_relevant_fact_by_keyword)
- [x] P5-03: Forgetting removes a fact and it is never recalled again (tests/test_memory.py::test_forget_removes_the_fact_and_it_is_not_recalled)
- [x] P5-04: Profile facts are loaded into system prompt at startup (tests/test_config.py::test_prompt_includes_profile_facts)
- [x] P5-05: Memory refuses to store API keys, passwords and card numbers (tests/test_memory.py::test_refuses_to_store_api_keys_and_passwords)
- [x] P5-06: A session summary is saved and can be retrieved in a later session (tests/test_memory.py::test_session_summary_is_saved_and_retrievable)
- [x] P5-L1: Live check passes across separate Python processes (scripts/live_checks.py memory)
- [x] Tools registered: remember, recall, forget available to Brain
- [x] Mutation gate: scripts/verify.py --mutate jarvis/memory.py passes (>= 60%) [89% achieved]
- [x] Verification: scripts/verify.py passes with 0 failures
