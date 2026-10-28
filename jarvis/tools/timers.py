"""Timers and persistent reminders using SQLite."""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class ActiveTimer:
    deadline: float
    label: str
    callback: Callable[[str], None] | None = None
    fired: bool = False


class TimerManager:
    """In-memory timer manager with injectable clock."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._timers: list[ActiveTimer] = []

    def set_timer(self, seconds: float, label: str = "timer", callback: Callable[[str], None] | None = None) -> str:
        deadline = self._clock() + seconds
        self._timers.append(ActiveTimer(deadline=deadline, label=label, callback=callback))
        return f"Timer set for {label} ({seconds}s)"

    def poll(self) -> list[str]:
        now = self._clock()
        fired_messages = []
        for timer in self._timers:
            if not timer.fired and now >= timer.deadline:
                timer.fired = True
                msg = f"Timer up: {timer.label}"
                fired_messages.append(msg)
                if timer.callback:
                    try:
                        timer.callback(msg)
                    except Exception:
                        pass
        return fired_messages


class ReminderStore:
    """Persistent reminder store using SQLite."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path("data/jarvis.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    remind_at TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    completed INTEGER DEFAULT 0
                )
                """
            )

    def add_reminder(self, text: str, remind_at_iso: str) -> int:
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO reminders (text, remind_at, created_at, completed) VALUES (?, ?, ?, 0)",
                (text, remind_at_iso, time.time()),
            )
            return cur.lastrowid or 0

    def list_reminders(self, include_completed: bool = False) -> list[dict[str, Any]]:
        query = "SELECT id, text, remind_at, created_at, completed FROM reminders"
        if not include_completed:
            query += " WHERE completed = 0"
        query += " ORDER BY remind_at ASC"

        with self._conn:
            rows = self._conn.execute(query).fetchall()
            return [
                {
                    "id": row["id"],
                    "text": row["text"],
                    "remind_at": row["remind_at"],
                    "created_at": row["created_at"],
                    "completed": bool(row["completed"]),
                }
                for row in rows
            ]

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
