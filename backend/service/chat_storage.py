"""Durable, owner-scoped MongoDB storage for chat sessions."""
from __future__ import annotations

import json
import hashlib
import os
import sqlite3
from collections.abc import Iterator, MutableMapping
from pathlib import Path
from threading import Lock
from typing import Any

from pymongo.database import Database

from service.mongodb import get_mongo_database, migration_marker, record_migration


def default_legacy_chat_db_path() -> Path:
    configured = os.getenv("UNIGURU_CHAT_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    if os.getenv("UNIGURU_ENVIRONMENT", "").strip().lower() == "production":
        return Path("/var/lib/uniguru/chats.sqlite3")
    return Path(__file__).resolve().parents[2] / "logs" / "chats.sqlite3"


class ChatSessionStore(MutableMapping[str, dict[str, Any]]):
    """Mapping-compatible MongoDB store preserving existing API response shapes."""

    def __init__(
        self,
        database: Database | None = None,
        legacy_db_path: str | Path | None = None,
    ) -> None:
        self._database = database
        self._legacy_db_path = (
            Path(legacy_db_path)
            if legacy_db_path is not None
            else default_legacy_chat_db_path() if database is None else None
        )
        self._ready = False
        self._initialization_lock = Lock()

    def _ensure_ready(self) -> Database:
        database = (
            self._database if self._database is not None else get_mongo_database()
        )
        if self._ready:
            return database

        with self._initialization_lock:
            if self._ready:
                return database

            database["chat_sessions"].create_index("owner_id")
            if self._legacy_db_path is not None:
                self._migrate_legacy_data(database, self._legacy_db_path)
            self._ready = True
        return database

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
        document = self._ensure_ready()["chat_sessions"].find_one(
            {"_id": key}, {"payload": 1}
        )
        if document is None:
            raise KeyError(key)
        return document["payload"]

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        owner_id = str(value.get("userId") or "").strip()
        if not owner_id:
            raise ValueError("chat session must have an owner")

        self._ensure_ready()["chat_sessions"].update_one(
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

    def __delitem__(self, key: str) -> None:
        result = self._ensure_ready()["chat_sessions"].delete_one({"_id": key})
        if result.deleted_count == 0:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        cursor = self._ensure_ready()["chat_sessions"].find(
            {}, {"_id": 1}
        ).sort("updated_at", 1)
        return iter([str(document["_id"]) for document in cursor])

    def __len__(self) -> int:
        return self._ensure_ready()["chat_sessions"].count_documents({})
