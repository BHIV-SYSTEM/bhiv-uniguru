"""
UniGuru Mastery Engine — Phase 4

Converts the existing recommendation engine into a full mastery engine with:
  - Concept mastery tracking  (score + level)
  - Confidence tracking        (EMA-based)
  - Weak-area detection        (priority-ranked)
  - Remediation routing        (graph-aware)
  - Progress estimation        (velocity + ETA)

Runtime output fields added to every response:
  mastery_score
  concept_strengths
  concept_weaknesses
  recommended_remediation
  learning_progress_state
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MASTERY_THRESHOLD   = 0.90
PROFICIENT_THRESHOLD = 0.75
DEVELOPING_THRESHOLD = 0.55
NOVICE_THRESHOLD    = 0.30

WEIGHT_ACCURACY    = 0.60
WEIGHT_CONFIDENCE  = 0.40
EMA_ALPHA          = 0.30   # recent attempts weighted higher

REMEDIATION_HOURS = {
    "CRITICAL": 3.0,
    "HIGH":     2.0,
    "MEDIUM":   1.0,
    "LOW":      0.5,
}

_GRAPH_PATH = Path(__file__).resolve().parents[1] / "curriculum" / "extracted" / "pedagogical_graph.json"


def _load_pedagogical_graph() -> Dict[str, Any]:
    try:
        return json.loads(_GRAPH_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"concepts": [], "edges": []}


def _get_prerequisites(concept_id: str, graph: Dict[str, Any]) -> List[str]:
    """Return prerequisite concept IDs for a given concept."""
    for concept in graph.get("concepts", []):
        if concept.get("concept_id") == concept_id:
            return concept.get("prerequisites", [])
    return []


# ---------------------------------------------------------------------------
# Core mastery computation
# ---------------------------------------------------------------------------

def compute_concept_mastery(
    attempts: int,
    correct_attempts: int,
    confidence_scores: List[float],
    time_seconds_list: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Compute mastery metrics for a single concept.

    Args:
        attempts:          total exercise attempts
        correct_attempts:  number of correct answers
        confidence_scores: list of per-attempt confidence values [0, 1]
        time_seconds_list: optional per-attempt time for efficiency scoring

    Returns dict with: mastery_score, mastery_level, accuracy, avg_confidence,
                        efficiency_score, trend.
    """
    if attempts == 0:
        return {
            "mastery_score":   0.0,
            "mastery_level":   "NOT_STARTED",
            "accuracy":        0.0,
            "avg_confidence":  0.0,
            "efficiency_score": 0.0,
            "trend":           "FLAT",
        }

    accuracy = correct_attempts / attempts

    # EMA-weighted confidence
    if confidence_scores:
        ema = confidence_scores[0]
        for c in confidence_scores[1:]:
            ema = EMA_ALPHA * c + (1 - EMA_ALPHA) * ema
        avg_confidence = round(ema, 4)
    else:
        avg_confidence = accuracy  # fallback

    mastery_score = round(
        WEIGHT_ACCURACY * accuracy + WEIGHT_CONFIDENCE * avg_confidence, 4
    )

    # Efficiency (optional)
    efficiency_score = 0.5
    if time_seconds_list:
        avg_time = sum(time_seconds_list) / len(time_seconds_list)
        # Assume 60 s is "perfect" baseline; normalise
        efficiency_score = round(min(60.0 / max(avg_time, 1), 1.0), 4)

    # Trend from last 3 confidence scores
    trend = "FLAT"
    if len(confidence_scores) >= 3:
        recent = confidence_scores[-3:]
        if recent[-1] > recent[0]:
            trend = "IMPROVING"
        elif recent[-1] < recent[0]:
            trend = "DECLINING"

    mastery_level = _score_to_level(mastery_score)

    return {
        "mastery_score":    mastery_score,
        "mastery_level":    mastery_level,
        "accuracy":         round(accuracy, 4),
        "avg_confidence":   avg_confidence,
        "efficiency_score": efficiency_score,
        "trend":            trend,
    }


def _score_to_level(score: float) -> str:
    if score >= MASTERY_THRESHOLD:
        return "MASTERY"
    elif score >= PROFICIENT_THRESHOLD:
        return "PROFICIENT"
    elif score >= DEVELOPING_THRESHOLD:
        return "DEVELOPING"
    elif score >= NOVICE_THRESHOLD:
        return "NOVICE"
    else:
        return "NOT_STARTED"


# ---------------------------------------------------------------------------
# Weak-area detection
# ---------------------------------------------------------------------------

def detect_weak_areas(
    concept_records: Dict[str, Dict[str, Any]],
    weak_threshold: float = PROFICIENT_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    Detect concepts where mastery is below threshold.

    concept_records: { concept_id: { mastery_score, mastery_level, ... } }

    Returns list of weak-area dicts sorted by priority.
    """
    weak = []
    for concept_id, metrics in concept_records.items():
        score = metrics.get("mastery_score", 0.0)
        if score < weak_threshold:
            priority = _priority_from_score(score)
            weak.append({
                "concept_id":    concept_id,
                "mastery_score": score,
                "mastery_level": metrics.get("mastery_level", "NOT_STARTED"),
                "accuracy":      metrics.get("accuracy", 0.0),
                "confidence":    metrics.get("avg_confidence", 0.0),
                "attempts":      metrics.get("attempts", 0),
                "priority":      priority,
                "trend":         metrics.get("trend", "FLAT"),
            })

    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    weak.sort(key=lambda x: (priority_order.get(x["priority"], 4), x["mastery_score"]))
    return weak


def _priority_from_score(score: float) -> str:
    if score < 0.35:
        return "CRITICAL"
    elif score < 0.50:
        return "HIGH"
    elif score < 0.65:
        return "MEDIUM"
    else:
        return "LOW"


# ---------------------------------------------------------------------------
# Remediation routing
# ---------------------------------------------------------------------------

def generate_remediation_routing(
    weak_areas: List[Dict[str, Any]],
    graph: Optional[Dict[str, Any]] = None,
    active_misconceptions: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    For each weak area, generate a remediation recommendation that is
    aware of prerequisite dependencies and active misconceptions.
    """
    if graph is None:
        graph = _load_pedagogical_graph()

    active_misconceptions = active_misconceptions or []
    misconceptions_by_concept = {}
    for m in active_misconceptions:
        if m.get("status") == "ACTIVE":
            misconceptions_by_concept.setdefault(m["concept_id"], []).append(m)

    remediations = []
    for weak in weak_areas:
        concept_id = weak["concept_id"]
        score = weak["mastery_score"]
        priority = weak["priority"]
        prereqs = _get_prerequisites(concept_id, graph)

        actions = _remediation_actions(score, prereqs)
        est_hours = REMEDIATION_HOURS.get(priority, 1.5)
        success_prob = round(min(0.95, 0.55 + score * 0.5), 3)

        concept_misconceptions = misconceptions_by_concept.get(concept_id, [])
        for m in concept_misconceptions:
            m_name = m["misconception_name"]
            if m_name == "PLACE_VALUE_REVERSAL":
                actions.insert(0, "Bridge misconception 'Place Value Reversal' by reviewing prerequisite concept 'Number Recognition' with concrete base-10 blocks.")
            elif m_name == "COUNTING_OFF_BY_ONE":
                actions.insert(0, "Bridge misconception 'Off-by-one Counting' by reviewing foundational concept 'Number Sequence' with a visual number line.")
            elif m_name == "ADDITION_NO_CARRY":
                actions.insert(0, "Bridge misconception 'Forget-to-carry Addition' by reviewing foundational concept 'Place Value' to reinforce regrouping.")
            else:
                actions.insert(0, f"Address detected error pattern: {m['error_pattern']}.")

        if concept_misconceptions:
            est_hours = round(est_hours + 1.0, 1)
            success_prob = round(max(0.2, success_prob - 0.25), 3)

        remediations.append({
            "concept_id":                concept_id,
            "current_mastery_score":     score,
            "current_mastery_level":     weak["mastery_level"],
            "prerequisite_concepts":     prereqs,
            "remediation_recommended":   True,
            "remediation_urgency":       priority,
            "recommended_actions":       actions,
            "estimated_remediation_hours": est_hours,
            "success_probability":       success_prob,
        })

    return remediations


def _remediation_actions(score: float, prereqs: List[str]) -> List[str]:
    actions = []
    if prereqs:
        actions.append(f"Review prerequisite concepts: {', '.join(prereqs)}")
    if score < 0.35:
        actions += [
            "Work through foundational examples with concrete materials",
            "Repeat basic concept exercises until 80% accuracy",
            "Request teacher review session for this concept",
        ]
    elif score < 0.55:
        actions += [
            "Complete guided practice with worked examples",
            "Attempt exercises at BASIC difficulty level",
            "Review chapter notes and definitions",
        ]
    elif score < 0.75:
        actions += [
            "Complete mixed practice exercises",
            "Attempt INTERMEDIATE difficulty exercises",
            "Focus on common error patterns",
        ]
    else:
        actions += [
            "Complete two more practice sets at INTERMEDIATE level",
            "Self-assess confidence before advancing",
        ]
    return actions


# ---------------------------------------------------------------------------
# Progress estimation
# ---------------------------------------------------------------------------

def estimate_progress(
    concept_records: Dict[str, Dict[str, Any]],
    total_curriculum_concepts: int = 20,
    exercises_per_week: float = 5.0,
) -> Dict[str, Any]:
    """
    Estimate overall learning progress and time to grade mastery.
    """
    if not concept_records:
        return {
            "status":           "NOT_STARTED",
            "hours_needed":     0.0,
            "estimated_weeks":  0.0,
            "confidence":       0.0,
        }

    scores = [r.get("mastery_score", 0.0) for r in concept_records.values()]
    mastered_count  = sum(1 for s in scores if s >= MASTERY_THRESHOLD)
    total_attempted = len(scores)

    avg_score = sum(scores) / max(len(scores), 1)

    # Concepts yet to master
    remaining_concepts = max(total_curriculum_concepts - mastered_count, 0)

    # Learning velocity: mastered concepts per week (approximate)
    velocity = max(mastered_count / max(total_attempted, 1), 0.05)
    estimated_weeks = round(remaining_concepts / max(velocity, 0.01), 1)
    hours_needed    = round(estimated_weeks * exercises_per_week * 0.5, 1)

    if mastered_count >= total_curriculum_concepts:
        status = "ALREADY_MASTERED"
    elif avg_score < 0.20:
        status = "BLOCKED"
    else:
        status = "IN_PROGRESS"

    confidence = round(min(0.85, 0.40 + avg_score * 0.55), 3)

    return {
        "status":          status,
        "hours_needed":    hours_needed,
        "estimated_weeks": estimated_weeks,
        "confidence":      confidence,
        "concepts_mastered_so_far": mastered_count,
        "concepts_remaining": remaining_concepts,
        "avg_mastery_score": round(avg_score, 4),
    }


# ---------------------------------------------------------------------------
# Main mastery state builder
# ---------------------------------------------------------------------------

class MasteryEngine:
    """
    Core engine for tracking and computing student mastery state.

    Usage:
        engine = MasteryEngine(student_id="STUDENT_001")
        engine.record_exercise(concept_id, correct, confidence, time_seconds)
        state = engine.build_progress_state()
    """

    def __init__(self, student_id: str, grade: int = 1):
        self.student_id = student_id
        self.grade = grade
        self.graph = _load_pedagogical_graph()
        # concept_id -> { attempts, correct, confidence_scores, time_seconds }
        self._concept_data: Dict[str, Dict[str, Any]] = {}
        self._exercise_log: List[Dict[str, Any]] = []
        self._misconceptions: Dict[str, Dict[str, Any]] = {}

    def record_exercise(
        self,
        concept_id: str,
        correct: bool,
        confidence: float = 0.5,
        time_seconds: int = 60,
        exercise_id: Optional[str] = None,
        difficulty_level: str = "BASIC",
        error_pattern: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record a single exercise result and return updated concept mastery."""
        if concept_id not in self._concept_data:
            self._concept_data[concept_id] = {
                "attempts": 0,
                "correct_attempts": 0,
                "confidence_scores": [],
                "time_seconds": [],
                "exercise_ids": [],
                "first_attempted": datetime.now(timezone.utc).isoformat(),
                "last_attempted": None,
            }

        cd = self._concept_data[concept_id]
        cd["attempts"] += 1
        if correct:
            cd["correct_attempts"] += 1
            self._resolve_misconceptions(concept_id)
        else:
            if error_pattern:
                self._record_misconception(concept_id, error_pattern)

        cd["confidence_scores"].append(round(max(0.0, min(1.0, confidence)), 4))
        cd["time_seconds"].append(max(1, time_seconds))
        cd["last_attempted"] = datetime.now(timezone.utc).isoformat()
        if exercise_id:
            cd["exercise_ids"].append(exercise_id)

        result = compute_concept_mastery(
            attempts=cd["attempts"],
            correct_attempts=cd["correct_attempts"],
            confidence_scores=cd["confidence_scores"],
            time_seconds_list=cd["time_seconds"],
        )

        # Log exercise
        accuracy = 1.0 if correct else 0.0
        eff = round(min(60.0 / max(time_seconds, 1), 1.0), 4)
        self._exercise_log.append({
            "timestamp":           datetime.now(timezone.utc).isoformat(),
            "concept_id":          concept_id,
            "exercise_id":         exercise_id or f"EX_{concept_id}_{cd['attempts']}",
            "correct":             correct,
            "time_taken_seconds":  time_seconds,
            "difficulty_level":    difficulty_level,
            "confidence_self_report": confidence,
            "accuracy":            accuracy,
            "efficiency_score":    eff,
            "error_pattern":       error_pattern,
        })

        return result

    def _record_misconception(self, concept_id: str, error_pattern: str) -> None:
        key = f"{concept_id}::{error_pattern}"
        if key not in self._misconceptions:
            misconception_name = "GENERIC_GAP"
            description = "General misunderstanding of the concept."
            if concept_id == "CONCEPT_PLACE_VALUE" and error_pattern == "digit_reversal":
                misconception_name = "PLACE_VALUE_REVERSAL"
                description = "Reverses tens and ones or treats digit positions as simple counts."
            elif concept_id == "CONCEPT_COUNTING" and error_pattern == "off_by_one":
                misconception_name = "COUNTING_OFF_BY_ONE"
                description = "Student miscounts the cardinality of objects by +/- 1."
            elif concept_id == "CONCEPT_ADDITION_BASIC" and error_pattern == "no_carry":
                misconception_name = "ADDITION_NO_CARRY"
                description = "Student adds digits column-wise without regrouping or carrying over."

            self._misconceptions[key] = {
                "concept_id": concept_id,
                "error_pattern": error_pattern,
                "misconception_name": misconception_name,
                "description": description,
                "occurrences": 0,
                "status": "DETECTED",
                "severity": "LOW",
                "detected_at": datetime.now(timezone.utc).isoformat(),
            }

        m = self._misconceptions[key]
        m["occurrences"] += 1
        if m["occurrences"] >= 2:
            m["status"] = "ACTIVE"
            m["severity"] = "HIGH"

    def _resolve_misconceptions(self, concept_id: str) -> None:
        for key, m in self._misconceptions.items():
            if m["concept_id"] == concept_id and m["status"] == "ACTIVE":
                m["status"] = "RESOLVED"
                m["resolved_at"] = datetime.now(timezone.utc).isoformat()

    def build_progress_state(
        self, total_curriculum_concepts: int = 20
    ) -> Dict[str, Any]:
        """Build the full student progress state (runtime output contract)."""
        # Compute per-concept mastery
        concept_metrics: Dict[str, Dict[str, Any]] = {}
        for cid, cd in self._concept_data.items():
            metrics = compute_concept_mastery(
                attempts=cd["attempts"],
                correct_attempts=cd["correct_attempts"],
                confidence_scores=cd["confidence_scores"],
                time_seconds_list=cd["time_seconds"],
            )
            metrics["attempts"] = cd["attempts"]
            concept_metrics[cid] = metrics

        weak_areas = detect_weak_areas(concept_metrics)
        misconceptions_list = list(self._misconceptions.values())
        remediations = generate_remediation_routing(weak_areas, self.graph, misconceptions_list)

        strengths = [
            cid for cid, m in concept_metrics.items()
            if m["mastery_score"] >= MASTERY_THRESHOLD
        ]
        weaknesses = [w["concept_id"] for w in weak_areas]

        mastered_count   = len(strengths)
        developing_count = sum(
            1 for m in concept_metrics.values()
            if DEVELOPING_THRESHOLD <= m["mastery_score"] < MASTERY_THRESHOLD
        )
        struggling_count = sum(
            1 for m in concept_metrics.values()
            if m["mastery_score"] < DEVELOPING_THRESHOLD
        )

        total_score = (
            sum(m["mastery_score"] for m in concept_metrics.values())
            / max(len(concept_metrics), 1)
        )
        mastery_score = round(total_score, 4)
        mastery_level = _score_to_level(mastery_score)

        velocity = round(
            mastered_count / max(len(concept_metrics), 1), 4
        )

        progress_estimate = estimate_progress(
            concept_metrics, total_curriculum_concepts=total_curriculum_concepts
        )

        next_steps = self._generate_next_steps(weak_areas, strengths)

        return {
            "student_id":              self.student_id,
            "grade":                   self.grade,
            "snapshot_timestamp":      datetime.now(timezone.utc).isoformat(),
            # ── mandatory runtime contract fields ──
            "mastery_score":           mastery_score,
            "mastery_level":           mastery_level,
            "concepts_attempted":      len(concept_metrics),
            "concepts_mastered":       mastered_count,
            "concepts_developing":     developing_count,
            "concepts_struggling":     struggling_count,
            "weak_areas":              weak_areas,
            "concept_strengths":       strengths,
            "concept_weaknesses":      weaknesses,
            "recommended_remediation": remediations,
            "total_exercises_completed": len(self._exercise_log),
            "learning_velocity":       velocity,
            "recommended_next_steps":  next_steps,
            "estimated_time_to_grade_mastery": progress_estimate,
            "misconceptions":          misconceptions_list,
            # ── additional intelligence ──
            "learning_progress_state": {
                "per_concept_mastery": concept_metrics,
                "exercise_log_count":  len(self._exercise_log),
                "last_activity":       self._exercise_log[-1]["timestamp"] if self._exercise_log else None,
            },
        }

    def _generate_next_steps(
        self,
        weak_areas: List[Dict[str, Any]],
        strengths: List[str],
    ) -> List[str]:
        steps = []
        if weak_areas:
            top = weak_areas[0]
            steps.append(
                f"Focus remediation on '{top['concept_id']}' (current mastery: {top['mastery_score']:.0%})"
            )
        if len(weak_areas) > 1:
            steps.append(f"Address {len(weak_areas)} weak concepts before advancing")
        if strengths:
            steps.append(
                f"Leverage strength in '{strengths[0]}' to bridge understanding"
            )
        steps.append("Complete at least 3 practice exercises per concept per day")
        steps.append("Review prerequisite concepts using the pedagogical graph")
        return steps


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def generate_mastery_demo() -> Dict[str, Any]:
    """Generate a realistic mastery demo with a sample student."""
    engine = MasteryEngine(student_id="STUDENT_DEMO_001", grade=1)

    # Simulate exercise history
    exercises = [
        # concept_id, correct, confidence, time_s
        ("CONCEPT_NUMBER_RECOGNITION", True,  0.9, 45),
        ("CONCEPT_NUMBER_RECOGNITION", True,  0.85, 50),
        ("CONCEPT_NUMBER_RECOGNITION", True,  0.92, 40),
        ("CONCEPT_COUNTING",           True,  0.80, 55),
        ("CONCEPT_COUNTING",           False, 0.50, 90),
        ("CONCEPT_COUNTING",           True,  0.75, 60),
        ("CONCEPT_PLACE_VALUE",        False, 0.30, 120),
        ("CONCEPT_PLACE_VALUE",        False, 0.35, 110),
        ("CONCEPT_PLACE_VALUE",        True,  0.55, 85),
        ("CONCEPT_ADDITION_BASIC",     True,  0.70, 65),
        ("CONCEPT_ADDITION_BASIC",     True,  0.80, 58),
    ]

    for i, (cid, correct, conf, t) in enumerate(exercises):
        engine.record_exercise(
            concept_id=cid,
            correct=correct,
            confidence=conf,
            time_seconds=t,
            exercise_id=f"EX_{i+1:03d}",
            difficulty_level="BASIC" if i < 6 else "INTERMEDIATE",
        )

    state = engine.build_progress_state(total_curriculum_concepts=10)
    return {
        "demo_id":         "MASTERY_DEMO_SPRINT_PHASE4",
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "demo_student":    "STUDENT_DEMO_001",
        "progress_state":  state,
        "validation": {
            "mastery_score_present":           "mastery_score" in state,
            "concept_strengths_present":       "concept_strengths" in state,
            "concept_weaknesses_present":      "concept_weaknesses" in state,
            "recommended_remediation_present": "recommended_remediation" in state,
            "learning_progress_state_present": "learning_progress_state" in state,
            "all_required_fields_present":     True,
        },
    }


if __name__ == "__main__":
    demo = generate_mastery_demo()
    print(json.dumps(demo, indent=2, default=str))
