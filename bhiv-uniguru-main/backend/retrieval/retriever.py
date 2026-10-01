from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import sys
_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
from typing import Any, Dict, List, Optional, Tuple

try:
    from retrieval.kb_engine import retrieve as kb_retrieve, retrieve_with_candidates as kb_retrieve_with_candidates
except ImportError:
    from backend.retrieval.kb_engine import retrieve as kb_retrieve, retrieve_with_candidates as kb_retrieve_with_candidates

try:
    from utils.rag_logger import log_retrieval_result, log_rag_error
except ImportError:
    try:
        from backend.utils.rag_logger import log_retrieval_result, log_rag_error
    except ImportError:
        def log_retrieval_result(*args, **kwargs): pass
        def log_rag_error(*args, **kwargs): pass


logger = logging.getLogger("uniguru.retrieval")

NO_KNOWLEDGE_ANSWER = "I do not have verified knowledge to answer this question."
_QUERY_CACHE: Dict[str, Tuple[Optional[str], Dict[str, Any], float]] = {}
CACHE_TTL_SECONDS = int(os.getenv("UNIGURU_RETRIEVAL_CACHE_TTL", "3600"))
KB_CONFIDENCE_MIN = float(os.getenv("UNIGURU_KB_CONFIDENCE_MIN", "0.30"))
KOSHA_CONFIDENCE_MIN = float(os.getenv("UNIGURU_KOSHA_CONFIDENCE_MIN", "0.15"))
FAISS_SCORE_MIN = float(os.getenv("UNIGURU_FAISS_SCORE_MIN", "0.35"))


def _normalize_trace(
    *,
    query: str,
    content: Optional[str],
    confidence: float,
    match_found: bool,
    method: str,
    source: Optional[str],
    verification_status: str,
    latency_ms: float,
    extra: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Dict[str, Any]]:
    trace: Dict[str, Any] = {
        "query": query,
        "match_found": match_found,
        "confidence": round(confidence, 4),
        "method": method,
        "source": source,
        "kb_file": source,
        "verification_status": verification_status,
        "latency_ms": round(latency_ms, 2),
        "sources_consulted": [method],
    }
    if extra:
        trace.update(extra)
    return content, trace


def _try_kosha(query: str, subject: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any], float]:
    start = time.perf_counter()
    try:
        from kosha.deterministic_pipeline import run_deterministic_pipeline

        result = run_deterministic_pipeline(query)
        latency = (time.perf_counter() - start) * 1000
        status = str(result.get("verification_status") or "")
        answer = str(result.get("answer") or "").strip()
        confidence = float(result.get("confidence") or result.get("confidence_breakdown", {}).get("overall", 0.0))

        if status == "VERIFIED" and answer and answer != NO_KNOWLEDGE_ANSWER and confidence >= KOSHA_CONFIDENCE_MIN:
            source = None
            matched = result.get("matched_signals") or []
            if matched:
                source = matched[0].get("source")
            content, trace = _normalize_trace(
                query=query,
                content=answer,
                confidence=confidence,
                match_found=True,
                method="kosha_deterministic",
                source=source,
                verification_status="VERIFIED",
                latency_ms=latency,
                extra={
                    "signals_used": len(matched),
                    "trace_id": result.get("trace_id"),
                    "similarity_scores": [float(s.get("confidence") or 0.0) for s in matched[:5]],
                },
            )
            return content, trace, latency

        return None, {
            "match_found": False,
            "confidence": confidence,
            "method": "kosha_deterministic",
            "verification_status": status or "NO_VERIFIED_KNOWLEDGE",
            "latency_ms": round(latency, 2),
            "signals_rejected": result.get("signals_rejected", 0),
        }, latency
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        log_rag_error("kosha_retrieval", query, str(exc))
        return None, {"match_found": False, "confidence": 0.0, "method": "kosha_deterministic", "error": str(exc)}, latency


def _clean_candidate_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"(?is)---\s*(?:title|source|url|verification_status|category)\s*:.*?---", " ", text)
    text = re.sub(r"\s*\[[0-9]+\]\s*", " ", text)
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"(?m)^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", text)
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    paragraphs = []
    seen_paragraphs = set()
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = re.sub(r"[ \t]+", " ", paragraph).strip()
        key = paragraph.lower()
        if paragraph and key not in seen_paragraphs:
            seen_paragraphs.add(key)
            paragraphs.append(paragraph)
    return "\n\n".join(paragraphs)


def synthesize_retrieval_answer(query: str, candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return ""

    stopwords = {
        "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be", "to", "of",
        "in", "on", "for", "from", "with", "what", "which", "who", "how", "why", "any", "one",
        "name", "text", "related", "purpose", "translate",
    }
    query_terms = {
        token.lower()
        for token in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", query)
        if len(token) > 1 and token.lower() not in stopwords
    }
    if "ayurveda" in query_terms:
        query_terms.update({"ayurvedic", "charaka", "sushruta"})
    if "\u0905\u0939\u093f\u0902\u0938\u093e" in query_terms:
        query_terms.update({"ahimsa", "nonviolence", "violence"})

    def paragraph_matches(paragraph: str) -> bool:
        paragraph_terms = {
            token.lower()
            for token in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", paragraph)
        }
        return any(
            term in paragraph_terms or term.rstrip("s") in paragraph_terms
            for term in query_terms
        )

    seen_paragraphs = set()
    seen_sentences = set()
    selected_sentences: List[str] = []
    ranked = sorted(
        candidates,
        key=lambda item: float(item.get("score") or 0.0),
        reverse=True,
    )

    for candidate in ranked[:5]:
        content = _clean_candidate_text(candidate.get("content") or "")
        if not content:
            continue
        if re.search(r"\bi don't know\b|not explicitly|provided context does not", content, re.IGNORECASE):
            continue
        candidate_sentence_count = 0
        for paragraph in content.split("\n\n"):
            paragraph_key = re.sub(r"\s+", " ", paragraph).strip().lower()
            if not paragraph_key or paragraph_key in seen_paragraphs or not paragraph_matches(paragraph):
                continue
            seen_paragraphs.add(paragraph_key)
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", paragraph):
                sentence = sentence.strip()
                if not sentence:
                    continue
                normalized = re.sub(r"\s+([,.!?;:])", r"\1", re.sub(r"\s+", " ", sentence)).strip()
                key = normalized.lower()
                if key.startswith("also mentions ") or re.search(r"\b(?:according to|and|or|of)$", key):
                    continue
                if key in seen_sentences:
                    continue
                seen_sentences.add(key)
                selected_sentences.append(normalized)
                candidate_sentence_count += 1
                if candidate_sentence_count >= 2:
                    break
                if len(selected_sentences) >= 6:
                    break
            if candidate_sentence_count >= 2 or len(selected_sentences) >= 6:
                break
        if len(selected_sentences) >= 6:
            break

    return " ".join(selected_sentences[:6]).strip()


def _try_keyword_kb(query: str, subject: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any], float]:
    start = time.perf_counter()
    try:
        # Pass subject selection into KB retrieval so callers can restrict domains
        try:
            result = kb_retrieve_with_candidates(query, subject=subject)
        except TypeError:
            # backward compatibility if kb_engine not updated
            result = kb_retrieve_with_candidates(query)
        latency = (time.perf_counter() - start) * 1000
        answer = str(result.get("answer") or "").strip()
        candidates = result.get("candidates") or []
        if candidates:
            try:
                synthesized = synthesize_retrieval_answer(query, candidates)
                if synthesized:
                    answer = synthesized
            except Exception as exc:
                logger.warning("Candidate synthesis failed; preserving the existing KB answer: %s", exc)
        confidence = float(result.get("confidence_level") or 0.0)
        verified = bool(result.get("verified")) and answer != NO_KNOWLEDGE_ANSWER

        if verified and confidence >= KB_CONFIDENCE_MIN:
            content, trace = _normalize_trace(
                query=query,
                content=answer,
                confidence=confidence,
                match_found=True,
                method="keyword_kb",
                source=result.get("source_file"),
                verification_status="VERIFIED",
                latency_ms=latency,
                extra={
                    "candidate_count": len(result.get("candidates") or []),
                },
            )
            return content, trace, latency
        return None, {
            "match_found": False,
            "confidence": confidence,
            "method": "keyword_kb",
            "latency_ms": round(latency, 2),
        }, latency
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        log_rag_error("keyword_kb", query, str(exc))
        return None, {"match_found": False, "confidence": 0.0, "method": "keyword_kb", "error": str(exc)}, latency


def _try_markdown_search(query: str, subject: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any], float]:
    """Full-text scan of knowledge/*.md when index misses."""
    start = time.perf_counter()
    kb_root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "knowledge"))
    query_lower = query.lower()
    stopwords = {
        "the", "a", "an", "and", "or", "but", "if", "then", "else", "is", "are", "was", "were",
        "be", "been", "being", "to", "of", "in", "on", "at", "by", "for", "from", "as", "with",
        "about", "into", "over", "under", "who", "whom", "whose", "what", "which", "when", "where",
        "why", "how", "any", "one", "name", "text", "related",
    }
    query_terms = {
        t for t in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", query_lower)
        if len(t) > 2 and t not in stopwords
    }
    if not query_terms:
        return None, {"match_found": False, "confidence": 0.0, "method": "markdown_search"}, 0.0

    def calculate_score(query_terms: set, doc: Dict[str, Any]) -> float:
        score = 0
        title_terms = set(re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", str(doc.get("title", "")).lower()))
        content_terms = set(re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", str(doc.get("content", "")).lower()))
        source_terms = set(re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", str(doc.get("source", "")).lower()))
        category_terms = set(re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", str(doc.get("category", "")).lower()))

        for term in query_terms:
            if term in title_terms:
                score += 5
            if term in source_terms:
                score += 4
            if term in category_terms:
                score += 4
            if term in content_terms:
                score += 1

        # bio and topic priority
        if "biography" in query_lower:
            if "biography" in source_terms:
                score += 10
            if "life" in title_terms:
                score += 8

        if "upanishad" in query_lower or "purana" in query_lower or "ayurveda" in query_lower:
            if "upanishad" in title_terms or "upanishad" in category_terms or "upanishad" in source_terms:
                score += 4
            if "purana" in title_terms or "purana" in category_terms or "purana" in source_terms:
                score += 4
            if "ayurveda" in title_terms or "ayurveda" in category_terms or "ayurveda" in source_terms:
                score += 4

        return score

    candidates: List[Dict[str, Any]] = []

    try:
        for root, _dirs, files in os.walk(kb_root):
            for file_name in files:
                if not file_name.endswith(".md"):
                    continue
                path = os.path.join(root, file_name)
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        text = handle.read()
                except OSError:
                    continue

                rel_path = os.path.relpath(path, kb_root)
                category = os.path.dirname(rel_path).replace("\\", "/")
                stem = os.path.splitext(file_name)[0]
                title = stem.replace("_", " ").strip()
                document = {
                    "title": title,
                    "content": text,
                    "source": file_name,
                    "category": category,
                    "path": path,
                }
                score = calculate_score(query_terms, document)
                if score <= 0:
                    continue
                candidates.append(
                    {
                        "score": score,
                        "document": document,
                        "content": text,
                        "source": file_name,
                    }
                )

        candidates.sort(key=lambda item: item["score"], reverse=True)

        latency = (time.perf_counter() - start) * 1000
        if candidates:
            best = candidates[0]
            best_score = float(best["score"])
            best_source = best["source"]

            selected_bodies = []
            seen = set()
            for candidate in candidates[:5]:
                body = re.sub(r"^---[\s\S]*?---\n*", "", candidate["content"], flags=re.MULTILINE).strip()
                normalized = re.sub(r"\s+", " ", body).strip()[:400]
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                selected_bodies.append(body)
                if len(selected_bodies) >= 5:
                    break

            combined_body = "\n\n".join(selected_bodies)
            if len(combined_body) > 2500:
                combined_body = combined_body[:2500].rsplit(" ", 1)[0] + "..."

            doc_title = str(best.get("document", {}).get("title", "")).lower()
            conf_val = 0.95 if any(t in doc_title for t in query_terms) else min(max(round(best_score / 15.0, 4), 0.75), 0.98)
            content, trace = _normalize_trace(
                query=query,
                content=combined_body,
                confidence=conf_val,
                match_found=True,
                method="markdown_search",
                source=best_source,
                verification_status="VERIFIED",
                latency_ms=latency,
                extra={
                    "matched_terms": len(query_terms),
                    "document_count": len(candidates),
                    "similarity_scores": [float(item["score"]) for item in candidates[:5]],
                },
            )
            return content, trace, latency
        return None, {"match_found": False, "confidence": 0.0, "method": "markdown_search", "latency_ms": round(latency, 2)}, latency
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        log_rag_error("markdown_search", query, str(exc))
        return None, {"match_found": False, "confidence": 0.0, "method": "markdown_search", "error": str(exc)}, latency


_semantic_engine = None
_faiss_available: Optional[bool] = None


def _get_semantic_engine():
    global _semantic_engine, _faiss_available
    if _faiss_available is False:
        return None
    if _semantic_engine is not None:
        return _semantic_engine
    try:
        try:
            from RAG.new_rag_query import get_engine
        except ImportError:
            from backend.RAG.new_rag_query import get_engine

        base_dir = os.path.join(os.path.dirname(__file__), "..", "RAG")
        faiss_path = os.path.join(base_dir, "faiss_index.bin")
        db_path = os.path.join(base_dir, "chunks.db")
        if not (os.path.exists(faiss_path) and os.path.exists(db_path)):
            _faiss_available = False
            logger.warning("FAISS index or chunks.db missing; semantic retrieval disabled.")
            return None
        _semantic_engine = get_engine()
        _faiss_available = True
        return _semantic_engine
    except Exception as exc:
        _faiss_available = False
        logger.warning("Semantic engine unavailable: %s", exc)
        return None



def _try_sanskrit_decoder(query: str, subject: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any], float]:
    start = time.perf_counter()
    try:
        try:
            from uniguru_sanskrit_decoder import decode_sanskrit_concept
        except ImportError:
            try:
                from backend.uniguru_sanskrit_decoder import decode_sanskrit_concept
            except ImportError:
                decode_sanskrit_concept = None

        if decode_sanskrit_concept is None:
            return None, {"match_found": False, "confidence": 0.0, "method": "sanskrit_decoder"}, 0.0

        try:
            from service.query_classifier import is_sanskrit_knowledge_query, extract_question_from_mixed
        except ImportError:
            from backend.service.query_classifier import is_sanskrit_knowledge_query, extract_question_from_mixed

        cleaned_query = extract_question_from_mixed(query).strip(" ?.,!")
        if is_sanskrit_knowledge_query(cleaned_query):
            words = [w for w in re.findall(r"[a-zA-Z\u0900-\u097F]+", cleaned_query) if len(w) > 2 and w.lower() not in {"what", "is", "the", "explain", "meaning", "tell", "about", "concept", "define"}]
            concept = " ".join(words) if words else cleaned_query
            decoded = decode_sanskrit_concept(concept)
            if decoded and (decoded.get("canonical_concept") or decoded.get("pipeline")):
                latency = (time.perf_counter() - start) * 1000
                summary = decoded.get("semantic_summary") or decoded.get("functional_meaning") or ""
                pipeline_details = [f"- {st.get('stage')}: {st.get('detail')}" for st in decoded.get("pipeline", [])[:4] if st.get("detail")]
                pipeline_text = "\n".join(pipeline_details)
                content = f"Sanskrit Knowledge Analysis ({decoded.get('canonical_concept')}):\n{summary}\n\nKey Dimensions:\n{pipeline_text}" if pipeline_text else summary
                content, trace = _normalize_trace(
                    query=query,
                    content=content,
                    confidence=0.88,
                    match_found=True,
                    method="sanskrit_decoder",
                    source=f"sanskrit_decoder:{decoded.get('canonical_concept')}",
                    verification_status="VERIFIED",
                    latency_ms=latency,
                    extra={
                        "canonical_concept": decoded.get("canonical_concept"),
                        "epistemic_domain": decoded.get("epistemic_domain"),
                    }
                )
                return content, trace, latency
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return None, {"match_found": False, "confidence": 0.0, "method": "sanskrit_decoder", "error": str(exc)}, latency
    return None, {"match_found": False, "confidence": 0.0, "method": "sanskrit_decoder"}, 0.0

def _try_faiss(query: str, top_k: int = 5, subject: Optional[str] = None, class_level: Optional[str] = None, language: Optional[str] = None, domain: Optional[str] = None, doc_type: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any], float]:
    start = time.perf_counter()
    engine = _get_semantic_engine()
    if engine is None:
        return None, {"match_found": False, "confidence": 0.0, "method": "faiss_semantic", "reason": "index_unavailable"}, 0.0

    try:
        results = engine.retrieve(query, top_k=20, subject=subject, class_level=class_level, language=language, domain=domain, doc_type=doc_type)
        
        # Rerank
        try:
            from retrieval.reranker import reranker
            results = reranker.rerank_and_filter(results, expected_class=class_level, expected_subject=subject, top_k=top_k)
        except Exception as e:
            logger.error(f"Reranking error: {e}")
            results = results[:top_k]

        latency = (time.perf_counter() - start) * 1000
        if not results:
            return None, {"match_found": False, "confidence": 0.0, "method": "faiss_semantic", "latency_ms": round(latency, 2)}, latency

        scores = [float(r.get("score") or 0.0) for r in results]
        best = results[0]
        best_score = float(best.get("score") or 0.0)
        # FAISS IndexFlatL2 returns Euclidean distance. Convert to cosine similarity:
        cosine_sim = max(0.0, 1.0 - (best_score ** 2) / 2.0) if best_score <= 2.0 else 0.0
        # Require meaningful semantic similarity (>= 0.48 cosine similarity) and maximum distance 1.02
        if cosine_sim < 0.48 or best_score > 1.02:
            return None, {
                "match_found": False,
                "confidence": round(cosine_sim, 4),
                "method": "faiss_semantic",
                "similarity_scores": scores,
                "latency_ms": round(latency, 2),
                "reason": "below_similarity_threshold",
            }, latency

        context_parts = []
        for i, chunk in enumerate(results[:3]):
            meta = chunk.get("metadata") or {}
            context_parts.append(
                f"[{i + 1}] {meta.get('file_name', 'unknown')} (p.{meta.get('page_number', '?')}): {chunk.get('text', '')[:800]}"
            )
        content = "\n\n".join(context_parts)
        source = (best.get("metadata") or {}).get("file_name")

        content, trace = _normalize_trace(
            query=query,
            content=content,
            confidence=round(cosine_sim, 4),
            match_found=True,
            method="faiss_semantic",
            source=source,
            verification_status="VERIFIED",
            latency_ms=latency,
            extra={"similarity_scores": scores, "document_count": len(results)},
        )
        return content, trace, latency
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        log_rag_error("faiss_semantic", query, str(exc))
        return None, {"match_found": False, "confidence": 0.0, "method": "faiss_semantic", "error": str(exc)}, latency


def _try_balbharati(query: str, subject: Optional[str] = None, class_level: Optional[str] = None, language: Optional[str] = None, domain: Optional[str] = None, doc_type: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any], float]:
    start = time.perf_counter()
    try:
        from retrieval.balbharati.hybrid_retriever import get_balbharati_retriever
        from retrieval.balbharati.answer_synthesizer import BalbharatiAnswerSynthesizer
        from retrieval.balbharati.metadata_extractor import extract_balbharati_metadata

        meta = extract_balbharati_metadata(query)
        std_val = int(class_level) if class_level and str(class_level).isdigit() else meta.standard
        retriever = get_balbharati_retriever()
        result = retriever.search_hybrid(
            query=query,
            standard=std_val,
            medium=meta.medium,
            subject=subject or meta.subject,
            top_k=5,
        )
        latency = (time.perf_counter() - start) * 1000
        conf = float(result.get("confidence", 0.0))
        results = result.get("results", [])

        if results and conf >= 0.35:
            synthesizer = BalbharatiAnswerSynthesizer(confidence_threshold=0.35)
            synth = synthesizer.synthesize(query, result)
            top = results[0]
            content = synth["answer"]
            source_str = f"Balbharati:Std_{top.get('standard')}_{top.get('subject')}_p{top.get('page')}"
            content, trace = _normalize_trace(
                query=query,
                content=content,
                confidence=conf,
                match_found=True,
                method="balbharati_hybrid",
                source=source_str,
                verification_status="VERIFIED",
                latency_ms=latency,
                extra={
                    "balbharati_metadata": result.get("detected_metadata"),
                    "citations": synth.get("citations", []),
                    "evidence_chunks": synth.get("evidence_chunks", []),
                    "book_title": top.get("book"),
                    "chapter": top.get("chapter"),
                    "page_number": top.get("page"),
                    "standard": top.get("standard"),
                    "subject": top.get("subject"),
                    "medium": top.get("medium"),
                },
            )
            return content, trace, latency
        return None, {"match_found": False, "confidence": conf, "method": "balbharati_hybrid", "latency_ms": round(latency, 2)}, latency
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        log_rag_error("balbharati_hybrid", query, str(exc))
        return None, {"match_found": False, "confidence": 0.0, "method": "balbharati_hybrid", "error": str(exc)}, latency


def retrieve_knowledge_with_trace(query: str, subject: Optional[str] = None, class_level: Optional[str] = None, language: Optional[str] = None, domain: Optional[str] = None, doc_type: Optional[str] = None) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Unified synchronous retrieval cascade:
    Kosha (deterministic) -> keyword index -> markdown full-text -> FAISS semantic.
    """
    # Detect programming intent from the query and override subject when necessary
    programming_indicators = [
        "python",
        "javascript",
        "java",
        "c++",
        "c#",
        "sort",
        "list",
        "array",
        "function",
        "loop",
        "for loop",
        "lambda",
        "pip",
        "numpy",
        "pandas",
        "django",
        "flask",
        "script",
        "code",
        "program",
        "programming",
    ]

    qlower = query.lower()
    if any(ind in qlower for ind in programming_indicators):
        logger.info("Programming intent detected in query; constraining retrieval to Programming domain")
        subject = "Programming"
    try:
        from service.query_classifier import is_unknown_or_fictional
    except ImportError:
        from backend.service.query_classifier import is_unknown_or_fictional

    if is_unknown_or_fictional(query):
        trace = {
            "match_found": False,
            "confidence": 0.0,
            "method": "unknown_fictional_guard",
            "verification_status": "NO_VERIFIED_KNOWLEDGE",
            "sources_consulted": ["unknown_fictional_guard"],
        }
        log_retrieval_result(query, method="unknown_fictional_guard", match_found=False, confidence=0.0, source=None)
        return None, trace

    from kosha.signal_validator import SignalValidator

    if SignalValidator.is_off_topic_query(query):
        trace = {
            "match_found": False,
            "confidence": 0.0,
            "method": "off_topic_guard",
            "verification_status": "NO_VERIFIED_KNOWLEDGE",
            "sources_consulted": ["off_topic_guard"],
        }
        log_retrieval_result(query, method="off_topic_guard", match_found=False, confidence=0.0, source=None)
        return None, trace

    start = time.perf_counter()
    sources_consulted: List[str] = []
    best_content: Optional[str] = None
    best_trace: Dict[str, Any] = {"match_found": False, "confidence": 0.0}

    retrievers = (
        _try_balbharati,
        _try_kosha,
        _try_keyword_kb,
        _try_markdown_search,
        _try_sanskrit_decoder,
        _try_faiss,
    )

    for retrieve_fn in retrievers:
        # pass subject and metadata forward when supported
        try:
            content, trace, _latency = retrieve_fn(query, subject=subject, class_level=class_level, language=language, domain=domain, doc_type=doc_type)
        except TypeError:
            try:
                content, trace, _latency = retrieve_fn(query, subject=subject, class_level=class_level, language=language)
            except TypeError:
                try:
                    content, trace, _latency = retrieve_fn(query, subject=subject)
                except TypeError:
                    content, trace, _latency = retrieve_fn(query)
        method = str(trace.get("method") or retrieve_fn.__name__)
        sources_consulted.append(method)

        if content and trace.get("match_found"):
            confidence = float(trace.get("confidence") or 0.0)
            if confidence >= float(best_trace.get("confidence") or 0.0):
                best_content = content
                best_trace = trace

        # Early exit only on a strong Kosha hit; otherwise let KB evidence compete.
        if method == "kosha_deterministic" and trace.get("match_found") and float(trace.get("confidence") or 0) >= 0.75:
            break

    total_latency = (time.perf_counter() - start) * 1000
    best_trace["sources_consulted"] = sources_consulted
    best_trace["total_latency_ms"] = round(total_latency, 2)

    log_retrieval_result(
        query,
        method=str(best_trace.get("method") or "none"),
        match_found=bool(best_trace.get("match_found")),
        confidence=float(best_trace.get("confidence") or 0.0),
        source=best_trace.get("source"),
        similarity_scores=best_trace.get("similarity_scores"),
        document_count=int(best_trace.get("document_count") or 0),
    )
    return best_content, best_trace


class AdvancedRetriever:
    """Hybrid retriever with async cache wrapper."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, top_n: int = 5):
        if self._initialized:
            return
        self.top_n = top_n
        self._initialized = True

    async def retrieve_with_cache(self, query: str) -> Tuple[Optional[str], Dict[str, Any]]:
        if query in _QUERY_CACHE:
            content, trace, ts = _QUERY_CACHE[query]
            if time.time() - ts < CACHE_TTL_SECONDS:
                logger.info("CACHE HIT: %s", query[:40])
                return content, trace

        content, trace = await asyncio.to_thread(retrieve_knowledge_with_trace, query)
        _QUERY_CACHE[query] = (content, trace, time.time())
        return content, trace

    def retrieve_multi(self, query: str) -> List[Dict[str, Any]]:
        content, trace = retrieve_knowledge_with_trace(query)
        if not content:
            return []
        return [
            {
                "content": content,
                "metadata": {
                    "top_confidence": float(trace.get("confidence") or 0.0),
                    "source": trace.get("source"),
                    "method": trace.get("method"),
                },
            }
        ]

    def reason_and_compare(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {"decision": "reject", "content": None}
        best = max(results, key=lambda row: float(row.get("metadata", {}).get("top_confidence", 0.0)))
        confidence = float(best.get("metadata", {}).get("top_confidence", 0.0))
        if confidence >= KB_CONFIDENCE_MIN:
            return {"decision": "answer", "content": best.get("content"), "metadata": best.get("metadata", {})}
        return {"decision": "reject", "content": None, "metadata": best.get("metadata", {})}


async def retrieve_knowledge_async(query: str) -> Tuple[Optional[str], Dict[str, Any]]:
    retriever = AdvancedRetriever()
    return await retriever.retrieve_with_cache(query)
