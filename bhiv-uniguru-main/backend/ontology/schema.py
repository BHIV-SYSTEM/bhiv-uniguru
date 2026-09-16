from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class Domain(str, Enum):
    QUANTUM = "quantum"
    JAIN = "jain"
    SWAMINARAYAN = "swaminarayan"
    GURUKUL = "gurukul"
    CORE = "core"


TRUTH_LEVELS: Dict[int, str] = {
    0: "Unknown",
    1: "Partially Verified",
    2: "Verified Secondary",
    3: "Canonical Verified",
    4: "Foundational Immutable",
}

REQUIRED_CONCEPT_FIELDS = {
    "concept_id",
    "canonical_name",
    "parent_id",
    "truth_level",
    "domain",
    "source_reference",
    "snapshot_version",
    "created_at",
    "immutable",
}


@dataclass(frozen=True)
class Concept:
    concept_id: str
    canonical_name: str
    parent_id: Optional[str]
    truth_level: int
    domain: Domain
    source_reference: str
    snapshot_version: int
    created_at: str
    immutable: bool


def _validate_timestamp(value: str) -> None:
    candidate = value.replace("Z", "+00:00")
    datetime.fromisoformat(candidate)


def _validate_uuid(value: Optional[str], field_name: str) -> None:
    if value is None:
        return
    try:
        UUID(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a UUID: {value}") from exc


def validate_concept_dict(data: Dict[str, Any]) -> None:
    keys = set(data.keys())
    if keys != REQUIRED_CONCEPT_FIELDS:
        missing = sorted(REQUIRED_CONCEPT_FIELDS - keys)
        extra = sorted(keys - REQUIRED_CONCEPT_FIELDS)
        raise ValueError(
            f"Concept schema mismatch. Missing={missing or '[]'} Extra={extra or '[]'}"
        )

    _validate_uuid(data["concept_id"], "concept_id")
    _validate_uuid(data["parent_id"], "parent_id")

    truth_level = data["truth_level"]
    if not isinstance(truth_level, int) or truth_level not in TRUTH_LEVELS:
        raise ValueError("truth_level must be an integer in [0, 1, 2, 3, 4].")

    if not isinstance(data["canonical_name"], str) or not data["canonical_name"].strip():
        raise ValueError("canonical_name must be a non-empty string.")

    if not isinstance(data["source_reference"], str) or not data["source_reference"].strip():
        raise ValueError("source_reference must be a non-empty string.")

    if not isinstance(data["snapshot_version"], int) or data["snapshot_version"] < 1:
        raise ValueError("snapshot_version must be a positive integer.")

    if not isinstance(data["immutable"], bool):
        raise ValueError("immutable must be a boolean.")

    _validate_timestamp(data["created_at"])

    try:
        Domain(data["domain"])
    except ValueError as exc:
        valid = ", ".join(member.value for member in Domain)
        raise ValueError(f"domain must be one of: {valid}") from exc


def concept_from_dict(data: Dict[str, Any]) -> Concept:
    validate_concept_dict(data)
    return Concept(
        concept_id=data["concept_id"],
        canonical_name=data["canonical_name"],
        parent_id=data["parent_id"],
        truth_level=data["truth_level"],
        domain=Domain(data["domain"]),
        source_reference=data["source_reference"],
        snapshot_version=data["snapshot_version"],
        created_at=data["created_at"],
        immutable=data["immutable"],
    )


def concept_to_dict(concept: Concept) -> Dict[str, Any]:
    return {
        "concept_id": concept.concept_id,
        "canonical_name": concept.canonical_name,
        "parent_id": concept.parent_id,
        "truth_level": concept.truth_level,
        "domain": concept.domain.value,
        "source_reference": concept.source_reference,
        "snapshot_version": concept.snapshot_version,
        "created_at": concept.created_at,
        "immutable": concept.immutable,
    }
