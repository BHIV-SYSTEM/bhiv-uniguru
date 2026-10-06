from fastapi.testclient import TestClient

import pytest
from retrieval.retriever import get_rag_health
from service import api

app = api.app


@pytest.mark.skip(reason="FAISS index is not committed to the repository (.gitignore). Active pipeline is deterministic Kosha, not FAISS.")
def test_rag_health_reports_active_markdown_corpus_and_loaded_vector_index():
    health = get_rag_health()

    assert health["source_documents"] == 75
    assert health["lexical_documents_loaded"] == 75
    assert health["index"] == "loaded"
    assert health["indexed_chunks"] > 0
    assert health["metadata_available"] is True
    assert health["embedding_model"] == "all-MiniLM-L6-v2"
    assert health["embedding_dimension"] == 384
    assert health["index_type"] == "IndexIDMap2"
    assert health["metadata_chunk_count"] == health["indexed_chunks"]
    assert health["metadata_claimed_chunks"] == health["indexed_chunks"]
    assert health["status"] == "healthy"


def test_debug_retrieval_is_disabled_outside_explicit_development_mode(monkeypatch):
    monkeypatch.setenv("UNIGURU_ENV", "production")
    monkeypatch.setenv("UNIGURU_DEBUG_RETRIEVAL", "true")
    client = TestClient(app)

    response = client.post(
        "/debug/retrieval",
        json={"query": "What agricultural practices are mentioned in the Padma Purana?"},
    )

    assert response.status_code == 404


def test_debug_retrieval_exposes_candidate_stages_only_when_enabled(monkeypatch):
    monkeypatch.setenv("UNIGURU_ENV", "development")
    monkeypatch.setenv("UNIGURU_DEBUG_RETRIEVAL", "true")
    client = TestClient(app)

    response = client.post(
        "/debug/retrieval",
        json={"query": "What agricultural practices are mentioned in the Padma Purana?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized_query"].startswith("What agricultural practices")
    assert "padma" in payload["extracted_entities"]
    assert payload["dense_candidates"] == []
    assert payload["final_chunks"] == []


def test_ask_answers_from_relevant_kb_and_rejects_missing_source_topic_evidence():
    client = TestClient(app)
    context = {"caller": "rag-api-test"}
    session_id = "rag-api-test-session"

    dharma = client.post(
        "/ask",
        json={"query": "What is Dharma?", "context": context, "session_id": session_id},
    ).json()
    karma_yoga = client.post(
        "/ask",
        json={"query": "What is Karma Yoga?", "context": context, "session_id": session_id},
    ).json()
    unsupported_source = client.post(
        "/ask",
        json={
            "query": "What agricultural practices are mentioned in the Padma Purana?",
            "context": context,
            "session_id": session_id,
        },
    ).json()
    unsupported_after_answer = client.post(
        "/ask",
        json={
            "query": "Who won the FIFA World Cup in 2022?",
            "context": context,
            "session_id": session_id,
        },
    ).json()

    assert "Dharma" in dharma["answer"]
    assert "sanskrit/dharma.md" in dharma["answer"]
    assert "Karma yoga" in karma_yoga["answer"] or "Karma Yoga" in karma_yoga["answer"]
    assert "sanskrit/karma.md" in karma_yoga["answer"]
    # /ask follows the deterministic Kosha refusal contract.
    assert unsupported_source["verification_status"] == "NO_VERIFIED_KNOWLEDGE"
    assert "puranas.md" not in unsupported_source["answer"]
    assert unsupported_after_answer["verification_status"] == "NO_VERIFIED_KNOWLEDGE"
    assert "Maya" not in unsupported_after_answer["answer"]
    assert "I do not have verified knowledge" in unsupported_after_answer["answer"]


def test_ask_rejects_entity_matches_when_query_type_requires_another_domain():
    client = TestClient(app)
    headers = {"Authorization": "Bearer release-test-token"}
    context = {"caller": "rag-api-test"}

    for query in ("What is Dharma?", "What is the meaning of Dharma?"):
        response = client.post(
            "/ask",
            headers=headers,
            json={"query": query, "context": context, "session_id": "dharma-domain-regression"},
        )
        assert response.status_code == 200
        assert response.json()["verification_status"] == "VERIFIED"
        assert any(
            signal.get("knowledge_id") == "KOSHA_sanskrit_dharma"
            for signal in response.json()["matched_signals"]
        )

    for query in (
        "What is the current stock market price of Dharma?",
        "What is the weather in Dharma?",
        "What is the capital of Dharma?",
        "Who won the FIFA World Cup in 2022?",
    ):
        response = client.post(
            "/ask",
            headers=headers,
            json={"query": query, "context": context, "session_id": "dharma-domain-regression"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["verification_status"] == "NO_VERIFIED_KNOWLEDGE"
        assert payload["decision"] == "block"
        assert payload["confidence"] == 0.0
        assert payload["matched_signals"] == []
        assert payload["fallback_to_llm"] is False
        assert payload["routing"]["route"] == "DETERMINISTIC_KOSHA"
        assert payload["retrieval_trace"]["match_found"] is False


def test_chat_new_answers_india_prime_minister_with_source_evidence(monkeypatch):
    monkeypatch.setattr(api, "_DEMO_AUTH_ENABLED", True)
    monkeypatch.setattr(
        api,
        "_DEMO_AUTH_TOKENS",
        {"test-local-token": {"id": "india-history-user", "email": "india@example.test", "name": "India"}},
    )
    client = TestClient(app)
    response = client.post(
        "/chat/new",
        json={"message": "india prime minister", "chatbotId": "test-guru", "userId": "india-history-user"},
        headers={"Authorization": "Bearer test-local-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    answer = payload["aiResponse"]["content"]
    assert "Narendra Modi" in answer
    assert "9 June 2024" in answer
    assert "history/india_government_and_history.md" in answer
    assert payload["aiResponse"]["metadata"]["verification_status"] == "VERIFIED"


def test_new_rag_answers_greetings_without_running_kosha_retrieval(monkeypatch):
    monkeypatch.setenv("EXTERNAL_API_SECRET_KEY", "uniguru_secret_123")
    client = TestClient(app)

    response = client.post(
        "/new_rag",
        json={"query": "Hi"},
        headers={"Authorization": "Bearer uniguru_secret_123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "UniGuru" in payload["answer"]
    assert payload["kosha_attempted"] is False
    assert payload["signals"] == []


def test_new_rag_does_not_reuse_narada_vishnu_for_padma_agriculture(monkeypatch):
    monkeypatch.setenv("EXTERNAL_API_SECRET_KEY", "uniguru_secret_123")
    client = TestClient(app)

    response = client.post(
        "/new_rag",
        json={"query": "What agricultural practices are mentioned in the Padma Purana?"},
        headers={"Authorization": "Bearer uniguru_secret_123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "NO_VERIFIED_KNOWLEDGE"
    assert "Vishnu" not in payload["answer"]


def test_new_rag_uses_verified_hybrid_evidence_when_kosha_has_no_valid_signal(monkeypatch):
    monkeypatch.setenv("EXTERNAL_API_SECRET_KEY", "uniguru_secret_123")
    client = TestClient(app)

    response = client.post(
        "/new_rag",
        json={"query": "What is Karma Yoga?"},
        headers={"Authorization": "Bearer uniguru_secret_123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification_status"] == "VERIFIED"
    assert "karma yoga" in payload["answer"].casefold()
    assert any(signal["source"] == "sanskrit/karma.md" for signal in payload["signals"])
    assert payload["fallback_to_llm"] is False
