"""
TANTRA Curriculum Intelligence Capability.

Reusable capability boundary for curriculum intelligence.
UniGuru consumes this capability; it does not own the implementation.

Execution is delegated to the canonical runtime so there is exactly
one retrieval/intelligence/evidence execution path.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from learning_runtime.canonical_runtime import execute_query


CAPABILITY_ID = "tantra.curriculum_intelligence"
CAPABILITY_VERSION = "1.0.0"
CAPABILITY_SCHEMA = "TANTRA_CURRICULUM_INTELLIGENCE_CAPABILITY_V1"


def execute_curriculum_query(
    query: str,
    student_id: str = "ANONYMOUS",
    grade: Optional[int] = None,
    medium: Optional[str] = None,
    subject: Optional[str] = None,
    exercise_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a curriculum intelligence request through the canonical runtime.

    This function is intentionally an adapter only. It does not perform
    independent retrieval, scoring, evidence generation, or intelligence.
    """

    result = execute_query(
        query=query,
        student_id=student_id,
        grade=grade,
        medium=medium,
        subject=subject,
        exercise_result=exercise_result,
    )

    return {
        "capability": {
            "id": CAPABILITY_ID,
            "version": CAPABILITY_VERSION,
            "schema": CAPABILITY_SCHEMA,
        },
        "result": result,
    }


def capability_metadata() -> Dict[str, Any]:
    """Return deterministic capability metadata for registration/discovery."""

    return {
        "capability_id": CAPABILITY_ID,
        "version": CAPABILITY_VERSION,
        "schema": CAPABILITY_SCHEMA,
        "provider": "TANTRA",
        "domain": "curriculum_intelligence",
        "execution_mode": "deterministic",
        "evidence_required": True,
        "replay_safe": True,
        "canonical_runtime": "learning_runtime.canonical_runtime.execute_query",
        "consumer": "UniGuru",
    }