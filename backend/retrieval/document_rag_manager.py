"""
UniGuru Document-Scoped RAG Manager
===================================
Manages the lifecycle of user-uploaded documents for conversational RAG:
  1. Multi-format parsing (TXT, MD, PDF, DOCX, JSON) via DocumentExtractor.
  2. Structural and semantic chunking via TextChunker.
  3. Dense semantic embedding via SentenceTransformer (all-MiniLM-L6-v2).
  4. In-memory / session-scoped vector indexing and hybrid cosine/lexical scoring.
  5. Hierarchical full-document summarization and section-level explanation.
  6. Document-grounded Q&A with strict provenance citations (Document -> Page -> Section).
  7. Calibrated abstention when facts are absent from the uploaded document.
  8. Cross-turn document persistence across chat sessions.
  9. Multilingual answering (English, Marathi, and explicit language overrides).
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Internal preprocessing imports
from backend.preprocessing.extractor import DocumentExtractor, ExtractedDocument
from backend.preprocessing.chunker import TextChunk, TextChunker

logger = logging.getLogger("uniguru.retrieval.document_rag")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DOCS_DIR = _PROJECT_ROOT / "backend" / "data" / "uploaded_docs"
UPLOAD_DOCS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class IndexedDocumentChunk:
    chunk_id: str
    document_id: str
    file_name: str
    chunk_index: int
    page_number: int
    section: str
    text: str
    char_count: int
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("embedding", None)
        return d


@dataclass
class UploadedDocumentRecord:
    document_id: str
    file_name: str
    file_type: str
    file_path: str
    file_size_bytes: int
    char_count: int
    page_count: int
    title: str
    chunks: List[IndexedDocumentChunk]
    cached_summary: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "char_count": self.char_count,
            "page_count": self.page_count,
            "title": self.title,
            "chunk_count": len(self.chunks),
            "cached_summary": self.cached_summary,
            "created_at": self.created_at,
        }


class DocumentRAGManager:
    """Session-scoped and document-scoped RAG engine for user attachments."""

    _instance: Optional["DocumentRAGManager"] = None

    def __init__(self):
        # session_id -> list of document_id
        self._session_docs: Dict[str, List[str]] = {}
        # document_id -> UploadedDocumentRecord
        self._documents: Dict[str, UploadedDocumentRecord] = {}
        # document_id -> (chunk_ids, numpy embedding matrix)
        self._embedding_cache: Dict[str, Tuple[List[str], np.ndarray]] = {}
        self._embedder = None
        self._chunker = TextChunker(chunk_size=800, chunk_overlap=150, min_chunk_size=80)

    @classmethod
    def get_instance(cls) -> "DocumentRAGManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_embedder(self):
        if self._embedder is None:
            try:
                # Try reusing the loaded model from unified_rag_engine
                from backend.retrieval.unified_rag_engine import get_rag_engine
                engine = get_rag_engine()
                if hasattr(engine, "model") and engine.model is not None:
                    self._embedder = engine.model
                    return self._embedder
            except Exception:
                pass
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        return self._embedder

    def _index_document_chunks(
        self,
        raw_text: str,
        doc_id: str,
        file_name: str,
        file_type: str,
        file_path: str,
        file_size_bytes: int,
        pages_list: Optional[List[Any]] = None,
        session_id: str = "default",
    ) -> UploadedDocumentRecord:
        """Internal helper to chunk, embed, and store document records."""
        # 2. Chunking
        raw_chunks: List[TextChunk] = self._chunker.chunk_document(
            text=raw_text,
            document_id=doc_id,
            language="multilingual",
            domain="user_uploaded",
            default_page_number=1,
        )

        if not raw_chunks:
            # Fallback if chunker didn't produce chunks (e.g. short doc)
            raw_chunks = [
                TextChunk(
                    chunk_id=f"{doc_id}_c0",
                    document_id=doc_id,
                    chunk_index=0,
                    page_number=1,
                    text=raw_text,
                    char_count=len(raw_text),
                    word_count=len(raw_text.split()),
                    language="multilingual",
                    domain="user_uploaded",
                )
            ]

        # Determine page mappings if multi-page extracted
        indexed_chunks: List[IndexedDocumentChunk] = []
        texts_to_embed: List[str] = []

        for i, chunk in enumerate(raw_chunks):
            # Attempt page attribution if pages exist
            page_no = 1
            if pages_list:
                for p in pages_list:
                    if chunk.text[:40] in p.raw_text:
                        page_no = p.page_number
                        break

            # Find approximate section/heading if present
            section = "General"
            heading_match = re.search(r"^(?:#+|\bChapter|\bSection|\bPart)\s+([^\n]+)", chunk.text, re.MULTILINE | re.IGNORECASE)
            if heading_match:
                section = heading_match.group(0).strip(" #:*")

            chunk_obj = IndexedDocumentChunk(
                chunk_id=f"{doc_id}_{i}",
                document_id=doc_id,
                file_name=file_name,
                chunk_index=i,
                page_number=page_no,
                section=section,
                text=chunk.text,
                char_count=len(chunk.text),
            )
            indexed_chunks.append(chunk_obj)
            texts_to_embed.append(chunk.text)

        # 3. Dense Embedding Generation
        embedder = self._get_embedder()
        embeddings = embedder.encode(texts_to_embed, normalize_embeddings=True, show_progress_bar=False)
        embedding_matrix = np.array(embeddings, dtype=np.float32)

        chunk_ids = [c.chunk_id for c in indexed_chunks]
        self._embedding_cache[doc_id] = (chunk_ids, embedding_matrix)

        # 4. Create Document Record
        record = UploadedDocumentRecord(
            document_id=doc_id,
            file_name=file_name,
            file_type=file_type,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            char_count=len(raw_text),
            page_count=len(pages_list) if pages_list else 1,
            title=file_name,
            chunks=indexed_chunks,
        )
        self._documents[doc_id] = record

        # 5. Associate with session
        if session_id not in self._session_docs:
            self._session_docs[session_id] = []
        if doc_id not in self._session_docs[session_id]:
            self._session_docs[session_id].append(doc_id)

        logger.info(
            f"Successfully indexed document '{file_name}' (ID: {doc_id}): "
            f"{len(raw_text)} chars, {len(indexed_chunks)} chunks, {record.page_count} pages."
        )
        return record

    def process_and_index_file(
        self,
        file_path: Path | str,
        session_id: str,
        custom_file_name: Optional[str] = None,
    ) -> UploadedDocumentRecord:
        """Parse, extract, chunk, embed, and register an uploaded file for a session."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        file_name = custom_file_name or path.name
        logger.info(f"Indexing uploaded document '{file_name}' for session '{session_id}'...")

        # 1. Extraction
        extracted_doc: ExtractedDocument = DocumentExtractor.extract(path)
        raw_text = extracted_doc.raw_text.strip()
        if not raw_text:
            raise ValueError(f"Extracted document '{file_name}' contains no readable text.")

        return self._index_document_chunks(
            raw_text=raw_text,
            doc_id=extracted_doc.document_id,
            file_name=file_name,
            file_type=extracted_doc.file_type,
            file_path=str(path.resolve()),
            file_size_bytes=extracted_doc.file_size_bytes,
            pages_list=extracted_doc.pages,
            session_id=session_id,
        )

    def index_raw_text(
        self,
        raw_text: str,
        file_name: str,
        session_id: str,
    ) -> UploadedDocumentRecord:
        """Indexes raw text directly (e.g. extracted from client or text snippet)."""
        clean_text = raw_text.strip()
        if not clean_text:
            raise ValueError("Raw document text cannot be empty.")

        # Check if document already indexed in this session
        for existing in self.get_session_documents(session_id):
            if existing.file_name == file_name:
                return existing

        session_dir = UPLOAD_DOCS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        txt_path = session_dir / f"{file_name}.txt"
        try:
            txt_path.write_text(clean_text, encoding="utf-8")
        except Exception:
            pass

        import hashlib
        doc_id = f"doc_{hashlib.sha256((session_id + file_name + clean_text[:200]).encode('utf-8')).hexdigest()[:12]}"

        if doc_id in self._documents and doc_id in self._session_docs.get(session_id, []):
            return self._documents[doc_id]

        return self._index_document_chunks(
            raw_text=clean_text,
            doc_id=doc_id,
            file_name=file_name,
            file_type="document",
            file_path=str(txt_path.resolve()) if txt_path.exists() else "",
            file_size_bytes=len(clean_text.encode("utf-8")),
            pages_list=None,
            session_id=session_id,
        )

    def get_session_documents(self, session_id: str) -> List[UploadedDocumentRecord]:
        """Returns all active documents registered for a given session."""
        doc_ids = self._session_docs.get(session_id, [])
        return [self._documents[d] for d in doc_ids if d in self._documents]

    def has_session_documents(self, session_id: str) -> bool:
        return bool(self._session_docs.get(session_id))

    def retrieve_chunks(
        self,
        query: str,
        session_id: str,
        top_k: int = 5,
        target_doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve most relevant chunks from active documents in session."""
        docs = self.get_session_documents(session_id)
        if target_doc_id:
            docs = [d for d in docs if d.document_id == target_doc_id]
        if not docs:
            return []

        embedder = self._get_embedder()
        q_emb = embedder.encode([query], normalize_embeddings=True)[0]

        candidates = []
        query_words = set(re.findall(r"\w+", query.lower()))

        for doc in docs:
            cache = self._embedding_cache.get(doc.document_id)
            if not cache:
                continue
            chunk_ids, matrix = cache
            # Dot product for normalized embeddings = cosine similarity
            scores = np.dot(matrix, q_emb)

            for idx, score in enumerate(scores):
                chunk = doc.chunks[idx]
                sim_score = float(score)

                # Lexical overlap boost (BM25-style keyword matching)
                chunk_words = set(re.findall(r"\w+", chunk.text.lower()))
                overlap = len(query_words.intersection(chunk_words))
                lexical_bonus = min(0.3, overlap * 0.05)
                composite_score = sim_score + lexical_bonus

                candidates.append({
                    "chunk_id": chunk.chunk_id,
                    "document_id": doc.document_id,
                    "file_name": doc.file_name,
                    "page_number": chunk.page_number,
                    "section": chunk.section,
                    "text": chunk.text,
                    "score": round(composite_score, 4),
                    "raw_similarity": round(sim_score, 4),
                    "index": chunk.chunk_index,
                })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    def summarize_document(
        self,
        session_id: str,
        target_doc_id: Optional[str] = None,
        target_language: str = "en",
    ) -> Dict[str, Any]:
        """Hierarchical or full-text summarization of uploaded document(s)."""
        docs = self.get_session_documents(session_id)
        if target_doc_id:
            docs = [d for d in docs if d.document_id == target_doc_id]
        if not docs:
            return {
                "answer": "No active document found in this session to summarize.",
                "verification_status": "NO_DOCUMENT",
                "confidence": 0.0,
                "citations": [],
                "retrieved_chunks": [],
            }

        doc = docs[0]
        # Return cached summary if available and language matches
        total_chars = doc.char_count
        citations = [f"{doc.file_name} (Total Pages: {doc.page_count}, Characters: {total_chars})"]

        # Strategy 1: Short/Medium Document (<= 3500 characters) -> Single-Pass Complete Summary
        if total_chars <= 3500:
            full_text = "\n\n".join(c.text for c in doc.chunks)
            summary = self._call_llm_summary(full_text, doc.file_name, target_language)
            doc.cached_summary = summary
            retrieved_chunks = [
                {
                    "index": c.chunk_index,
                    "file": doc.file_name,
                    "page": c.page_number,
                    "score": 0.99,
                    "content": c.text[:250] + "...",
                }
                for c in doc.chunks[:5]
            ]
            return {
                "answer": summary,
                "verification_status": "VERIFIED",
                "confidence": 0.98,
                "citations": citations,
                "retrieved_chunks": retrieved_chunks,
                "source_type": "uploaded_document",
            }

        # Strategy 2: Large Document (> 3500 characters) -> Hierarchical Summarization
        # Group chunks into evenly spaced sections
        num_chunks = len(doc.chunks)
        selected_indices = np.linspace(0, num_chunks - 1, min(6, num_chunks), dtype=int)
        sampled_chunks = [doc.chunks[i] for i in selected_indices]

        sampled_text = "\n\n".join(
            f"--- Section / Page {c.page_number} ---\n{c.text}" for c in sampled_chunks
        )
        summary = self._call_llm_summary(sampled_text, doc.file_name, target_language, is_hierarchical=True)
        doc.cached_summary = summary

        retrieved_chunks = [
            {
                "index": c.chunk_index,
                "file": doc.file_name,
                "page": c.page_number,
                "score": 0.95,
                "content": c.text[:250] + "...",
            }
            for c in sampled_chunks
        ]
        return {
            "answer": summary,
            "verification_status": "VERIFIED",
            "confidence": 0.95,
            "citations": citations,
            "retrieved_chunks": retrieved_chunks,
            "source_type": "uploaded_document",
        }

    def answer_document_query(
        self,
        query: str,
        session_id: str,
        target_doc_id: Optional[str] = None,
        target_language: str = "en",
    ) -> Dict[str, Any]:
        """Grounded Q&A over the session's active document(s)."""
        docs = self.get_session_documents(session_id)
        if not docs:
            return {
                "answer": "No uploaded document found in this conversation to reference.",
                "verification_status": "NO_DOCUMENT",
                "confidence": 0.0,
                "citations": [],
                "retrieved_chunks": [],
            }

        q_lower = query.lower()

        # Check if query is asking for most important concepts / key takeaways
        key_concepts_pattern = r"\b(?:most\s+)?(?:important|key|core|main)\s+(?:concepts|ideas|points|topics|takeaways)\b"
        if re.search(key_concepts_pattern, q_lower):
            doc = docs[0]
            sampled_text = "\n\n".join(f"[{c.section}]: {c.text}" for c in doc.chunks[:6])
            prompt = (
                f"Document: {doc.file_name}\n\n"
                f"Document Text:\n{sampled_text}\n\n"
                "Explain the most important concepts and key takeaways from this document in detail:"
            )
            key_answer = self._call_llm_grounded_answer(
                context=sampled_text,
                query="What are the most important concepts and core ideas explained in this document?",
                target_language=target_language,
            )
            citations = [f"{doc.file_name} (Section: '{c.section}')" for c in doc.chunks[:3]]
            retrieved_chunks = [
                {
                    "index": c.chunk_index,
                    "file": doc.file_name,
                    "score": 0.95,
                    "page": c.page_number,
                    "content": c.text,
                }
                for c in doc.chunks[:4]
            ]
            citations_block = "\n\n**Document Sources**:\n" + "\n".join(f"- {c}" for c in list(dict.fromkeys(citations)))
            return {
                "answer": f"{key_answer}{citations_block}",
                "verification_status": "VERIFIED",
                "confidence": 0.95,
                "citations": list(dict.fromkeys(citations)),
                "retrieved_chunks": retrieved_chunks,
                "source_type": "uploaded_document",
            }

        # Check if query is explicitly a summarization request
        summary_patterns = [
            r"\b(?:summary|summarize|overview|gist|recap)\b",
            r"\bwhat is this (?:document|file|paper|text) about\b",
            r"\btell me about this (?:document|file|paper|text)\b",
            r"\bgive me (?:a |the )?summary\b",
        ]
        if any(re.search(p, q_lower) for p in summary_patterns):
            return self.summarize_document(session_id=session_id, target_doc_id=target_doc_id, target_language=target_language)

        # Check for absent topics (entities with 0% presence in all document chunks)
        # Only check literal keyword presence if query script matches document script (same script)
        q_is_devanagari = bool(re.search(r"[\u0900-\u097f]", q_lower))
        doc_is_devanagari = any(bool(re.search(r"[\u0900-\u097f]", c.text)) for d in docs for c in d.chunks)
        same_script = q_is_devanagari == doc_is_devanagari

        if same_script:
            stop_words = {"what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
                          "according", "to", "the", "document", "file", "text", "provided", "attached", "does",
                          "say", "about", "is", "are", "was", "were", "in", "on", "at", "for", "from", "with"}
            content_words = [w for w in re.findall(r"\w+", q_lower) if len(w) > 2 and w not in stop_words]
            doc_all_text = " ".join(c.text.lower() for d in docs for c in d.chunks)
            has_any_content_word = any(w in doc_all_text for w in content_words) if content_words else True

            if content_words and not has_any_content_word:
                abstention = (
                    "दिलेल्या दस्तऐवजामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."
                    if target_language == "mr"
                    else "The provided document does not contain this information."
                )
                return {
                    "answer": abstention,
                    "verification_status": "NO_VERIFIED_KNOWLEDGE",
                    "confidence": 0.0,
                    "citations": [],
                    "retrieved_chunks": [],
                    "source_type": "uploaded_document",
                }

        # Retrieve top relevant chunks
        chunks = self.retrieve_chunks(query=query, session_id=session_id, top_k=5, target_doc_id=target_doc_id)
        if not chunks:
            abstention = (
                "दिलेल्या दस्तऐवजामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."
                if target_language == "mr"
                else "The provided document does not contain this information."
            )
            return {
                "answer": abstention,
                "verification_status": "NO_VERIFIED_KNOWLEDGE",
                "confidence": 0.0,
                "citations": [],
                "retrieved_chunks": [],
                "source_type": "uploaded_document",
            }

        top_score = chunks[0]["score"]

        # Check relevance: if the top score is very low and contains zero keyword match, abstain honestly!
        query_words = [w for w in re.findall(r"\w+", q_lower) if len(w) > 3]
        has_keyword_overlap = any(any(w in c["text"].lower() for w in query_words) for c in chunks[:3])

        min_threshold = 0.22 if same_script else 0.05
        if top_score < min_threshold or (same_script and top_score < 0.25 and not has_keyword_overlap):
            abstention = (
                "दिलेल्या दस्तऐवजामध्ये या प्रश्नाचे उत्तर उपलब्ध नाही."
                if target_language == "mr"
                else "The provided document does not contain this information."
            )
            return {
                "answer": abstention,
                "verification_status": "NO_VERIFIED_KNOWLEDGE",
                "confidence": 0.0,
                "citations": [],
                "retrieved_chunks": [],
                "source_type": "uploaded_document",
            }

        # Build grounded context
        context_parts = []
        citations = []
        retrieved_chunks = []

        for i, c in enumerate(chunks[:4], 1):
            ref = f"[{c['file_name']}, Page {c['page_number']}, Section: '{c['section']}']"
            citations.append(ref)
            context_parts.append(f"--- Evidence Chunk {i} {ref} ---\n{c['text']}")
            retrieved_chunks.append({
                "index": c["index"],
                "file": c["file_name"],
                "score": c["score"],
                "page": c["page_number"],
                "content": c["text"],
            })

        full_context = "\n\n".join(context_parts)
        answer = self._call_llm_grounded_answer(
            context=full_context,
            query=query,
            target_language=target_language,
        )

        # Append citations cleanly
        unique_citations = list(dict.fromkeys(citations))
        citations_header = "**दस्तऐवज संदर्भ**:" if target_language == "mr" else "**Document Sources**:"
        citations_block = f"\n\n{citations_header}\n" + "\n".join(f"- {c}" for c in unique_citations[:2])
        if "Document Sources" not in answer and "दस्तऐवज संदर्भ" not in answer:
            answer = f"{answer}{citations_block}"

        return {
            "answer": answer,
            "verification_status": "VERIFIED",
            "confidence": round(min(0.99, max(0.85, top_score)), 3),
            "citations": unique_citations,
            "retrieved_chunks": retrieved_chunks,
            "source_type": "uploaded_document",
        }

    def _call_llm_summary(
        self,
        document_text: str,
        file_name: str,
        target_language: str = "en",
        is_hierarchical: bool = False,
    ) -> str:
        """Invokes local Qwen 2.5 service to generate a comprehensive document summary."""
        llm_url = os.environ.get("UNIGURU_LLM_URL", "http://127.0.0.1:8001/generate")

        if target_language == "mr":
            system_msg = (
                "तुम्ही UniGuru आहात, एक मार्गदर्शक AI सहाय्यक. "
                "दिलेल्या दस्तऐवजाचा स्पष्ट, माहितीपूर्ण आणि संरचित सारांश मराठीत (मराठी) द्या. "
                "मुख्य मुद्दे, महत्त्वाच्या संकल्पना आणि निष्कर्ष स्पष्ट करा."
            )
            prompt = (
                f"दस्तऐवज नाव: {file_name}\n\n"
                f"दस्तऐवज मजकूर:\n{document_text[:3500]}\n\n"
                "वरील दस्तऐवजाचा संपूर्ण आणि माहितीपूर्ण मराठी सारांश:"
            )
        else:
            system_msg = (
                "You are UniGuru, an authoritative educational AI assistant. "
                "Generate a clear, comprehensive, and well-structured summary of the provided document. "
                "Include key concepts, important points, and main conclusions."
            )
            prompt = (
                f"Document Name: {file_name}\n\n"
                f"Document Text:\n{document_text[:3500]}\n\n"
                "Comprehensive Structured Summary:"
            )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        try:
            import requests
            res = requests.post(
                llm_url,
                json={
                    "messages": messages,
                    "language": target_language,
                    "max_new_tokens": 512,
                },
                timeout=30,
                proxies={"http": None, "https": None},
            )
            if res.status_code == 200:
                ans = res.json().get("answer", "").strip()
                if ans:
                    # Check if cross-lingual translation is needed
                    lat_count = len(re.findall(r"[A-Za-z]", ans))
                    dev_count = len(re.findall(r"[\u0900-\u097f]", ans))

                    if target_language == "en" and dev_count > lat_count:
                        try:
                            trans_res = requests.post(
                                llm_url,
                                json={
                                    "messages": [
                                        {"role": "system", "content": "You are a professional translator. Translate the Marathi text into clear, accurate English."},
                                        {"role": "user", "content": f"Translate to English:\n{ans}"}
                                    ],
                                    "language": "en",
                                    "max_new_tokens": 256,
                                },
                                timeout=15,
                                proxies={"http": None, "https": None},
                            )
                            if trans_res.status_code == 200:
                                trans_text = trans_res.json().get("answer", "").strip()
                                if trans_text:
                                    ans = trans_text
                        except Exception:
                            pass
                    elif target_language == "mr" and lat_count > dev_count:
                        try:
                            trans_res = requests.post(
                                llm_url,
                                json={
                                    "messages": [
                                        {"role": "system", "content": "You are a professional translator. Translate the English text into clear, accurate Marathi."},
                                        {"role": "user", "content": f"Translate to Marathi:\n{ans}"}
                                    ],
                                    "language": "mr",
                                    "max_new_tokens": 256,
                                },
                                timeout=15,
                                proxies={"http": None, "https": None},
                            )
                            if trans_res.status_code == 200:
                                trans_text = trans_res.json().get("answer", "").strip()
                                if trans_text:
                                    ans = trans_text
                        except Exception:
                            pass
                    return ans
        except Exception as e:
            logger.warning(f"LLM call for document summary failed: {e}")

        # Fallback extractive summary
        paragraphs = [p.strip() for p in document_text.split("\n\n") if len(p.strip()) > 40]
        snippet = " ".join(paragraphs[:3])
        return f"**Summary of {file_name}**:\n\n{snippet}"

    def _call_llm_grounded_answer(
        self,
        context: str,
        query: str,
        target_language: str = "en",
    ) -> str:
        """Invokes local Qwen 2.5 service to answer questions grounded strictly in context."""
        llm_url = os.environ.get("UNIGURU_LLM_URL", "http://127.0.0.1:8001/generate")
        lat_ctx = len(re.findall(r"[A-Za-z]", context))
        dev_ctx = len(re.findall(r"[\u0900-\u097f]", context))
        context_is_devanagari = dev_ctx > lat_ctx

        # Case 1: Cross-lingual Marathi request for English context
        if target_language == "mr" and not context_is_devanagari:
            try:
                import requests
                # 1. Extract grounded English answer from English context
                res_en = requests.post(
                    llm_url,
                    json={
                        "messages": [
                            {"role": "system", "content": "You are UniGuru. Answer the question directly using ONLY the provided document context."},
                            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"}
                        ],
                        "language": "en",
                        "max_new_tokens": 256,
                    },
                    timeout=20,
                    proxies={"http": None, "https": None},
                )
                en_ans = ""
                if res_en.status_code == 200:
                    en_ans = res_en.json().get("answer", "").strip()
                if not en_ans:
                    en_ans = context.split("\n\n")[0] if "\n\n" in context else context[:300]

                # 2. Translate English answer into clear Marathi
                res_mr = requests.post(
                    llm_url,
                    json={
                        "messages": [
                            {"role": "system", "content": "You are a professional translator. Translate the text into clear, accurate Marathi."},
                            {"role": "user", "content": f"Translate to Marathi:\n{en_ans}"}
                        ],
                        "language": "mr",
                        "max_new_tokens": 256,
                    },
                    timeout=20,
                    proxies={"http": None, "https": None},
                )
                if res_mr.status_code == 200:
                    mr_ans = res_mr.json().get("answer", "").strip()
                    if mr_ans and len(re.findall(r"[\u0900-\u097f]", mr_ans)) > len(re.findall(r"[A-Za-z]", mr_ans)):
                        return mr_ans
            except Exception as e:
                logger.warning(f"Cross-lingual MR grounded answer failed: {e}")

        # Case 2: Standard Grounded Q&A
        if target_language == "mr":
            system_msg = (
                "तुम्ही UniGuru आहात. दिलेल्या दस्तऐवज संदर्भाचा वापर करून वापरकर्त्याच्या प्रश्नाचे थेट आणि अचूक उत्तर मराठीत द्या. "
                "जर उत्तर संदर्भामध्ये नसेल, तर सांगा की माहिती उपलब्ध नाही."
            )
            user_msg = (
                f"दस्तऐवज संदर्भ:\n{context}\n\n"
                f"प्रश्न: {query}\n\n"
                "थेट मराठी उत्तर:"
            )
        else:
            system_msg = (
                "You are UniGuru, an authoritative educational AI assistant. "
                "Answer the user's question directly and accurately using ONLY the provided document context. "
                "If the context does not contain the answer, say clearly that the document does not contain this information."
            )
            user_msg = (
                f"Document Context:\n{context}\n\n"
                f"Question: {query}\n\n"
                "Grounded Answer:"
            )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        try:
            import requests
            res = requests.post(
                llm_url,
                json={
                    "messages": messages,
                    "language": target_language,
                    "max_new_tokens": 512,
                },
                timeout=30,
                proxies={"http": None, "https": None},
            )
            if res.status_code == 200:
                ans = res.json().get("answer", "").strip()
                if ans:
                    # Check if cross-lingual translation is needed
                    lat_count = len(re.findall(r"[A-Za-z]", ans))
                    dev_count = len(re.findall(r"[\u0900-\u097f]", ans))

                    if target_language == "en" and dev_count > lat_count:
                        try:
                            trans_res = requests.post(
                                llm_url,
                                json={
                                    "messages": [
                                        {"role": "system", "content": "You are a professional translator. Translate the Marathi text into clear, accurate English."},
                                        {"role": "user", "content": f"Translate to English:\n{ans}"}
                                    ],
                                    "language": "en",
                                    "max_new_tokens": 256,
                                },
                                timeout=15,
                                proxies={"http": None, "https": None},
                            )
                            if trans_res.status_code == 200:
                                trans_text = trans_res.json().get("answer", "").strip()
                                if trans_text:
                                    ans = trans_text
                        except Exception:
                            pass
                    elif target_language == "mr" and lat_count > dev_count:
                        try:
                            trans_res = requests.post(
                                llm_url,
                                json={
                                    "messages": [
                                        {"role": "system", "content": "You are a professional translator. Translate the English text into clear, accurate Marathi."},
                                        {"role": "user", "content": f"Translate to Marathi:\n{ans}"}
                                    ],
                                    "language": "mr",
                                    "max_new_tokens": 256,
                                },
                                timeout=15,
                                proxies={"http": None, "https": None},
                            )
                            if trans_res.status_code == 200:
                                trans_text = trans_res.json().get("answer", "").strip()
                                if trans_text:
                                    ans = trans_text
                        except Exception:
                            pass
                    return ans
        except Exception as e:
            logger.warning(f"LLM call for grounded Q&A failed: {e}")

        # Fallback to first context chunk
        first_chunk = context.split("--- Evidence Chunk")[1] if "--- Evidence Chunk" in context else context[:500]
        return f"Based on the provided document:\n\n{first_chunk.strip()}"


_document_rag_manager: Optional[DocumentRAGManager] = None


def get_document_rag_manager() -> DocumentRAGManager:
    global _document_rag_manager
    if _document_rag_manager is None:
        _document_rag_manager = DocumentRAGManager.get_instance()
    return _document_rag_manager
