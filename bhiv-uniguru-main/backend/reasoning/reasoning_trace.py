from __future__ import annotations

from typing import Any, Dict, List


class ReasoningTraceGenerator:
    """Builds replayable deterministic ontology reasoning traces."""

    @staticmethod
    def from_reasoning_path(
        reasoning_path: List[Dict[str, Any]],
        snapshot_version: int,
        snapshot_hash: str,
    ) -> Dict[str, Any]:
        return {
            "concept_chain": [str(node["canonical_name"]).lower() for node in reasoning_path],
            "truth_levels": [int(node["truth_level"]) for node in reasoning_path],
            "snapshot_version": int(snapshot_version),
            "snapshot_hash": snapshot_hash,
        }
