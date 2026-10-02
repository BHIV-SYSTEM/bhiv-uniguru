from kosha.signal_validator import AnswerSynthesizer


def test_direct_definition_outranks_related_sentence_for_canonical_entity():
    signals = [{
        "content": (
            "Atman is the individual self or soul. "
            "Brahman is the ultimate reality. Atman is identical with Brahman."
        ),
        "confidence": 0.9,
        "source": "test",
    }]
    result = AnswerSynthesizer.synthesize(
        "What is Brahman?",
        {"accepted_signals": signals, "rejected_signals": []},
    )
    assert result["answer"] == "Brahman is the ultimate reality."


def test_related_mention_without_definition_is_insufficient_evidence():
    signals = [{
        "content": "The yugas show an increase in adharma and a decline in dharma.",
        "confidence": 0.9,
        "source": "test",
    }]
    result = AnswerSynthesizer.synthesize(
        "What is Dharma?",
        {"accepted_signals": signals, "rejected_signals": []},
    )
    assert result["verification_status"] == "NO_VERIFIED_KNOWLEDGE"


def test_entity_normalization_handles_diacritics_possessives_and_plural_forms():
    from kosha.signal_validator import SignalValidator

    assert "rta" in SignalValidator.tokenize("Ṛta")
    assert "shakti" in SignalValidator.tokenize("Śaktis")
    assert "grover" in SignalValidator.tokenize("Grover's algorithm")
    assert "algorithm" in SignalValidator.tokenize("Grover's algorithms")


def test_definition_query_keeps_only_sentences_defining_the_requested_concept():
    selected = AnswerSynthesizer._relevant_sentences(
        "What is Addition?",
        "It is the inverse of addition. Number recognition forms the basis for addition. "
        "Addition is the operation of combining numbers to find their sum.",
    )
    assert selected == ["Addition is the operation of combining numbers to find their sum."]


def test_definition_with_parenthetical_name_is_direct_evidence():
    selected = AnswerSynthesizer._relevant_sentences(
        "What is Om?",
        "Om (also written as Aum) is the sacred primordial sound.",
    )
    assert selected == ["Om (also written as Aum) is the sacred primordial sound."]


def test_direct_entity_definition_beats_related_entity_sentence():
    selected = AnswerSynthesizer._relevant_sentences(
        "What is Dharma?",
        "The Bhagavad Gita is an important source on Dharma. Dharma is that which upholds order and duty.",
    )
    assert selected == ["Dharma is that which upholds order and duty."]


def test_exact_topic_source_precedes_generic_high_authority_source():
    from kosha.kosha_retriever import KoshaRetriever
    from kosha.kosha_validator import KoshaEntry

    def entry(knowledge_id, content, source, tags):
        return KoshaEntry(
            knowledge_id=knowledge_id,
            domain="upanishads",
            content=content,
            source=source,
            confidence=0.9,
            timestamp="2026-01-01T00:00:00Z",
            tags=tags,
        )

    entries = [
        entry("generic", "Brahman is mentioned in this scripture's discussion of many topics.", "Upanishad", ["scripture"]),
        entry("KOSHA_sanskrit_brahman", "Brahman is the ultimate reality.", "Curated knowledge note", ["Brahman"]),
    ]
    signals, _ = KoshaRetriever(entries).retrieve("What is Brahman?")
    assert signals[0]["trace"]["knowledge_id"] == "KOSHA_sanskrit_brahman"


def test_living_nonliving_query_cannot_select_brahman_evidence():
    from kosha.signal_validator import NO_KNOWLEDGE_RESPONSE

    result = AnswerSynthesizer.synthesize(
        "What are Living and Non-Living things?",
        {"accepted_signals": [{
            "content": "Brahman is the supreme reality. It is the ground of all existence.",
            "confidence": 0.9,
            "source": "unrelated",
        }], "rejected_signals": []},
    )
    assert result["answer"] == NO_KNOWLEDGE_RESPONSE
    assert result["verification_status"] == "NO_VERIFIED_KNOWLEDGE"


def test_authoritative_sanskrit_markdown_is_routed_into_kosha():
    from kosha.deterministic_pipeline import _KOSHA_DIR, _SANSKRIT_KNOWLEDGE_DIR
    from kosha.kosha_loader import KoshaLoader
    from kosha.kosha_enforcer import KoshaEnforcer
    from kosha.kosha_retriever import KoshaRetriever

    entries = KoshaEnforcer.validate_existing_entries(
        KoshaLoader([str(_KOSHA_DIR), str(_SANSKRIT_KNOWLEDGE_DIR)]).load_all()
    )["valid_entries"]
    for concept in ("Karma", "Shakti", "Prana", "Atman", "Yoga", "Om", "Maya"):
        signals, _ = KoshaRetriever(entries).retrieve(f"What is {concept}?")
        assert any(
            signal["trace"]["knowledge_id"] == f"KOSHA_sanskrit_{concept.casefold()}"
            for signal in signals
        ), concept


def test_kosha_retriever_does_not_construct_embedding_provider():
    from unittest.mock import patch
    from kosha.kosha_retriever import KoshaRetriever
    from retrieval.embedding_provider import LocalHashEmbeddingProvider

    with patch.object(LocalHashEmbeddingProvider, "__init__", side_effect=AssertionError("embedding used")):
        retriever = KoshaRetriever([])
        assert retriever.retrieve("What is Atman?")[0] == []

