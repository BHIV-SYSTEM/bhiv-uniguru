"""Durable, owner-scoped storage for chat sessions."""
from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from typing import Any


def default_chat_db_path() -> Path:
    configured = os.getenv("UNIGURU_CHAT_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    if os.getenv("UNIGURU_ENVIRONMENT", "").strip().lower() == "production":
        return Path("/var/lib/uniguru/chats.sqlite3")
    return Path(__file__).resolve().parents[2] / "logs" / "chats.sqlite3"


class ChatSessionStore(MutableMapping[str, dict[str, Any]]):
    """Mapping-compatible SQLite store so existing API response shapes remain stable."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or default_chat_db_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS chat_sessions (
                    chat_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner ON chat_sessions(owner_id)"
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def __getitem__(self, key: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM chat_sessions WHERE chat_id = ?", (key,)
            ).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row["payload"])

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        owner_id = str(value.get("userId") or "").strip()
        if not owner_id:
            raise ValueError("chat session must have an owner")
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO chat_sessions(chat_id, owner_id, payload, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(chat_id) DO UPDATE SET
                     owner_id=excluded.owner_id,
                     payload=excluded.payload,
                     updated_at=CURRENT_TIMESTAMP""",
                (key, owner_id, payload),
            )

    def __delitem__(self, key: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM chat_sessions WHERE chat_id = ?", (key,))
        if cursor.rowcount == 0:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        with self._connect() as connection:
            rows = connection.execute("SELECT chat_id FROM chat_sessions ORDER BY updated_at").fetchall()
        return iter([row["chat_id"] for row in rows])

    def __len__(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS n FROM chat_sessions").fetchone()
        return int(row["n"])

