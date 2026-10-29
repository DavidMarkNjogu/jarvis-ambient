"""Persistent personal memory across sessions stored in SQLite. Standard library only."""

from __future__ import annotations

import datetime
import re
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "jarvis.db"

SECRET_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"AQ\.[0-9A-Za-z_\-]{20,}"),
    re.compile(r"gsk_[0-9A-Za-z]{15,}"),
    re.compile(r"sk-[0-9A-Za-z]{15,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(my\s+password\s+is|password\s*[:=])\s*\S+"),
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),
]


class Memory:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._init_tables()

    def _init_tables(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'profile',
                    created_at TEXT NOT NULL
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _check_secrets(self, text: str) -> None:
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise ValueError("Memory refuses to store credentials, passwords, or credit card numbers.")

    def remember(self, fact: str, category: str = "profile") -> int:
        clean = fact.strip()
        if not clean:
            return 0
        self._check_secrets(clean)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO facts (fact, category, created_at) VALUES (?, ?, ?)",
                (clean, category, now_iso),
            )
            return cur.lastrowid or 0

    def recall(self, keyword: str) -> list[str]:
        clean = keyword.strip()
        if not clean:
            return []
        cur = self.conn.execute(
            "SELECT fact FROM facts WHERE fact LIKE ? ORDER BY id ASC",
            (f"%{clean}%",),
        )
        return [row[0] for row in cur.fetchall()]

    def forget(self, keyword: str) -> int:
        clean = keyword.strip()
        if not clean:
            return 0
        with self.conn:
            cur = self.conn.execute(
                "DELETE FROM facts WHERE fact LIKE ?",
                (f"%{clean}%",),
            )
            return cur.rowcount

    def get_profile_facts(self) -> list[str]:
        cur = self.conn.execute("SELECT fact FROM facts ORDER BY id ASC")
        return [row[0] for row in cur.fetchall()]

    def save_session_summary(self, summary: str) -> int:
        clean = summary.strip()
        if not clean:
            return 0
        self._check_secrets(clean)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO session_summaries (summary, created_at) VALUES (?, ?)",
                (clean, now_iso),
            )
            return cur.lastrowid or 0

    def search_session_summaries(self, keyword: str) -> list[str]:
        clean = keyword.strip()
        if not clean:
            return []
        cur = self.conn.execute(
            "SELECT summary FROM session_summaries WHERE summary LIKE ? ORDER BY id DESC",
            (f"%{clean}%",),
        )
        return [row[0] for row in cur.fetchall()]

    def close(self) -> None:
        self.conn.close()
