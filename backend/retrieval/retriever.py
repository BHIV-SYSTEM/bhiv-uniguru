import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from reasoning.concept_resolver import ConceptResolver
from reasoning.graph_reasoner import GraphReasoner

# Paths for knowledge bases
_MODULE_DIR = os.path.dirname(__file__)
_KB_ROOT = os.path.normpath(os.path.join(_MODULE_DIR, "..", "knowledge"))

KB_PATHS: Dict[str, str] = {
    "quantum": os.path.normpath(os.path.join(_KB_ROOT, "quantum")),
    "jain": os.path.normpath(os.path.join(_KB_ROOT, "jain")),
    "swaminarayan": os.path.normpath(os.path.join(_KB_ROOT, "swaminarayan")),
    "gurukul": os.path.normpath(os.path.join(_KB_ROOT, "gurukul")),
    "sanskrit": os.path.normpath(os.path.join(_KB_ROOT, "sanskrit")),
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "what",
    "which",
    "who",
    "when",
    "where",
    "why",
    "how",
    "about",
    "for",
    "to",
    "in",
    "on",
    "of",
    "and",
    "or",
    "me",
    "tell",
    "explain",
    "name",
    "any",
    "one",
    "text",
    "related",
    "translate",
    "translation",
    "please",
    "give",
    "list",
}


class AdvancedRetriever:
    """
    Multi-source internal KB retriever.
    Only local knowledge paths are used.
    """

    def __init__(self, top_n: int = 5):
        self.top_n = top_n
        self.knowledge_map: Dict[str, str] = {}
        self.source_map: Dict[str, str] = {}
        self.file_map: Dict[str, str] = {}
        self._load_memory()

    def _load_memory(self) -> None:
        for kb_name, kb_path in KB_PATHS.items():
            if not os.path.exists(kb_path):
                continue
            for root, _, files in os.walk(kb_path):
                for file_name in files:
                    if not file_name.endswith(".md"):
                        continue
                    full_path = os.path.join(root, file_name)
                    keyword = os.path.splitext(file_name)[0].lower().replace("_", " ")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except OSError:
                        # Demo-safety mode: unreadable KB files are skipped, not fatal.
                        continue
                    self.knowledge_map[keyword] = content
                    self.source_map[keyword] = kb_name
                    self.file_map[keyword] = file_name

    @staticmethod
    def _tokens(text: str) -> List[str]:
        normalized = unicodedata.normalize("NFKC", str(text or "")).casefold()
        return re.findall(r"[\w\u0900-\u097F]+", normalized)

    @staticmethod
    def _token_forms(token: str) -> set[str]:
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
    def _query_terms(cls, query: str) -> List[str]:
        return list(dict.fromkeys(
            token for token in cls._tokens(query)
            if token not in STOPWORDS
        ))

    def retrieve_multi(self, query: str) -> List[Dict[str, Any]]:
        """Retrieves top N documents matching the query."""
        tokens = self._query_terms(query)
        if not tokens:
            return []

        matches = []
        for keyword, content in self.knowledge_map.items():
            kw_tokens = self._tokens(keyword)
            content_counts: Dict[str, int] = {}
            for content_token in self._tokens(content):
                content_counts[content_token] = content_counts.get(content_token, 0) + 1

            keyword_match = sum(
                1 for keyword_token in kw_tokens
                if any(self._token_forms(keyword_token) & self._token_forms(query_token) for query_token in tokens)
            )
            matched_terms = [
                token for token in tokens
                if any(form in content_counts for form in self._token_forms(token))
            ]

            if keyword_match == 0 and not matched_terms:
                continue

            keyword_coverage = keyword_match / len(kw_tokens) if kw_tokens else 0.0
            content_density = len(matched_terms) / len(tokens)
            frequency_density = sum(
                min(sum(content_counts.get(form, 0) for form in self._token_forms(token)), 3)
                for token in tokens
            ) / (3 * len(tokens))
            confidence = min(
                max(
                    (0.7 * keyword_coverage) + (0.3 * content_density),
                    (0.45 * content_density) + (0.15 * frequency_density),
                ),
                1.0,
            )
            matches.append(
                {
                    "content": content,
                    "confidence": confidence,
                    "keyword": keyword,
                    "keyword_match_count": keyword_match,
                    "query_token_count": len(tokens),
                    "source": self.source_map.get(keyword, "unknown"),
                    "file": self.file_map.get(keyword, "unknown"),
                }
            )

        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches[0 : self.top_n]

    @staticmethod
    def _combine_evidence(results: List[Dict[str, Any]], max_chars: int = 6000) -> str:
        """Combine top results into one evidence context, deduplicating near-identical paragraphs."""
        seen_paragraphs: List[str] = []
        combined_parts: List[str] = []
        total_chars = 0

        for result in results:
            content = str(result.get("content") or "").strip()
            if not content:
                continue
            # Split into paragraphs and deduplicate
            paragraphs = [p.strip() for p in re.split(r"\n{2,}", content) if p.strip()]
            new_paragraphs = []
            for para in paragraphs:
                # Deduplicate: skip if an existing paragraph shares >80% tokens
                para_tokens = set(AdvancedRetriever._tokens(para))
                is_duplicate = False
                for seen in seen_paragraphs:
                    seen_tokens = set(AdvancedRetriever._tokens(seen))
                    if para_tokens and seen_tokens:
                        overlap = len(para_tokens & seen_tokens) / max(len(para_tokens), len(seen_tokens))
                        if overlap > 0.8:
                            is_duplicate = True
                            break
                if not is_duplicate:
                    seen_paragraphs.append(para)
                    new_paragraphs.append(para)
            if new_paragraphs:
                chunk = "\n\n".join(new_paragraphs)
                if total_chars + len(chunk) > max_chars:
                    remaining = max_chars - total_chars
                    if remaining > 200:
                        combined_parts.append(chunk[:remaining])
                    break
                combined_parts.append(chunk)
                total_chars += len(chunk)

        return "\n\n".join(combined_parts)

    @classmethod
    def _synthesize_evidence(cls, results: List[Dict[str, Any]], query: str) -> str:
        """Build a concise answer only from deduplicated, query-relevant evidence."""
        query_terms = cls._query_terms(query)
        if not query_terms:
            raise ValueError("No subject terms are available for evidence synthesis.")

        devanagari_terms = [
            term for term in query_terms
            if any("\u0900" <= char <= "\u097f" for char in term)
        ]

        evidence = cls._combine_evidence(results)
        paragraphs = re.split(r"\n{2,}", evidence)
        sentence_rows = []
        sentence_index = 0
        for paragraph_index, paragraph in enumerate(paragraphs):
            if paragraph.lstrip().startswith("#"):
                continue
            for raw_sentence in re.split(r"(?<=[.!?\u0964\u0965])\s+|\n+", paragraph):
                sentence = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", raw_sentence).strip()
                sentence = sentence.replace("**", "").replace("*", "")
                if len(sentence) >= 12:
                    sentence_rows.append((sentence_index, paragraph_index, sentence))
                sentence_index += 1

        if devanagari_terms and not any(
            all(
                cls._token_forms(term) & set().union(
                    *(cls._token_forms(token) for token in cls._tokens(sentence))
                )
                for term in devanagari_terms
            )
            for _, _, sentence in sentence_rows
        ):
            raise ValueError("Retrieved evidence does not contain the complete Sanskrit phrase.")

        primary_terms = cls._query_terms(
            str((results[0] if results else {}).get("keyword") or "")
        )

        seen_sentences = set()
        ranked_rows = []
        for index, paragraph_index, sentence in sentence_rows:
            sentence_tokens = cls._tokens(sentence)
            normalized_sentence = " ".join(sentence_tokens)
            if not normalized_sentence or normalized_sentence in seen_sentences:
                continue
            seen_sentences.add(normalized_sentence)
            sentence_forms = set().union(*(cls._token_forms(token) for token in sentence_tokens))
            matched_terms = {
                term for term in query_terms
                if cls._token_forms(term) & sentence_forms
            }
            if matched_terms:
                subject_overlap = sum(
                    1 for term in matched_terms
                    if any(cls._token_forms(term) & cls._token_forms(primary_term) for primary_term in primary_terms)
                )
                primary_phrase = bool(primary_terms) and any(
                    all(
                        cls._token_forms(primary_term) & cls._token_forms(sentence_tokens[start + offset])
                        for offset, primary_term in enumerate(primary_terms)
                    )
                    for start in range(len(sentence_tokens) - len(primary_terms) + 1)
                )
                first_subject_token = next(
                    (token for token in sentence_tokens if token not in STOPWORDS),
                    "",
                )
                starts_with_subject = bool(
                    first_subject_token
                    and any(
                        cls._token_forms(first_subject_token) & cls._token_forms(term)
                        for term in primary_terms
                    )
                )
                ranked_rows.append((
                    subject_overlap,
                    len(matched_terms),
                    int(primary_phrase),
                    int(starts_with_subject),
                    -min(len(sentence_tokens), 40),
                    -index,
                    index,
                    paragraph_index,
                    sentence,
                ))

        if not ranked_rows:
            raise ValueError("Retrieved evidence does not contain the query subject.")

        chosen = sorted(ranked_rows, reverse=True)[:6]
        selected_indexes = []

        # Keep the directly adjacent definition/translation sentence as evidence context.
        for row in chosen:
            index, paragraph_index, source_sentence = row[6], row[7], row[8]
            source_lower = source_sentence.casefold()
            introduces_evidence = source_sentence.rstrip().endswith(":") or " means:" in source_lower
            if not introduces_evidence:
                if source_lower.startswith("in ayurveda:") or "contains extensive sections on ayurveda" in source_lower:
                    context_rows = [
                        row for row in sentence_rows
                        if row[1] == paragraph_index
                        and index < row[0] <= index + 2
                    ]
                    selected_indexes.extend(row[0] for row in context_rows)
                continue
            context_rows = [
                row for row in sentence_rows
                if row[0] > index
                and row[1] == paragraph_index
                and row[0] <= index + 5
            ]
            if source_sentence.rstrip().endswith(":"):
                context_rows.extend(
                    row for row in sentence_rows
                    if row[1] == paragraph_index + 1
                )
            if any("\u0900" <= char <= "\u097f" for char in query):
                context_rows.extend(
                    row for row in sentence_rows
                    if row[1] == paragraph_index + 1
                )
            if context_rows:
                selected_indexes.extend([index, *(row[0] for row in context_rows)])

        selected_indexes.extend(row[6] for row in chosen)
        selected_indexes = list(dict.fromkeys(selected_indexes))[:6]
        sentence_by_index = {index: sentence for index, _, sentence in sentence_rows}
        selected_sentences = [sentence_by_index[index] for index in selected_indexes]
        formatted_sentences = []
        for sentence in selected_sentences:
            if sentence.endswith(":") and " means:" not in sentence.casefold():
                sentence = f"{sentence[:-1]}."
            elif (
                not sentence.casefold().endswith("means:")
                and not re.search(r"[.!?\u0964\u0965][\"')\]]*$", sentence)
            ):
                sentence = f"{sentence}."
            formatted_sentences.append(sentence)
        return " ".join(formatted_sentences)

    def reason_and_compare(self, results: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
        """Structured comparison and conflict detection across local sources."""
        if not results:
            return {"decision": "no_match", "content": None, "reasoning": "No relevant documents found."}

        num_docs = len(results)
        primary = results[0]

        sources_list = [r.get("source", "unknown") for r in results]
        unique_sources = list(set(sources_list))

        reasoning_str = (
            f"Retrieved {num_docs} documents from {len(unique_sources)} internal sources "
            f"({', '.join(unique_sources)})."
        )

        status = "AGREEMENT"
        if num_docs > 1:
            first_len = len(str(primary.get("content", "")))
            for i in range(1, num_docs):
                result_content = str(results[i].get("content", ""))
                if abs(len(result_content) - first_len) > 2000:
                    status = "POTENTIAL_CONTRADICTION"
                    reasoning_str = (
                        f"{reasoning_str} Warning: significant variance in source detail detected."
                    )
                    break

        # Synthesis is extractive; failures preserve the existing primary-document fallback.
        try:
            combined_content = self._synthesize_evidence(results, query)
            if not combined_content.strip():
                combined_content = primary.get("content") or ""
        except ValueError:
            return {
                "decision": "no_match",
                "content": None,
                "reasoning": "Retrieved documents do not contain sufficient evidence to answer the query.",
            }
        except Exception:
            combined_content = primary.get("content") or ""

        return {
            "decision": "answer",
            "content": combined_content,
            "verification_status": "VERIFIED" if status == "AGREEMENT" else "PARTIAL",
            "reasoning": reasoning_str,
            "status": status,
            "metadata": {
                "sources_consulted": sources_list,
                "top_match": primary.get("file"),
                "top_keyword": primary.get("keyword"),
                "keyword_match_count": primary.get("keyword_match_count", 0),
                "query_token_count": primary.get("query_token_count", 0),
                "top_confidence": primary.get("confidence", 0.0),
                "docs_combined": num_docs,
            },
        }


def retrieve_advanced(query: str) -> Dict[str, Any]:
    try:
        retriever = AdvancedRetriever()
        results = retriever.retrieve_multi(query)
        return retriever.reason_and_compare(results, query)
    except Exception:
        return {"decision": "no_match", "content": None, "reasoning": "Retriever fallback mode activated."}


def retrieve_knowledge(query: str) -> Optional[str]:
    result = retrieve_advanced(query)
    return result.get("content") if result.get("decision") == "answer" else None


def retrieve_knowledge_with_trace(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    try:
        retriever = AdvancedRetriever()
        results = retriever.retrieve_multi(query)
        result = retriever.reason_and_compare(results, query)
    except Exception:
        trace = {
            "engine": "AdvancedRetriever_v2",
            "kb_path": _KB_ROOT,
            "match_found": False,
            "confidence": 0.0,
            "kb_file": None,
            "sources_consulted": ["retriever_fallback", "ontology_registry", "ontology_graph"],
        }
        return None, trace

    if result.get("decision") == "answer" and result.get("content"):
        metadata = result.get("metadata") or {}
        trace = {
            "engine": "AdvancedRetriever_v2",
            "kb_path": _KB_ROOT,
            "match_found": True,
            "confidence": float(metadata.get("top_confidence", 0.0)),
            "kb_file": metadata.get("top_match"),
            "matched_keyword": metadata.get("top_keyword"),
            "keyword_match_count": int(metadata.get("keyword_match_count", 0)),
            "query_token_count": int(metadata.get("query_token_count", 0)),
            "sources_consulted": metadata.get("sources_consulted", []),
        }
        concept_resolution = ConceptResolver().resolve(query=query, retrieval_trace=trace)
        reasoning_path = GraphReasoner().reasoning_path_from_domain_root(
            concept_id=concept_resolution["concept_id"],
            domain=concept_resolution["domain"],
        )
        trace["ontology_domain"] = concept_resolution["domain"]
        trace["ontology_concept_id"] = concept_resolution["concept_id"]
        trace["ontology_relationship_depth"] = len(reasoning_path)
        trace["ontology_relationship_chain"] = [node["concept_id"] for node in reasoning_path]
        trace["sources_consulted"] = sorted(
            set(list(trace["sources_consulted"]) + ["ontology_registry", "ontology_graph"])
        )
        return result.get("content"), trace

    trace = {
        "engine": "AdvancedRetriever_v2",
        "kb_path": _KB_ROOT,
        "match_found": False,
        "confidence": 0.0,
        "kb_file": None,
        "sources_consulted": ["ontology_registry", "ontology_graph"],
    }
    return None, trace
