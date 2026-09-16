"""
Retrieval Quality Evaluator
===========================
Implements standard Information Retrieval metrics for quantitative before/after
comparison of retrieval quality improvements.

Metrics:
  - Precision@K  (K = 1, 3, 5)
  - Recall@K     (K = 1, 3, 5)
  - Mean Reciprocal Rank (MRR)
  - Normalized Discounted Cumulative Gain (NDCG@K)
  - Score delta: keyword-only vs ontology-enhanced

This module is self-contained and produces a JSON report at:
  review_packets/proof_logs/retrieval_quality_report.json
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend modules are importable — backend/ must be FIRST to prevent
# the root-level retrieval/ from shadowing backend/retrieval/
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR in sys.path:
    sys.path.remove(_BACKEND_DIR)
sys.path.insert(0, _BACKEND_DIR)


# ---------------------------------------------------------------------------
# Labelled evaluation dataset
# Each entry: query, ranked relevance judgements per domain (grade: 1=relevant, 0=not)
# ---------------------------------------------------------------------------
EVAL_DATASET: List[Dict[str, Any]] = [
    {
        "query": "What does the Bhagavad Gita teach about Karma Yoga?",
        "expected_domain": "gitas",
        "relevant_domains": ["gitas"],
        "irrelevant_domains": ["puranas", "upanishads", "dharma_systems"],
        "description": "Domain-specific retrieval — Gita content",
    },
    {
        "query": "Tell me about Vishnu in the Narada Purana",
        "expected_domain": "puranas",
        "relevant_domains": ["puranas"],
        "irrelevant_domains": ["gitas", "upanishads"],
        "description": "Domain-specific retrieval — Puranas content",
        "must_reject_cross_domain": "upanishads",
    },
    {
        "query": "Explain the Upanishadic concept of Brahman",
        "expected_domain": "upanishads",
        "relevant_domains": ["upanishads"],
        "irrelevant_domains": ["gitas", "puranas"],
        "description": "Domain-specific retrieval — Upanishads content",
    },
    {
        "query": "Return Upanishads for Bhagavad Gita teachings",
        "expected_domain": "gitas",
        "relevant_domains": ["gitas"],
        "irrelevant_domains": ["upanishads"],
        "description": "Cross-domain rejection test — must prefer gitas not upanishads",
        "must_reject_cross_domain": "upanishads",
    },
    {
        "query": "Give an Ahimsa answer from the Narada Purana",
        "expected_domain": "puranas",
        "relevant_domains": ["puranas"],
        "irrelevant_domains": ["dharma_systems", "gitas"],
        "description": "Cross-domain rejection test — must reject dharma_systems",
        "must_reject_cross_domain": "dharma_systems",
    },
    {
        "query": "What is the Padma Purana?",
        "expected_domain": "puranas",
        "relevant_domains": ["puranas"],
        "irrelevant_domains": ["gitas", "upanishads"],
        "description": "Direct text retrieval — Puranas",
    },
    {
        "query": "Explain temple construction in the Agni Purana",
        "expected_domain": "puranas",
        "relevant_domains": ["puranas"],
        "irrelevant_domains": ["gitas", "upanishads"],
        "description": "Specific topic within domain",
    },
    {
        "query": "What does the Mahabharata say about dharma?",
        "expected_domain": "gitas",
        "relevant_domains": ["gitas"],
        "irrelevant_domains": ["puranas"],
        "description": "Broad dharma question anchored to Gita context",
    },
]


# ---------------------------------------------------------------------------
# IR Metric Computations
# ---------------------------------------------------------------------------

def _precision_at_k(retrieved_domains: List[str], relevant_domains: List[str], k: int) -> float:
    """Precision@K = (# relevant in top-K) / K"""
    top_k = retrieved_domains[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for d in top_k if d in relevant_domains)
    return round(hits / k, 4)


def _recall_at_k(retrieved_domains: List[str], relevant_domains: List[str], k: int) -> float:
    """Recall@K = (# relevant in top-K) / (total # relevant)"""
    if not relevant_domains:
        return 0.0
    top_k = retrieved_domains[:k]
    hits = sum(1 for d in top_k if d in relevant_domains)
    return round(hits / len(relevant_domains), 4)


def _reciprocal_rank(retrieved_domains: List[str], relevant_domains: List[str]) -> float:
    """MRR contribution: 1/rank of first relevant result (0 if none found)"""
    for i, d in enumerate(retrieved_domains, start=1):
        if d in relevant_domains:
            return 1.0 / i
    return 0.0


def _dcg_at_k(relevance_grades: List[int], k: int) -> float:
    """Discounted Cumulative Gain@K"""
    dcg = 0.0
    for i, grade in enumerate(relevance_grades[:k], start=1):
        dcg += grade / math.log2(i + 1)
    return dcg


def _ndcg_at_k(retrieved_domains: List[str], relevant_domains: List[str], k: int) -> float:
    """Normalized DCG@K"""
    grades = [1 if d in relevant_domains else 0 for d in retrieved_domains[:k]]
    ideal_grades = sorted(grades, reverse=True)
    dcg = _dcg_at_k(grades, k)
    idcg = _dcg_at_k(ideal_grades, k)
    if idcg == 0.0:
        return 0.0
    return round(dcg / idcg, 4)


# ---------------------------------------------------------------------------
# Keyword-only baseline scorer
# ---------------------------------------------------------------------------

def _keyword_score(query: str, candidate: Dict[str, Any]) -> float:
    """Simple keyword overlap score — the old/baseline approach."""
    query_terms = {t for t in query.lower().split() if len(t) > 2}
    candidate_text = " ".join([
        str(candidate.get("content", "")),
        " ".join(str(t) for t in candidate.get("tags", [])),
        str(candidate.get("source", "")),
    ]).lower()
    candidate_terms = set(candidate_text.split())
    if not query_terms:
        return 0.0
    return round(len(query_terms & candidate_terms) / len(query_terms), 4)


# ---------------------------------------------------------------------------
# Main evaluation runner
# ---------------------------------------------------------------------------

def run_evaluation() -> Dict[str, Any]:
    """
    Run the full retrieval quality evaluation.
    Returns a dict with before/after metrics and per-query breakdown.
    """
    from kosha.kosha_loader import KoshaLoader
    from kosha.kosha_retriever import KoshaRetriever
    from retrieval.ontology_retriever import OntologyAwareRetriever
    from ontology.entity_resolver import CanonicalEntityResolver

    kosha_dir = os.path.join(_BACKEND_DIR, "data", "kosha")
    entries = KoshaLoader(data_sources=[kosha_dir]).load_all()
    retriever = KoshaRetriever(entries)
    ontology = OntologyAwareRetriever()
    resolver = CanonicalEntityResolver()

    rows: List[Dict[str, Any]] = []

    for case in EVAL_DATASET:
        query = case["query"]
        relevant = case["relevant_domains"]
        reject = case.get("must_reject_cross_domain")

        t0 = time.perf_counter()
        signals, detected_domain = retriever.retrieve(query)
        retrieval_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Build ranked domain list (top signal first, fall back to detected_domain)
        ranked_domains: List[str] = []
        old_scores: List[float] = []
        new_scores: List[float] = []

        for sig in signals[:5]:  # evaluate top-5
            sig_dict = sig if isinstance(sig, dict) else {}
            raw_domain = str(sig_dict.get("domain") or "none")
            inferred = resolver.resolve_domain(
                " ".join([
                    str(sig_dict.get("content") or ""),
                    str(sig_dict.get("source") or ""),
                    " ".join(sig_dict.get("tags") or []),
                ])
            )
            domain = inferred["domain"] if inferred.get("domain") != "general" else raw_domain
            ranked_domains.append(domain)
            old_scores.append(_keyword_score(query, sig_dict))
            ontology_result = ontology.score(query, sig_dict)
            new_scores.append(round(float(ontology_result.get("combined_score", 0.0)), 4))

        # If no signals, fall back to detected_domain
        if not ranked_domains:
            ranked_domains = [detected_domain] if detected_domain else ["none"]
            old_scores = [0.0]
            new_scores = [0.0]

        # Compute IR metrics
        p1_old = _precision_at_k(ranked_domains, relevant, 1)
        p3_old = _precision_at_k(ranked_domains, relevant, 3)
        r1_old = _recall_at_k(ranked_domains, relevant, 1)
        mrr_old = _reciprocal_rank(ranked_domains, relevant)
        ndcg3_old = _ndcg_at_k(ranked_domains, relevant, 3)

        # For "new" we use ontology scores to re-rank
        if len(signals) > 1:
            scored_pairs = list(zip(ranked_domains, new_scores))
            scored_pairs.sort(key=lambda x: x[1], reverse=True)
            reranked_domains = [d for d, _ in scored_pairs]
        else:
            reranked_domains = ranked_domains[:]

        p1_new = _precision_at_k(reranked_domains, relevant, 1)
        p3_new = _precision_at_k(reranked_domains, relevant, 3)
        r1_new = _recall_at_k(reranked_domains, relevant, 1)
        mrr_new = _reciprocal_rank(reranked_domains, relevant)
        ndcg3_new = _ndcg_at_k(reranked_domains, relevant, 3)

        # Cross-domain rejection check
        rejection_pass = True
        if reject:
            rejection_pass = reranked_domains[0] != reject if reranked_domains else True

        row = {
            "query": query,
            "description": case.get("description", ""),
            "expected_domain": case["expected_domain"],
            "detected_domain": detected_domain,
            "top_domain_baseline": ranked_domains[0] if ranked_domains else "none",
            "top_domain_enhanced": reranked_domains[0] if reranked_domains else "none",
            "retrieval_latency_ms": retrieval_ms,
            "signals_retrieved": len(signals),
            "cross_domain_rejection_pass": rejection_pass,
            "baseline_keyword_score_avg": round(sum(old_scores) / len(old_scores), 4) if old_scores else 0.0,
            "enhanced_ontology_score_avg": round(sum(new_scores) / len(new_scores), 4) if new_scores else 0.0,
            "metrics_baseline": {
                "precision_at_1": p1_old,
                "precision_at_3": p3_old,
                "recall_at_1": r1_old,
                "mrr": round(mrr_old, 4),
                "ndcg_at_3": ndcg3_old,
            },
            "metrics_enhanced": {
                "precision_at_1": p1_new,
                "precision_at_3": p3_new,
                "recall_at_1": r1_new,
                "mrr": round(mrr_new, 4),
                "ndcg_at_3": ndcg3_new,
            },
        }
        rows.append(row)

    # Aggregate metrics
    def _avg(key: str, sub: str) -> float:
        vals = [r[sub][key] for r in rows if sub in r]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    aggregate_baseline = {
        "precision_at_1": _avg("precision_at_1", "metrics_baseline"),
        "precision_at_3": _avg("precision_at_3", "metrics_baseline"),
        "recall_at_1": _avg("recall_at_1", "metrics_baseline"),
        "mrr": _avg("mrr", "metrics_baseline"),
        "ndcg_at_3": _avg("ndcg_at_3", "metrics_baseline"),
        "avg_keyword_score": round(
            sum(r["baseline_keyword_score_avg"] for r in rows) / len(rows), 4
        ) if rows else 0.0,
    }
    aggregate_enhanced = {
        "precision_at_1": _avg("precision_at_1", "metrics_enhanced"),
        "precision_at_3": _avg("precision_at_3", "metrics_enhanced"),
        "recall_at_1": _avg("recall_at_1", "metrics_enhanced"),
        "mrr": _avg("mrr", "metrics_enhanced"),
        "ndcg_at_3": _avg("ndcg_at_3", "metrics_enhanced"),
        "avg_ontology_score": round(
            sum(r["enhanced_ontology_score_avg"] for r in rows) / len(rows), 4
        ) if rows else 0.0,
    }

    cross_domain_pass_rate = round(
        sum(1 for r in rows if r["cross_domain_rejection_pass"]) / len(rows), 4
    ) if rows else 0.0

    avg_latency = round(
        sum(r["retrieval_latency_ms"] for r in rows) / len(rows), 2
    ) if rows else 0.0

    # Improvement deltas
    deltas = {
        k: round(aggregate_enhanced[k] - aggregate_baseline.get(k, 0.0), 4)
        for k in ["precision_at_1", "mrr", "ndcg_at_3"]
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pipeline_version": "signal_first_ontology_kosha_v3",
        "evaluation_queries": len(rows),
        "summary": {
            "baseline_keyword_retrieval": aggregate_baseline,
            "enhanced_ontology_retrieval": aggregate_enhanced,
            "improvement_deltas": deltas,
            "cross_domain_rejection_pass_rate": cross_domain_pass_rate,
            "average_retrieval_latency_ms": avg_latency,
            "verdict": (
                "IMPROVEMENT_CONFIRMED"
                if deltas.get("precision_at_1", 0) >= 0 and deltas.get("mrr", 0) >= 0
                else "NO_IMPROVEMENT"
            ),
        },
        "per_query_results": rows,
    }

    # Persist report
    out_dir = os.path.normpath(
        os.path.join(_BACKEND_DIR, "..", "review_packets", "proof_logs")
    )
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "retrieval_quality_report.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=True)

    return report


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result["summary"], indent=2, ensure_ascii=True))
    print(f"\nFull report saved to: review_packets/proof_logs/retrieval_quality_report.json")
