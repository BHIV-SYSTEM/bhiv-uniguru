from __future__ import annotations

import base64
import json
import os
import pytest
from starlette.requests import Request

os.environ["UNIGURU_API_AUTH_REQUIRED"] = "false"

from service import api


def _request(token: str | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
            "scheme": "http",
        }
    )


def test_production_mode_does_not_crash_without_supabase(monkeypatch):
    """Verify that in production mode, startup succeeds without any Supabase credentials."""
    monkeypatch.setenv("UNIGURU_ENVIRONMENT", "production")
    monkeypatch.setenv("UNIGURU_CORS_ORIGINS", "https://uni-guru.vercel.app")
    assert api.auth_service.enabled is True


def test_api_signup_login_logout_flow():
    email = "integration_direct@uniguru.test"
    password = "strongPassword123"

    # 1. Signup
    signup_payload = {
        "name": "Integration User",
        "email": email,
        "password": password,
    }
    signup_res = api.user_signup(signup_payload)
    assert signup_res["success"] is True
    assert signup_res["email"] == email
    token = signup_res["token"]
    assert token

    # 2. Login
    login_payload = {
        "email": email,
        "password": password,
    }
    login_res = api.user_login(login_payload)
    assert login_res["email"] == email
    assert login_res["token"]

    # 3. Authenticated request using the token
    req = _request(token)
    user = api._require_user_identity(req)
    assert user["email"] == email

    # 4. Logout
    logout_res = api.user_logout(req)
    assert logout_res["status"] == "ok"


def test_api_google_oauth_callback():
    payload = {
        "sub": "google-test-sub-999",
        "email": "google_test_user@gmail.com",
        "name": "Google Test User",
    }
    b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    fake_token = f"eyJhbGciOiJSUzI1NiJ9.{b64}.sig"

    res = api.google_oauth_callback({"token": fake_token})
    assert res["user"]["email"] == "google_test_user@gmail.com"
    assert res["token"]
