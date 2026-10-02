"""Canonical Sanskrit Concept Schema supplied by the Sanskar source package."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

REQUIRED_SANSKRIT_FIELDS = {"concept_id", "canonical_name", "sanskrit", "transliteration", "shabda", "dhatu", "vyakarana", "nirukta", "beeja", "tattva", "shakti", "functional_meaning", "related_concepts", "ontology_version", "semantic_version"}


@dataclass(frozen=True)
class SanskritConcept:
    concept_id: str; canonical_name: str; sanskrit: str; transliteration: str
    shabda: str; dhatu: str; vyakarana: str; nirukta: str
    beeja: Optional[str]; tattva: Optional[str]; shakti: Optional[str]
    functional_meaning: str; related_concepts: List[str]
    ontology_version: str; semantic_version: str


def validate_sanskrit_concept_dict(data: Dict[str, Any]) -> None:
    if set(data) != REQUIRED_SANSKRIT_FIELDS:
        raise ValueError(f"Sanskrit Concept schema mismatch. Missing={sorted(REQUIRED_SANSKRIT_FIELDS - set(data)) or '[]'} Extra={sorted(set(data) - REQUIRED_SANSKRIT_FIELDS) or '[]'}")
    for field in ("concept_id", "canonical_name", "sanskrit", "transliteration", "shabda", "dhatu", "vyakarana", "nirukta", "functional_meaning", "ontology_version", "semantic_version"):
        if not isinstance(data[field], str) or not data[field].strip():
            raise ValueError(f"{field} must be a non-empty string.")
    for field in ("beeja", "tattva", "shakti"):
        if data[field] is not None and not isinstance(data[field], str):
            raise ValueError(f"{field} must be a string or None.")
    if not isinstance(data["related_concepts"], list) or not all(isinstance(item, str) for item in data["related_concepts"]):
        raise ValueError("related_concepts must be a list of strings.")


def sanskrit_concept_from_dict(data: Dict[str, Any]) -> SanskritConcept:
    validate_sanskrit_concept_dict(data)
    return SanskritConcept(**data)


def sanskrit_concept_to_dict(concept: SanskritConcept) -> Dict[str, Any]:
    return {field: getattr(concept, field) for field in REQUIRED_SANSKRIT_FIELDS}
