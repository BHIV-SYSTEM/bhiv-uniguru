import re

import pytest
from starlette.requests import Request

from kosha.deterministic_pipeline import _KOSHA_DIR, run_deterministic_pipeline
from kosha.kosha_enforcer import KoshaEnforcer
from kosha.kosha_loader import KoshaLoader
from kosha.kosha_retriever import KoshaRetriever
from kosha.signal_validator import AnswerSynthesizer, SignalValidator
from memory.semantic_memory import SemanticMemoryStore


QUERIES = [
    "What is Brahman?",
    "Name any one Upanishad.",
    "Which text is related to Ayurveda?",
    "What is the purpose of the Puranas?",
    'Translate "अहिंसा परमो धर्मः"',
]

EXPECTED_RETRIEVED_IDS = {
    QUERIES[0]: ["KOSHA_da8756d0729f", "KOSHA_0ee0e39422ee", "KOSHA_9a8183e951a4"],
    QUERIES[1]: ["KOSHA_9a8183e951a4", "KOSHA_0ee0e39422ee", "KOSHA_da8756d0729f"],
    QUERIES[2]: ["KOSHA_b4aaddfc7d6a", "KOSHA_af7f56640546", "KOSHA_941a6dd7c900"],
    QUERIES[3]: ["KOSHA_15ea4d9ceaf4", "KOSHA_941a6dd7c900", "KOSHA_b4aaddfc7d6a"],
    QUERIES[4]: ["KOSHA_15ea4d9ceaf4", "KOSHA_9e0093dbdf4f", "KOSHA_bf72b8578590"],
}

EXPECTED_ACCEPTED_IDS = {
    QUERIES[0]: {"KOSHA_0ee0e39422ee", "KOSHA_9a8183e951a4", "KOSHA_da8756d0729f"},
    QUERIES[1]: {"KOSHA_9a8183e951a4"},
    QUERIES[2]: {"KOSHA_b4aaddfc7d6a", "KOSHA_bf72b8578590", "KOSHA_c99f33b95d6f"},
    QUERIES[3]: set(),
    QUERIES[4]: {"KOSHA_15ea4d9ceaf4"},
}


def _load_valid_entries():
    raw_entries = KoshaLoader(data_sources=[str(_KOSHA_DIR)]).load_all()
    return KoshaEnforcer.validate_existing_entries(raw_entries)["valid_entries"]


def _run_readonly_pipeline(monkeypatch, query, trace_id):
    monkeypatch.setattr("kosha.deterministic_pipeline._write_proof_log", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        SemanticMemoryStore,
        "update_from_pipeline",
        lambda _self, **kwargs: {"event": {"trace_id": kwargs.get("trace_id")}},
    )
    return run_deterministic_pipeline(query=query, trace_id=trace_id, user_id="kosha-synthesis-test")


def _used_ids(reasoning):
    return re.findall(r"KOSHA_[a-f0-9]{12}", reasoning or "")


def _sentences(text):
    return [part.strip() for part in re.split(r"(?<=[.!?\u0964\u0965])\s+", text or "") if part.strip()]


def _clean_record(content):
    text = re.sub(r"\[\d+\]", "", content or "")
    return re.sub(r"\s+([.!?])", r"\1", re.sub(r"\s+", " ", text)).strip()


def _assert_answer_is_grounded(answer, signals):
    cleaned_records = [_clean_record(signal.get("content", "")).casefold() for signal in signals]
    for sentence in _sentences(answer):
        normalized = _clean_record(sentence).casefold()
        assert normalized
        assert any(normalized in record for record in cleaned_records), sentence


@pytest.fixture(scope="module")
def valid_entries():
    return _load_valid_entries()


@pytest.mark.parametrize("query", QUERIES)
def test_real_kosha_pipeline_retrieval_and_synthesis(query, valid_entries, monkeypatch):
    raw_signals, _ = KoshaRetriever(valid_entries).retrieve(query)
    validation = SignalValidator.validate_all(raw_signals, query)
    payload = _run_readonly_pipeline(monkeypatch, query, f"synthesis-{QUERIES.index(query)}")
    answer = payload["answer"]
    actually_used_ids = _used_ids(payload.get("reasoning"))
    retrieved_ids = [signal.get("trace", {}).get("knowledge_id") for signal in raw_signals]
    accepted_ids = {
        signal.get("trace", {}).get("knowledge_id")
        for signal in validation["accepted_signals"]
    }
    accepted_by_id = {
        signal.get("trace", {}).get("knowledge_id"): signal
        for signal in validation["accepted_signals"]
    }

    assert payload["retrieval_truth_payload"]["raw_signal_count"] == len(raw_signals)
    assert set(payload["retrieval_truth_payload"]["accepted_signal_ids"]) == {
        signal.get("signal_id") for signal in validation["accepted_signals"]
    }
    assert payload["confidence_breakdown"]["accepted_count"] == len(validation["accepted_signals"])
    assert retrieved_ids[:3] == EXPECTED_RETRIEVED_IDS[query]
    assert accepted_ids == EXPECTED_ACCEPTED_IDS[query]
    assert len(actually_used_ids) == len(set(actually_used_ids))
    assert all(knowledge_id in accepted_by_id for knowledge_id in actually_used_ids)
    assert len(actually_used_ids) == _signals_used_from_reasoning(payload.get("reasoning"))

    if actually_used_ids:
        used_signals = [accepted_by_id[knowledge_id] for knowledge_id in actually_used_ids]
        _assert_answer_is_grounded(answer, used_signals)
        assert answer != "I do not have verified knowledge to answer this question."
        assert not re.search(r"\[\d+\]|\.\.\.\s*\[truncated\]", answer, re.IGNORECASE)
        assert len({" ".join(sentence.casefold().split()) for sentence in _sentences(answer)}) == len(_sentences(answer))
    else:
        assert answer == "I do not have verified knowledge to answer this question."
        assert payload["verification_status"] == "NO_VERIFIED_KNOWLEDGE"

    if query == QUERIES[0]:
        assert len(raw_signals) == 12
        assert len(validation["accepted_signals"]) == 3
        assert len(actually_used_ids) >= 2
        assert "Brahman" in answer
    elif query == QUERIES[1]:
        assert len(validation["accepted_signals"]) == 1
        assert len(actually_used_ids) == 1
        assert "Taittiriya Upanishad" in answer
    elif query == QUERIES[2]:
        assert validation["accepted_signals"]
        assert actually_used_ids == []
        assert "Padma Purana" not in answer
    elif query == QUERIES[3]:
        assert validation["accepted_signals"] == []
        assert actually_used_ids == []
    elif query == QUERIES[4]:
        assert len(validation["accepted_signals"]) == 1
        assert actually_used_ids == []
        assert "Satyam vada" not in answer


def _signals_used_from_reasoning(reasoning):
    match = re.search(r"Answer uses (\d+) accepted evidence record", reasoning or "")
    return int(match.group(1)) if match else 0


def _accepted_signal(signal_id, knowledge_id, source, content):
    return {
        "signal_id": signal_id,
        "source": source,
        "content": content,
        "confidence": 0.8,
        "trace": {"knowledge_id": knowledge_id},
        "_validation": {},
    }


def test_synthesis_uses_multiple_relevant_records_and_deduplicates_sentences():
    repeated = "Brahman is the ultimate reality."
    accepted = [
        _accepted_signal("sig-a", "KOSHA_aaaaaaaaaaaa", "source-a.pdf", f"{repeated} Brahman is described in the first source."),
        _accepted_signal("sig-b", "KOSHA_bbbbbbbbbbbb", "source-b.pdf", f"{repeated} Brahman is described in the second source."),
        _accepted_signal("sig-c", "KOSHA_cccccccccccc", "irrelevant.pdf", "Ayurveda describes medicine and health."),
    ]

    synthesis = AnswerSynthesizer.synthesize(
        query="What is Brahman?",
        validation_result={"accepted_signals": accepted, "rejected_signals": []},
    )

    assert synthesis["signals_used"] == 2
    assert synthesis["evidence_signal_ids"] == ["sig-a", "sig-b"]
    assert synthesis["answer"].count(repeated) == 1
    assert "first source" in synthesis["answer"]
    assert "second source" in synthesis["answer"]
    assert "Ayurveda" not in synthesis["answer"]


def test_explicit_purana_query_requires_matching_source_and_agriculture_evidence(valid_entries):
    query = "What agricultural practices are mentioned in the Padma Purana?"

    signals, _domain = KoshaRetriever(valid_entries).retrieve(query)
    validation = SignalValidator.validate_all(signals, query)

    assert signals == []
    assert validation["accepted_signals"] == []


def test_validator_rejects_wrong_purana_source_even_when_content_mentions_padma():
    signal = {
        "signal_id": "wrong-purana-source",
        "source": "The Narada-Purana, Part 4_ocred.pdf",
        "content": "The main deity praised in the Padma Purana is Vishnu.",
        "tags": ["padma", "purana", "vishnu"],
        "confidence": 0.8,
    }

    valid, reason, details = SignalValidator.validate_signal(
        signal,
        "What agricultural practices are mentioned in the Padma Purana?",
    )

    assert not valid
    assert reason == "source_entity_mismatch"
    assert "padma" in details["missing_source_entities"]


def test_validator_rejects_correct_source_without_requested_topic():
    signal = {
        "signal_id": "missing-topic",
        "source": "Padma Purana, Part 4_ocred.pdf",
        "content": "The main deity praised in the Padma Purana is Vishnu.",
        "tags": ["padma", "purana", "vishnu"],
        "confidence": 0.8,
    }

    valid, reason, _details = SignalValidator.validate_signal(
        signal,
        "What agricultural practices are mentioned in the Padma Purana?",
    )

    assert not valid
    assert reason == "no_topic_evidence_for_named_source"


def test_one_relevant_record_is_used_without_unrelated_accepted_record():
    accepted = [
        _accepted_signal(
            "sig-upanishad",
            "KOSHA_aaaaaaaaaaaa",
            "taittiriya.pdf",
            "The Taittiriya Upanishad is one of the principal Upanishads.",
        ),
        _accepted_signal(
            "sig-unrelated",
            "KOSHA_bbbbbbbbbbbb",
            "ayurveda.pdf",
            "Ayurveda describes medicine and health.",
        ),
    ]

    synthesis = AnswerSynthesizer.synthesize(
        query="Name any one Upanishad.",
        validation_result={"accepted_signals": accepted, "rejected_signals": []},
    )

    assert synthesis["signals_used"] == 1
    assert synthesis["evidence_signal_ids"] == ["sig-upanishad"]
    assert "Taittiriya Upanishad" in synthesis["answer"]
    assert "Ayurveda" not in synthesis["answer"]


def test_accepted_records_without_relevant_evidence_keep_existing_refusal():
    accepted = [
        _accepted_signal(
            "sig-satyam",
            "KOSHA_aaaaaaaaaaaa",
            "narada.pdf",
            'Satyam vada translates to "Speak the truth".',
        )
    ]

    synthesis = AnswerSynthesizer.synthesize(
        query='Translate "अहिंसा परमो धर्मः"',
        validation_result={"accepted_signals": accepted, "rejected_signals": []},
    )

    assert synthesis["answer"] == "I do not have verified knowledge to answer this question."
    assert synthesis["verification_status"] == "NO_VERIFIED_KNOWLEDGE"
    assert synthesis["signals_used"] == 0
    assert synthesis["evidence_signal_ids"] == []


def test_chat_new_uses_shared_verified_rag_service(monkeypatch):
    from service import api

    chat_id = "kosha-pipeline-route-test"
    chat = {"id": chat_id, "userId": "test-user", "messages": [], "lastActivity": None}
    monkeypatch.setitem(api._CHAT_SESSIONS, chat_id, chat)
    monkeypatch.setattr(api, "_serialize_chat_session", lambda *_args, **_kwargs: {"id": chat_id})
    calls = []

    def fake_ask(**kwargs):
        calls.append(kwargs)
        return {
            "answer": "verified shared RAG response",
            "verification_status": "VERIFIED",
            "retrieval_trace": {"match_found": True},
        }

    monkeypatch.setattr(api.service, "ask", fake_ask)
    monkeypatch.setattr(
        api,
        "_execute_kosha_pipeline",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("chat must not use Kosha-only retrieval")),
    )
    request = Request(
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

    response = api.chat_new(
        {"message": "What is Brahman?", "chatbotId": "test-guru", "userId": "test-user", "chatId": chat_id},
        request,
    )

    assert response["aiResponse"]["content"] == "verified shared RAG response"
    assert calls == [{
        "user_query": "What is Brahman?",
        "session_id": chat_id,
        "context": {"caller": "test-user", "source_language": "en"},
        "allow_web_retrieval": False,
    }]
