from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from ontology.exceptions import OntologyGraphValidationError
from ontology.schema import Concept, concept_from_dict


_FROZEN_CONCEPT_ROWS: Tuple[dict, ...] = (
    {
        "concept_id": "8cb2fa29-2d7e-4bd0-af9d-080f3dd0459d",
        "canonical_name": "UniGuru Canonical Root",
        "parent_id": None,
        "truth_level": 4,
        "domain": "core",
        "source_reference": "uniguru/ontology/schema.py",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "f5e3a359-9ad5-4fcb-b483-598d0917f865",
        "canonical_name": "UniGuru Unresolved Concept",
        "parent_id": "8cb2fa29-2d7e-4bd0-af9d-080f3dd0459d",
        "truth_level": 0,
        "domain": "core",
        "source_reference": "uniguru/ontology/registry.py",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "adf9434a-c8b9-4f5d-9d4b-8b7e3c286028",
        "canonical_name": "Quantum Knowledge Domain",
        "parent_id": "8cb2fa29-2d7e-4bd0-af9d-080f3dd0459d",
        "truth_level": 3,
        "domain": "quantum",
        "source_reference": "backend/knowledge/quantum/README.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "ceb14ea2-d665-4ebf-ab6a-8dcaed4bd793",
        "canonical_name": "Jain Knowledge Domain",
        "parent_id": "8cb2fa29-2d7e-4bd0-af9d-080f3dd0459d",
        "truth_level": 3,
        "domain": "jain",
        "source_reference": "backend/knowledge/jain",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "eb517fbb-1585-4f83-8532-42489d0975d5",
        "canonical_name": "Swaminarayan Knowledge Domain",
        "parent_id": "8cb2fa29-2d7e-4bd0-af9d-080f3dd0459d",
        "truth_level": 3,
        "domain": "swaminarayan",
        "source_reference": "backend/knowledge/swaminarayan",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "70dedec2-fc86-41a0-ab4f-30299e4a5fb7",
        "canonical_name": "Gurukul Knowledge Domain",
        "parent_id": "8cb2fa29-2d7e-4bd0-af9d-080f3dd0459d",
        "truth_level": 3,
        "domain": "gurukul",
        "source_reference": "backend/knowledge/gurukul",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "ac1320c6-08f2-42a2-8ff2-841f7b263ad5",
        "canonical_name": "Quantum Root",
        "parent_id": "adf9434a-c8b9-4f5d-9d4b-8b7e3c286028",
        "truth_level": 4,
        "domain": "quantum",
        "source_reference": "backend/knowledge/quantum/README.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "2200072c-5a0d-4f68-a56a-a0c807f6cf5e",
        "canonical_name": "Qubit",
        "parent_id": "ac1320c6-08f2-42a2-8ff2-841f7b263ad5",
        "truth_level": 3,
        "domain": "quantum",
        "source_reference": "backend/knowledge/quantum/qubit.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "1f460503-ebf7-4f5a-a0f0-c0f17d0fa6f5",
        "canonical_name": "Superposition",
        "parent_id": "2200072c-5a0d-4f68-a56a-a0c807f6cf5e",
        "truth_level": 3,
        "domain": "quantum",
        "source_reference": "backend/knowledge/quantum/superposition.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "70c47ad2-e0ee-499e-9065-c3a31f1e0e9d",
        "canonical_name": "Entanglement",
        "parent_id": "1f460503-ebf7-4f5a-a0f0-c0f17d0fa6f5",
        "truth_level": 3,
        "domain": "quantum",
        "source_reference": "backend/knowledge/quantum/entanglement.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "8e362941-2580-4c5f-b273-7dfeb9c62046",
        "canonical_name": "Quantum Algorithms",
        "parent_id": "70c47ad2-e0ee-499e-9065-c3a31f1e0e9d",
        "truth_level": 3,
        "domain": "quantum",
        "source_reference": "backend/knowledge/quantum/Quantum_Algorithms/quantum_algorithms_overview.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "7676764d-7f7d-4bc2-8c80-f689e113baec",
        "canonical_name": "Jain Root",
        "parent_id": "ceb14ea2-d665-4ebf-ab6a-8dcaed4bd793",
        "truth_level": 4,
        "domain": "jain",
        "source_reference": "backend/knowledge/jain",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "2fdd0676-f275-4190-b90c-0ef344f35ca6",
        "canonical_name": "Ahimsa",
        "parent_id": "7676764d-7f7d-4bc2-8c80-f689e113baec",
        "truth_level": 3,
        "domain": "jain",
        "source_reference": "backend/knowledge/jain/acharanga_sutra.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "495fe91d-d5c8-4a89-b3f0-5e16e001ec9a",
        "canonical_name": "Anekantavada",
        "parent_id": "2fdd0676-f275-4190-b90c-0ef344f35ca6",
        "truth_level": 3,
        "domain": "jain",
        "source_reference": "backend/knowledge/jain/anekantavada_syadvada.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "a1648e74-dceb-4816-b47e-33db755626b8",
        "canonical_name": "Swaminarayan Root",
        "parent_id": "eb517fbb-1585-4f83-8532-42489d0975d5",
        "truth_level": 4,
        "domain": "swaminarayan",
        "source_reference": "backend/knowledge/swaminarayan",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "f172f859-a04f-44dd-a94a-2e5b6bef4de8",
        "canonical_name": "Vachanamrut",
        "parent_id": "a1648e74-dceb-4816-b47e-33db755626b8",
        "truth_level": 3,
        "domain": "swaminarayan",
        "source_reference": "backend/knowledge/swaminarayan/vachanamrut_core.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
    {
        "concept_id": "720137eb-f204-44b0-a45d-d8b4ad73c9f0",
        "canonical_name": "Akshar Purushottam Darshan",
        "parent_id": "f172f859-a04f-44dd-a94a-2e5b6bef4de8",
        "truth_level": 3,
        "domain": "swaminarayan",
        "source_reference": "backend/knowledge/swaminarayan/akshar_purushottam_darshan.md",
        "snapshot_version": 1,
        "created_at": "2026-03-04T00:00:00Z",
        "immutable": True,
    },
)


def get_frozen_concepts() -> Tuple[Concept, ...]:
    return tuple(concept_from_dict(row) for row in _FROZEN_CONCEPT_ROWS)


class OntologyGraph:
    def __init__(self, concepts: Iterable[Concept]):
        self.concepts = tuple(concepts)
        if len({concept.concept_id for concept in self.concepts}) != len(self.concepts):
            raise OntologyGraphValidationError("Duplicate concept_id detected in ontology graph.")
        self.by_id: Dict[str, Concept] = {concept.concept_id: concept for concept in self.concepts}
        self.children: Dict[Optional[str], List[str]] = {}
        self._index_children()
        self.validate_structure()

    def _index_children(self) -> None:
        for concept in self.concepts:
            self.children.setdefault(concept.parent_id, []).append(concept.concept_id)
        for child_ids in self.children.values():
            child_ids.sort()

    def validate_structure(self) -> None:
        allowed_domains: Set[str] = {"quantum", "jain", "swaminarayan", "gurukul", "core"}

        roots = [concept.concept_id for concept in self.concepts if concept.parent_id is None]
        if len(roots) != 1:
            raise OntologyGraphValidationError(
                f"Single root constraint violated. Expected 1 root, found {len(roots)}."
            )

        for concept in self.concepts:
            if not concept.immutable:
                raise OntologyGraphValidationError(f"Concept is not immutable: {concept.concept_id}")
            if concept.parent_id is not None and concept.parent_id not in self.by_id:
                raise OntologyGraphValidationError(
                    f"Parent concept missing for {concept.concept_id}: {concept.parent_id}"
                )
            if concept.parent_id == concept.concept_id:
                raise OntologyGraphValidationError(
                    f"Invalid parent-child loop: concept {concept.concept_id} points to itself."
                )
            if concept.domain.value not in allowed_domains:
                raise OntologyGraphValidationError(
                    f"Invalid domain assignment for {concept.concept_id}: {concept.domain.value}"
                )
        self._ensure_acyclic()

    def _ensure_acyclic(self) -> None:
        visited: Dict[str, int] = {}
        lineage: List[str] = []

        def dfs(concept_id: str) -> None:
            state = visited.get(concept_id, 0)
            if state == 1:
                if concept_id in lineage:
                    start = lineage.index(concept_id)
                    cycle_path = lineage[start:] + [concept_id]
                    rendered = " -> ".join(cycle_path)
                else:
                    rendered = concept_id
                raise OntologyGraphValidationError(f"Ontology cycle detected: {rendered}")
            if state == 2:
                return
            visited[concept_id] = 1
            lineage.append(concept_id)
            for child_id in self.children.get(concept_id, []):
                dfs(child_id)
            lineage.pop()
            visited[concept_id] = 2

        for concept_id in self.by_id:
            if visited.get(concept_id, 0) == 0:
                dfs(concept_id)

