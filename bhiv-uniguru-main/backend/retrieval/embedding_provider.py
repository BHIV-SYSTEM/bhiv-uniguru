from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Iterable, List


class EmbeddingProvider(ABC):
    """Provider-neutral embedding contract for sovereign/offline retrieval."""

    @abstractmethod
    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        raise NotImplementedError

    def normalize(self, vector: List[float]) -> List[float]:
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude <= 0:
            return list(vector)
        return [value / magnitude for value in vector]

    def similarity(self, left: List[float], right: List[float]) -> float:
        left_n = self.normalize(left)
        right_n = self.normalize(right)
        return round(sum(a * b for a, b in zip(left_n, right_n)), 6)


class LocalHashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embedding path using hashed lexical features."""

    def __init__(self, dimensions: int = 256) -> None:
        self.dimensions = int(dimensions)

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        return [self.normalize(self._encode_one(text)) for text in texts]

    def _encode_one(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", str(text or "").lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        return vector
