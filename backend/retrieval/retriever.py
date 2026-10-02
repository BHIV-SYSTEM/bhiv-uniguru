import json
import os
import math
import re
import unicodedata
import threading
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

_DENSE_STATE: Optional[Dict[str, Any]] = None
_DENSE_STATE_KEY: Optional[Tuple[str, str, float]] = None
_DENSE_STATE_LOCK = threading.Lock()


def _active_index_paths() -> Tuple[Any, Any, Any]:
    from pathlib import Path

    rag_root = Path(_MODULE_DIR).parent / "RAG"
    pointer_path = rag_root / "active_index.json"
    pointer = {}
    if pointer_path.is_file():
        try:
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pointer = {}
    database_path = Path(os.getenv("UNIGURU_RAG_DB_PATH", rag_root / pointer.get("database_path", "chunks.db")))
    index_path = Path(os.getenv("UNIGURU_RAG_INDEX_PATH", rag_root / pointer.get("index_path", "faiss_index.bin")))
    metadata_path = Path(os.getenv("UNIGURU_RAG_METADATA_PATH", rag_root / pointer.get("metadata_path", "index_metadata.json")))
    return database_path, index_path, metadata_path


def _load_dense_state() -> Optional[Dict[str, Any]]:
    global _DENSE_STATE, _DENSE_STATE_KEY
    database_path, index_path, metadata_path = _active_index_paths()
    if not database_path.is_file() or not index_path.is_file() or not metadata_path.is_file():
        return None
    state_key = (str(database_path), str(index_path), index_path.stat().st_mtime)
    if _DENSE_STATE_KEY == state_key:
        return _DENSE_STATE
    with _DENSE_STATE_LOCK:
        if _DENSE_STATE_KEY == state_key:
            return _DENSE_STATE
        try:
            import faiss
            import sqlite3
            from sentence_transformers import SentenceTransformer

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            index = faiss.read_index(str(index_path))
            with sqlite3.connect(str(database_path)) as connection:
                row_ids = {
                    int(row[0])
                    for row in connection.execute("SELECT id FROM chunks")
                }
            index_ids = {
                int(value)
                for value in faiss.vector_to_array(index.id_map)
            } if hasattr(index, "id_map") else set()
            if int(index.ntotal) != len(row_ids) or index_ids != row_ids:
                _DENSE_STATE = None
                _DENSE_STATE_KEY = state_key
                return None
            model_name = str(metadata.get("embedding_model") or "all-MiniLM-L6-v2")
            model = SentenceTransformer(model_name)
            if int(index.d) != int(model.get_embedding_dimension()):
                _DENSE_STATE = None
                _DENSE_STATE_KEY = state_key
                return None
            _DENSE_STATE = {
                "database_path": str(database_path),
                "index": index,
                "metadata": metadata,
                "model": model,
            }
            _DENSE_STATE_KEY = state_key
            return _DENSE_STATE
        except Exception:
            _DENSE_STATE = None
            _DENSE_STATE_KEY = state_key
            return None


def warm_rag_index() -> bool:
    """Load the active vector index and model before serving user requests."""
    return _load_dense_state() is not None


def _dense_search(query: str, top_k: int = 30) -> List[Dict[str, Any]]:
    state = _load_dense_state()
    if state is None:
        return []
    try:
        import numpy as np
        import sqlite3

        vector = state["model"].encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        scores, ids = state["index"].search(np.asarray(vector, dtype="float32"), top_k)
        results = []
        with sqlite3.connect(state["database_path"]) as connection:
            for score, chunk_id in zip(scores[0], ids[0]):
                if int(chunk_id) < 0:
                    continue
                row = connection.execute(
                    """SELECT file_name, page_number, text, domain, category, topic,
                              chapter, source, language, chunk_number
                       FROM chunks WHERE id = ?""",
                    (int(chunk_id),),
                ).fetchone()
                if row:
                    results.append({
                        "file_name": row[0],
                        "page_number": row[1],
                        "text": row[2],
                        "domain": row[3],
                        "category": row[4],
                        "topic": row[5],
                        "chapter": row[6],
                        "source": row[7],
                        "language": row[8],
                        "chunk_number": row[9],
                        "score": float(score),
                        "chunk_id": int(chunk_id),
                    })
        return results
    except Exception:
        return []

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
    "it",
    "simply",
    "can",
    "you",
    "your",
    "my",
    "i",
    "me",
    "could",
    "would",
    "should",
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
        self.path_map: Dict[str, str] = {}
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
                    key = keyword
                    if key in self.knowledge_map:
                        relative_path = os.path.relpath(full_path, _KB_ROOT)
                        key = os.path.splitext(relative_path)[0].replace(os.sep, "/").lower()
                    self.knowledge_map[key] = content
                    self.source_map[key] = kb_name
                    self.file_map[key] = file_name
                    self.path_map[key] = os.path.relpath(full_path, _KB_ROOT).replace(os.sep, "/")

    @staticmethod
    def _tokens(text: str) -> List[str]:
        normalized = unicodedata.normalize("NFKC", str(text or "")).casefold()
        return re.findall(r"[\w\u0900-\u097F]+", normalized)

    @staticmethod
    def _token_forms(token: str) -> set[str]:
        forms = {token}
        if token == "agriculture":
            forms.add("agricultural")
        elif token == "agricultural":
            forms.add("agriculture")
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

    @staticmethod
    def _source_entity_terms(query: str) -> set[str]:
        source_suffixes = r"purana|purāṇa|sutra|sūtra|gita|gītā|upanishad|veda"
        matches = re.findall(rf"\b([\w]+)\s+({source_suffixes})\b", query.casefold())
        return {
            term
            for match in matches
            for term in match
            if term not in STOPWORDS
        }

    def retrieve_multi(self, query: str) -> List[Dict[str, Any]]:
        """Retrieve topic-supported documents and honor explicit source entities."""
        tokens = self._query_terms(query)
        if not tokens:
            return []

        source_terms = self._source_entity_terms(query)
        topic_terms = [token for token in tokens if not (self._token_forms(token) & source_terms)]
        query_forms = {token: self._token_forms(token) for token in tokens}
        document_rows = []
        dense_by_key: Dict[str, Dict[str, Any]] = {}
        dense_candidates = _dense_search(query, top_k=30) if getattr(self, "path_map", None) else []
        for chunk in dense_candidates:
            source_path = str(chunk.get("source") or chunk.get("file_name") or "").replace("\\", "/")
            chunk_tokens = set(self._tokens(chunk.get("text", "")))
            source_tokens = set(self._tokens(f"{source_path} {chunk.get('topic') or ''} {chunk.get('chapter') or ''}"))
            combined_tokens = chunk_tokens | source_tokens
            if source_terms and not all(
                any(form in combined_tokens for form in self._token_forms(term))
                for term in source_terms
            ):
                continue
            matched_topics = [
                term for term in topic_terms
                if self._token_forms(term) & chunk_tokens
            ]
            minimum_dense_score = float(os.getenv("UNIGURU_DENSE_SCORE_MIN", "0.35"))
            if source_terms and topic_terms and not matched_topics:
                continue
            if not matched_topics and float(chunk["score"]) < minimum_dense_score:
                continue
            lexical_key = next(
                (key for key, path in getattr(self, "path_map", {}).items() if path.casefold() == source_path.casefold()),
                None,
            )
            dense_key = lexical_key or os.path.splitext(source_path)[0].casefold()
            current = dense_by_key.get(dense_key)
            if current is None or chunk["score"] > current["dense_score"]:
                dense_by_key[dense_key] = {
                    "content": chunk["text"],
                    "tokens": self._tokens(chunk["text"]),
                    "counts": {},
                    "title_tokens": source_tokens,
                    "matched_terms": matched_topics,
                    "matched_topics": matched_topics,
                    "keyword": dense_key,
                    "dense_score": chunk["score"],
                    "chunk": chunk,
                    "source_path": source_path,
                    "source": chunk.get("domain") or "unknown",
                    "file": os.path.basename(source_path),
                }

        for dense_key, row in dense_by_key.items():
            row["counts"] = {token: row["tokens"].count(token) for token in set(row["tokens"])}
            row["dense_chunk"] = row["chunk"]
            document_rows.append(row)

        for keyword, content in self.knowledge_map.items():
            content_tokens = self._tokens(content)
            title = f"{keyword} {self.file_map.get(keyword, '')} {getattr(self, 'path_map', {}).get(keyword, '')}"
            title_tokens = set(self._tokens(title))
            content_token_set = set(content_tokens)
            document_forms = content_token_set | title_tokens
            if source_terms and not all(
                any(form in document_forms for form in self._token_forms(term))
                for term in source_terms
            ):
                continue

            matched_terms = [token for token in tokens if query_forms[token] & document_forms]
            matched_topics = [token for token in topic_terms if query_forms[token] & content_token_set]
            if not matched_terms or (source_terms and topic_terms and not matched_topics):
                continue

            source_path = getattr(self, "path_map", {}).get(keyword)
            if source_path and any(
                row.get("source_path", "").casefold() == source_path.casefold()
                for row in document_rows
            ):
                continue

            token_counts: Dict[str, int] = {}
            for token in content_tokens:
                token_counts[token] = token_counts.get(token, 0) + 1
            document_rows.append(
                {
                    "keyword": keyword,
                    "content": content,
                    "tokens": content_tokens,
                    "counts": token_counts,
                    "title_tokens": title_tokens,
                    "matched_terms": matched_terms,
                    "matched_topics": matched_topics,
                }
            )

        if not document_rows:
            return []

        document_frequency: Dict[str, int] = {token: 0 for token in tokens}
        for row in document_rows:
            content_tokens = set(row["tokens"])
            for token in tokens:
                if query_forms[token] & content_tokens:
                    document_frequency[token] += 1

        average_length = sum(len(row["tokens"]) for row in document_rows) / len(document_rows) or 1.0
        lexical_scores: Dict[str, float] = {}
        entity_scores: Dict[str, float] = {}
        dense_scores: Dict[str, float] = {}
        for row in document_rows:
            keyword = row["keyword"]
            length = max(len(row["tokens"]), 1)
            bm25_score = 0.0
            for token in tokens:
                term_frequency = sum(row["counts"].get(form, 0) for form in query_forms[token])
                if not term_frequency:
                    continue
                document_count = len(document_rows)
                document_freq = document_frequency[token]
                inverse_document_frequency = math.log1p(
                    (document_count - document_freq + 0.5) / (document_freq + 0.5)
                )
                bm25_score += inverse_document_frequency * (
                    term_frequency * 2.5
                    / (term_frequency + 1.5 * (0.25 + 0.75 * length / average_length))
                )
            lexical_scores[keyword] = bm25_score
            entity_scores[keyword] = (
                (len(source_terms) * 2 if source_terms else 0)
                + len(set(tokens) & row["title_tokens"])
                + int(" ".join(tokens) in " ".join(row["tokens"]))
            )
            dense_scores[keyword] = float(row.get("dense_score", 0.0))

        fused_scores: Dict[str, float] = {}
        for ranking in (
            sorted(lexical_scores, key=lexical_scores.get, reverse=True),
            sorted(entity_scores, key=entity_scores.get, reverse=True),
            sorted(dense_scores, key=dense_scores.get, reverse=True),
        ):
            for rank, keyword in enumerate(ranking, start=1):
                fused_scores[keyword] = fused_scores.get(keyword, 0.0) + 1.0 / (60 + rank)

        rows_by_key = {row["keyword"]: row for row in document_rows}
        results = []
        for keyword in sorted(fused_scores, key=fused_scores.get, reverse=True)[: self.top_n]:
            row = rows_by_key[keyword]
            coverage = (
                len(row["matched_topics"]) / len(topic_terms)
                if topic_terms else len(row["matched_terms"]) / len(tokens)
            )
            results.append(
                {
                    "content": row["content"],
                    "confidence": coverage,
                    "retrieval_score": fused_scores[keyword],
                    "fusion_score": fused_scores[keyword],
                    "bm25_score": lexical_scores[keyword],
                    "entity_score": entity_scores[keyword],
                    "dense_score": dense_scores[keyword],
                    "evidence_coverage": coverage,
                    "keyword": keyword,
                    "keyword_match_count": len(set(tokens) & row["title_tokens"]),
                    "query_token_count": len(tokens),
                    "source": row.get("source", self.source_map.get(keyword, "unknown")),
                    "file": row.get("file", self.file_map.get(keyword, "unknown")),
                    "path": row.get("source_path", getattr(self, "path_map", {}).get(keyword, keyword)),
                    "matched_terms": row["matched_terms"],
                    "dense_chunk": row.get("dense_chunk"),
                }
            )
        results.sort(
            key=lambda row: (
                row["evidence_coverage"],
                row["entity_score"],
                row["bm25_score"],
                row["fusion_score"],
            ),
            reverse=True,
        )
        return results

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

        seen_sentences = set()
        ranked_rows = []
        for index, paragraph_index, sentence in sentence_rows:
            sentence_tokens = cls._tokens(sentence)
            normalized_sentence = " ".join(sentence_tokens)
            if not normalized_sentence or normalized_sentence in seen_sentences:
                continue
            seen_sentences.add(normalized_sentence)
            sentence_forms = set().union(*(cls._token_forms(token) for token in sentence_tokens))
            overlap = sum(1 for term in query_terms if cls._token_forms(term) & sentence_forms)
            if overlap:
                ranked_rows.append((overlap, -index, index, paragraph_index, sentence))

        if not ranked_rows:
            raise ValueError("Retrieved evidence does not contain the query subject.")

        chosen = sorted(ranked_rows, key=lambda row: (row[0], row[1]), reverse=True)[:6]
        selected_indexes = []

        # Keep the directly adjacent definition/translation sentence as evidence context.
        for _, _, index, paragraph_index, source_sentence in chosen:
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

        selected_indexes.extend(row[2] for row in chosen)
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
                "retrieval_score": primary.get("fusion_score", 0.0),
                "evidence_coverage": primary.get("evidence_coverage", 0.0),
                "evidence_sources": [
                    {
                        "source": result.get("source", "unknown"),
                        "file": result.get("file", "unknown"),
                        "path": result.get("path", result.get("file", "unknown")),
                        "chunk_id": (result.get("dense_chunk") or {}).get("chunk_id"),
                        "page_number": (result.get("dense_chunk") or {}).get("page_number"),
                        "chapter": (result.get("dense_chunk") or {}).get("chapter"),
                        "excerpt": str(
                            (result.get("dense_chunk") or {}).get("text")
                            or result.get("content")
                            or ""
                        )[:1200],
                        "evidence_coverage": result.get("evidence_coverage", 0.0),
                    }
                    for result in results
                ],
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
            "retrieval_score": float(metadata.get("retrieval_score", 0.0)),
            "reranker_score": float(metadata.get("evidence_coverage", 0.0)),
            "evidence_coverage": float(metadata.get("evidence_coverage", 0.0)),
            "answer_confidence": None,
            "kb_file": metadata.get("top_match"),
            "matched_keyword": metadata.get("top_keyword"),
            "keyword_match_count": int(metadata.get("keyword_match_count", 0)),
            "query_token_count": int(metadata.get("query_token_count", 0)),
            "evidence_sources": metadata.get("evidence_sources", []),
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


def get_rag_health() -> Dict[str, Any]:
    """Report only artifacts used by this checkout's active retrieval path."""
    from pathlib import Path

    rag_root = Path(_MODULE_DIR).parent / "RAG"
    database_path, index_path, metadata_path = _active_index_paths()
    source_files = [
        path for path in Path(_KB_ROOT).rglob("*.md")
        if path.is_file()
    ] if Path(_KB_ROOT).is_dir() else []
    retriever = AdvancedRetriever()
    database_chunks = 0
    vector_chunks = 0
    metadata_available = database_path.is_file()
    metadata = {}
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
    if metadata_available:
        try:
            import sqlite3

            with sqlite3.connect(str(database_path)) as connection:
                database_chunks = int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
        except (OSError, sqlite3.Error):
            metadata_available = False

    index_available = index_path.is_file()
    index_type = None
    embedding_dimension = None
    if index_available:
        try:
            import faiss

            index = faiss.read_index(str(index_path))
            index_type = type(index).__name__
            embedding_dimension = int(index.d)
            vector_chunks = int(index.ntotal)
        except Exception:
            index_available = False

    index_loaded = (
        index_available
        and metadata_available
        and database_chunks > 0
        and vector_chunks == database_chunks
        and _load_dense_state() is not None
    )
    return {
        "status": "healthy" if index_loaded else ("degraded" if retriever.knowledge_map else "unavailable"),
        "active_retrieval": "FAISS dense + BM25 + exact-title/entity RRF",
        "source_root": str(Path(_KB_ROOT)),
        "source_documents": len(source_files),
        "lexical_documents_loaded": len(retriever.knowledge_map),
        "index": "loaded" if index_loaded else "missing_or_invalid",
        "index_path": str(index_path),
        "index_type": index_type,
        "index_version": metadata.get("index_version") or metadata.get("created_at"),
        "embedding_model": metadata.get("embedding_model") if index_loaded else None,
        "embedding_dimension": embedding_dimension,
        "indexed_chunks": vector_chunks if index_loaded else 0,
        "metadata_available": metadata_available,
        "metadata_database": str(database_path),
        "metadata_chunk_count": database_chunks if metadata_available else 0,
        "vector_count": vector_chunks,
        "metadata_claimed_chunks": metadata.get("total_chunks"),
        "indexed_documents": metadata.get("indexed_documents", 0) if index_loaded else 0,
        "chunking": (
            f"Character windows of {metadata.get('chunk_size')} with {metadata.get('chunk_overlap')} overlap."
            if index_loaded else "No active vector chunks; lexical retrieval scans Markdown documents."
        ),
    }
