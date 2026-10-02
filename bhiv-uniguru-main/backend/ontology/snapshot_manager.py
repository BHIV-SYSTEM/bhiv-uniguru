from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ontology.exceptions import ImmutableConceptViolation
from ontology.graph import OntologyGraph, get_frozen_concepts
from ontology.schema import Concept, concept_from_dict, concept_to_dict


_MODULE_DIR = Path(__file__).resolve().parent
SNAPSHOT_DIR = _MODULE_DIR / "snapshots"
SNAPSHOT_V1_PATH = SNAPSHOT_DIR / "snapshot_v1.json"


class SnapshotManager:
    @staticmethod
    def _canonical_json(data: Dict[str, Any]) -> str:
        return json.dumps(data, sort_keys=True)

    @staticmethod
    def _sorted_concepts(concepts: Iterable[Concept]) -> List[Dict[str, Any]]:
        return [
            concept_to_dict(concept)
            for concept in sorted(concepts, key=lambda item: item.concept_id)
        ]

    def build_snapshot_payload(self, concepts: Iterable[Concept], snapshot_version: int) -> Dict[str, Any]:
        payload = {
            "snapshot_version": snapshot_version,
            "concepts": self._sorted_concepts(concepts),
        }
        payload["snapshot_hash"] = self.hash_payload(payload)
        return payload

    def hash_payload(self, payload: Dict[str, Any]) -> str:
        core = dict(payload)
        core.pop("snapshot_hash", None)
        return hashlib.sha256(self._canonical_json(core).encode("utf-8")).hexdigest()

    @staticmethod
    def _by_id(concepts: Iterable[Concept]) -> Dict[str, Concept]:
        return {concept.concept_id: concept for concept in concepts}

    def enforce_immutable_constraints(
        self,
        previous_concepts: Iterable[Concept],
        candidate_concepts: Iterable[Concept],
    ) -> None:
        previous_index = self._by_id(previous_concepts)
        candidate_index = self._by_id(candidate_concepts)

        for concept_id, previous in previous_index.items():
            if not previous.immutable:
                continue
            candidate = candidate_index.get(concept_id)
            if candidate is None:
                raise ImmutableConceptViolation(
                    f"Immutable concept cannot be deleted: {concept_id}"
                )
            if concept_to_dict(previous) != concept_to_dict(candidate):
                raise ImmutableConceptViolation(
                    f"Immutable concept cannot be modified: {concept_id}"
                )

    def _load_existing_concepts(self, path: Path) -> List[Concept]:
        if not path.exists():
            return []
        payload = self.load_snapshot(path)
        return [concept_from_dict(row) for row in payload.get("concepts", [])]

    def save_snapshot(
        self,
        concepts: Iterable[Concept],
        snapshot_version: int,
        path: Path,
    ) -> Dict[str, Any]:
        candidate_concepts = list(concepts)
        existing_concepts = self._load_existing_concepts(path)
        if existing_concepts:
            self.enforce_immutable_constraints(existing_concepts, candidate_concepts)

        payload = self.build_snapshot_payload(concepts=candidate_concepts, snapshot_version=snapshot_version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    def load_snapshot(self, path: Path) -> Dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        calculated_hash = self.hash_payload(payload)
        if payload.get("snapshot_hash") != calculated_hash:
            raise ValueError(
                f"Snapshot hash mismatch for {path}: "
                f"stored={payload.get('snapshot_hash')} calculated={calculated_hash}"
            )

        # Validate each concept against schema and graph structure.
        concepts = [concept_from_dict(concept_row) for concept_row in payload.get("concepts", [])]
        OntologyGraph(concepts)

        return payload

    def create_default_snapshot_v1(self) -> Dict[str, Any]:
        concepts = get_frozen_concepts()
        return self.save_snapshot(concepts=concepts, snapshot_version=1, path=SNAPSHOT_V1_PATH)

    def mutate_snapshot_concepts(
        self,
        path: Path,
        updates: Dict[str, Dict[str, Any]],
        deletions: Iterable[str],
        snapshot_version: int,
    ) -> Dict[str, Any]:
        current_payload = self.load_snapshot(path)
        current_concepts = [concept_from_dict(row) for row in current_payload.get("concepts", [])]
        current_index = {concept.concept_id: concept for concept in current_concepts}

        candidate_rows: List[Dict[str, Any]] = []
        deleted_ids = set(deletions)
        for concept in current_concepts:
            if concept.concept_id in deleted_ids:
                if concept.immutable:
                    raise ImmutableConceptViolation(
                        f"Immutable concept cannot be deleted: {concept.concept_id}"
                    )
                continue

            if concept.concept_id in updates:
                if concept.immutable:
                    raise ImmutableConceptViolation(
                        f"Immutable concept cannot be modified: {concept.concept_id}"
                    )
                row = concept_to_dict(concept)
                row.update(dict(updates[concept.concept_id]))
                candidate_rows.append(row)
            else:
                candidate_rows.append(concept_to_dict(concept))

        # Add updates for new concept ids only.
        for concept_id, update_row in updates.items():
            if concept_id in current_index:
                continue
            candidate_rows.append(dict(update_row))

        candidate_concepts = [concept_from_dict(row) for row in candidate_rows]
        self.enforce_immutable_constraints(current_concepts, candidate_concepts)
        OntologyGraph(candidate_concepts).validate_structure()

        return self.save_snapshot(
            concepts=candidate_concepts,
            snapshot_version=snapshot_version,
            path=path,
        )
