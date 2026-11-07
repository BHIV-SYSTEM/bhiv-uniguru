"""
Semantic, Section-Aware Text Chunker for UniGuru.
Splits educational text respecting sentence and Devanagari Danda boundaries.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    page_number: int
    text: str
    char_count: int
    word_count: int
    language: str
    domain: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TextChunker:
    """
    Splits text into overlapping chunks respecting sentence, paragraph,
    and Sanskrit/Hindi/Marathi punctuation marks (। and ॥).
    """

    # Splits on newlines or sentence boundaries: '.', '!', '?', '।', '॥'
    SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?।॥\n])\s+")

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self,
        text: str,
        document_id: str,
        language: str = "english",
        domain: str = "general",
        default_page_number: int = 1,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[TextChunk]:
        """
        Split document text into a list of TextChunk objects.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        # Split into sentence-level units
        sentences = [s.strip() for s in self.SENTENCE_SPLIT_REGEX.split(clean_text) if s.strip()]
        if not sentences:
            sentences = [clean_text]

        chunks: List[TextChunk] = []
        current_sentences: List[str] = []
        current_length = 0
        chunk_idx = 0

        for sentence in sentences:
            sent_len = len(sentence)
            
            # If a single sentence exceeds chunk_size, split by words
            if sent_len > self.chunk_size:
                # Flush existing buffer first
                if current_sentences:
                    chunk_text = " ".join(current_sentences).strip()
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(
                            self._create_chunk(
                                chunk_text, document_id, chunk_idx, default_page_number,
                                language, domain, source_metadata
                            )
                        )
                        chunk_idx += 1
                    current_sentences = []
                    current_length = 0

                # Slice large sentence by character length
                for start in range(0, sent_len, self.chunk_size - self.chunk_overlap):
                    sub = sentence[start : start + self.chunk_size].strip()
                    if len(sub) >= self.min_chunk_size:
                        chunks.append(
                            self._create_chunk(
                                sub, document_id, chunk_idx, default_page_number,
                                language, domain, source_metadata
                            )
                        )
                        chunk_idx += 1
                continue

            if current_length + sent_len > self.chunk_size and current_sentences:
                # Emit chunk
                chunk_text = " ".join(current_sentences).strip()
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(
                        self._create_chunk(
                            chunk_text, document_id, chunk_idx, default_page_number,
                            language, domain, source_metadata
                        )
                    )
                    chunk_idx += 1

                # Overlap preservation: keep trailing sentences up to chunk_overlap chars
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_sentences):
                    if overlap_len + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break

                current_sentences = overlap_sentences
                current_length = overlap_len

            current_sentences.append(sentence)
            current_length += sent_len

        # Flush remaining sentences
        if current_sentences:
            chunk_text = " ".join(current_sentences).strip()
            if len(chunk_text) >= self.min_chunk_size or not chunks:
                chunks.append(
                    self._create_chunk(
                        chunk_text, document_id, chunk_idx, default_page_number,
                        language, domain, source_metadata
                    )
                )

        return chunks

    @staticmethod
    def _create_chunk(
        text: str,
        document_id: str,
        chunk_idx: int,
        page_number: int,
        language: str,
        domain: str,
        source_metadata: Optional[Dict[str, Any]],
    ) -> TextChunk:
        words = re.findall(r"[\u0900-\u097F\w]+", text)
        return TextChunk(
            chunk_id=f"chk_{document_id}_{chunk_idx:04d}",
            document_id=document_id,
            chunk_index=chunk_idx,
            page_number=page_number,
            text=text,
            char_count=len(text),
            word_count=len(words),
            language=language,
            domain=domain,
            metadata=source_metadata or {},
        )

