"""Immutable registry contract supplied by the Sanskar source package."""
from typing import Dict, List
from .schema import SanskritConcept, sanskrit_concept_to_dict


class SanskritRegistry:
    def __init__(self) -> None:
        self._concepts: Dict[str, SanskritConcept] = {}

    def register(self, concept: SanskritConcept) -> None:
        if concept.concept_id in self._concepts:
            raise ValueError(f"Concept already registered: {concept.concept_id}")
        self._concepts[concept.concept_id] = concept

    def get(self, concept_id: str) -> SanskritConcept:
        if concept_id not in self._concepts:
            raise ValueError(f"Unknown Sanskrit concept: {concept_id}")
        return self._concepts[concept_id]

    def exists(self, concept_id: str) -> bool:
        return concept_id in self._concepts

    def remove(self, concept_id: str) -> None:
        raise ValueError("Canonical Sanskrit Concepts are immutable.")

    def update(self, concept: SanskritConcept) -> None:
        raise ValueError("Canonical Sanskrit Concepts are immutable.")

    def list_concepts(self) -> List[SanskritConcept]:
        return [self._concepts[key] for key in sorted(self._concepts)]

    def export_registry(self) -> List[Dict]:
        return [sanskrit_concept_to_dict(concept) for concept in self.list_concepts()]
