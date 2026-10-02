from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from ontology.snapshot_manager import SNAPSHOT_V1_PATH, SnapshotManager


DOMAIN_TOKENS: Dict[str, List[str]] = {
    "quantum": ["quantum", "qubit", "superposition", "entanglement", "algorithm"],
    "jain": ["jain", "ahimsa", "anekantavada", "mahavira", "tirthankara"],
    "swaminarayan": ["swaminarayan", "vachanamrut", "akshar", "purushottam", "baps"],
    "gurukul": ["gurukul", "nyaya", "vedic", "math"],
}


class ConceptResolver:
    """Deterministic query-to-concept resolver over ontology snapshot."""

    def __init__(self, snapshot_path: Optional[Path] = None):
        self.snapshot_manager = SnapshotManager()
        self.snapshot_path = snapshot_path or SNAPSHOT_V1_PATH
        self.snapshot = self.snapshot_manager.load_snapshot(self.snapshot_path)
        self.concepts = list(self.snapshot.get("concepts", []))
        self.by_id = {row["concept_id"]: row for row in self.concepts}
        self.unresolved = next(
            (
                row
                for row in self.concepts
                if row.get("canonical_name") == "UniGuru Unresolved Concept"
            ),
            None,
        )

    @staticmethod
    def _tokens(text: str) -> List[str]:
        cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
        return [token for token in cleaned.split() if token]

    def _resolve_domain(self, query: str, retrieval_trace: Optional[Dict[str, Any]]) -> Optional[str]:
        if retrieval_trace and retrieval_trace.get("match_found"):
            consulted = retrieval_trace.get("sources_consulted") or []
            valid = sorted({domain for domain in consulted if domain in DOMAIN_TOKENS})
            if valid:
                return valid[0]

        query_tokens = set(self._tokens(query))
        for domain in sorted(DOMAIN_TOKENS):
            if any(token in query_tokens for token in DOMAIN_TOKENS[domain]):
                return domain
        return None

    def _best_match_in_domain(self, query: str, domain: Optional[str]) -> Optional[Dict[str, Any]]:
        query_tokens = set(self._tokens(query))
        query_text = " ".join(self._tokens(query))

        candidates = self.concepts
        if domain:
            candidates = [row for row in candidates if row.get("domain") == domain]

        scored = []
        for row in candidates:
            name_tokens = self._tokens(str(row.get("canonical_name", "")))
            if not name_tokens:
                continue
            phrase = " ".join(name_tokens)
            phrase_hit = phrase in query_text
            token_hits = sum(1 for token in name_tokens if token in query_tokens)
            if token_hits == 0 and not phrase_hit:
                continue
            scored.append((1 if phrase_hit else 0, token_hits, -len(name_tokens), row["concept_id"], row))

        if not scored:
            return None
        scored.sort(reverse=True)
        return scored[0][-1]

    def resolve(self, query: str, retrieval_trace: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        domain = self._resolve_domain(query, retrieval_trace)
        matched = self._best_match_in_domain(query, domain)

        if matched is None:
            if domain:
                matched = next(
                    (
                        row
                        for row in self.concepts
                        if row.get("domain") == domain and "Domain" in str(row.get("canonical_name", ""))
                    ),
                    None,
                )
            matched = matched or self.unresolved or self.concepts[0]

        return {
            "concept_id": matched["concept_id"],
            "canonical_name": matched["canonical_name"],
            "domain": matched["domain"],
            "truth_level": matched["truth_level"],
            "snapshot_version": self.snapshot["snapshot_version"],
            "snapshot_hash": self.snapshot["snapshot_hash"],
        }
