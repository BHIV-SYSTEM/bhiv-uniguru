"""Deterministic ontology backbone for UniGuru."""

from ontology.exceptions import ImmutableConceptViolation, OntologyGraphValidationError
from ontology.graph import OntologyGraph, get_frozen_concepts
from ontology.registry import OntologyRegistry
from ontology.snapshot_manager import SnapshotManager

__all__ = [
    "ImmutableConceptViolation",
    "OntologyGraphValidationError",
    "OntologyGraph",
    "OntologyRegistry",
    "SnapshotManager",
    "get_frozen_concepts",
]
