"""
UniGuru Adaptive Educational Loop and Misconception Test Suite
Validates the full student learning loop:
  Student Misconception -> Detection -> Targeted Prerequisite Remediation -> Recovery -> Resolution & Mastery Increase
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from learning_runtime.mastery_engine import MasteryEngine


def test_student_misconception_adaptation_loop():
    # 1. Initialize MasteryEngine for a student
    engine = MasteryEngine(student_id="STUDENT_LOOP_TEST_001", grade=1)

    # Initially, no misconceptions are present
    state = engine.build_progress_state()
    assert len(state.get("misconceptions", [])) == 0

    # 2. Simulate student answering a PLACE_VALUE question incorrectly with a digit_reversal error pattern
    engine.record_exercise(
        concept_id="CONCEPT_PLACE_VALUE",
        correct=False,
        confidence=0.40,
        time_seconds=110,
        exercise_id="EX_PV_001",
        difficulty_level="BASIC",
        error_pattern="digit_reversal",
    )

    # First attempt: misconception is DETECTED (low severity), not yet ACTIVE
    state = engine.build_progress_state()
    misconceptions = state.get("misconceptions", [])
    assert len(misconceptions) == 1
    assert misconceptions[0]["status"] == "DETECTED"
    assert misconceptions[0]["severity"] == "LOW"

    # 3. Student answers incorrectly a second time with the same error pattern
    engine.record_exercise(
        concept_id="CONCEPT_PLACE_VALUE",
        correct=False,
        confidence=0.30,
        time_seconds=120,
        exercise_id="EX_PV_002",
        difficulty_level="BASIC",
        error_pattern="digit_reversal",
    )

    # Second attempt: misconception becomes ACTIVE (high severity)
    state = engine.build_progress_state()
    misconceptions = state.get("misconceptions", [])
    assert len(misconceptions) == 1
    assert misconceptions[0]["status"] == "ACTIVE"
    assert misconceptions[0]["severity"] == "HIGH"
    assert misconceptions[0]["misconception_name"] == "PLACE_VALUE_REVERSAL"

    # 4. Verify that remediation recommendations are adapted dynamically
    remediations = state.get("recommended_remediation", [])
    assert len(remediations) == 1
    rem = remediations[0]
    
    # Custom action must be prepended
    actions = rem.get("recommended_actions", [])
    assert any("Place Value Reversal" in action for action in actions)
    assert actions[0].startswith("Bridge misconception 'Place Value Reversal'")

    # Success probability must be lower and estimated hours higher due to misconception severity
    assert rem.get("estimated_remediation_hours") >= 2.5
    assert rem.get("success_probability") <= 0.50

    # 5. Simulate student recovering: reviews foundations, then gets a question correct
    engine.record_exercise(
        concept_id="CONCEPT_PLACE_VALUE",
        correct=True,
        confidence=0.85,
        time_seconds=50,
        exercise_id="EX_PV_003",
        difficulty_level="BASIC",
    )

    # Verify resolution
    state = engine.build_progress_state()
    misconceptions = state.get("misconceptions", [])
    assert len(misconceptions) == 1
    assert misconceptions[0]["status"] == "RESOLVED"
    assert "resolved_at" in misconceptions[0]

    # Verify that remediation actions revert to normal, estimated hours decrease, and success probability increases
    remediations = state.get("recommended_remediation", [])
    assert len(remediations) == 1
    rem = remediations[0]
    actions = rem.get("recommended_actions", [])
    # Reverted: no misconception actions should be active
    assert not any("Place Value Reversal" in action for action in actions)
    assert rem.get("success_probability") > 0.60
    assert rem.get("estimated_remediation_hours") < 2.5
    assert state.get("mastery_score") > 0.40
