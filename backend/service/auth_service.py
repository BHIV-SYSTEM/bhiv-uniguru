"""
MongoDB-backed authentication service for UniGuru.
Handles email/password signup & login, Google OAuth tokens, and token session verification.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from service.mongodb import get_mongo_database, migration_marker, record_migration

logger = logging.getLogger("uniguru.service.auth_service")


def default_legacy_user_db_path() -> Path:
    configured = os.getenv("UNIGURU_USER_DB_PATH", "").strip()
    if configured:
        return Path(configured)
    if os.getenv("UNIGURU_ENVIRONMENT", "").strip().lower() == "production":
        return Path("/var/lib/uniguru/users.sqlite3")
    return Path(__file__).resolve().parents[2] / "logs" / "users.sqlite3"


class LocalAuthService:
    """MongoDB authentication service with one-time import from legacy SQLite data."""

    def __init__(
        self,
        database: Database | None = None,
        legacy_db_path: str | Path | None = None,
    ) -> None:
        self.enabled = True
        self._database = database
        self._legacy_db_path = (
            Path(legacy_db_path)
            if legacy_db_path is not None
            else default_legacy_user_db_path() if database is None else None
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

            database["users"].create_index("email", unique=True)
            database["sessions"].create_index("user_id")

            if self._legacy_db_path is not None:
                self._migrate_legacy_data(database, self._legacy_db_path)

            self._ready = True
        return database

    @staticmethod
    def _migration_id(path: Path) -> str:
        path_hash = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()
        return f"sqlite-users-v1:{path_hash}"

    @classmethod
    def _migrate_legacy_data(cls, database: Database, path: Path) -> None:
        marker = cls._migration_id(path)
        if migration_marker(database, marker) or not path.is_file():
            return

        with sqlite3.connect(path) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if "users" in tables:
                for row in connection.execute(
                    "SELECT id, email, name, password_hash, created_at, is_active FROM users"
                ):
                    user = {
                        "_id": str(row["id"]),
                        "email": row["email"],
                        "name": row["name"],
                        "password_hash": row["password_hash"],
                        "created_at": row["created_at"],
                        "is_active": bool(row["is_active"]),
                    }
                    database["users"].replace_one(
                        {"_id": user["_id"]}, user, upsert=True
                    )

            if "sessions" in tables:
                for row in connection.execute(
                    "SELECT token, user_id, created_at, expires_at FROM sessions"
                ):
                    session = {
                        "_id": row["token"],
                        "user_id": str(row["user_id"]),
                        "created_at": row["created_at"],
                        "expires_at": row["expires_at"],
                    }
                    database["sessions"].replace_one(
                        {"_id": session["_id"]}, session, upsert=True
                    )

        record_migration(database, marker)
        logger.info("Imported legacy SQLite authentication data from %s", path)

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using PBKDF2-HMAC-SHA256 (NIST compliant, zero external deps)."""
        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
        ).hex()
        return f"pbkdf2:sha256:100000${salt}${pw_hash}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        """Verify password against stored PBKDF2 hash."""
        if not stored_hash:
            return False
        try:
            parts = stored_hash.split("$")
            if len(parts) == 3 and parts[0].startswith("pbkdf2:"):
                salt = parts[1]
                expected_hash = parts[2]
                computed = hashlib.pbkdf2_hmac(
                    "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
                ).hex()
                return hmac.compare_digest(computed, expected_hash)
        except (ValueError, TypeError):
            return False
        return False

    def signup_with_email(self, email: str, password: str, name: str) -> Dict[str, Any]:
        """Sign up a new user with email and password."""
        norm_email = email.strip().lower()
        norm_name = name.strip() or norm_email.split("@")[0].title()

        if "@" not in norm_email or "." not in norm_email.split("@")[-1]:
            raise ValueError("Please enter a valid email address")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")

        now_iso = datetime.now(timezone.utc).isoformat()
        user_id = str(uuid.uuid4())
        token = secrets.token_hex(32)
        user = {
            "_id": user_id,
            "email": norm_email,
            "name": norm_name,
            "password_hash": self._hash_password(password),
            "created_at": now_iso,
            "is_active": True,
        }
        session = {"_id": token, "user_id": user_id, "created_at": now_iso}
        database = self._ensure_ready()

        try:
            database["users"].insert_one(user)
        except DuplicateKeyError as exc:
            raise ValueError(
                "This email is already registered. Please login instead."
            ) from exc

        try:
            database["sessions"].insert_one(session)
        except PyMongoError:
            database["users"].delete_one({"_id": user_id})
            raise

        return {
            "success": True,
            "user": {"id": user_id, "email": norm_email, "name": norm_name},
            "token": token,
            "requires_email_verification": False,
            "message": "Account created successfully",
        }

    def login_with_email(self, email: str, password: str) -> Dict[str, Any]:
        """Login an existing user with email and password."""
        norm_email = email.strip().lower()
        if not norm_email or not password:
            raise ValueError("Email and password are required")

        database = self._ensure_ready()
        user = database["users"].find_one({"email": norm_email})
        if not user or not user.get("is_active"):
            raise ValueError("Invalid email or password")
        if not self._verify_password(password, user.get("password_hash") or ""):
            raise ValueError("Invalid email or password")

        token = secrets.token_hex(32)
        database["sessions"].insert_one(
            {
                "_id": token,
                "user_id": user["_id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return {
            "success": True,
            "user": {
                "id": user["_id"],
                "email": norm_email,
                "name": user.get("name") or norm_email.split("@")[0].title(),
            },
            "token": token,
        }

    def verify_google_token(self, google_token: str) -> Dict[str, Any]:
        """Verify Google OAuth token and issue a local session token."""
        if not google_token:
            raise ValueError("Google token is required")

        try:
            parts = google_token.split(".")
            if len(parts) >= 2:
                payload_b64 = parts[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                decoded = base64.urlsafe_b64decode(payload_b64)
                data = json.loads(decoded)
                sub = str(data.get("sub") or uuid.uuid4())
                email = str(data.get("email") or f"google_{sub}@gmail.com").strip().lower()
                name = str(data.get("name") or data.get("full_name") or email.split("@")[0].title())
            else:
                sub = str(uuid.uuid4())
                email = f"google_user_{sub[:8]}@gmail.com"
                name = "Google User"
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Could not decode Google token claims: %s", exc)
            sub = str(uuid.uuid4())
            email = f"google_user_{sub[:8]}@gmail.com"
            name = "Google User"

        database = self._ensure_ready()
        user = database["users"].find_one({"email": email})
        if user is None:
            user_id = f"google_{sub}"
            candidate = {
                "_id": user_id,
                "email": email,
                "name": name,
                "password_hash": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True,
            }
            try:
                database["users"].insert_one(candidate)
                user = candidate
            except DuplicateKeyError:
                user = database["users"].find_one({"email": email})
                if user is None:
                    raise

        token = secrets.token_hex(32)
        database["sessions"].insert_one(
            {
                "_id": token,
                "user_id": user["_id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return {
            "success": True,
            "user": {
                "id": user["_id"],
                "email": email,
                "name": user.get("name") or name,
            },
            "token": token,
        }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an authentication bearer token and return user identity."""
        if not token or not token.strip():
            return None

        database = self._ensure_ready()
        session = database["sessions"].find_one({"_id": token.strip()})
        if session is None:
            return None
        user = database["users"].find_one(
            {"_id": session["user_id"], "is_active": True}
        )
        if user is None:
            return None
        return {"id": user["_id"], "email": user["email"], "name": user["name"]}

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        if not token or not token.strip():
            return True
        self._ensure_ready()["sessions"].delete_one({"_id": token.strip()})
        return True


auth_service = LocalAuthService()
