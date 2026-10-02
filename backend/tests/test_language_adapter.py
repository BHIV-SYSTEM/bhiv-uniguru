from fastapi.testclient import TestClient

from integrations.language_adapter import LanguageAdapter
from service import api


MARATHI_CASES = [
    ("धर्म म्हणजे काय?", "dharma"),
    ("कर्मयोग म्हणजे काय?", "karma yoga"),
    ("अहिंसा म्हणजे काय?", "ahimsa"),
    ("जैन धर्मातील अनेकांतवाद म्हणजे काय?", "anekantavada"),
    ("क्वांटम सुपरपोझिशन सोप्या भाषेत समजावून सांगा.", "quantum superposition"),
]


def test_marathi_queries_are_detected_and_normalized_to_kb_concepts():
    adapter = LanguageAdapter()

    for query, expected_term in MARATHI_CASES:
        adapted = adapter.normalize_query(query)
        assert adapted.source_language == "mr"
        assert expected_term in adapted.normalized_query.casefold()


def test_localization_uses_only_the_verified_source_summary():
    adapter = LanguageAdapter()
    response = {
        "answer": "English answer from verified evidence.",
        "verification_status": "VERIFIED",
        "retrieval_trace": {
            "evidence_sources": [
                {"path": "sanskrit/karma.md", "chapter": "Psychology"},
            ]
        },
    }

    localized = adapter.localize_response(response, "mr")

    assert "कर्मयोग म्हणजे" in localized["answer"]
    assert "स्रोत: sanskrit/karma.md" in localized["answer"]
    assert localized["language_adapter"]["response_localization_applied"] is True


def test_unverified_answer_is_not_localized_as_a_supported_kb_claim():
    adapter = LanguageAdapter()
    response = {
        "answer": "I do not have verified knowledge.",
        "verification_status": "UNVERIFIED",
        "retrieval_trace": {
            "evidence_sources": [{"path": "sanskrit/karma.md"}],
        },
    }

    localized = adapter.localize_response(response, "mr")

    assert localized["answer"] == response["answer"]
    assert localized["language_adapter"]["response_localization_applied"] is False


def test_chat_new_uses_verified_marathi_retrieval_path(monkeypatch):
    chat_id = "marathi-chat-route-test"
    chat = {"id": chat_id, "userId": "marathi-user", "messages": [], "lastActivity": None}
    monkeypatch.setitem(api._CHAT_SESSIONS, chat_id, chat)
    monkeypatch.setattr(api, "_serialize_chat_session", lambda *_args, **_kwargs: {"id": chat_id})
    calls = []

    def fake_ask(**kwargs):
        calls.append(kwargs)
        return {
            "answer": "Verified English evidence.",
            "verification_status": "VERIFIED",
            "retrieval_trace": {
                "match_found": True,
                "evidence_sources": [
                    {"path": "sanskrit/karma.md", "chapter": "Psychology", "excerpt": "Karma Yoga source."}
                ],
            },
        }

    monkeypatch.setattr(api.service, "ask", fake_ask)
    request = api.Request(
        scope={
            "type": "http",
            "method": "POST",
            "path": "/chat/new",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
            "scheme": "http",
        }
    )

    result = api.chat_new(
        {
            "message": "कर्मयोग म्हणजे काय?",
            "chatbotId": "test-guru",
            "userId": "marathi-user",
            "chatId": chat_id,
        },
        request,
    )

    assert calls[0]["user_query"] == "karma yoga what is?"
    assert "कर्मयोग म्हणजे" in result["aiResponse"]["content"]
    assert result["aiResponse"]["metadata"]["language_adapter"]["response_localization_applied"] is True


def test_new_rag_normalizes_marathi_queries(monkeypatch):
    monkeypatch.setenv("EXTERNAL_API_SECRET_KEY", "uniguru_secret_123")
    monkeypatch.setattr(
        api.service,
        "ask",
        lambda **kwargs: {
            "answer": "Verified.",
            "verification_status": "VERIFIED",
            "retrieval_trace": {
                "match_found": True,
                "evidence_sources": [
                    {"path": "sanskrit/dharma.md", "chapter": "Functional Meaning", "excerpt": "Dharma evidence."}
                ],
            },
        },
    )
    client = TestClient(api.app)

    response = client.post(
        "/new_rag",
        json={"query": "धर्म म्हणजे काय?", "caller": "marathi-user"},
        headers={"Authorization": "Bearer uniguru_secret_123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized_query"] == "dharma what is?"
    assert "धर्म म्हणजे" in payload["answer"]
    assert payload["verification_status"] == "VERIFIED"