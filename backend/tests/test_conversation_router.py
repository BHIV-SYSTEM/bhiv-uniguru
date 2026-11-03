from __future__ import annotations

import logging
import requests
from router import conversation_router as router_module
from router.conversation_router import ConversationRouter
from service.universal_orchestrator import UniversalOrchestrator


class StubOrchestrator:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def process_query(self, query, **kwargs):
        self.queries.append(query)
        return dict(self.result)


def patch_orchestrator(monkeypatch, result):
    stub = StubOrchestrator(result)
    monkeypatch.setattr("service.universal_orchestrator.get_universal_orchestrator", lambda: stub)
    return stub


def verified_result(answer="Karma Yoga is action without attachment."):
    return {"answer": answer, "category": "KNOWLEDGE_BASE", "verification_status": "VERIFIED", "citations": ["gita.txt"]}


def unverified_result(answer="I do not have verified knowledge to answer this question."):
    return {"answer": answer, "category": "KNOWLEDGE_BASE", "verification_status": "UNVERIFIED", "citations": []}


def test_greeting_and_identity_bypass_knowledge_retrieval(monkeypatch):
    service = patch_orchestrator(monkeypatch, verified_result())
    router = ConversationRouter()
    greeting = router.route_query("Hi", {"session_id": "s1", "caller": "user-a"})
    identity = router.route_query("What is your name?", {"session_id": "s1", "caller": "user-a"})
    assert greeting["answer"] == "Hello! How can I help you today?"
    assert "UniGuru" in identity["answer"]
    assert greeting["verification_status"] == "NOT_REQUIRED"
    assert greeting["source_type"] == "conversation"
    assert greeting["retrieved_evidence"] is False
    assert greeting["processing_diagnostics"]["generation"]["status"] == "not_run"
    assert service.queries == []


def test_introduction_name_is_retained_only_in_its_session_scope():
    router = ConversationRouter()
    user_a = {"session_id": "shared-test-id", "caller": "user-a"}
    user_b = {"session_id": "shared-test-id", "caller": "user-b"}
    introduction = router.route_query("My name is Vijay", user_a)
    followup = router.route_query("Can you help me with my question?", user_a)
    other_user = router.route_query("Can you help me with my question?", user_b)
    assert "Vijay" in introduction["answer"]
    assert "Vijay" in followup["answer"]
    assert "Vijay" not in other_user["answer"]


def test_knowledge_precedes_broad_direct_llm_rule_and_followup_uses_kb(monkeypatch):
    service = patch_orchestrator(monkeypatch, verified_result())
    router = ConversationRouter()
    context = {"session_id": "s2", "caller": "user-a"}
    assert router.classify("What is Karma Yoga?").value == "KNOWLEDGE_QUERY"
    router.route_query("What is Karma Yoga?", context)
    answer = router.route_query("Explain it simply.", context)
    assert "Karma Yoga" in service.queries[0]
    assert "Karma Yoga" in service.queries[-1]
    assert answer["routing"]["route"] == "ROUTE_UNIGURU"
    assert len(service.queries) == 2


def test_retrieval_diagnostics_and_logs_include_sources_and_scores(monkeypatch, caplog):
    result = verified_result()
    result["retrieval_trace"] = {
        "evidence_sources": [
            {"file": "gita.md", "source": "Gita", "reranker_score": 0.91, "retrieval_score": 0.024}
        ]
    }
    patch_orchestrator(monkeypatch, result)
    router = ConversationRouter()

    with caplog.at_level(logging.DEBUG, logger=router_module.__name__):
        response = router.route_query("What is Karma Yoga?")

    assert response["processing_diagnostics"]["retrieval"] == {
        "status": "success",
        "evidence_count": 1,
        "selected_sources": [{"source": "gita.md", "score": 0.91}],
    }
    assert "retrieval=success" in caplog.text
    assert "gita.md" in caplog.text
    assert "0.91" in caplog.text


def test_orchestrator_exposes_only_compact_retrieval_source_scores():
    class StubRagEngine:
        def answer_query(self, query):
            return {
                "verification_status": "VERIFIED",
                "answer": "Grounded answer.",
                "confidence": 0.9,
                "citations": ["Karma Yoga, page 1"],
                "sources_consulted": ["Gita"],
                "evidence": [
                    {
                        "file_name": "gita.md",
                        "source_name": "Gita",
                        "composite_score": 0.91,
                        "rrf_score": 0.024,
                        "text": "Private document excerpt that should not enter the trace.",
                    }
                ],
            }

    orchestrator = object.__new__(UniversalOrchestrator)
    orchestrator.rag_engine = StubRagEngine()

    result = orchestrator._execute_capability(
        query="What is Karma Yoga?",
        category="KNOWLEDGE_BASE",
        language="English",
        session=None,
    )

    assert result["retrieval_trace"]["evidence_sources"] == [
        {
            "file": "gita.md",
            "source": "Gita",
            "reranker_score": 0.91,
            "retrieval_score": 0.024,
        }
    ]
    assert "text" not in result["retrieval_trace"]["evidence_sources"][0]


def test_route_logs_provider_fallback_without_query_text(caplog):
    router = ConversationRouter()
    router._llm_url = ""

    with caplog.at_level(logging.DEBUG, logger=router_module.__name__):
        response = router.route_query("Write a Python program to test fallback logging.")

    assert response["provider_status"] == "unconfigured"
    assert "fallback=llm_unconfigured" in caplog.text
    assert "Write a Python program" not in caplog.text


def test_followup_without_session_topic_requests_clarification():
    router = ConversationRouter()
    answer = router.route_query("Explain it simply.", {"session_id": "s3", "caller": "user-a"})
    assert "what would you like me to explain" in answer["answer"].casefold()


def test_anonymous_shared_session_does_not_persist_personal_names():
    router = ConversationRouter()
    anonymous = {"session_id": "shared-anonymous-session", "caller": "anonymous-client"}
    router.route_query("My name is Vijay", anonymous)
    answer = router.route_query("Can you help me with my question?", anonymous)
    assert "Vijay" not in answer["answer"]


def test_verified_kb_response_does_not_open_latency_circuit(monkeypatch):
    service = patch_orchestrator(monkeypatch, verified_result())
    router = ConversationRouter(latency_threshold_ms=0.0001)
    context = {"session_id": "slow-verified-test", "caller": "user-a"}
    first = router.route_query("What is Karma Yoga?", context)
    second = router.route_query("What is Dharma?", context)
    assert first["verification_status"] == second["verification_status"] == "VERIFIED"
    assert service.queries == ["What is Karma Yoga?", "What is Dharma?"]
    assert not router._breaker.should_fallback()


def test_explicit_absent_from_kb_query_does_not_retrieve_unrelated_chunks(monkeypatch):
    service = patch_orchestrator(monkeypatch, verified_result())
    router = ConversationRouter()
    answer = router.route_query("Tell me something that is not present in the KB.")
    assert answer["verification_status"] == "UNVERIFIED"
    assert answer["answer"] == "I couldn't find sufficient information in the available documents."
    assert service.queries == []


def test_unverified_kb_uses_configured_provider_with_abstention_instruction(monkeypatch):
    patch_orchestrator(monkeypatch, unverified_result())
    router = ConversationRouter(allow_unverified_fallback=True)
    calls = []
    def generate(**kwargs):
        calls.append(kwargs)
        return {"answer": "I cannot verify that from the available knowledge base.", "reason": "test", "governance_reason": "test", "provider_status": "success"}
    router._request_llm = generate
    result = router.route_query("What is Karma Yoga?")
    assert result["routing"]["route"] == "ROUTE_LLM"
    assert calls[0]["verification_status"] == "UNVERIFIED"
    assert calls[0]["verified_context"] == ""
    assert result["verification_status"] == "NOT_REQUIRED"


def test_strict_source_request_does_not_fall_back_to_unverified_generation(monkeypatch):
    patch_orchestrator(monkeypatch, unverified_result())
    router = ConversationRouter(allow_unverified_fallback=True)
    calls = []
    router._request_llm = lambda **kwargs: calls.append(kwargs)
    result = router.route_query("What agricultural practices are mentioned in the Padma Purana?")
    assert result["routing"]["route"] == "ROUTE_UNIGURU"
    assert result["verification_status"] == "UNVERIFIED"
    assert calls == []


def test_no_provider_returns_truthful_unavailable_response():
    router = ConversationRouter()
    router._llm_url = ""
    result = router.route_query("Write a Python function to reverse a string.")
    assert result["decision"] == "block"
    assert result["provider_status"] == "unconfigured"
    assert result["source_type"] == "llm_unavailable"
    assert "no language-model provider is configured" in result["answer"]
    assert router.llm_status()["available"] is False


def test_configured_provider_receives_auth_verified_context_and_bounded_history(monkeypatch):
    router = ConversationRouter()
    router._llm_url = "https://llm.example/v1/chat/completions"
    router._llm_model = "test-model"
    router._llm_api_key = "test-secret"
    captured = {}
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": "Grounded answer."}}]}
    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()
    monkeypatch.setattr(router_module.requests, "post", post)
    history = [{"role": "user", "content": "Prior question"}, {"role": "assistant", "content": "Prior answer"}]
    result = router._request_llm("Current question", "s1", history=history, verified_context="Verified KB excerpt.", verification_status="VERIFIED")
    assert result["provider_status"] == "success"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    messages = captured["json"]["messages"]
    assert "VERIFIED RETRIEVED CONTEXT" in messages[0]["content"]
    assert "Verified KB excerpt." in messages[0]["content"]
    assert messages[1:] == [*history, {"role": "user", "content": "Current question"}]
    assert router.llm_status()["available"] is True


def test_route_passes_persisted_history_and_verified_context_to_provider(monkeypatch):
    patch_orchestrator(monkeypatch, verified_result("Retrieved verified fact."))
    router = ConversationRouter()
    router._llm_url = "https://llm.example/v1/chat/completions"
    router._llm_model = "test-model"
    captured = {}

    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": "Grounded response."}}]}

    def post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(router_module.requests, "post", post)
    result = router.route_query("What is Karma Yoga?", {
        "user_id": "u1", "session_id": "s1",
        "conversation_history": [
            {"sender": "user", "content": "Earlier question", "timestamp": "t1"},
            {"sender": "bot", "content": "Earlier answer", "timestamp": "t2"},
            {"sender": "user", "content": "What is Karma Yoga?", "timestamp": "t3"},
        ],
    })
    messages = captured["json"]["messages"]
    assert result["verification_status"] == "VERIFIED"
    assert "Retrieved verified fact." in messages[0]["content"]
    assert messages[1:3] == [
        {"role": "user", "content": "Earlier question"},
        {"role": "assistant", "content": "Earlier answer"},
    ]
    assert messages[-1] == {"role": "user", "content": "What is Karma Yoga?"}


def test_external_chat_history_excludes_current_message_and_is_bounded():
    router = ConversationRouter()
    history = [{"sender": "user", "content": f"old {i}", "timestamp": "now"} for i in range(10)]
    history += [{"sender": "user", "content": "Current question"}, {"sender": "bot", "content": "Prior response"}]
    bounded = router._history_for_query({"conversation_history": history}, {}, "Current question")
    assert len(bounded) == 6
    assert all(not (m["role"] == "user" and m["content"] == "Current question") for m in bounded)
    assert bounded[-1] == {"role": "assistant", "content": "Prior response"}


def test_provider_failure_is_not_replaced_by_canned_success(monkeypatch):
    router = ConversationRouter()
    router._llm_url = "https://llm.example/v1/chat/completions"
    router._llm_model = "test-model"
    monkeypatch.setattr(router_module.requests, "post", lambda *args, **kwargs: (_ for _ in ()).throw(requests.Timeout("timeout")))
    result = router.route_query("Write a Python function to reverse a string.")
    assert result["provider_status"] == "failed"
    assert result["decision"] == "block"
    assert "couldn't get a response" in result["answer"]
    assert result["answer"] != "I couldn't find sufficient information in the available documents."
    assert router.llm_status()["available"] is False


def test_empty_provider_response_is_failure_not_canned_answer(monkeypatch):
    router = ConversationRouter()
    router._llm_url = "https://llm.example/v1/chat/completions"
    router._llm_model = "test-model"
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": []}
    monkeypatch.setattr(router_module.requests, "post", lambda *args, **kwargs: Response())
    result = router._request_llm("What is Python?", None)
    assert result["provider_status"] == "failed"
    assert "empty response" in result["answer"]


def test_programming_requests_use_direct_route_and_language_specific_prompt(monkeypatch):
    router = ConversationRouter()
    router._llm_url = "http://llm.example/api/generate"
    router._llm_model = "test-model"
    query = "give me a program of even odd number in python"
    captured = []
    responses = [
        {"response": "Python is a high-level programming language."},
        {
            "response": (
                "Here is the program:\n\n```python\n"
                "number = int(input('Enter a number: '))\n"
                "print('Even number' if number % 2 == 0 else 'Odd number')\n"
                "```\n\nIt checks the remainder after division by two.\n\n"
                "Example output: `Odd number`"
            )
        },
    ]

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    def post(url, **kwargs):
        captured.append(kwargs["json"])
        return Response(responses.pop(0))

    monkeypatch.setattr(router_module.requests, "post", post)
    result = router.route_query(query)

    assert result["routing"]["query_type"] == "CODE_QUERY"
    assert result["routing"]["route"] == "ROUTE_LLM"
    assert result["source_type"] == "llm_code_generation"
    assert "```python" in result["answer"]
    assert len(captured) == 2
    assert "programming solution request" in captured[0]["system"]
    assert query in captured[0]["prompt"]
    assert captured[0]["query"] == query
    assert "did not include a fenced code block" in captured[1]["prompt"]
    assert result["processing_diagnostics"]["retrieval"]["status"] == "skipped"
    assert result["processing_diagnostics"]["interpretation"]["status"] == "success"
    assert result["processing_diagnostics"]["generation"]["status"] == "success"
    assert result["processing_diagnostics"]["confidence"]["answer_quality"] == {
        "status": "not_scored",
        "value": None,
    }


def test_programming_response_without_code_after_retry_is_rejected(monkeypatch):
    router = ConversationRouter()
    router._llm_url = "https://llm.example/v1/chat/completions"
    router._llm_model = "test-model"

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Python is a programming language."}}]}

    monkeypatch.setattr(router_module.requests, "post", lambda *args, **kwargs: Response())
    result = router.route_query("Write a Python program to check whether a number is prime.")

    assert result["provider_status"] == "invalid_response"
    assert result["decision"] == "block"
    assert "did not return the requested code format" in result["answer"]
    assert result["processing_diagnostics"]["generation"]["status"] == "invalid_response"


def test_programming_and_general_questions_skip_rag_but_textbook_questions_do_not():
    router = ConversationRouter()

    assert router.classify("give me a program of even odd number in python") == router_module.QueryRoutingType.CODE_QUERY
    assert router.classify("Write a Python program to check whether a number is prime.") == router_module.QueryRoutingType.CODE_QUERY
    assert router.classify("Explain Python loops with examples.") == router_module.QueryRoutingType.DIRECT_QUERY
    assert router.classify("How do I make a lasagna?") == router_module.QueryRoutingType.DIRECT_QUERY
    assert router.classify("What does Balbharati say about photosynthesis?") == router_module.QueryRoutingType.KNOWLEDGE_QUERY


def test_direct_followup_keeps_current_message_and_prior_turn_separate():
    router = ConversationRouter()
    captured = []

    def generate(**kwargs):
        captured.append(kwargs)
        return {
            "answer": "```python\nprint('updated')\n```",
            "reason": "test",
            "governance_reason": "test",
            "provider_status": "success",
        }

    router._request_llm = generate
    context = {"session_id": "code-followup", "user_id": "code-user"}
    router.route_query("Write a Python program to check whether a number is prime.", context)
    result = router.route_query("Explain it simply.", context)

    assert captured[-1]["query"] == "Explain it simply."
    assert captured[-1]["history"][-2:] == [
        {"role": "user", "content": "Write a Python program to check whether a number is prime."},
        {"role": "assistant", "content": "```python\nprint('updated')\n```"},
    ]
    assert result["routing"]["query_type"] == "CODE_QUERY"
