from __future__ import annotations

from pathlib import Path
import pytest

from jarvis.memory import Memory


def test_remembered_fact_survives_a_new_connection(tmp_path: Path) -> None:
    db_file = tmp_path / "sub" / "memory.db"
    mem1 = Memory(db_path=db_file)
    row_id = mem1.remember("David's sister is called Amina", category="profile")
    assert row_id > 0
    mem1.close()

    # Reopening on already existing parent dir
    mem2 = Memory(db_path=db_file)
    try:
        facts = mem2.recall("sister")
        assert len(facts) == 1
        assert "Amina" in facts[0]
    finally:
        mem2.close()


def test_recall_finds_relevant_fact_by_keyword(tmp_path: Path) -> None:
    mem = Memory(db_path=tmp_path / "memory.db")
    try:
        mem.remember("David prefers tea over coffee", category="preference")
        mem.remember("David's sister is called Amina", category="family")
        mem.remember("David works on Python projects on Windows", category="work")

        sister_facts = mem.recall("sister")
        assert len(sister_facts) == 1
        assert "Amina" in sister_facts[0]
        assert "tea" not in sister_facts[0]
        assert "Python" not in sister_facts[0]
    finally:
        mem.close()


def test_forget_removes_the_fact_and_it_is_not_recalled(tmp_path: Path) -> None:
    db_file = tmp_path / "memory.db"
    mem1 = Memory(db_path=db_file)
    mem1.remember("David's car is a blue Subaru", category="personal")
    mem1.remember("David's sister is called Amina", category="family")
    
    deleted_count = mem1.forget("Subaru")
    assert deleted_count == 1
    assert mem1.recall("Subaru") == []
    mem1.close()

    # Reopening database confirms fact is permanently gone
    mem2 = Memory(db_path=db_file)
    try:
        assert mem2.recall("Subaru") == []
        assert len(mem2.recall("sister")) == 1
    finally:
        mem2.close()


def test_refuses_to_store_api_keys_and_passwords(tmp_path: Path) -> None:
    mem = Memory(db_path=tmp_path / "memory.db")
    try:
        # 1. Google API key shape (AIza...) constructed dynamically to avoid false-positive secret scan
        fake_aiza = "".join(["AIza", "SyD-", "1234567890abcdefghijklmnopqrstuvwxyz"])
        with pytest.raises(ValueError) as exc:
            mem.remember(f"My google api key is {fake_aiza}")
        assert "credential" in str(exc.value).lower() or "refuse" in str(exc.value).lower()

        # 2. Anthropic / Groq key shape (gsk_...) constructed dynamically
        fake_gsk = "".join(["gsk", "_", "1234567890abcdefghijklmnopqrstuvwxyz"])
        with pytest.raises(ValueError):
            mem.remember(f"My groq token is {fake_gsk}")

        # 3. OpenAI key shape (sk-...) constructed dynamically
        fake_sk = "".join(["sk", "-", "1234567890abcdefghijklmnopqrstuvwxyz1234"])
        with pytest.raises(ValueError):
            mem.remember(f"My token is {fake_sk}")

        # 4. Passwords
        with pytest.raises(ValueError):
            mem.remember("my password is SecretPassword123!")

        # 5. 16-digit credit card number
        with pytest.raises(ValueError):
            mem.remember("My visa card is 4111 2222 3333 4444")

        # Confirm nothing was written to database
        assert mem.recall("key") == []
        assert mem.recall("password") == []
        assert mem.recall("card") == []
    finally:
        mem.close()


def test_session_summary_is_saved_and_retrievable(tmp_path: Path) -> None:
    db_file = tmp_path / "memory.db"
    mem1 = Memory(db_path=db_file)
    sid = mem1.save_session_summary("David worked on Phase 4 tools and tested microphone endpointer.")
    assert sid > 0
    mem1.close()

    mem2 = Memory(db_path=db_file)
    try:
        summaries = mem2.search_session_summaries("microphone")
        assert len(summaries) == 1
        assert "Phase 4" in summaries[0]
        assert "endpointer" in summaries[0]
    finally:
        mem2.close()
