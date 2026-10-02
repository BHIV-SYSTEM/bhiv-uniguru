"""Curriculum Retrieval Evaluation Benchmark: Hit Rate@K, Recall@K, and MRR."""

import pytest
from backend.retrieval.balbharati.hybrid_retriever import get_balbharati_retriever


BENCHMARK_QUERIES = [
    {
        "query": "Explain photosynthesis in plants from Class 7 Science textbook",
        "expected_standard": 7,
        "expected_subject": "Science",
        "required_terms": ["photosynthesis", "plants", "chlorophyll", "food", "energy"],
    },
    {
        "query": "Characteristics of living things and cellular structure in Class 6 Science",
        "expected_standard": 6,
        "expected_subject": "Science",
        "required_terms": ["living", "growth", "respiration", "cell"],
    },
    {
        "query": "Newton laws of motion and force in Class 8 Science textbook",
        "expected_standard": 8,
        "expected_subject": "Science",
        "required_terms": ["motion", "force", "inertia", "action"],
    },
    {
        "query": "इयत्ता ७ विज्ञानातील प्रकाशसंश्लेषण आणि वनस्पतींमधील पोषण",
        "expected_standard": 7,
        "expected_subject": "Science",
        "required_terms": ["photosynthesis", "plants", "nutrition", "chlorophyll"],
    },
    {
        "query": "Geometric angles acute right obtuse in Class 5 Mathematics",
        "expected_standard": 5,
        "expected_subject": "Mathematics",
        "required_terms": ["angle", "degree", "geometry", "right", "acute"],
    },
    {
        "query": "Medieval Indian history and Shivaji Maharaj administration in Class 7 History",
        "expected_standard": 7,
        "expected_subject": "History",
        "required_terms": ["shivaji", "administration", "maratha", "swarajya", "history"],
    },
]


def test_balbharati_retrieval_benchmark_metrics():
    retriever = get_balbharati_retriever()
    k = 3
    hits = 0
    reciprocal_ranks = []

    for item in BENCHMARK_QUERIES:
        query = item["query"]
        expected_std = item["expected_standard"]
        expected_subj = item["expected_subject"]

        response = retriever.search_hybrid(query, top_k=k)
        results = response.get("results", [])

        hit = False
        rr = 0.0

        for rank, res in enumerate(results, start=1):
            doc_std = res.get("standard")
            doc_subj = str(res.get("subject") or "").lower()
            doc_text = str(res.get("text") or "").lower()

            # Relevance criteria: matches standard, subject, and at least one concept term
            is_std_match = doc_std == expected_std
            is_subj_match = expected_subj.lower() in doc_subj or doc_subj in expected_subj.lower()
            has_term = any(term in doc_text for term in item["required_terms"])

            if is_std_match and is_subj_match and has_term:
                hit = True
                rr = 1.0 / rank
                break

        if hit:
            hits += 1
        reciprocal_ranks.append(rr)

    total = len(BENCHMARK_QUERIES)
    hit_rate = hits / total
    mrr = sum(reciprocal_ranks) / total

    print(f"\n[Retrieval Benchmark] Total: {total} | Hits@{k}: {hits} | Hit Rate@{k}: {hit_rate:.2%} | MRR: {mrr:.4f}")

    # Benchmark assertions: high fidelity retrieval across classes & subjects
    assert hit_rate >= 0.80, f"Hit Rate@{k} of {hit_rate:.2%} is below required 80%"
    assert mrr >= 0.70, f"MRR of {mrr:.4f} is below target 0.70"
