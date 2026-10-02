from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ontology.exceptions import ImmutableConceptViolation
from ontology.graph import OntologyGraph
from ontology.schema import concept_from_dict
from ontology.snapshot_manager import SNAPSHOT_V1_PATH, SnapshotManager


DOMAIN_CONCEPT_MAP: Dict[str, str] = {
    "quantum": "adf9434a-c8b9-4f5d-9d4b-8b7e3c286028",
    "jain": "ceb14ea2-d665-4ebf-ab6a-8dcaed4bd793",
    "swaminarayan": "eb517fbb-1585-4f83-8532-42489d0975d5",
    "gurukul": "70dedec2-fc86-41a0-ab4f-30299e4a5fb7",
    "core": "f5e3a359-9ad5-4fcb-b483-598d0917f865",
}


class OntologyRegistry:
    def __init__(self, snapshot_path: Optional[Path] = None):
        self.snapshot_manager = SnapshotManager()
        self.snapshot_path = snapshot_path or SNAPSHOT_V1_PATH
        self.snapshot = self.snapshot_manager.load_snapshot(self.snapshot_path)
        self._concept_index = {
            row["concept_id"]: row for row in self.snapshot.get("concepts", [])
        }
        self._registry_index = {
            concept_id: {
                "concept_id": row["concept_id"],
                "canonical_name": row["canonical_name"],
                "domain": row["domain"],
                "truth_level": row["truth_level"],
                "snapshot_version": self.snapshot["snapshot_version"],
                "snapshot_hash": self.snapshot["snapshot_hash"],
                "reasoning_path": [],
            }
            for concept_id, row in self._concept_index.items()
        }

    def default_reference(self) -> Dict[str, Any]:
        return {
            "concept_id": DOMAIN_CONCEPT_MAP["core"],
            "canonical_name": self._concept_index[DOMAIN_CONCEPT_MAP["core"]]["canonical_name"],
            "domain": "core",
            "truth_level": self._concept_index[DOMAIN_CONCEPT_MAP["core"]]["truth_level"],
            "snapshot_version": self.snapshot["snapshot_version"],
            "snapshot_hash": self.snapshot["snapshot_hash"],
            "reasoning_path": [],
        }

    def _resolve_domain_from_trace(self, trace: Optional[Dict[str, Any]]) -> str:
        if not trace or not trace.get("match_found"):
            return "core"
        consulted = trace.get("sources_consulted") or []
        valid_domains = sorted({domain for domain in consulted if domain in DOMAIN_CONCEPT_MAP})
        return valid_domains[0] if valid_domains else "core"

    def build_reference(
        self,
        decision: str,
        trace: Optional[Dict[str, Any]],
        resolved_concept: Optional[Dict[str, Any]] = None,
        reasoning_path: Optional[list] = None,
    ) -> Dict[str, Any]:
        if decision != "answer":
            return self.default_reference()
        if resolved_concept:
            concept_id = resolved_concept["concept_id"]
            row = self._concept_index.get(concept_id)
            if row is None:
                raise ValueError(f"Unknown resolved concept_id: {concept_id}")
            domain = row["domain"]
        else:
            domain = self._resolve_domain_from_trace(trace)
            concept_id = DOMAIN_CONCEPT_MAP[domain]
            row = self._concept_index[concept_id]
        return {
            "concept_id": concept_id,
            "canonical_name": row["canonical_name"],
            "domain": domain,
            "truth_level": row["truth_level"],
            "snapshot_version": self.snapshot["snapshot_version"],
            "snapshot_hash": self.snapshot["snapshot_hash"],
            "reasoning_path": reasoning_path or [],
        }

    def get_registry_contract(self, ontology_reference: Dict[str, Any]) -> Dict[str, Any]:
        if ontology_reference.get("snapshot_version") != self.snapshot["snapshot_version"]:
            raise ValueError("Ontology reference snapshot_version mismatch.")
        if ontology_reference.get("snapshot_hash") != self.snapshot["snapshot_hash"]:
            raise ValueError("Ontology reference snapshot_hash mismatch.")
        concept_id = ontology_reference.get("concept_id")
        if concept_id not in self._registry_index:
            raise ValueError(f"Unknown concept_id in ontology reference: {concept_id}")
        contract = dict(self._registry_index[concept_id])
        contract["reasoning_path"] = list(ontology_reference.get("reasoning_path") or [])
        return contract

    def get_concept(self, concept_id: str) -> Dict[str, Any]:
        row = self._concept_index.get(concept_id)
        if row is None:
            raise ValueError(f"Unknown concept_id: {concept_id}")
        return {
            "concept_id": row["concept_id"],
            "domain": row["domain"],
            "truth_level": row["truth_level"],
            "snapshot_version": self.snapshot["snapshot_version"],
            "snapshot_hash": self.snapshot["snapshot_hash"],
            "immutable": bool(row.get("immutable", False)),
        }

    def refresh_snapshot(self, snapshot_payload: Dict[str, Any]) -> None:
        if "concepts" not in snapshot_payload:
            raise ValueError("Invalid snapshot payload: missing concepts.")
        concepts = [concept_from_dict(row) for row in snapshot_payload.get("concepts", [])]
        OntologyGraph(concepts).validate_structure()

        previous_index = self._concept_index
        candidate_index = {row["concept_id"]: row for row in snapshot_payload.get("concepts", [])}
        for concept_id, previous in previous_index.items():
            if not previous.get("immutable"):
                continue
            candidate = candidate_index.get(concept_id)
            if candidate is None:
                raise ImmutableConceptViolation(
                    f"Immutable concept cannot be deleted in registry update: {concept_id}"
                )
            if candidate != previous:
                raise ImmutableConceptViolation(
                    f"Immutable concept cannot be modified in registry update: {concept_id}"
                )

        self.snapshot = dict(snapshot_payload)
        self._concept_index = candidate_index
        self._registry_index = {
            concept_id: {
                "concept_id": row["concept_id"],
                "canonical_name": row["canonical_name"],
                "domain": row["domain"],
                "truth_level": row["truth_level"],
                "snapshot_version": self.snapshot["snapshot_version"],
                "snapshot_hash": self.snapshot["snapshot_hash"],
                "reasoning_path": [],
            }
            for concept_id, row in self._concept_index.items()
        }
