import re
from typing import List, Dict, Any
import hashlib
from .kosha_validator import KoshaEntry
from governance.source_governance import SourceGovernance
from ontology.entity_resolver import CanonicalEntityResolver

class KoshaRetriever:
    def __init__(self, entries: List[KoshaEntry]):
        self.entries = entries
        self.entity_resolver = CanonicalEntityResolver()

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
            "name",
            "any",
            "one",
            "tell",
            "please",
            "text",
            "purpose",
            "translate",
            "translation",
        }

        query_normalized = query.lower()
        raw_query_terms = re.findall(r"\b\w+\b", query_normalized)
        query_words = set()
        for term in raw_query_terms:
            term = re.sub(r"['’]s$", "", term)
            if len(term) >= 2 and term not in STOPWORDS:
                query_words.add(term)
                if term.endswith("ies") and len(term) > 4:
                    query_words.add(term[:-3] + "y")
                elif term.endswith("s") and len(term) > 3:
                    query_words.add(term[:-1])
        query_words.update(self.entity_resolver.expand_terms(query))
        
        if not domain:
            domain_resolution = self.entity_resolver.resolve_domain(query)
            domain = domain_resolution["domain"] if domain_resolution["domain"] != "general" else self._detect_domain(query)
        else:
            domain_resolution = self.entity_resolver.resolve_domain(query, domain_hint=domain)

        definition_query = bool(re.search(r"\bwhat\s+(?:is|are)\b|\bdefine\b|\bmeaning\s+of\b", query_normalized))
        subject_text = re.sub(
            r"^\s*(?:what\s+(?:is|are)|define|meaning\s+of)\s+", "", query_normalized, flags=re.IGNORECASE
        ).strip(" ?.!	")
        query_subjects = [
            re.sub(r"\s+", " ", part).strip(" ?.!	")
            for part in re.split(r"\s+(?:and|or)\s+", subject_text, flags=re.IGNORECASE)
        ]

        scored_entries: List[tuple[float, float, float, float, float, float, float, KoshaEntry, Dict[str, Any]]] = []

        for entry in self.entries:
            # Tag match score: proportion of query terms covered by this entry's tags.
            normalized_tags = []
            for tag in entry.tags or []:
                tag_norm = str(tag).lower().strip()
                if len(tag_norm) >= 2 and tag_norm not in STOPWORDS:
                    normalized_tags.append(tag_norm)

            matched_tags = [t for t in normalized_tags if t in query_words]
            tag_match_score = 0.0
            if query_words:
                # Value in [0..1]; prevents "the" from dominating tag confidence.
                tag_match_score = len(matched_tags) / len(query_words)

            # Content similarity score: exact word overlap between query and entry.content.
            content_raw_terms = re.findall(r"\b\w+\b", str(entry.content).lower())
            content_words = {t for t in content_raw_terms if len(t) >= 2 and t not in STOPWORDS}
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
            # Use only deterministic canonical-entity and term overlap scores here.
            # The active Kosha answer path must not depend on vector embeddings.
            ontology_score = self.entity_resolver.semantic_scores(
                query=query,
                content=str(candidate.get("content") or ""),
                tags=list(candidate.get("tags") or []),
                source=str(candidate.get("source") or ""),
                domain=str(candidate.get("domain") or ""),
            )
            source_governance = SourceGovernance.assess(candidate)

            query_entities = ontology_score.get("query_entities", [])
            candidate_entities = self.entity_resolver.extract(
                " ".join([str(entry.content or ""), " ".join(entry.tags or []), str(entry.source or "")])
            )
            candidate_entity_names = {row["canonical"] for row in candidate_entities}
            required_entity_names = {
                row["canonical"] for row in query_entities
                if row.get("entity_type") not in {"text", "text_group"}
            }
            exact_entity_match = (
                len(required_entity_names & candidate_entity_names) / len(required_entity_names)
                if required_entity_names else 0.0
            )
            topic_aliases = set()
            for entity in query_entities:
                canonical = str(entity.get("canonical") or "")
                seed = self.entity_resolver.alias_index.get(self.entity_resolver._normalize(canonical))
                topic_aliases.update(
                    self.entity_resolver._normalize(alias)
                    for alias in [canonical, *(seed or {}).get("aliases", [])]
                )
            topic_id = str(entry.knowledge_id or "").casefold()
            topic_tags = {self.entity_resolver._normalize(tag) for tag in entry.tags or []}
            exact_topic_match = float(any(
                topic_id.endswith(f"_{alias.replace(' ', '_')}") or alias in topic_tags
                for alias in topic_aliases if alias
            ))
            normalized_content = self.entity_resolver._normalize(str(entry.content or ""))
            direct_definition = float(definition_query and any(
                re.search(
                    rf"^\s*(?:the\s+)?{re.escape(self.entity_resolver._normalize(subject))}\b(?:\s*\([^)]*\))?(?:\s+things)?\s+(?:is|are|means|refers to|denotes|translates to|does not|do not)\b|\b(?:explains|describes)\s+{re.escape(self.entity_resolver._normalize(subject))}\b\s+as\b",
                    normalized_content,
                    re.MULTILINE,
                )
                for subject in query_subjects if subject
            ))

            # Domain agreement is part of the score, not a silent hard filter.
            domain_boost = 0.05 if domain and str(entry.domain).lower() == str(domain).lower() else 0.0
            source_weight = float(source_governance.get("authority_weight") or 0.0)
            match_score = min(
                1.0,
                (0.72 * max(base_match_score, ontology_score["semantic_score"]))
                + (0.23 * source_weight)
                + domain_boost,
            )

            # Authority raises confidence only after relevance is established. It
            # must never make every record a candidate by itself.
            has_relevance = base_match_score > 0 or exact_entity_match > 0
            if has_relevance and match_score > 0 and str(entry.content).strip():
                scored_entries.append((
                    exact_topic_match,
                    exact_entity_match,
                    direct_definition,
                    base_match_score,
                    float(ontology_score.get("contextual_proximity") or 0.0),
                    source_weight,
                    match_score,
                    entry,
                    ontology_score,
                ))

        # Topical fit and direct evidence precede context and source authority.
        scored_entries.sort(
            key=lambda x: (*x[:7], x[7].timestamp, x[7].knowledge_id),
            reverse=True,
        )

        signals: List[Dict[str, Any]] = []
        for rank, (_, _, _, _, _, _, match_score, entry, ontology_score) in enumerate(scored_entries):
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
                        "evidence_priority": {
                            "exact_topic_match": exact_topic_match,
                            "exact_entity_match": exact_entity_match,
                            "direct_definition": direct_definition,
                            "query_coverage": base_match_score,
                            "contextual_proximity": float(ontology_score.get("contextual_proximity") or 0.0),
                            "source_authority": source_weight,
                        },
                        "embedding_trace": ontology_score.get("embedding_trace", {}),
                        "source_lineage": source_governance.get("lineage", {}),
                    },
                }
            )

        return signals, domain
