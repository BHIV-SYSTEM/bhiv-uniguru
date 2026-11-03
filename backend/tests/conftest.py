from __future__ import annotations

import mongomock
import pytest


@pytest.fixture(autouse=True)
def use_isolated_mongodb_for_api_tests(monkeypatch):
    from service import api
    from service.auth_service import LocalAuthService
    from service.chat_storage import ChatSessionStore

    database = mongomock.MongoClient()["api_test"]
    monkeypatch.setattr(api, "auth_service", LocalAuthService(database=database))
    monkeypatch.setattr(api, "_CHAT_SESSIONS", ChatSessionStore(database=database))
