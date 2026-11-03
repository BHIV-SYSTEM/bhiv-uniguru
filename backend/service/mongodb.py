from __future__ import annotations

import logging
import os
from threading import Lock
from typing import Any

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import PyMongoError

logger = logging.getLogger("uniguru.service.mongodb")

_client: MongoClient | None = None
_database: Database | None = None
_lock = Lock()


def get_mongo_database() -> Database:
    """Return the shared MongoDB database, connecting only when first used."""
    global _client, _database
    if _database is not None:
        return _database

    with _lock:
        if _database is not None:
            return _database

        uri = os.getenv("MONGODB_URI", "").strip()
        if not uri:
            raise RuntimeError(
                "MongoDB is not configured. Set MONGODB_URI in the backend environment."
            )

        database_name = os.getenv("MONGODB_DATABASE", "uniguru").strip()
        if not database_name:
            raise RuntimeError("MONGODB_DATABASE must not be empty.")

        client: MongoClient | None = None
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=5000, appname="UniGuru")
            client.admin.command("ping")
        except PyMongoError:
            if client is not None:
                client.close()
            logger.error("Could not connect to the configured MongoDB server.")
            raise RuntimeError(
                "Could not connect to MongoDB. Check MONGODB_URI and Atlas network access."
            ) from None

        _client = client
        _database = client[database_name]
        logger.info("Connected to MongoDB database %s", database_name)
        return _database


def close_mongo_client() -> None:
    """Close the shared MongoDB client, primarily for application shutdown."""
    global _client, _database
    with _lock:
        if _client is not None:
            _client.close()
        _client = None
        _database = None


def migration_marker(database: Any, marker: str) -> bool:
    """Return whether a legacy data migration has already completed."""
    return database["schema_migrations"].find_one({"_id": marker}) is not None


def record_migration(database: Any, marker: str) -> None:
    database["schema_migrations"].update_one(
        {"_id": marker},
        {"$set": {"completed": True}},
        upsert=True,
    )
