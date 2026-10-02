from __future__ import annotations

from typing import Any, Dict, List

from ontology.entity_resolver import CanonicalEntityResolver
from .embedding_provider import EmbeddingProvider, LocalHashEmbeddingProvider


class OntologyAwareRetriever:
    """Compares old keyword scores against ontology/entity/embedding-aware scores."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.resolver = CanonicalEntityResolver()
        self.embedding_provider = embedding_provider or LocalHashEmbeddingProvider()

    def score(self, query: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
        semantic = self.resolver.semantic_scores(
            query=query,
            content=str(candidate.get("content") or ""),
            tags=list(candidate.get("tags") or []),
            source=str(candidate.get("source") or ""),
            domain=str(candidate.get("domain") or ""),
        )
        expanded_query = " ".join(sorted(self.resolver.expand_terms(query)))
        expanded_candidate = " ".join(
            sorted(
                self.resolver.expand_terms(
                    " ".join(
                        [
                            str(candidate.get("content") or ""),
                            " ".join(candidate.get("tags") or []),
                            str(candidate.get("source") or ""),
                            str(candidate.get("domain") or ""),
                        ]
                    )
                )
            )
        )
        query_vector, candidate_vector = self.embedding_provider.encode(
            [
                expanded_query,
                expanded_candidate,
            ]
        )
        embedding_similarity = max(0.0, self.embedding_provider.similarity(query_vector, candidate_vector))
        combined = round((0.8 * semantic["semantic_score"]) + (0.2 * embedding_similarity), 4)
        return {
            **semantic,
            "embedding_similarity": round(embedding_similarity, 4),
            "embedding_trace": {
                "provider": self.embedding_provider.__class__.__name__,
                "vector_source": "local_hash_expanded_canonical_terms",
                "dimensions": getattr(self.embedding_provider, "dimensions", None),
                "query_feature_count": len(expanded_query.split()),
                "candidate_feature_count": len(expanded_candidate.split()),
                "similarity_score": round(embedding_similarity, 4),
                "retrieval_reasoning": "Offline deterministic semantic similarity over canonical term expansion.",
            },
            "combined_score": combined,
        }

    def rank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked = []
        for candidate in candidates:
            score = self.score(query, candidate)
            ranked.append({**candidate, "_ontology_score": score})
        ranked.sort(
            key=lambda row: (
                float(row.get("_ontology_score", {}).get("combined_score", 0.0)),
                float(row.get("confidence") or 0.0),
                str(row.get("signal_id") or ""),
            ),
            reverse=True,
        )
        return ranked
