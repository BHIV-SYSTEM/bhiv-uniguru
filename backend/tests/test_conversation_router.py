from router.conversation_router import ConversationRouter


class StubKnowledgeService:
    def __init__(self):
        self.queries = []

    def ask(self, user_query, **kwargs):
        self.queries.append(user_query)
        return {
            "answer": "Karma Yoga is the path of action without attachment to its fruits.",
            "verification_status": "VERIFIED",
        }


def test_greeting_and_identity_bypass_knowledge_retrieval():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service)

    greeting = router.route_query("Hi", {"session_id": "s1", "caller": "user-a"})
    identity = router.route_query("What is your name?", {"session_id": "s1", "caller": "user-a"})

    assert "UniGuru" in greeting["answer"]
    assert "UniGuru" in identity["answer"]
    assert greeting["verification_status"] == "NOT_REQUIRED"
    assert greeting["source_type"] == "conversation"
    assert greeting["retrieved_evidence"] is False
    assert service.queries == []


def test_introduction_name_is_retained_only_in_its_session_scope():
    router = ConversationRouter(uniguru_service=StubKnowledgeService())
    user_a = {"session_id": "shared-test-id", "caller": "user-a"}
    user_b = {"session_id": "shared-test-id", "caller": "user-b"}

    introduction = router.route_query("My name is Vijay", user_a)
    followup = router.route_query("Can you help me with my question?", user_a)
    other_user = router.route_query("Can you help me with my question?", user_b)

    assert "Vijay" in introduction["answer"]
    assert "Vijay" in followup["answer"]
    assert "Vijay" not in other_user["answer"]


def test_followup_reuses_previous_knowledge_topic():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service)
    context = {"session_id": "s2", "caller": "user-a"}

    router.route_query("What is Karma Yoga?", context)
    answer = router.route_query("Explain it simply.", context)

    assert "Karma Yoga" in service.queries[-1]
    assert "Karma Yoga" in answer["answer"]
    assert len(service.queries) == 2


def test_followup_without_session_topic_requests_clarification():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service)

    answer = router.route_query("Explain it simply.", {"session_id": "s3", "caller": "user-a"})

    assert "what would you like me to explain" in answer["answer"].casefold()
    assert service.queries == []


def test_anonymous_shared_session_does_not_persist_personal_names():
    router = ConversationRouter(uniguru_service=StubKnowledgeService())
    anonymous = {"session_id": "shared-anonymous-session", "caller": "anonymous-client"}

    router.route_query("My name is Vijay", anonymous)
    answer = router.route_query("Can you help me with my question?", anonymous)

    assert "Vijay" not in answer["answer"]


def test_slow_verified_kb_response_does_not_open_latency_circuit():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service, latency_threshold_ms=0.0001)
    context = {"session_id": "slow-verified-test", "caller": "user-a"}

    first = router.route_query("What is Karma Yoga?", context)
    second = router.route_query("What is Dharma?", context)

    assert first["verification_status"] == "VERIFIED"
    assert second["verification_status"] == "VERIFIED"
    assert service.queries == ["What is Karma Yoga?", "What is Dharma?"]
    assert not router._breaker.should_fallback()


def test_unrelated_sentence_with_that_is_not_treated_as_a_followup():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service)
    context = {"session_id": "unsupported-after-kb", "caller": "user-a"}
    query = "Tell me something that is not present in the KB."

    router.route_query("What is Karma Yoga?", context)
    answer = router.route_query(query, context)

    assert answer["verification_status"] == "UNVERIFIED"
    assert "explicitly absent" in answer["answer"]
    assert service.queries == ["What is Karma Yoga?"]


def test_general_knowledge_query_falls_back_to_llm_when_kb_has_no_answer():
    class UnverifiedKnowledgeService:
        def ask(self, user_query, **kwargs):
            return {
                "answer": "I do not have verified knowledge to answer this question.",
                "verification_status": "UNVERIFIED",
            }

    router = ConversationRouter(
        uniguru_service=UnverifiedKnowledgeService(),
        allow_unverified_fallback=True,
    )
    router._request_llm = lambda query, session_id: {
        "answer": "Python is a general-purpose programming language.",
        "reason": "test LLM response",
        "governance_reason": "test fallback",
    }

    answer = router.route_query("What is Python?")

    assert answer["routing"]["route"] == "ROUTE_LLM"
    assert "general knowledge" in answer["answer"]
    assert "Python is a general-purpose programming language." in answer["answer"]
    assert answer["source_type"] == "llm_general_knowledge"
    assert answer["verification_status"] == "NOT_REQUIRED"
    assert answer["retrieval_performed"] is True
    assert answer["retrieved_evidence"] is False


def test_explicit_source_request_keeps_verification_gate():
    class UnverifiedKnowledgeService:
        def ask(self, user_query, **kwargs):
            return {
                "answer": "I do not have verified knowledge to answer this question.",
                "verification_status": "UNVERIFIED",
            }

    router = ConversationRouter(uniguru_service=UnverifiedKnowledgeService())
    router._request_llm = lambda query, session_id: {
        "answer": "This should not be used for source-scoped requests.",
        "reason": "test LLM response",
        "governance_reason": "test fallback",
    }

    answer = router.route_query("What agricultural practices are mentioned in the Padma Purana?")

    assert answer["routing"]["route"] == "ROUTE_UNIGURU"
    assert "verified knowledge" in answer["answer"]
    assert answer["verification_status"] == "UNVERIFIED"
    assert answer["source_type"] == "rag"


def test_math_and_coding_queries_use_direct_llm_route():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service)

    math_answer = router.route_query("What is 2 + 2?")
    coding_answer = router.route_query("Write a Python function to reverse a string.")

    assert math_answer["routing"]["route"] == "ROUTE_LLM"
    assert math_answer["answer"] == "4"
    assert "def reverse_string" in coding_answer["answer"]
    assert coding_answer["source_type"] == "llm_general_knowledge"
    assert service.queries == []


def test_general_knowledge_demo_answers_cover_common_queries():
    examples = {
        "What is Python?": "high-level",
        "What is machine learning?": "patterns from data",
        "What is NLP?": "Natural language processing",
        "Explain gravity": "mass",
        "Who was Mahavira?": "Tirthankara",
    }

    for query, expected in examples.items():
        answer = ConversationRouter._build_local_demo_answer(query)
        assert expected.casefold() in answer.casefold()


def test_explicit_absent_from_kb_query_does_not_retrieve_unrelated_chunks():
    service = StubKnowledgeService()
    router = ConversationRouter(uniguru_service=service)

    answer = router.route_query("Tell me something that is not present in the KB.")

    assert answer["verification_status"] == "UNVERIFIED"
    assert "explicitly absent" in answer["answer"]
    assert service.queries == []