import re
from typing import List, Dict, Any
import hashlib
from .kosha_validator import KoshaEntry
from governance.source_governance import SourceGovernance
from ontology.entity_resolver import CanonicalEntityResolver

try:
    from retrieval.ontology_retriever import OntologyAwareRetriever
except ModuleNotFoundError:  # pragma: no cover - defensive fallback for local/test environments
    class OntologyAwareRetriever:
        def score(self, query: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "combined_score": 0.0,
                "semantic_score": 0.0,
                "embedding_similarity": 0.0,
                "embedding_trace": {},
            }

        def rank(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return list(candidates)


class KoshaRetriever:
    def __init__(self, entries: List[KoshaEntry]):
        self.entries = entries
        self.entity_resolver = CanonicalEntityResolver()
        self.ontology_retriever = OntologyAwareRetriever()

    def _detect_domain(self, query: str) -> str:
        """
        Phase 7: Deterministic Keyword-based Domain Authentication. 
        Categorizes query strictly to allowed domains without LLM randomness.
        """
        query_low = query.lower()
        
        domain_weights = {
            "Agriculture": ["crop", "farm", "soil", "nitrogen", "legume", "irrigation", "harvest", "plant", "seed", "rural", "grow"],
            "Urban": ["transit", "density", "city", "metropolitan", "zoning", "traffic", "building", "street", "pollution", "urban"],
            "Water / Rivers": ["river", "runoff", "water", "ocean", "lake", "stream", "basin", "riparian", "aquifer", "marine"],
            "Infrastructure": ["grid", "energy", "load", "electrical", "sensor", "blackout", "bridge", "road", "telecom", "infrastructure"]
        }
        
        scores = {d: 0 for d in domain_weights}
        
        for domain, keywords in domain_weights.items():
            for kw in keywords:
                if kw in query_low:
                    scores[domain] += 1
                    
        # Find dominant domain
        best_domain = max(scores, key=scores.get)
        if scores[best_domain] > 0:
            return best_domain
            
        return None  # No strict domain caught

    def retrieve(self, query: str, domain: str = None) -> tuple[List[Dict[str, Any]], str]:
        """
        Deterministic Keyword + Tag matched retrieval. NO embeddings.
        """
        STOPWORDS = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "if",
            "then",
            "else",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "to",
            "of",
            "in",
            "on",
            "at",
            "by",
            "for",
            "from",
            "as",
            "with",
            "about",
            "into",
            "over",
            "under",
            "who",
            "whom",
            "whose",
            "what",
            "which",
            "when",
            "where",
            "why",
            "how",
        }

        query_normalized = query.lower()
        raw_query_terms = re.findall(r"\b\w+\b", query_normalized)
        query_words = {t for t in raw_query_terms if len(t) > 2 and t not in STOPWORDS}
        query_words.update(self.entity_resolver.expand_terms(query))
        
        if not domain:
            domain_resolution = self.entity_resolver.resolve_domain(query)
            domain = domain_resolution["domain"] if domain_resolution["domain"] != "general" else self._detect_domain(query)
        else:
            domain_resolution = self.entity_resolver.resolve_domain(query, domain_hint=domain)

        scored_entries: List[tuple[float, KoshaEntry]] = []

        for entry in self.entries:
            # Tag match score: proportion of query terms covered by this entry's tags.
            normalized_tags = []
            for tag in entry.tags or []:
                tag_norm = str(tag).lower().strip()
                if len(tag_norm) > 2 and tag_norm not in STOPWORDS:
                    normalized_tags.append(tag_norm)

            matched_tags = [t for t in normalized_tags if t in query_words]
            tag_match_score = 0.0
            if query_words:
                # Value in [0..1]; prevents "the" from dominating tag confidence.
                tag_match_score = len(matched_tags) / len(query_words)

            # Content similarity score: exact word overlap between query and entry.content.
            content_raw_terms = re.findall(r"\b\w+\b", str(entry.content).lower())
            content_words = {t for t in content_raw_terms if len(t) > 2 and t not in STOPWORDS}
            overlap = query_words.intersection(content_words)
            similarity_score = 0.0
            if query_words:
                similarity_score = len(overlap) / len(query_words)

            # Kosha confidence rule: similarity_score OR tag_match_score.
            base_match_score = max(tag_match_score, similarity_score)

            candidate = {
                "content": entry.content,
                "tags": entry.tags or [],
                "source": entry.source,
                "domain": entry.domain,
            }
            ontology_score = self.ontology_retriever.score(query, candidate)
            source_governance = SourceGovernance.assess(candidate)

            # Domain agreement is part of the score, not a silent hard filter.
            domain_boost = 0.05 if domain and str(entry.domain).lower() == str(domain).lower() else 0.0
            source_weight = float(source_governance.get("authority_weight") or 0.0)
            match_score = min(
                1.0,
                (0.72 * max(base_match_score, ontology_score["combined_score"]))
                + (0.23 * source_weight)
                + domain_boost,
            )

            if match_score > 0 and str(entry.content).strip():
                scored_entries.append((match_score, entry, ontology_score))

        # Sort descending deterministically by match_score, then timestamp, then knowledge_id.
        scored_entries.sort(key=lambda x: (x[0], x[1].timestamp, x[1].knowledge_id), reverse=True)

        signals: List[Dict[str, Any]] = []
        for rank, (match_score, entry, ontology_score) in enumerate(scored_entries):
            signal_id_hash = hashlib.md5(f"{entry.knowledge_id}_{entry.source}_{rank}".encode()).hexdigest()[:12]
            confidence = float(min(1.0, max(match_score, 0.0)))
            source_governance = SourceGovernance.assess(
                {
                    "content": entry.content,
                    "source": entry.source,
                    "tags": entry.tags or [],
                    "domain": entry.domain,
                }
            )

            signals.append(
                {
                    "signal_id": f"signal_{signal_id_hash}",
                    "type": "string",
                    "content": entry.content,
                    "source": entry.source,
                    "confidence": confidence,
                    "tags": entry.tags or [],
                    "domain": entry.domain,
                    "ontology_score": ontology_score,
                    "source_governance": source_governance,
                    "trace": {
                        "knowledge_id": entry.knowledge_id,
                        "method": "ontology_aware_kosha_retrieval",
                        "domain_resolution": domain_resolution,
                        "embedding_trace": ontology_score.get("embedding_trace", {}),
                        "source_lineage": source_governance.get("lineage", {}),
                    },
                }
            )

        return signals, domain
