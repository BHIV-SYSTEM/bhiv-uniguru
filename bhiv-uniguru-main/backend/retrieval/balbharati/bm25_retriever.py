"""Multilingual Okapi BM25 Lexical Retriever for Balbharati Textbooks."""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


_STOPWORDS_EN = {
    "a", "an", "the", "is", "are", "was", "were", "what", "which", "who", "when",
    "where", "why", "how", "explain", "tell", "about", "for", "to", "in", "on",
    "of", "and", "or", "me", "please", "can", "could", "would", "should", "according",
    "book", "textbook", "standard", "class", "std", "grade", "balbharati", "maharashtra",
}

_STOPWORDS_MR = {
    "आहे", "नाही", "सांग", "करा", "स्पष्ट", "च्या", "तील", "वर", "मध्ये", "हे", "ती",
    "तो", "ते", "आणि", "किंवा", "म्हणजे", "काय", "पुस्तकातील", "इयत्ता", "विषय",
}

_STOPWORDS_HI = {
    "है", "नहीं", "बताओ", "क्या", "की", "का", "के", "में", "पर", "और", "या",
    "पुस्तक", "कक्षा", "से", "को",
}


def tokenize(text: str) -> List[str]:
    """Tokenize multilingual English/Devanagari text into clean stems/tokens."""
    norm = unicodedata.normalize("NFC", str(text or "").lower())
    # Match alphanumeric words + Devanagari words
    raw_tokens = re.findall(r"[\w\u0900-\u097F]+", norm)
    tokens: List[str] = []
    for token in raw_tokens:
        if len(token) <= 1:
            continue
        if token in _STOPWORDS_EN or token in _STOPWORDS_MR or token in _STOPWORDS_HI:
            continue
        # simple English suffix stripping
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            token = token[:-1]
        tokens.append(token)
    return tokens


class BM25Retriever:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: List[Dict[str, Any]] = []
        self.doc_lens: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)  # term -> [(doc_idx, freq)]
        self.total_docs: int = 0

    def index_documents(self, documents: List[Dict[str, Any]]) -> None:
        self.documents = list(documents)
        self.total_docs = len(self.documents)
        self.doc_lens = []
        self.doc_freqs = defaultdict(int)
        self.inverted_index = defaultdict(list)

        total_len = 0
        for doc_idx, doc in enumerate(self.documents):
            # Index text, chapter, concept, subject, title
            fields = [
                doc.get("text", ""),
                doc.get("chapter", ""),
                doc.get("concept", ""),
                doc.get("subject", ""),
                doc.get("book_title", ""),
                doc.get("definition", ""),
            ]
            full_text = " ".join(str(f or "") for f in fields)
            tokens = tokenize(full_text)
            self.doc_lens.append(len(tokens))
            total_len += len(tokens)

            tf = Counter(tokens)
            for term, count in tf.items():
                self.doc_freqs[term] += 1
                self.inverted_index[term].append((doc_idx, count))

        self.avg_doc_len = (total_len / self.total_docs) if self.total_docs > 0 else 0.0

    def search(
        self,
        query: str,
        standard: Optional[int] = None,
        medium: Optional[str] = None,
        subject: Optional[str] = None,
        chapter: Optional[str] = None,
        top_k: int = 20,
    ) -> List[Dict[str, Any]]:
        if self.total_docs == 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Filter candidate indices
        allowed_indices: Optional[Set[int]] = None
        if standard is not None or medium is not None or subject is not None or chapter is not None:
            def _filter_candidates(use_medium: bool) -> Set[int]:
                matched: Set[int] = set()
                for doc_idx, doc in enumerate(self.documents):
                    doc_std = doc.get("standard") or doc.get("grade")
                    if standard is not None and doc_std is not None:
                        if int(doc_std) != int(standard):
                            continue

                    if use_medium and medium is not None:
                        doc_med = str(doc.get("medium") or "").lower()
                        med_req = str(medium).lower()
                        if med_req not in doc_med and doc_med not in med_req:
                            continue

                    doc_subj = str(doc.get("subject") or "").lower()
                    if subject is not None:
                        subj_req = str(subject).lower()
                        if subj_req not in doc_subj and doc_subj not in subj_req:
                            continue

                    if chapter is not None:
                        doc_chap = str(doc.get("chapter") or "").lower()
                        chap_req = str(chapter).lower()
                        if chap_req not in doc_chap and doc_chap not in chap_req:
                            continue

                    matched.add(doc_idx)
                return matched

            res = _filter_candidates(use_medium=True)
            if not res and medium is not None:
                res = _filter_candidates(use_medium=False)
            allowed_indices = res

        scores: Dict[int, float] = defaultdict(float)

        for term in query_tokens:
            df = self.doc_freqs.get(term, 0)
            if df == 0:
                continue

            # Standard Okapi BM25 idf
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            postings = self.inverted_index.get(term, [])

            for doc_idx, freq in postings:
                if allowed_indices is not None and doc_idx not in allowed_indices:
                    continue

                doc_len = self.doc_lens[doc_idx]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avg_doc_len or 1.0)))
                scores[doc_idx] += idf * (numerator / denominator)

        if not scores:
            return []

        # Sort descending
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        results = []
        max_score = ranked[0][1] if ranked else 1.0

        for doc_idx, raw_score in ranked:
            doc = dict(self.documents[doc_idx])
            # Normalized BM25 score in range 0.0 - 1.0
            norm_score = round(min(1.0, raw_score / (max_score + 1e-6)), 4)
            results.append({
                "document": doc,
                "score": norm_score,
                "raw_bm25_score": round(raw_score, 4),
                "retriever": "bm25",
            })

        return results

    def save_to_file(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "total_docs": self.total_docs,
            "avg_doc_len": self.avg_doc_len,
            "documents": self.documents,
        }
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load_from_file(self, path: str | Path) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            self.index_documents(payload.get("documents", []))
            return True
        except Exception:
            return False
