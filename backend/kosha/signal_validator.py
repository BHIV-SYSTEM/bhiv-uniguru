import re
import unicodedata
import logging
from typing import List, Dict, Any, Optional, Tuple
from governance.epistemic_confidence import EpistemicConfidenceEngine
from governance.source_governance import SourceGovernance
from ontology.entity_resolver import CanonicalEntityResolver

logger = logging.getLogger(__name__)

NO_KNOWLEDGE_RESPONSE = "I do not have verified knowledge to answer this question."

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "at", "by", "for", "from", "as", "with",
    "about", "into", "over", "under", "who", "what", "which", "when",
    "where", "why", "how", "tell", "explain", "does", "have", "this",
    "that", "chapter", "verse", "me", "translate", "translation",
}

_TRANSLITERATION = str.maketrans({
    "ā": "a", "ī": "i", "ū": "u", "ṛ": "r", "ṝ": "r", "ḷ": "l",
    "ṃ": "m", "ṁ": "m", "ḥ": "h", "ś": "s", "ṣ": "s", "ṭ": "t",
    "ḍ": "d", "ṇ": "n", "ṅ": "n", "ñ": "n",
})


def _normalize_latin(text: str) -> str:
    raw = str(text or "").casefold().replace("ś", "sh").replace("ṣ", "sh")
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.translate(_TRANSLITERATION)

# Minimum thresholds for signal acceptance
MIN_SIGNAL_CONFIDENCE = 0.15
MIN_TAG_OVERLAP = 1  # At least 1 tag must match query
MIN_SEMANTIC_SCORE = 0.28
MIN_ENTITY_OVERLAP_WHEN_ENTITY_QUERY = 0.5


class SignalValidator:
    """
    Phase 4: Deterministic Signal Validation
    Rule: signal must match domain + tags + query
    If no valid signal -> explicitly return NO VERIFIED KNOWLEDGE
    No silent fallback.
    """
    entity_resolver = CanonicalEntityResolver()

    @staticmethod
    def tokenize(text: str) -> set:
        """Extract meaningful tokens from text"""
        normalized = _normalize_latin(text)
        normalized = normalized.translate(_TRANSLITERATION)
        normalized = re.sub(r"(?<=\w)['’]s\b", "", normalized)
        terms = re.findall(r'[a-zA-Z0-9\u0900-\u097F]+', normalized)
        normalized_terms = set()
        for term in terms:
            if len(term) < 2 or term in STOPWORDS:
                continue
            normalized_terms.add(term)
            if term.isascii() and term.isalpha():
                if term.endswith("ies") and len(term) > 4:
                    normalized_terms.add(term[:-3] + "y")
                elif term.endswith("s") and len(term) > 3:
                    normalized_terms.add(term[:-1])
        return normalized_terms

    @staticmethod
    def compute_tag_match(query_tokens: set, signal_tags: List[str]) -> Tuple[float, List[str]]:
        """Compute tag match score and return matched tags"""
        if not query_tokens or not signal_tags:
            return 0.0, []

        tag_tokens = set()
        for tag in signal_tags:
            tag_tokens.update(SignalValidator.tokenize(tag))

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
            "missing_source_entities": [],
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

        # Rule 3: Tag match
        text_entities = [
            entity
            for entity in cls.entity_resolver.extract(query)
            if entity.get("entity_type") == "text"
        ]
        if text_entities:
            source_tokens = cls.tokenize(source)
            required_source_tokens = {
                token
                for entity in text_entities
                for token in cls.tokenize(str(entity.get("canonical") or ""))
            }
            missing_source_tokens = sorted(required_source_tokens - source_tokens)
            details["missing_source_entities"] = missing_source_tokens
            if missing_source_tokens:
                return False, "source_entity_mismatch", details

            filler_terms = {"according", "describe", "describes", "mentioned", "mentions", "says", "say"}
            topic_tokens = query_tokens - required_source_tokens - filler_terms
            if topic_tokens:
                evidence_tokens = cls.tokenize(content)
                evidence_tokens.update(
                    token
                    for tag in tags
                    for token in cls.tokenize(str(tag))
                )
                topic_forms = set(topic_tokens)
                evidence_forms = set(evidence_tokens)
                if "agricultural" in topic_forms:
                    topic_forms.add("agriculture")
                elif "agriculture" in topic_forms:
                    topic_forms.add("agricultural")
                for token in tuple(topic_forms):
                    if token.endswith("s") and len(token) > 4:
                        topic_forms.add(token[:-1])
                for token in tuple(evidence_forms):
                    if token.endswith("s") and len(token) > 4:
                        evidence_forms.add(token[:-1])
                if not topic_forms & evidence_forms:
                    return False, "no_topic_evidence_for_named_source", details

        # Rule 3: Tag match — at least 1 tag must overlap with query
        tag_score, matched_tags = cls.compute_tag_match(query_tokens, tags)
        details["tag_match_score"] = tag_score
        details["matched_tags"] = matched_tags

        # Rule 4: Content overlap
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

        # Accept if EITHER tag match OR content overlap is sufficient,
        # OR if semantic/entity scores are strong enough.
        # This handles concept-term queries like "What is Atman?" where the term
        # does not appear literally in the KB entry's tags or content, but the
        # ontology resolver correctly identifies the entity and domain.
        has_tag_match = len(matched_tags) >= MIN_TAG_OVERLAP
        has_content_match = content_overlap > 0.1
        semantic_score = float(details["semantic_score"])
        entity_overlap_val = float(details["entity_overlap"])
        has_semantic_match = semantic_score >= 0.6 and entity_overlap_val >= 0.5

        if not has_tag_match and not has_content_match and not has_semantic_match:
            return False, "no_query_relevance:tags_and_content_both_miss", details

        query_entities = details.get("query_entities") or []
        if details.get("missing_required_entities"):
            return False, "entity_conflict", details

        if query_entities and float(details["entity_overlap"]) < MIN_ENTITY_OVERLAP_WHEN_ENTITY_QUERY:
            return False, "entity_conflict", details

        if float(details["domain_consistency"]) <= 0.0:
            return False, "domain_mismatch", details

        exact_lexical_match = (
            not query_entities
            and tag_score >= 0.8
            and content_overlap >= 0.8
        )
        if float(details["semantic_score"]) < MIN_SEMANTIC_SCORE and not exact_lexical_match:
            return False, "weak_semantic_alignment", details

        if content_overlap <= 0.1 and float(details["contextual_proximity"]) < 0.5 and not has_semantic_match:
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

        # Preserve topical evidence ordering; confidence and authority break ties only.
        accepted.sort(key=lambda signal: (
            *(float(signal.get("trace", {}).get("evidence_priority", {}).get(key) or 0.0)
              for key in ("exact_topic_match", "exact_entity_match", "direct_definition", "query_coverage", "contextual_proximity", "source_authority")),
            float(signal.get("confidence") or 0.0),
        ), reverse=True)

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

    SYNTHESIS_STOPWORDS = STOPWORDS | {
        "name", "any", "one", "translate", "translation", "text", "related", "purpose",
    }

    @staticmethod
    def _token_forms(token: str) -> set:
        forms = {token}
        if token.isascii() and token.isalpha() and len(token) > 3:
            if token.endswith("ies") and len(token) > 4:
                forms.add(token[:-3] + "y")
            elif token.endswith("s"):
                forms.add(token[:-1])
            else:
                forms.add(token + "s")
        return forms

    @classmethod
    def _relevant_sentences(cls, query: str, content: str) -> List[str]:
        query_terms = {
            term for term in SignalValidator.tokenize(query)
            if term not in cls.SYNTHESIS_STOPWORDS
        }
        if not query_terms:
            return []

        translation_query = "translate" in query.casefold() or "translation" in query.casefold()
        name_query = bool(re.search(r"\bname\b|\bwhich\s+text\b", query.casefold()))
        definition_query = bool(re.search(r"\bwhat\s+(?:is|are)\b|\bdefine\b|\bmeaning\s+of\b", query.casefold()))
        subject_text = re.sub(
            r"^\s*(?:what\s+(?:is|are)|define|meaning\s+of)\s+", "", query, flags=re.IGNORECASE
        ).strip(" ?.!\t")
        query_subjects = [
            re.sub(r"\s+", " ", part).strip(" ?.!\t")
            for part in re.split(r"\s+(?:and|or)\s+", subject_text, flags=re.IGNORECASE)
        ]
        text = re.sub(r"\[\d+\]", "", str(content or ""))
        sentences = re.split(r"(?<=[.!?\u0964\u0965])\s+|\n+", text)
        relevant = []
        resolver = CanonicalEntityResolver()
        query_entities = resolver.extract(query)
        entity_terms = {
            name.casefold(): SignalValidator.tokenize(name)
            for entity in query_entities
            for name in (entity["canonical"], entity.get("matched_alias", ""))
            if name
        }
        for raw_sentence in sentences:
            if raw_sentence.lstrip().startswith("#"):
                continue
            sentence = re.sub(r"^\s*(?:[-*]|\d+[.])\s*", "", raw_sentence).strip()
            sentence = re.sub(r"\s+", " ", sentence)
            if len(sentence) < 12:
                continue
            if re.match(r"(?:also|additionally|furthermore)\b", sentence, re.IGNORECASE):
                continue
            sentence_terms = SignalValidator.tokenize(sentence)
            sentence_forms = set().union(*(cls._token_forms(term) for term in sentence_terms))
            matched_terms = {
                term for term in query_terms
                if cls._token_forms(term) & sentence_forms
            }
            if translation_query:
                is_relevant = matched_terms == query_terms
            else:
                is_relevant = bool(matched_terms)
            if is_relevant:
                normalized_sentence = _normalize_latin(sentence)
                if name_query and any(entity.get("entity_type") in {"text", "text_group"} for entity in query_entities):
                    # A request to name a text needs a sentence that actually names
                    # one, not a sentence that merely discusses the text category.
                    if not re.search(r"\b[A-Z][\w-]+(?:\s+[A-Z][\w-]+)*\s+Upanishad\b", sentence):
                        continue
                normalized_sentence_terms = SignalValidator.tokenize(normalized_sentence)
                direct_entity = any(
                    bool(terms) and terms.issubset(normalized_sentence_terms)
                    for terms in entity_terms.values()
                )
                # When a canonical entity is known, require the selected sentence to
                # actually mention it. Shared words like "self", "reality", or "yoga"
                # must not pull a neighboring entity's definition into the answer.
                if query_entities and not direct_entity:
                    continue
                direct_definition = definition_query and any(
                    re.search(
                        rf"^\s*(?:the\s+)?{re.escape(_normalize_latin(subject))}\b(?:\s*\([^)]*\))?(?:\s+things)?\s+(?:is|are|means|refers to|denotes|translates to|does not|do not)\b|\b(?:explains|describes)\s+{re.escape(_normalize_latin(subject))}\b\s+as\b",
                        normalized_sentence,
                    )
                    for subject in query_subjects if subject
                )
                if definition_query and not direct_definition:
                    continue
                relevant.append((int(direct_definition), len(matched_terms), sentence))

        # Fallback: if no sentence contains the literal query term (e.g. "atman" not in
        # Upanishad entry text), return the first substantive sentences from the content.
        # This handles concept-term queries where the KB entry discusses the concept
        # without using the exact query word.
        if not relevant and not translation_query and not query_entities and not definition_query:
            fallback = []
            for s in sentences:
                cleaned = re.sub(r"\s+", " ", re.sub(r"^\s*(?:[-*]|\d+[.])\s*", "", s).strip())
                if len(cleaned) >= 20:
                    fallback.append(cleaned)
            return fallback[:3]

        relevant.sort(key=lambda row: (row[0], row[1]), reverse=True)
        if relevant and relevant[0][0]:
            relevant = [row for row in relevant if row[0]]
        return [sentence for _, _, sentence in relevant[:3]]

    @staticmethod
    def _is_duplicate_sentence(sentence: str, previous: List[str]) -> bool:
        tokens = SignalValidator.tokenize(sentence)
        for existing in previous:
            existing_tokens = SignalValidator.tokenize(existing)
            if tokens == existing_tokens:
                return True
            if tokens and existing_tokens:
                overlap = len(tokens & existing_tokens) / max(len(tokens), len(existing_tokens))
                if overlap >= 0.9:
                    return True
        return False

    @staticmethod
    def synthesize(
        query: str,
        validation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Synthesize a clean answer from validated signals.
        If no valid signals -> return explicit NO VERIFIED KNOWLEDGE.
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

        used_signals = []
        answer_sentences = []
        name_query = bool(re.search(r"\bname\b|\bwhich\s+text\b", query.casefold()))
        for signal in accepted:
            for sentence in AnswerSynthesizer._relevant_sentences(
                query=query,
                content=str(signal.get("content") or ""),
            ):
                if not AnswerSynthesizer._is_duplicate_sentence(sentence, answer_sentences):
                    answer_sentences.append(sentence)
                    if signal not in used_signals:
                        used_signals.append(signal)
                if len(answer_sentences) >= (1 if name_query else 6):
                    break
            if len(answer_sentences) >= (1 if name_query else 6):
                break

        if not used_signals:
            return {
                "answer": NO_KNOWLEDGE_RESPONSE,
                "verification_status": "NO_VERIFIED_KNOWLEDGE",
                "confidence": 0.0,
                "signals_used": 0,
                "evidence_signal_ids": [],
                "signals_rejected": len(rejected),
                "rejection_reasons": [r["rejection_reason"] for r in rejected],
                "source": None,
                "reasoning": "No accepted Kosha record contains evidence relevant to the query.",
            }

        answer = AnswerSynthesizer._format_answer(" ".join(answer_sentences))
        best = used_signals[0]
        confidence = max(float(signal.get("confidence") or 0.0) for signal in used_signals)
        source = str(best.get("source") or "unknown")
        evidence_refs = [
            f"{signal.get('trace', {}).get('knowledge_id', 'unknown')} ({signal.get('source') or 'unknown'})"
            for signal in used_signals
        ]

        return {
            "answer": answer,
            "verification_status": "VERIFIED",
            "confidence": round(confidence, 4),
            "signals_used": len(used_signals),
            "evidence_signal_ids": [signal.get("signal_id") for signal in used_signals],
            "signals_rejected": len(rejected),
            "source": source,
            "reasoning": (
                f"Answer uses {len(used_signals)} accepted evidence record(s): "
                f"{'; '.join(evidence_refs)}. Sentences are extracted from retrieved content."
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
        text = re.sub(r'\s+([.!?])', r'\1', text)

        # Remove trailing incomplete sentences
        if text and text[-1] not in '.!?':
            last_period = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
            if last_period > len(text) // 2:
                text = text[:last_period + 1]

        return text.strip() or NO_KNOWLEDGE_RESPONSE

    entity_resolver = CanonicalEntityResolver()
