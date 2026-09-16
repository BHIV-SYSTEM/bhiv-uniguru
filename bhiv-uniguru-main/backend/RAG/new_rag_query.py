import sqlite3
import os
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("uniguru.rag.engine")

MIN_SIMILARITY_THRESHOLD = float(os.getenv("UNIGURU_RAG_CONFIDENCE_MIN", "0.75"))
TOP_K = int(os.getenv("UNIGURU_RAG_TOP_K", "5"))

base_dir = os.path.dirname(os.path.abspath(__file__))

def _resolve_paths():
    candidates_db = ["chunks_v4.db", "chunks_v3.db", "chunks.db", "chunks_v2.db"]
    candidates_faiss = ["faiss_index_v4.bin", "faiss_index_v3.bin", "faiss_index.bin", "faiss_index_v2.bin"]
    
    found_db = None
    for name in candidates_db:
        p = os.path.join(base_dir, name)
        if os.path.exists(p):
            found_db = p
            break
    if not found_db:
        found_db = os.path.join(base_dir, "chunks_v4.db")

    found_faiss = None
    for name in candidates_faiss:
        p = os.path.join(base_dir, name)
        if os.path.exists(p):
            found_faiss = p
            break
    if not found_faiss:
        found_faiss = os.path.join(base_dir, "faiss_index_v4.bin")

    return found_db, found_faiss

db_path, faiss_path = _resolve_paths()
engine = None


def _normalize_chunk_text(text: str) -> str:
    return " ".join(str(text or "").split()).strip()


def _log_rag_debug(query: str, candidates: List[Dict[str, Any]], selected: List[Dict[str, Any]], rejected: List[Dict[str, Any]], final_context: str) -> None:
    debug_payload = {
        "stage": "rag_debug",
        "query": query,
        "threshold": MIN_SIMILARITY_THRESHOLD,
        "retrieved_documents": [
            {
                "id": candidate.get("id"),
                "score": candidate.get("score"),
                "file_name": candidate.get("metadata", {}).get("file_name"),
            }
            for candidate in candidates
        ],
        "selected_chunks": [
            {
                "id": chunk.get("id"),
                "score": chunk.get("score"),
                "file_name": chunk.get("metadata", {}).get("file_name"),
            }
            for chunk in selected
        ],
        "rejected_chunks": rejected,
        "final_context_snippet": final_context[:1000],
        "selected_count": len(selected),
        "rejected_count": len(rejected),
    }
    logger.info(json.dumps(debug_payload, default=str, sort_keys=True))


def _index_available() -> bool:
    curr_db, curr_faiss = _resolve_paths()
    return os.path.exists(curr_faiss) and os.path.exists(curr_db)


class NewRAGEngine:
    def __init__(self, model_name=None):
        curr_db, curr_faiss = _resolve_paths()
        if not (os.path.exists(curr_faiss) and os.path.exists(curr_db)):
            raise FileNotFoundError(
                f"FAISS index missing. Expected {curr_faiss} and {curr_db}. "
                "Run index build or mount persistent storage."
            )

        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        model_name = model_name or os.getenv("UNIGURU_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.model = SentenceTransformer(model_name)
        self.index = faiss.read_index(curr_faiss)
        self.db_path = curr_db
        self.faiss_path = curr_faiss
        self._faiss = faiss
        self.ollama = self._init_ollama()
        self.groq_client = self._init_groq()

    def _init_ollama(self):
        try:
            from integrations.ollama_client import OllamaClient
            return OllamaClient()
        except Exception:
            return None

    def _init_groq(self):
        try:
            from groq import Groq
            from dotenv import load_dotenv
            _env_path = os.path.join(base_dir, "..", ".env")
            if os.path.exists(_env_path):
                load_dotenv(_env_path)
            groq_key = os.getenv("GROQ_API_KEY") or os.getenv("UNIGURU_LLM_API_KEY")
            if groq_key:
                return Groq(api_key=groq_key)
        except Exception:
            pass
        return None

    def retrieve(self, query: str, top_k: int = 20, class_level: str = None, subject: str = None, language: str = None, domain: str = None, doc_type: str = None, topic: str = None):
        query_emb = self.model.encode([query])
        self._faiss.normalize_L2(query_emb)
        search_k = 50 if (class_level or subject or language or domain or doc_type or topic) else top_k
        scores, ids = self.index.search(query_emb, search_k)

        candidates: List[Dict[str, Any]] = []
        with sqlite3.connect(self.db_path) as conn:
            for col in ["class_level", "subject", "chapter", "source", "language", "domain", "type", "topic"]:
                try:
                    conn.execute(f"ALTER TABLE chunks ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass
                    
            cur = conn.cursor()
            for score, doc_id in zip(scores[0], ids[0]):
                if doc_id == -1:
                    continue
                
                query_sql = "SELECT file_name, page_number, text, class_level, subject, chapter, source, language, domain, type, topic FROM chunks WHERE id = ?"
                params = [int(doc_id)]
                
                if class_level:
                    query_sql += " AND class_level = ?"
                    params.append(class_level)
                if subject:
                    query_sql += " AND LOWER(subject) = LOWER(?)"
                    params.append(subject)
                if language:
                    query_sql += " AND LOWER(language) = LOWER(?)"
                    params.append(language)
                if domain:
                    query_sql += " AND LOWER(domain) = LOWER(?)"
                    params.append(domain)
                if doc_type:
                    query_sql += " AND LOWER(type) = LOWER(?)"
                    params.append(doc_type)
                if topic:
                    query_sql += " AND LOWER(topic) = LOWER(?)"
                    params.append(topic)
                    
                cur.execute(query_sql, tuple(params))
                row = cur.fetchone()
                if not row:
                    continue
                # FAISS IndexFlatL2 returns Euclidean distance. Convert to cosine similarity:
                raw_dist = float(score)
                cosine_sim = float(max(0.0, 1.0 - (raw_dist ** 2) / 2.0)) if raw_dist <= 2.0 else 0.0
                candidates.append(
                    {
                        "id": int(doc_id),
                        "text": row[2],
                        "metadata": {
                            "file_name": row[0], 
                            "page_number": row[1],
                            "class_level": row[3],
                            "subject": row[4],
                            "chapter": row[5],
                            "source": row[6],
                            "language": row[7],
                            "domain": row[8],
                            "type": row[9],
                            "topic": row[10]
                        },
                        "score": round(cosine_sim, 4),
                        "raw_l2_distance": round(raw_dist, 4),
                    }
                )

        candidates.sort(key=lambda candidate: candidate["score"], reverse=True)

        selected: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        seen_texts = set()

        for candidate in candidates:
            score = candidate["score"]
            normalized_text = _normalize_chunk_text(candidate["text"])

            if score < MIN_SIMILARITY_THRESHOLD:
                rejected.append(
                    {
                        "id": candidate["id"],
                        "score": score,
                        "reason": "below_threshold",
                        "file_name": candidate["metadata"].get("file_name"),
                    }
                )
                continue

            if normalized_text in seen_texts:
                rejected.append(
                    {
                        "id": candidate["id"],
                        "score": score,
                        "reason": "duplicate_chunk",
                        "file_name": candidate["metadata"].get("file_name"),
                    }
                )
                continue

            seen_texts.add(normalized_text)
            selected.append(candidate)
            if len(selected) >= TOP_K:
                break

        final_context = "\n\n".join(
            f"--- [{idx + 1}] {chunk['metadata']['file_name']} (page {chunk['metadata'].get('page_number', '?')}) ---\n{chunk['text']}"
            for idx, chunk in enumerate(selected)
        )
        if len(final_context) > 5000:
            final_context = final_context[:5000] + "\n...[truncated]"

        _log_rag_debug(query, candidates, selected, rejected, final_context)
        return selected

    def _synthesize_answer(self, query: str, context: str, citations: List[str]) -> str:
        # 1. Try Groq if configured
        if getattr(self, "groq_client", None):
            try:
                system_prompt = (
                    "You are UniGuru, an intelligent knowledge assistant. "
                    "Your Answer MUST be constructed ONLY from the provided context signals.\n"
                    "Rules:\n"
                    "1. No hallucination whatsoever\n"
                    "2. No extra information outside the provided text\n"
                    "3. Only use signal-derived facts\n"
                    "4. If context is insufficient, reply exactly: 'I do not have verified knowledge to answer this question.'"
                )
                model_name = os.getenv("UNIGURU_LLM_MODEL", "llama-3.1-8b-instant")
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
                    ],
                    model=model_name,
                    temperature=0.1,
                    max_tokens=1000
                )
                ans = chat_completion.choices[0].message.content
                if ans and ans.strip():
                    return ans.strip()
            except Exception as e:
                logger.warning(f"Groq generation failed: {e}")

        # 2. Try Ollama if configured
        if self.ollama and getattr(self.ollama, "enabled", False):
            try:
                system_prompt = (
                    "You are UniGuru, a sovereign knowledge assistant. "
                    "Answer ONLY using the provided context. If context is insufficient, reply exactly: "
                    "'I do not have verified knowledge to answer this question.'"
                )
                user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
                ans = self.ollama.generate(user_prompt, system_prompt=system_prompt)
                if ans and ans.strip():
                    return ans.strip()
            except Exception as e:
                logger.warning(f"Ollama generation failed: {e}")

        # 3. Deterministic local grounded synthesis
        if context.strip():
            first_chunk = context.split("--- [1]")[1].split("--- [2]")[0] if "--- [1]" in context else context
            lines = [l.strip() for l in first_chunk.splitlines() if l.strip() and not l.strip().startswith("---")]
            snippet = " ".join(lines)[:600]
            citation_str = f"\n\nSource: {citations[0]}" if citations else ""
            return f"{snippet}{citation_str}"

        return "No relevant context found."

    def answer_question(self, query: str, max_context_chars: int = 4000, top_k: int = 5, class_level: str = None, subject: str = None, language: str = None, domain: str = None, doc_type: str = None, topic: str = None):
        retrieved = self.retrieve(query, top_k=20, class_level=class_level, subject=subject, language=language, domain=domain, doc_type=doc_type, topic=topic)
        if not retrieved:
            return {"answer": "No relevant context found.", "retrieved": []}

        try:
            from retrieval.reranker import reranker
            retrieved = reranker.rerank_and_filter(retrieved, expected_class=class_level, expected_subject=subject, top_k=top_k)
        except Exception as e:
            retrieved = retrieved[:top_k]

        if not retrieved:
            return {"answer": "I could not find the correct textbook information. Please try again.", "retrieved": []}

        # Apply strict score thresholding
        valid_retrieved = [c for c in retrieved if c.get("score", 0.0) >= MIN_SIMILARITY_THRESHOLD]
        if not valid_retrieved:
            return {"answer": "No relevant context found.", "retrieved": []}
        retrieved = valid_retrieved

        # Deduplicate retrieved chunks by normalized text
        deduped = []
        seen_texts = set()
        for chunk in retrieved:
            norm = _normalize_chunk_text(chunk.get("text", ""))
            if norm and norm not in seen_texts:
                seen_texts.add(norm)
                deduped.append(chunk)
            elif not norm and chunk not in deduped:
                deduped.append(chunk)
        retrieved = deduped

        context_parts = []
        citations = []
        for i, chunk in enumerate(retrieved):
            meta = chunk["metadata"]
            citations.append(f"[{i + 1}] {meta['file_name']} (page {meta.get('page_number', '?')})")
            context_parts.append(
                f"--- [{i + 1}] {meta['file_name']} (page {meta.get('page_number', '?')}) ---\n{chunk['text']}"
            )
        context = "\n\n".join(context_parts)
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "\n...[truncated]"

        answer = self._synthesize_answer(query, context, citations)
        return {"answer": answer, "retrieved": retrieved}


def get_engine():
    global engine
    if engine is None:
        engine = NewRAGEngine()
    return engine


def get_index_status() -> dict:
    curr_db, curr_faiss = _resolve_paths()
    status = {
        "faiss_index_exists": os.path.exists(curr_faiss),
        "chunks_db_exists": os.path.exists(curr_db),
        "faiss_path": curr_faiss,
        "db_path": curr_db,
        "vector_count": 0,
        "chunk_count": 0,
    }
    if status["chunks_db_exists"]:
        try:
            with sqlite3.connect(curr_db) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM chunks")
                status["chunk_count"] = int(cur.fetchone()[0])
        except Exception as exc:
            status["db_error"] = str(exc)
    if status["faiss_index_exists"]:
        try:
            import faiss
            index = faiss.read_index(curr_faiss)
            status["vector_count"] = int(index.ntotal)
        except Exception as exc:
            status["faiss_error"] = str(exc)
    return status
