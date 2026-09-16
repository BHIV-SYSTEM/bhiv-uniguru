import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from governance.epistemic_confidence import EpistemicConfidenceEngine
from governance.source_governance import SourceGovernance
from ontology.entity_resolver import CanonicalEntityResolver

logger = logging.getLogger(__name__)

OFF_TOPIC_PATTERNS = (
    r"\bcricket\b",
    r"\bstock price\b",
    r"\bapple inc\b",
    r"\bpizza\b",
    r"\bleaking faucet\b",
    r"\bmovie to watch\b",
    r"\btime travel\b.*\bpossible\b",
    r"\bquantum entanglement\b.*\bbhagavad gita\b",
)

NO_KNOWLEDGE_RESPONSE = "I do not have verified knowledge to answer this question."

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "at", "by", "for", "from", "as", "with",
    "about", "into", "over", "under", "who", "what", "which", "when",
    "where", "why", "how", "tell", "explain", "does", "have", "this",
    "that", "chapter", "verse", "me",
}

# Minimum thresholds for signal acceptance
MIN_SIGNAL_CONFIDENCE = 0.15
MIN_TAG_OVERLAP = 1  # At least 1 tag must match query
MIN_SEMANTIC_SCORE = 0.28
MIN_ENTITY_OVERLAP_WHEN_ENTITY_QUERY = 0.5


class SignalValidator:
    @classmethod
    def is_off_topic_query(cls, query: str) -> bool:
        import re
        text = str(query or "").lower()
        return any(re.search(pattern, text) for pattern in OFF_TOPIC_PATTERNS)

    """
    Phase 4: Deterministic Signal Validation
    Rule: signal must match domain + tags + query
    If no valid signal → explicitly return NO VERIFIED KNOWLEDGE
    No silent fallback.
    """

    @staticmethod
    def tokenize(text: str) -> set:
        """Extract meaningful tokens from text"""
        terms = re.findall(r'[a-zA-Z0-9\u0900-\u097F]+', text.lower())
        return {t for t in terms if len(t) > 2 and t not in STOPWORDS}

    @staticmethod
    def compute_tag_match(query_tokens: set, signal_tags: List[str]) -> Tuple[float, List[str]]:
        """Compute tag match score and return matched tags"""
        if not query_tokens or not signal_tags:
            return 0.0, []

        tag_tokens = set()
        for tag in signal_tags:
            tag_tokens.update(re.findall(r'[a-zA-Z0-9]+', tag.lower()))

        matched = query_tokens.intersection(tag_tokens)
        score = len(matched) / len(query_tokens) if query_tokens else 0.0
        return round(score, 4), list(matched)

    @staticmethod
    def compute_content_overlap(query_tokens: set, content: str) -> float:
        """Compute content overlap score"""
        if not query_tokens or not content:
            return 0.0

        content_tokens = SignalValidator.tokenize(content)
        overlap = query_tokens.intersection(content_tokens)
        return round(len(overlap) / len(query_tokens), 4) if query_tokens else 0.0

    @classmethod
    def validate_signal(
        cls,
        signal: Dict[str, Any],
        query: str,
        query_tokens: Optional[set] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate a single signal against the query.
        Returns: (is_valid, rejection_reason, validation_details)
        """
        if query_tokens is None:
            query_tokens = cls.tokenize(query)

        content = str(signal.get("content") or "").strip()
        tags = signal.get("tags") or []
        confidence = float(signal.get("confidence") or 0.0)
        source = str(signal.get("source") or "unknown")

        details = {
            "signal_id": signal.get("signal_id", "unknown"),
            "source": source,
            "confidence": confidence,
            "tag_match_score": 0.0,
            "content_overlap": 0.0,
            "matched_tags": [],
            "semantic_score": 0.0,
            "concept_overlap": 0.0,
            "entity_overlap": 0.0,
            "domain_consistency": 0.0,
            "contextual_proximity": 0.0,
            "query_entities": [],
            "candidate_entities": [],
            "missing_required_entities": [],
            "confidence_derivation": {},
            "source_governance": {},
        }

        # Rule 1: Content must exist and be non-empty
        if not content or len(content) < 10:
            return False, "empty_or_short_content", details

        non_answer_markers = (
            "not explicitly mentioned",
            "not provided in the given context",
            "not provided in the context",
            "i don't know",
            "cannot be answered from the provided context",
        )
        if any(marker in content.lower() for marker in non_answer_markers):
            return False, "low_contextual_overlap", details

        # Rule 2: Confidence must meet minimum threshold
        if confidence < MIN_SIGNAL_CONFIDENCE:
            return False, f"confidence_below_threshold:{confidence:.3f}", details

        source_governance = signal.get("source_governance")
        if not isinstance(source_governance, dict):
            source_governance = SourceGovernance.assess(signal)
        details["source_governance"] = source_governance
        if source_governance.get("suppression_reason"):
            return False, str(source_governance["suppression_reason"]), details

        # Rule 3: Tag match — at least 1 tag must overlap with query
        tag_score, matched_tags = cls.compute_tag_match(query_tokens, tags)
        details["tag_match_score"] = tag_score
        details["matched_tags"] = matched_tags

        # Rule 4: Content overlap — query terms must appear in content
        content_overlap = cls.compute_content_overlap(query_tokens, content)
        details["content_overlap"] = content_overlap

        semantic = signal.get("ontology_score")
        if not isinstance(semantic, dict):
            semantic = cls.entity_resolver.semantic_scores(
                query=query,
                content=content,
                tags=tags,
                source=source,
                domain=str(signal.get("domain") or ""),
            )
        for key in (
            "semantic_score",
            "concept_overlap",
            "entity_overlap",
            "domain_consistency",
            "contextual_proximity",
            "query_entities",
            "candidate_entities",
            "domain_resolution",
            "missing_required_entities",
        ):
            if key in semantic:
                details[key] = semantic[key]

        match_confidence = round(
            (0.25 * confidence)
            + (0.25 * tag_score)
            + (0.2 * content_overlap)
            + (0.3 * float(details["semantic_score"])),
            4,
        )
        epistemic = EpistemicConfidenceEngine.derive(
            retrieval_confidence=confidence,
            validation_details=details,
            source_governance=source_governance,
        )
        details["confidence_derivation"] = {
            "retrieval_confidence": round(confidence, 4),
            "tag_match_score": tag_score,
            "content_overlap": content_overlap,
            "semantic_score": float(details["semantic_score"]),
            "entity_overlap": float(details["entity_overlap"]),
            "domain_consistency": float(details["domain_consistency"]),
            "formula": "0.25*retrieval + 0.25*tag + 0.2*content + 0.3*semantic",
            "match_confidence": match_confidence,
            "epistemic_confidence": epistemic,
            "derived_confidence": epistemic["score"],
        }

        # Accept if EITHER tag match OR content overlap is sufficient
        has_tag_match = len(matched_tags) >= MIN_TAG_OVERLAP
        has_content_match = content_overlap > 0.1

        if not has_tag_match and not has_content_match:
            return False, "no_query_relevance:tags_and_content_both_miss", details

        query_entities = details.get("query_entities") or []
        if details.get("missing_required_entities"):
            return False, "entity_conflict", details

        if query_entities and float(details["entity_overlap"]) < MIN_ENTITY_OVERLAP_WHEN_ENTITY_QUERY:
            return False, "entity_conflict", details

        if float(details["domain_consistency"]) <= 0.0:
            return False, "domain_mismatch", details

        if float(details["semantic_score"]) < MIN_SEMANTIC_SCORE:
            return False, "weak_semantic_alignment", details

        if content_overlap <= 0.1 and float(details["contextual_proximity"]) < 0.5:
            return False, "low_contextual_overlap", details

        return True, "valid", details

    @classmethod
    def validate_all(
        cls,
        signals: List[Dict[str, Any]],
        query: str,
    ) -> Dict[str, Any]:
        """
        Validate all signals for a query.
        Returns structured result with accepted/rejected signals and reasoning.
        """
        query_tokens = cls.tokenize(query)

        accepted = []
        rejected = []

        for signal in signals:
            is_valid, reason, details = cls.validate_signal(signal, query, query_tokens)
            if is_valid:
                accepted.append({**signal, "confidence": details["confidence_derivation"]["derived_confidence"], "_validation": details})
            else:
                rejected.append({
                    "signal_id": signal.get("signal_id", "unknown"),
                    "source": signal.get("source", "unknown"),
                    "rejection_reason": reason,
                    "details": details,
                })

        # Sort accepted by confidence descending
        accepted.sort(key=lambda s: float(s.get("confidence") or 0.0), reverse=True)

        return {
            "query": query,
            "query_tokens": list(query_tokens),
            "signals_found": len(accepted),
            "signals_rejected": len(rejected),
            "accepted_signals": accepted,
            "rejected_signals": rejected,
            "has_valid_knowledge": len(accepted) > 0,
        }


class AnswerSynthesizer:
    """
    Phase 6: Answer Synthesis Layer
    Converts validated signals into clean, human-readable answers.
    No raw text dumping. No broken formatting. No hallucinated Sanskrit.
    """

    @staticmethod
    def synthesize(
        query: str,
        validation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Synthesize a clean answer from validated signals.
        If no valid signals → return explicit NO VERIFIED KNOWLEDGE.
        """
        accepted = validation_result.get("accepted_signals", [])
        rejected = validation_result.get("rejected_signals", [])

        if not accepted:
            return {
                "answer": NO_KNOWLEDGE_RESPONSE,
                "verification_status": "NO_VERIFIED_KNOWLEDGE",
                "confidence": 0.0,
                "signals_used": 0,
                "signals_rejected": len(rejected),
                "rejection_reasons": [r["rejection_reason"] for r in rejected],
                "source": None,
                "reasoning": "No signals passed domain+tag+query validation.",
            }

        # Use top signal (highest confidence)
        best = accepted[0]
        content = str(best.get("content") or "").strip()
        confidence = float(best.get("confidence") or 0.0)
        source = str(best.get("source") or "unknown")
        validation = best.get("_validation", {})

        # Clean the content for output
        answer = AnswerSynthesizer._format_answer(content)

        return {
            "answer": answer,
            "verification_status": "VERIFIED",
            "confidence": round(confidence, 4),
            "signals_used": len(accepted),
            "signals_rejected": len(rejected),
            "source": source,
            "reasoning": (
                f"Accepted signal because tags {validation.get('matched_tags', [])}, "
                f"content overlap {validation.get('content_overlap', 0):.2f}, "
                f"entity overlap {validation.get('entity_overlap', 0):.2f}, "
                f"domain consistency {validation.get('domain_consistency', 0):.2f}, "
                f"and derived confidence {confidence:.3f} met deterministic thresholds."
            ),
        }

    @staticmethod
    def _format_answer(content: str) -> str:
        """Format content into clean, readable answer"""
        if not content:
            return NO_KNOWLEDGE_RESPONSE

        # Remove citation markers like [1], [2]
        text = re.sub(r'\[\d+\]', '', content)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove trailing incomplete sentences
        if text and not text[-1] in '.!?':
            last_period = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_period > len(text) // 2:
                text = text[:last_period + 1]

        return text.strip() or NO_KNOWLEDGE_RESPONSE
    entity_resolver = CanonicalEntityResolver()
