from __future__ import annotations

import base64
import json
import sqlite3
import mongomock
import pytest
from service.auth_service import LocalAuthService


@pytest.fixture
def auth_service(tmp_path):
    client = mongomock.MongoClient()
    return LocalAuthService(database=client["test_users"])


def test_signup_and_login_success(auth_service):
    signup_res = auth_service.signup_with_email("test@example.com", "secret123", "Test User")
    assert signup_res["success"] is True
    assert signup_res["user"]["email"] == "test@example.com"
    assert signup_res["user"]["name"] == "Test User"
    assert signup_res["token"] is not None

    token = signup_res["token"]
    user_info = auth_service.verify_token(token)
    assert user_info is not None
    assert user_info["email"] == "test@example.com"
    assert user_info["name"] == "Test User"

    # Test login with same credentials
    login_res = auth_service.login_with_email("test@example.com", "secret123")
    assert login_res["success"] is True
    assert login_res["user"]["email"] == "test@example.com"
    assert login_res["token"] is not None


def test_signup_duplicate_email_fails(auth_service):
    auth_service.signup_with_email("dup@example.com", "password123", "User One")
    with pytest.raises(Exception) as exc:
        auth_service.signup_with_email("dup@example.com", "password456", "User Two")
    assert "already registered" in str(exc.value).lower()


def test_login_invalid_password_fails(auth_service):
    auth_service.signup_with_email("alice@example.com", "correct_pass", "Alice")
    with pytest.raises(Exception) as exc:
        auth_service.login_with_email("alice@example.com", "wrong_pass")
    assert "invalid" in str(exc.value).lower()


def test_login_nonexistent_email_fails(auth_service):
    with pytest.raises(Exception) as exc:
        auth_service.login_with_email("nobody@example.com", "pass123")
    assert "invalid" in str(exc.value).lower()


def test_verify_google_token_creates_and_authenticates_user(auth_service):
    # Construct a valid dummy JWT payload
    payload = {
        "sub": "google-uid-12345",
        "email": "googleuser@gmail.com",
        "name": "Google User",
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    fake_jwt = f"header.{payload_b64}.signature"

    result = auth_service.verify_google_token(fake_jwt)
    assert result["success"] is True
    assert result["user"]["email"] == "googleuser@gmail.com"
    assert result["user"]["name"] == "Google User"
    assert result["token"] is not None

    verified = auth_service.verify_token(result["token"])
    assert verified is not None
    assert verified["email"] == "googleuser@gmail.com"


def test_logout_invalidates_token(auth_service):
    signup_res = auth_service.signup_with_email("logout_test@example.com", "pass1234", "Logout User")
    token = signup_res["token"]
    assert auth_service.verify_token(token) is not None

    success = auth_service.logout(token)
    assert success is True
    assert auth_service.verify_token(token) is None


def test_invalid_and_empty_token_returns_none(auth_service):
    assert auth_service.verify_token("") is None
    assert auth_service.verify_token("   ") is None
    assert auth_service.verify_token("nonexistent-token-xyz") is None


def test_legacy_sqlite_users_and_sessions_are_imported_once(tmp_path):
    source = tmp_path / "legacy_users.sqlite3"
    password_hash = LocalAuthService._hash_password("legacy-password")
    with sqlite3.connect(source) as connection:
        connection.executescript(
            """CREATE TABLE users (
                   id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                   password_hash TEXT, created_at TEXT NOT NULL, is_active INTEGER NOT NULL
               );
               CREATE TABLE sessions (
                   token TEXT PRIMARY KEY, user_id TEXT NOT NULL, created_at TEXT NOT NULL,
                   expires_at TEXT
               );"""
        )
        connection.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
            ("legacy-user", "legacy@example.com", "Legacy User", password_hash, "2024-01-01", 1),
        )
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?)",
            ("legacy-token", "legacy-user", "2024-01-01", None),
        )

    database = mongomock.MongoClient()["legacy_migration"]
    service = LocalAuthService(database=database, legacy_db_path=source)

    assert service.verify_token("legacy-token") == {
        "id": "legacy-user",
        "email": "legacy@example.com",
        "name": "Legacy User",
    }
    assert service.login_with_email("legacy@example.com", "legacy-password")["success"]

    database["users"].update_one(
        {"_id": "legacy-user"}, {"$set": {"name": "Changed in Mongo"}}
    )
    reopened = LocalAuthService(database=database, legacy_db_path=source)
    assert reopened.verify_token("legacy-token")["name"] == "Changed in Mongo"
