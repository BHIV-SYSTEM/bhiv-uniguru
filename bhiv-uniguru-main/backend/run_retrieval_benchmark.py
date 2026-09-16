from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR in sys.path:
    sys.path.remove(_BACKEND_DIR)
sys.path.insert(0, _BACKEND_DIR)

from kosha.kosha_loader import KoshaLoader
from kosha.kosha_retriever import KoshaRetriever
from retrieval.ontology_retriever import OntologyAwareRetriever
from ontology.entity_resolver import CanonicalEntityResolver


KOSHA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kosha")

BENCHMARK_QUERIES = [
    {"query": "What does the Bhagavad Gita teach about Karma Yoga?", "expected_domain": "gitas"},
    {"query": "Tell me about Vishnu in the Narada Purana", "expected_domain": "puranas"},
    {"query": "Explain the Upanishadic concept of Brahman", "expected_domain": "upanishads"},
    {"query": "Return Upanishads for Bhagavad Gita teachings", "expected_domain": "gitas", "must_reject_cross_domain": "upanishads"},
    {"query": "Give an Ahimsa answer from the Narada Purana", "expected_domain": "puranas", "must_reject_cross_domain": "dharma_systems"},
]


def _old_keyword_score(query: str, candidate: dict) -> float:
    query_terms = {term for term in query.lower().split() if len(term) > 2}
    candidate_terms = set(str(candidate.get("content", "")).lower().split())
    candidate_terms.update(str(tag).lower() for tag in candidate.get("tags", []))
    if not query_terms:
        return 0.0
    return round(len(query_terms & candidate_terms) / len(query_terms), 4)


def run_benchmark() -> dict:
    entries = KoshaLoader(data_sources=[KOSHA_DIR]).load_all()
    retriever = KoshaRetriever(entries)
    ontology = OntologyAwareRetriever()
    resolver = CanonicalEntityResolver()
    rows = []
    for case in BENCHMARK_QUERIES:
        query = case["query"]
        signals, detected_domain = retriever.retrieve(query)
        top = signals[0] if signals else {}
        old_score = _old_keyword_score(query, top) if top else 0.0
        new_score = ontology.score(query, top)["combined_score"] if top else 0.0
        top_domain_raw = str(top.get("domain") or "none")
        inferred = resolver.resolve_domain(
            " ".join([str(top.get("content") or ""), str(top.get("source") or ""), " ".join(top.get("tags") or [])])
        )
        top_domain = inferred["domain"] if inferred["domain"] != "general" else top_domain_raw
        expected_domain = case["expected_domain"]
        semantic_accuracy = top_domain == expected_domain
        rejection_correctness = True
        if case.get("must_reject_cross_domain"):
            rejection_correctness = top_domain != case["must_reject_cross_domain"]
        rows.append(
            {
                "query": query,
                "expected_domain": expected_domain,
                "detected_domain": detected_domain,
                "top_domain": top_domain,
                "top_domain_raw": top_domain_raw,
                "old_keyword_score": old_score,
                "new_ontology_score": new_score,
                "precision_hit": semantic_accuracy,
                "rejection_correct": rejection_correctness,
            }
        )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": {
            "precision": round(sum(1 for row in rows if row["precision_hit"]) / len(rows), 4),
            "rejection_correctness": round(sum(1 for row in rows if row["rejection_correct"]) / len(rows), 4),
            "semantic_accuracy": round(sum(1 for row in rows if row["precision_hit"]) / len(rows), 4),
        },
        "rows": rows,
    }
    out_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "review_packets", "proof_logs"))
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "retrieval_benchmark.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=True, sort_keys=True)
    return report


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2, ensure_ascii=True))
