from __future__ import annotations


class OntologyGraphValidationError(ValueError):
    """Raised when ontology graph structure is invalid."""


class ImmutableConceptViolation(ValueError):
    """Raised when an immutable ontology concept is modified or deleted."""

