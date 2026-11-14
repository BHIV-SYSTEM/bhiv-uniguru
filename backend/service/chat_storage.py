"""Durable, owner-scoped storage for chat sessions (MongoDB with SQLite fallback)."""
from __future__ import annotations

import json
import hashlib
import logging
import os
import sqlite3
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from threading import Lock
from typing import Any

from pymongo.database import Database

from service.mongodb import get_mongo_database, migration_marker, record_migration

logger = logging.getLogger("uniguru.service.chat_storage")


def default_legacy_chat_db_path() -> Path:
    configured = os.getenv("UNIGURU_CHAT_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    if os.getenv("UNIGURU_ENVIRONMENT", "").strip().lower() == "production":
        return Path("/var/lib/uniguru/chats.sqlite3")
    return Path(__file__).resolve().parents[2] / "logs" / "chats.sqlite3"


class ChatSessionStore(MutableMapping[str, dict[str, Any]]):
    """Mapping-compatible store using MongoDB if configured, falling back to local SQLite."""

    def __init__(
        self,
        database: Database | None = None,
        legacy_db_path: str | Path | None = None,
    ) -> None:
        self._database = database
        self._legacy_db_path = (
            Path(legacy_db_path)
            if legacy_db_path is not None
            else default_legacy_chat_db_path()
        )
        self._use_mongo = False
        self._ready = False
        self._initialization_lock = Lock()

    def _ensure_ready(self) -> Database | None:
        if self._ready:
            return self._database

        with self._initialization_lock:
            if self._ready:
                return self._database

            uri = os.getenv("MONGODB_URI", "").strip()
            if self._database is not None or uri:
                try:
                    db = self._database if self._database is not None else get_mongo_database()
                    db["chat_sessions"].create_index("owner_id")
                    if self._legacy_db_path is not None and self._legacy_db_path.is_file():
                        self._migrate_legacy_data(db, self._legacy_db_path)
                    self._database = db
                    self._use_mongo = True
                    self._ready = True
                    logger.info("ChatSessionStore initialized with MongoDB backend")
                    return self._database
                except Exception as exc:
                    logger.warning("MongoDB unavailable (%s); ChatSessionStore falling back to SQLite", exc)

            self._init_sqlite()
            self._use_mongo = False
            self._ready = True
            logger.info("ChatSessionStore initialized with SQLite backend at %s", self._legacy_db_path)
            return None

    def _init_sqlite(self) -> None:
        path = self._legacy_db_path or default_legacy_chat_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect_sqlite() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS chat_sessions (
                    chat_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner ON chat_sessions(owner_id)"
            )

    def _connect_sqlite(self) -> sqlite3.Connection:
        path = self._legacy_db_path or default_legacy_chat_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _migration_id(path: Path) -> str:
        path_hash = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
        return f"sqlite-chats-v1:{path_hash}"

    @classmethod
    def _migrate_legacy_data(cls, database: Database, path: Path) -> None:
        marker = cls._migration_id(path)
        if migration_marker(database, marker) or not path.is_file():
            return

        with sqlite3.connect(path) as connection:
            connection.row_factory = sqlite3.Row
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'chat_sessions'"
            ).fetchone()
            if table is not None:
                for row in connection.execute(
                    "SELECT chat_id, owner_id, payload, updated_at FROM chat_sessions"
                ):
                    payload = json.loads(row["payload"])
                    if not isinstance(payload, dict):
                        raise ValueError(
                            f"Legacy chat {row['chat_id']} has a non-object payload."
                        )
                    document = {
                        "_id": str(row["chat_id"]),
                        "owner_id": str(row["owner_id"]),
                        "payload": payload,
                        "updated_at": row["updated_at"],
                    }
                    database["chat_sessions"].replace_one(
                        {"_id": document["_id"]}, document, upsert=True
                    )

        record_migration(database, marker)

    def __getitem__(self, key: str) -> dict[str, Any]:
        self._ensure_ready()
        if self._use_mongo and self._database is not None:
            document = self._database["chat_sessions"].find_one(
                {"_id": key}, {"payload": 1}
            )
            if document is None:
                raise KeyError(key)
            return document["payload"]
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    "SELECT payload FROM chat_sessions WHERE chat_id = ?", (key,)
                ).fetchone()
            if row is None:
                raise KeyError(key)
            return json.loads(row["payload"])

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        owner_id = str(value.get("userId") or "").strip()
        if not owner_id:
            raise ValueError("chat session must have an owner")

        self._ensure_ready()
        if self._use_mongo and self._database is not None:
            self._database["chat_sessions"].update_one(
                {"_id": key},
                {
                    "$set": {
                        "owner_id": owner_id,
                        "payload": value,
                        "updated_at": value.get("lastActivity") or "",
                    }
                },
                upsert=True,
            )
        else:
            payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            with self._connect_sqlite() as conn:
                conn.execute(
                    """INSERT INTO chat_sessions(chat_id, owner_id, payload, updated_at)
                       VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                       ON CONFLICT(chat_id) DO UPDATE SET
                         owner_id=excluded.owner_id,
                         payload=excluded.payload,
                         updated_at=CURRENT_TIMESTAMP""",
                    (key, owner_id, payload),
                )

    def __delitem__(self, key: str) -> None:
        self._ensure_ready()
        if self._use_mongo and self._database is not None:
            result = self._database["chat_sessions"].delete_one({"_id": key})
            if result.deleted_count == 0:
                raise KeyError(key)
        else:
            with self._connect_sqlite() as conn:
                cursor = conn.execute("DELETE FROM chat_sessions WHERE chat_id = ?", (key,))
            if cursor.rowcount == 0:
                raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        self._ensure_ready()
        if self._use_mongo and self._database is not None:
            cursor = self._database["chat_sessions"].find(
                {}, {"_id": 1}
            ).sort("updated_at", 1)
            return iter([str(document["_id"]) for document in cursor])
        else:
            with self._connect_sqlite() as conn:
                rows = conn.execute("SELECT chat_id FROM chat_sessions ORDER BY updated_at").fetchall()
            return iter([row["chat_id"] for row in rows])

    def __len__(self) -> int:
        self._ensure_ready()
        if self._use_mongo and self._database is not None:
            return self._database["chat_sessions"].count_documents({})
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute("SELECT COUNT(*) AS n FROM chat_sessions").fetchone()
            return int(row["n"]) if row else 0
