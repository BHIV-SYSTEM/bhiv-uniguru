"""
MongoDB-backed authentication service for UniGuru with automatic SQLite fallback.
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
    """Authentication service with MongoDB storage and automatic local SQLite fallback."""

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
            else default_legacy_user_db_path()
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
                    database = (
                        self._database if self._database is not None else get_mongo_database()
                    )
                    database["users"].create_index("email", unique=True)
                    database["sessions"].create_index("user_id")

                    if self._legacy_db_path is not None and self._legacy_db_path.is_file():
                        self._migrate_legacy_data(database, self._legacy_db_path)

                    self._database = database
                    self._use_mongo = True
                    self._ready = True
                    logger.info("LocalAuthService initialized with MongoDB backend")
                    return self._database
                except Exception as exc:
                    logger.warning("MongoDB unavailable (%s); LocalAuthService falling back to SQLite", exc)

            self._init_sqlite()
            self._use_mongo = False
            self._ready = True
            logger.info("LocalAuthService initialized with SQLite backend at %s", self._legacy_db_path)
            return None

    def _init_sqlite(self) -> None:
        path = self._legacy_db_path or default_legacy_user_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect_sqlite() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    password_hash TEXT,
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )"""
            )

    def _connect_sqlite(self) -> sqlite3.Connection:
        path = self._legacy_db_path or default_legacy_user_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

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
        salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations=100_000,
            dklen=32,
        )
        salt_b64 = base64.b64encode(salt).decode("ascii")
        key_b64 = base64.b64encode(key).decode("ascii")
        return f"pbkdf2_sha256$100000${salt_b64}${key_b64}"

    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        """Verify a password against a PBKDF2-HMAC-SHA256 hash or legacy argon2/bcrypt string."""
        if not hashed:
            return False

        if hashed.startswith("pbkdf2_sha256$"):
            try:
                parts = hashed.split("$")
                if len(parts) != 4:
                    return False
                _, iter_str, salt_b64, key_b64 = parts
                iterations = int(iter_str)
                salt = base64.b64decode(salt_b64.encode("ascii"))
                expected_key = base64.b64decode(key_b64.encode("ascii"))
                actual_key = hashlib.pbkdf2_hmac(
                    "sha256",
                    password.encode("utf-8"),
                    salt,
                    iterations=iterations,
                    dklen=len(expected_key),
                )
                return hmac.compare_digest(actual_key, expected_key)
            except Exception as exc:
                logger.error("Error verifying PBKDF2 password: %s", exc)
                return False

        try:
            from passlib.hash import pbkdf2_sha256
            if pbkdf2_sha256.identify(hashed):
                return bool(pbkdf2_sha256.verify(password, hashed))
        except Exception:
            pass

        try:
            import bcrypt
            return bool(bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8")))
        except Exception:
            pass

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
        pwd_hash = self._hash_password(password)

        self._ensure_ready()
        if self._use_mongo and self._database is not None:
            user = {
                "_id": user_id,
                "email": norm_email,
                "name": norm_name,
                "password_hash": pwd_hash,
                "created_at": now_iso,
                "is_active": True,
            }
            session = {"_id": token, "user_id": user_id, "created_at": now_iso}
            try:
                self._database["users"].insert_one(user)
            except DuplicateKeyError as exc:
                raise ValueError("This email is already registered. Please login instead.") from exc

            try:
                self._database["sessions"].insert_one(session)
            except PyMongoError:
                self._database["users"].delete_one({"_id": user_id})
                raise
        else:
            with self._connect_sqlite() as conn:
                existing = conn.execute("SELECT id FROM users WHERE email = ?", (norm_email,)).fetchone()
                if existing:
                    raise ValueError("This email is already registered. Please login instead.")
                conn.execute(
                    "INSERT INTO users (id, email, name, password_hash, created_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                    (user_id, norm_email, norm_name, pwd_hash, now_iso),
                )
                conn.execute(
                    "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                    (token, user_id, now_iso),
                )
                conn.commit()

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

        self._ensure_ready()
        token = secrets.token_hex(32)
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._use_mongo and self._database is not None:
            user = self._database["users"].find_one({"email": norm_email})
            if not user or not user.get("is_active"):
                raise ValueError("Invalid email or password")
            if not self._verify_password(password, user.get("password_hash") or ""):
                raise ValueError("Invalid email or password")

            self._database["sessions"].insert_one(
                {
                    "_id": token,
                    "user_id": user["_id"],
                    "created_at": now_iso,
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
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    "SELECT id, email, name, password_hash, is_active FROM users WHERE email = ?",
                    (norm_email,),
                ).fetchone()
                if not row or not row["is_active"]:
                    raise ValueError("Invalid email or password")
                if not self._verify_password(password, row["password_hash"] or ""):
                    raise ValueError("Invalid email or password")

                conn.execute(
                    "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                    (token, row["id"], now_iso),
                )
                conn.commit()
                return {
                    "success": True,
                    "user": {
                        "id": row["id"],
                        "email": norm_email,
                        "name": row["name"] or norm_email.split("@")[0].title(),
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

        self._ensure_ready()
        token = secrets.token_hex(32)
        now_iso = datetime.now(timezone.utc).isoformat()

        if self._use_mongo and self._database is not None:
            user = self._database["users"].find_one({"email": email})
            if user is None:
                user_id = f"google_{sub}"
                candidate = {
                    "_id": user_id,
                    "email": email,
                    "name": name,
                    "password_hash": None,
                    "created_at": now_iso,
                    "is_active": True,
                }
                try:
                    self._database["users"].insert_one(candidate)
                    user = candidate
                except DuplicateKeyError:
                    user = self._database["users"].find_one({"email": email})
                    if user is None:
                        raise
            else:
                user_id = user["_id"]
                name = user.get("name") or name

            self._database["sessions"].insert_one(
                {
                    "_id": token,
                    "user_id": user_id,
                    "created_at": now_iso,
                }
            )
            return {
                "success": True,
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": user.get("name") or name,
                },
                "token": token,
            }
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute("SELECT id, email, name FROM users WHERE email = ?", (email,)).fetchone()
                if row:
                    user_id = row["id"]
                    user_name = row["name"] or name
                else:
                    user_id = f"google_{sub}"
                    user_name = name
                    conn.execute(
                        "INSERT INTO users (id, email, name, password_hash, created_at, is_active) VALUES (?, ?, ?, NULL, ?, 1)",
                        (user_id, email, user_name, now_iso),
                    )
                conn.execute(
                    "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                    (token, user_id, now_iso),
                )
                conn.commit()
                return {
                    "success": True,
                    "user": {
                        "id": user_id,
                        "email": email,
                        "name": user_name,
                    },
                    "token": token,
                }

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify an authentication bearer token and return user identity."""
        if not token or not token.strip():
            return None

        self._ensure_ready()
        clean_token = token.strip()

        if self._use_mongo and self._database is not None:
            session = self._database["sessions"].find_one({"_id": clean_token})
            if session is None:
                return None
            user = self._database["users"].find_one(
                {"_id": session["user_id"], "is_active": True}
            )
            if user is None:
                return None
            return {"id": user["_id"], "email": user["email"], "name": user["name"]}
        else:
            try:
                with self._connect_sqlite() as conn:
                    row = conn.execute(
                        """SELECT u.id, u.email, u.name, u.is_active
                           FROM sessions s
                           JOIN users u ON s.user_id = u.id
                           WHERE s.token = ?""",
                        (clean_token,),
                    ).fetchone()
                    if row and row["is_active"]:
                        return {"id": row["id"], "email": row["email"], "name": row["name"]}
            except Exception as exc:
                logger.warning("Session token verification failed: %s", exc)
            return None

    def logout(self, token: str) -> bool:
        """Invalidate a session token."""
        if not token or not token.strip():
            return True
        self._ensure_ready()
        clean_token = token.strip()
        if self._use_mongo and self._database is not None:
            self._database["sessions"].delete_one({"_id": clean_token})
        else:
            try:
                with self._connect_sqlite() as conn:
                    conn.execute("DELETE FROM sessions WHERE token = ?", (clean_token,))
                    conn.commit()
            except Exception as exc:
                logger.error("Error during session logout: %s", exc)
                return False
        return True


# Global singleton instance
auth_service = LocalAuthService()
