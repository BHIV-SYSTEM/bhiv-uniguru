"""Hybrid Retrieval Engine for Balbharati Curriculum combining BM25 + FAISS + Metadata Filtering."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .bm25_retriever import BM25Retriever
from .metadata_extractor import extract_balbharati_metadata, BalbharatiQueryMetadata

logger = logging.getLogger("uniguru.balbharati.hybrid")

_CURR = Path(__file__).resolve()
ROOT = _CURR.parents[3]
BALBHARATI_DATA_DIR = ROOT / "backend" / "retrieval" / "balbharati" / "data"
INDEX_VERSION = "balbharati_index_v1"


def _clean_text_norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


class BalbharatiHybridRetriever:
    """Combines BM25 lexical search, FAISS dense embeddings, metadata filtering, and RRF reranking."""

    def __init__(
        self,
        data_dir: Path = BALBHARATI_DATA_DIR,
        model_name: str = "all-MiniLM-L6-v2",
        rrf_k: int = 60,
    ) -> None:
        self.data_dir = data_dir
        self.model_name = os.getenv("UNIGURU_EMBEDDING_MODEL", model_name)
        self.rrf_k = rrf_k
        self.bm25 = BM25Retriever()
        self.model = None
        self.index = None
        self.db_path = self.data_dir / "chunks.db"
        self.faiss_path = self.data_dir / "faiss.bin"
        self.bm25_path = self.data_dir / "bm25.json"
        self.meta_path = self.data_dir / "index_meta.json"
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        if self._initialized:
            return True

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load BM25 index if exists
        if self.bm25_path.exists():
            self.bm25.load_from_file(self.bm25_path)

        # Load FAISS index if exists
        if self.faiss_path.exists():
            try:
                import faiss
                self.index = faiss.read_index(str(self.faiss_path))
            except Exception as exc:
                logger.warning(f"Failed to load FAISS index: {exc}")
                self.index = None

        # Load SentenceTransformer embedding model
        if self.index is not None and self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
            except Exception as exc:
                logger.warning(f"Failed to load SentenceTransformer: {exc}")
                self.model = None

        self._initialized = True
        return True

    def index_chunks(self, chunks: List[Dict[str, Any]], version: str = INDEX_VERSION) -> Dict[str, Any]:
        """Builds and persists both the FAISS vector index and Okapi BM25 index for Balbharati chunks."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        import faiss
        from sentence_transformers import SentenceTransformer

        logger.info(f"Indexing {len(chunks)} Balbharati chunks under version {version}...")

        # 1. Setup SQLite storage
        if self.db_path.exists():
            try:
                os.remove(self.db_path)
            except OSError:
                pass

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY,
                    chunk_id TEXT UNIQUE,
                    text TEXT,
                    page_number INTEGER,
                    book_title TEXT,
                    standard INTEGER,
                    subject TEXT,
                    medium TEXT,
                    chapter TEXT,
                    section TEXT,
                    content_type TEXT,
                    source_url TEXT,
                    source_type TEXT,
                    metadata_json TEXT
                )
                """
            )
            for idx, c in enumerate(chunks):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO chunks
                    (id, chunk_id, text, page_number, book_title, standard, subject, medium, chapter, section, content_type, source_url, source_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        idx,
                        c.get("chunk_id", f"bb_chunk_{idx}"),
                        c.get("text", ""),
                        int(c.get("page_number", 1)),
                        c.get("book_title", ""),
                        int(c.get("standard") or c.get("grade") or 1),
                        c.get("subject", ""),
                        c.get("medium", "English"),
                        c.get("chapter", "General"),
                        c.get("section", ""),
                        c.get("content_type", "text"),
                        c.get("source_url", ""),
                        c.get("source_type", "Balbharati"),
                        json.dumps(c.get("metadata", {}), ensure_ascii=False),
                    ),
                )
            conn.commit()

        # 2. Build BM25 Index
        self.bm25 = BM25Retriever()
        self.bm25.index_documents(chunks)
        self.bm25.save_to_file(self.bm25_path)

        # 3. Build FAISS Vector Index
        self.model = SentenceTransformer(self.model_name)
        texts = [c.get("text", "") for c in chunks]
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner Product on normalized vectors = Cosine Similarity!
        index.add(embeddings)
        faiss.write_index(index, str(self.faiss_path))
        self.index = index

        meta = {
            "version": version,
            "total_chunks": len(chunks),
            "embedding_model": self.model_name,
            "dimension": dimension,
            "index_type": "IndexFlatIP_Cosine",
            "standards": sorted(list({int(c.get("standard") or c.get("grade") or 0) for c in chunks})),
            "subjects": sorted(list({str(c.get("subject") or "") for c in chunks if c.get("subject")})),
            "mediums": sorted(list({str(c.get("medium") or "") for c in chunks if c.get("medium")})),
        }
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        self._initialized = True
        return meta

    def search_vector(
        self,
        query: str,
        standard: Optional[int] = None,
        medium: Optional[str] = None,
        subject: Optional[str] = None,
        top_k: int = 30,
    ) -> List[Dict[str, Any]]:
        self._ensure_initialized()
        if self.index is None or self.model is None or not self.db_path.exists():
            return []

        query_emb = self.model.encode([query], normalize_embeddings=True)
        query_emb = np.array(query_emb, dtype=np.float32)

        search_k = min(self.index.ntotal, 100 if (standard or medium or subject) else top_k)
        if search_k <= 0:
            return []

        scores, ids = self.index.search(query_emb, search_k)
        candidates: List[Dict[str, Any]] = []

        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.cursor()
            for score, doc_id in zip(scores[0], ids[0]):
                if doc_id == -1:
                    continue

                cur.execute(
                    """
                    SELECT chunk_id, text, page_number, book_title, standard, subject, medium, chapter, section, content_type, source_url, source_type, metadata_json
                    FROM chunks WHERE id = ?
                    """,
                    (int(doc_id),),
                )
                row = cur.fetchone()
                if not row:
                    continue

                doc_std = int(row[4])
                doc_subj = str(row[5] or "")
                doc_med = str(row[6] or "")

                # Strict curriculum filtering on Standard and Subject
                if standard is not None and doc_std != standard:
                    continue
                if subject is not None:
                    if subject.lower() not in doc_subj.lower() and doc_subj.lower() not in subject.lower():
                        continue

                # Cosine similarity in range -1.0 to 1.0, clamp to 0.0 - 1.0
                cosine_sim = float(max(0.0, min(1.0, float(score))))

                # Soft medium preference: penalize slightly if medium doesn't match
                if medium is not None:
                    if medium.lower() not in doc_med.lower() and doc_med.lower() not in medium.lower():
                        cosine_sim *= 0.88

                candidates.append({
                    "document": {
                        "chunk_id": row[0],
                        "text": row[1],
                        "page_number": row[2],
                        "book_title": row[3],
                        "standard": row[4],
                        "subject": row[5],
                        "medium": row[6],
                        "chapter": row[7],
                        "section": row[8],
                        "content_type": row[9],
                        "source_url": row[10],
                        "source_type": row[11],
                        "metadata": json.loads(row[12]) if row[12] else {},
                    },
                    "score": round(cosine_sim, 4),
                    "retriever": "vector",
                })

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:top_k]

    def search_hybrid(
        self,
        query: str,
        standard: Optional[int] = None,
        medium: Optional[str] = None,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        top_k: int = 5,
        vector_weight: float = 0.6,
        bm25_weight: float = 0.4,
    ) -> Dict[str, Any]:
        self._ensure_initialized()

        # Extract query metadata if not explicitly provided
        meta_extracted = extract_balbharati_metadata(query)
        effective_standard = standard if standard is not None else meta_extracted.standard
        effective_medium = medium if medium is not None else meta_extracted.medium
        effective_subject = subject if subject is not None else meta_extracted.subject
        effective_chapter = chapter if chapter is not None else meta_extracted.chapter

        # 1. Lexical BM25 search
        bm25_results = self.bm25.search(
            query=meta_extracted.clean_query or query,
            standard=effective_standard,
            medium=effective_medium,
            subject=effective_subject,
            chapter=effective_chapter,
            top_k=25,
        )

        # 2. Dense Vector FAISS search
        vector_results = self.search_vector(
            query=meta_extracted.clean_query or query,
            standard=effective_standard,
            medium=effective_medium,
            subject=effective_subject,
            top_k=25,
        )

        # 3. Reciprocal Rank Fusion (RRF) & Score Combination
        combined_scores: Dict[str, float] = defaultdict(float)
        docs_by_id: Dict[str, Dict[str, Any]] = {}
        vector_ranks: Dict[str, int] = {}
        bm25_ranks: Dict[str, int] = {}

        for rank, item in enumerate(vector_results, start=1):
            doc = item["document"]
            cid = doc["chunk_id"]
            docs_by_id[cid] = doc
            vector_ranks[cid] = rank
            rrf_score = vector_weight / (self.rrf_k + rank)
            combined_scores[cid] += rrf_score + 0.5 * item["score"]

        for rank, item in enumerate(bm25_results, start=1):
            doc = item["document"]
            cid = doc.get("chunk_id") or f"bm25_{doc.get('standard')}_{doc.get('page_number')}_{rank}"
            docs_by_id[cid] = doc
            bm25_ranks[cid] = rank
            rrf_score = bm25_weight / (self.rrf_k + rank)
            combined_scores[cid] += rrf_score + 0.5 * item["score"]

        if not combined_scores:
            return {
                "query": query,
                "detected_metadata": meta_extracted.__dict__,
                "results": [],
                "confidence": 0.0,
            }

        # 4. Deduplication & Overlap Suppression
        ranked_cids = sorted(combined_scores.keys(), key=lambda cid: combined_scores[cid], reverse=True)
        max_combined = max(combined_scores.values()) if combined_scores else 1.0

        selected_results: List[Dict[str, Any]] = []
        seen_texts: Set[str] = set()

        for rank, cid in enumerate(ranked_cids, start=1):
            doc = docs_by_id[cid]
            norm_text = _clean_text_norm(doc.get("text", ""))

            # Skip duplicate or heavily overlapping texts
            is_dup = False
            for prev in seen_texts:
                if norm_text in prev or prev in norm_text:
                    is_dup = True
                    break
            if is_dup:
                continue

            seen_texts.add(norm_text)
            norm_score = round(min(1.0, combined_scores[cid] / (max_combined + 1e-6)), 4)

            selected_results.append({
                "rank": len(selected_results) + 1,
                "score": norm_score,
                "source": "Balbharati",
                "book": doc.get("book_title"),
                "standard": doc.get("standard"),
                "subject": doc.get("subject"),
                "medium": doc.get("medium"),
                "chapter": doc.get("chapter"),
                "page": doc.get("page_number"),
                "chunk_id": doc.get("chunk_id"),
                "content_type": doc.get("content_type", "text"),
                "source_url": doc.get("source_url", ""),
                "text": doc.get("text"),
                "vector_rank": vector_ranks.get(cid),
                "bm25_rank": bm25_ranks.get(cid),
            })

            if len(selected_results) >= top_k:
                break

        overall_confidence = selected_results[0]["score"] if selected_results else 0.0

        return {
            "query": query,
            "detected_metadata": meta_extracted.__dict__,
            "results": selected_results,
            "confidence": overall_confidence,
        }


_RETRIEVER_INSTANCE: Optional[BalbharatiHybridRetriever] = None


def get_balbharati_retriever() -> BalbharatiHybridRetriever:
    global _RETRIEVER_INSTANCE
    if _RETRIEVER_INSTANCE is None:
        _RETRIEVER_INSTANCE = BalbharatiHybridRetriever()
    return _RETRIEVER_INSTANCE
