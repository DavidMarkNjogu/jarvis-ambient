from __future__ import annotations

import random
import string
from pathlib import Path
import pytest

from jarvis.tools import ToolError, ToolDef, ToolRegistry, validate_arguments
from jarvis.brain import is_affirmative, is_negative
from jarvis.tools.timers import TimerManager, ReminderStore


def test_fuzz_affirmative_and_negative_matching() -> None:
    # Test random noise + affirmative / negative words
    affirmatives = ["yes", "yeah", "yep", "sure", "proceed", "do it", "confirm", "go ahead"]
    negatives = ["no", "nope", "cancel", "dont", "don't", "stop", "abort", "never mind"]

    for aff in affirmatives:
        assert is_affirmative(aff)
        assert is_affirmative(f"  {aff.upper()}!  ")
        assert is_affirmative(f"well, {aff}, please proceed.")

    for neg in negatives:
        assert is_negative(neg)
        assert is_negative(f"  {neg.upper()}...  ")
        assert is_negative(f"I said {neg} right now!")

    # Random ascii strings should not falsely trigger
    rnd = random.Random(42)
    for _ in range(200):
        length = rnd.randint(3, 15)
        text = "".join(rnd.choice(string.ascii_letters) for _ in range(length))
        if text.lower() not in affirmatives and text.lower() not in negatives:
            assert not is_affirmative(text)
            assert not is_negative(text)


def test_fuzz_validate_arguments() -> None:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer", "minimum": 1, "maximum": 100},
            "ratio": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "flag": {"type": "boolean"},
        },
        "required": ["name", "count"],
    }

    # 1. Valid cases must always pass
    valid_args = {"name": "test", "count": 10, "ratio": 0.5, "flag": True}
    validate_arguments(schema, valid_args)

    # 2. Fuzz with invalid types: must always raise ToolError cleanly without unhandled crash
    rnd = random.Random(123)
    weird_values = [
        None,
        [],
        {},
        {"nested": 123},
        float("nan"),
        float("inf"),
        -999999,
        999999,
        "a" * 1000,
        True,
        False,
        12.34,
        object(),
    ]

    for _ in range(200):
        fuzzed_args = {
            "name": rnd.choice(weird_values),
            "count": rnd.choice(weird_values),
            "ratio": rnd.choice(weird_values),
            "flag": rnd.choice(weird_values),
        }
        try:
            validate_arguments(schema, fuzzed_args)
        except ToolError:
            # Expected clean validation failure
            pass


def test_fuzz_reminder_store_sql_injection_and_weird_strings(tmp_path: Path) -> None:
    db_path = tmp_path / "fuzz.db"
    store = ReminderStore(db_path=db_path)

    # Malicious injection payloads and edge-case strings
    injections = [
        "'; DROP TABLE reminders; --",
        "1' OR '1'='1",
        "Robert'); DROP TABLE Students;--",
        "'''''",
        "\x00\x01\x02",
        "😊🚨🎉💻",
        "A" * 5000,
        "<script>alert(1)</script>",
        "\n\r\t\b",
    ]

    for payload in injections:
        rid = store.add_reminder(text=payload, remind_at_iso="2026-10-29T12:00:00")
        assert isinstance(rid, int)
        assert rid > 0

    reminders = store.list_reminders()
    assert len(reminders) == len(injections)

    # Table must still exist and be intact
    store.add_reminder(text="safe reminder", remind_at_iso="2026-10-29T13:00:00")
    assert len(store.list_reminders()) == len(injections) + 1
    store.close()


def test_fuzz_timer_manager_clock_jumps() -> None:
    clock_time = [100.0]
    mgr = TimerManager(clock=lambda: clock_time[0])

    mgr.set_timer(seconds=10, label="t1")
    mgr.set_timer(seconds=20, label="t2")

    # Time goes backwards (clock drift or NTP sync)
    clock_time[0] = 50.0
    assert mgr.poll() == []

    # Time jumps forward 15s (t1 fires, t2 pending)
    clock_time[0] = 115.0
    fired = mgr.poll()
    assert fired == ["Timer up: t1"]

    # Duplicate poll without clock change
    assert mgr.poll() == []

    # Time jumps forward 100s (t2 fires)
    clock_time[0] = 215.0
    fired = mgr.poll()
    assert fired == ["Timer up: t2"]

    # Nothing left
    assert mgr.poll() == []
