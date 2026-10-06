from __future__ import annotations

import os
import pytest
from fastapi import HTTPException
from starlette.requests import Request

os.environ["UNIGURU_API_AUTH_REQUIRED"] = "false"

from service import api
from service.chat_storage import ChatSessionStore


def _request(token: str | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode())] if token else []
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/chat",
            "headers": headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
            "scheme": "http",
        }
    )


@pytest.fixture
def chat_test_state(monkeypatch, tmp_path):
    store = ChatSessionStore(tmp_path / "chats.sqlite3")
    monkeypatch.setattr(api, "_CHAT_SESSIONS", store)
    monkeypatch.setattr(api, "_DEMO_AUTH_ENABLED", True)
    monkeypatch.setattr(
        api,
        "_DEMO_AUTH_TOKENS",
        {
            "token-a": {"id": "user-a", "email": "a@example.test", "name": "A"},
            "token-b": {"id": "user-b", "email": "b@example.test", "name": "B"},
        },
    )
    store["chat-a"] = {
        "id": "chat-a", "userId": "user-a", "title": "A", "guru": {"_id": "g"},
        "createdAt": "now", "lastActivity": "now", "messages": [],
    }
    store["chat-b"] = {
        "id": "chat-b", "userId": "user-b", "title": "B", "guru": {"_id": "g"},
        "createdAt": "now", "lastActivity": "now", "messages": [],
    }
    return store


def test_chat_store_survives_reopen_and_keeps_owner(chat_test_state, tmp_path):
    reopened = ChatSessionStore(tmp_path / "chats.sqlite3")
    assert reopened["chat-a"]["userId"] == "user-a"
    assert reopened["chat-a"]["messages"] == []
    assert {chat["userId"] for chat in reopened.values()} == {"user-a", "user-b"}


def test_user_a_and_b_can_only_read_their_own_chats(chat_test_state):
    assert api.chat_get("chat-a", _request("token-a"))["chat"]["id"] == "chat-a"
    assert api.chat_get("chat-b", _request("token-b"))["chat"]["id"] == "chat-b"
    for chat_id, token in (("chat-b", "token-a"), ("chat-a", "token-b")):
        with pytest.raises(HTTPException) as exc:
            api.chat_get(chat_id, _request(token))
        assert exc.value.status_code == 404


def test_chat_update_and_delete_require_ownership(chat_test_state):
    with pytest.raises(HTTPException) as exc:
        api.chat_update("chat-b", {"title": "hijack"}, _request("token-a"))
    assert exc.value.status_code == 404
    assert chat_test_state["chat-b"]["title"] == "B"

    with pytest.raises(HTTPException) as exc:
        api.chat_delete("chat-a", _request("token-b"))
    assert exc.value.status_code == 404
    assert "chat-a" in chat_test_state

    api.chat_update("chat-a", {"title": "owned"}, _request("token-a"))
    assert chat_test_state["chat-a"]["title"] == "owned"
    api.chat_delete("chat-b", _request("token-b"))
    assert "chat-b" not in chat_test_state


def test_chat_lists_never_fall_back_to_another_users_data(chat_test_state):
    assert [c["id"] for c in api.chat_list(_request("token-a"))["chats"]] == ["chat-a"]
    assert [c["id"] for c in api.chat_all_with_data(_request("token-b"))["chats"]] == ["chat-b"]


def test_chat_create_uses_verified_identity_not_request_user_id(chat_test_state):
    created = api.chat_create(
        {"guruId": "unowned-or-default-guru", "userId": "user-b"},
        _request("token-a"),
    )
    chat_id = created["chat"]["id"]
    assert chat_test_state[chat_id]["userId"] == "user-a"


def test_chat_message_uses_verified_identity_and_persists_trace(chat_test_state, monkeypatch):
    monkeypatch.setattr(
        api.service,
        "ask",
        lambda **_kwargs: {"answer": "verified answer", "verification_status": "VERIFIED"},
    )
    result = api.chat_new(
        {"message": "sample question", "chatbotId": "g", "userId": "user-b", "chatId": "chat-a"},
        _request("token-a"),
    )
    stored = chat_test_state["chat-a"]
    assert stored["userId"] == "user-a"
    assert stored["messages"][-1]["metadata"]["trace_id"].startswith("chat_chat-a_")
    assert result["aiResponse"]["content"] == "verified answer"


def test_auth_fails_closed_when_provider_is_unavailable(monkeypatch):
    monkeypatch.setattr(api, "_DEMO_AUTH_ENABLED", False)
    monkeypatch.setattr(api.supabase_auth, "enabled", False)
    with pytest.raises(HTTPException) as exc:
        api._require_user_identity(_request("untrusted-token"))
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        api._require_user_identity(_request())
    assert exc.value.status_code == 503
    with pytest.raises(HTTPException) as exc:
        api.user_login({"email": "a@example.test", "password": "anything"})
    assert exc.value.status_code == 503


def test_supabase_missing_or_invalid_token_is_denied(monkeypatch):
    monkeypatch.setattr(api, "_DEMO_AUTH_ENABLED", False)
    monkeypatch.setattr(api.supabase_auth, "enabled", True)
    monkeypatch.setattr(api.supabase_auth, "verify_token", lambda _token: None)
    for request in (_request(), _request("expired-or-revoked")):
        with pytest.raises(HTTPException) as exc:
            api._require_user_identity(request)
        assert exc.value.status_code == 401


def test_invalid_token_is_denied_and_local_demo_token_is_explicit(monkeypatch):
    monkeypatch.setattr(api, "_DEMO_AUTH_ENABLED", True)
    monkeypatch.setattr(api, "_DEMO_AUTH_TOKENS", {"valid-local": {"id": "local-user"}})
    with pytest.raises(HTTPException) as exc:
        api._require_user_identity(_request("not-valid"))
    assert exc.value.status_code == 401
    assert api._require_user_identity(_request("valid-local"))["id"] == "local-user"
    api.user_logout(_request("valid-local"))
    with pytest.raises(HTTPException) as exc:
        api._require_user_identity(_request("valid-local"))
    assert exc.value.status_code == 401
