from backend.retrieval.retriever import synthesize_retrieval_answer
from backend.retrieval.kb_engine import SovereignRetriever


def test_synthesize_retrieval_answer_deduplicates_and_keeps_it_concise():
    query = "What is Brahman?"
    candidates = [
        {
            "content": "Brahman is the ultimate reality. In the Upanishads it is described as the supreme self.",
            "source": "upanishads.md",
        },
        {
            "content": "Brahman is the ultimate reality. In the Upanishads it is described as the supreme self.",
            "source": "upanishads_duplicate.md",
        },
        {
            "content": "The Upanishads teach that Brahman is eternal and unchanging.",
            "source": "vedic_texts.md",
        },
    ]

    answer = synthesize_retrieval_answer(query, candidates)

    assert answer
    assert "Brahman" in answer
    assert answer.count("Brahman is the ultimate reality") <= 1
    assert len(answer.split(". ")) <= 6


def test_topic_aware_scoring_prefers_direct_matches():
    engine = SovereignRetriever(index_path="backend/knowledge/index/master_index.json")
    candidates = [
        {
            "content": "This entry discusses Jain ethics and non-violence, not Ayurveda.",
            "metadata": {"source": "jain.md"},
        },
        {
            "content": "Charaka Samhita is a foundational Ayurvedic text.",
            "metadata": {"source": "charaka.md"},
        },
        {
            "content": "The Upanishads explain Brahman as the ultimate reality.",
            "metadata": {"source": "upanishads.md"},
        },
    ]

    scored = []
    for entry in candidates:
        scored.append({
            "entry": entry,
            "score": engine.score_document("Which text is related to Ayurveda?", "ayurveda", entry),
        })

    scored.sort(key=lambda item: item["score"], reverse=True)
    top = scored[0]["entry"]["content"]

    assert "Charaka Samhita" in top
    assert "Ayurvedic" in top


def test_out_of_domain_queries_return_no_relevant_match():
    engine = SovereignRetriever(index_path="backend/knowledge/index/master_index.json")
    result = engine.retrieve_with_candidates("How many days are there in a week?")

    assert result["verified"] is False
    assert "relevant" in result["answer"].lower() or "no relevant" in result["answer"].lower()
