from __future__ import annotations

from pathlib import Path
import pytest

from jarvis.tools.timers import TimerManager, ReminderStore


def test_timer_fires_after_delay() -> None:
    current_time = [1000.0]

    def fake_clock() -> float:
        return current_time[0]

    fired = []
    mgr = TimerManager(clock=fake_clock)
    mgr.set_timer(seconds=60, label="tea", callback=lambda msg: fired.append(msg))

    # At t=1030s (30s elapsed), timer must not have fired
    current_time[0] = 1030.0
    mgr.poll()
    assert fired == []

    # At t=1059.9s, timer must still not have fired
    current_time[0] = 1059.9
    mgr.poll()
    assert fired == []

    # At t=1060.0s (60s elapsed), timer fires!
    current_time[0] = 1060.0
    mgr.poll()
    assert len(fired) == 1
    assert "tea" in fired[0]

    # Future polls do not duplicate fire
    current_time[0] = 1070.0
    mgr.poll()
    assert len(fired) == 1


def test_reminder_survives_restart(tmp_path: Path) -> None:
    db_path = tmp_path / "reminders.db"

    # Connection 1 writes a reminder
    store1 = ReminderStore(db_path=db_path)
    store1.add_reminder("take medicine", remind_at_iso="2026-10-29T10:00:00")
    store1.close()

    # Connection 2 (simulating fresh process startup) reads it back
    store2 = ReminderStore(db_path=db_path)
    active = store2.list_reminders()
    store2.close()

    assert len(active) == 1
    assert active[0]["text"] == "take medicine"
    assert active[0]["remind_at"] == "2026-10-29T10:00:00"
