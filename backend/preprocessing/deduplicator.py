"""
Deduplication Engine for UniGuru Educational Substrate.
Provides exact content hashing (SHA-256) and n-gram shingle near-duplicate detection.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("uniguru.preprocessing.deduplicator")


class DocumentDeduplicator:
    """
    Tracks seen document hashes and shingles to prevent duplicate ingestion.
    """

    def __init__(self, registry_path: Optional[str | Path] = None):
        self.registry_path = Path(registry_path) if registry_path else None
        # Maps sha256_hash -> {"doc_id": ..., "file_name": ...}
        self.exact_hashes: Dict[str, Dict[str, Any]] = {}
        # Maps doc_id -> set of 3-gram shingles
        self.shingle_index: Dict[str, Set[str]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        if self.registry_path and self.registry_path.is_file():
            try:
                data = json.loads(self.registry_path.read_text(encoding="utf-8"))
                self.exact_hashes = data.get("exact_hashes", {})
            except Exception as e:
                logger.warning(f"Failed to load deduplication registry: {e}")

    def save_registry(self) -> None:
        if self.registry_path:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "exact_hashes": self.exact_hashes,
                "total_documents_indexed": len(self.exact_hashes),
            }
            self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def calculate_sha256(text: str) -> str:
        """Deterministic hash of normalized text."""
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_shingles(text: str, n: int = 3) -> Set[str]:
        """Compute word n-gram shingles for near-duplicate Jaccard estimation."""
        words = re.findall(r"\w+", text.lower())
        if len(words) < n:
            return set(words)
        return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}

    def check_duplicate(
        self,
        text: str,
        document_id: str,
        file_name: str,
        near_duplicate_threshold: float = 0.90,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Check if document is an exact duplicate or near duplicate.
        Returns: (is_duplicate: bool, original_doc_id: Optional[str], match_type: str)
        """
        if not text.strip():
            return False, None, "empty"

        sha = self.calculate_sha256(text)

        # 1. Exact Duplicate Check
        if sha in self.exact_hashes:
            orig = self.exact_hashes[sha]
            return True, orig["doc_id"], "exact_hash_match"

        # 2. Near Duplicate Check via Jaccard Shingling
        shingles = self.compute_shingles(text, n=3)
        if shingles:
            for existing_id, existing_shingles in self.shingle_index.items():
                intersection = len(shingles & existing_shingles)
                union = len(shingles | existing_shingles)
                jaccard = intersection / max(1, union)
                if jaccard >= near_duplicate_threshold:
                    return True, existing_id, f"near_duplicate_jaccard_{jaccard:.2f}"

        # Register as new unique document
        self.exact_hashes[sha] = {"doc_id": document_id, "file_name": file_name}
        if shingles:
            self.shingle_index[document_id] = shingles

        return False, None, "unique"

