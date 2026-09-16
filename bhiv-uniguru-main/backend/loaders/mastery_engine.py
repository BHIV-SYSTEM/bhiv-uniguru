"""
Mastery Intelligence Engine

Implements mastery tracking for curriculum concepts with:
- Concept mastery scoring (confidence + coverage)
- Weak-area detection
- Remediation routing
- Progress state tracking
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from enum import Enum


class MasteryLevel(Enum):
    """Mastery level definitions."""
    NOT_STARTED = 0
    NOVICE = 1
    DEVELOPING = 2
    PROFICIENT = 3
    MASTERY = 4
    EXPERT = 5


class MasteryEngine:
    """
    Tracks and computes student mastery across curriculum concepts.
    """

    def __init__(self, student_id: str, pedagogical_graph_path: str = None):
        self.student_id = student_id
        self.concept_mastery: Dict[str, Dict[str, Any]] = {}
        self.learning_history: List[Dict[str, Any]] = []
        self.mastery_thresholds = {
            "basic_mastery": 0.70,
            "proficiency": 0.80,
            "mastery": 0.90,
            "expert": 0.95
        }
        self.pedagogical_graph = pedagogical_graph_path or {}

    def record_exercise_completion(
        self,
        concept_id: str,
        exercise_id: str,
        correct: bool,
        time_taken_seconds: int,
        difficulty_level: str,
        confidence_self_report: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Record completion of an exercise and update mastery metrics.
        """
        exercise_result = {
            "timestamp": datetime.now().isoformat(),
            "concept_id": concept_id,
            "exercise_id": exercise_id,
            "correct": correct,
            "time_taken_seconds": time_taken_seconds,
            "difficulty_level": difficulty_level,
            "confidence_self_report": confidence_self_report,
            "accuracy": 1.0 if correct else 0.0,
            "efficiency_score": self._calculate_efficiency(difficulty_level, time_taken_seconds)
        }

        self.learning_history.append(exercise_result)
        self._update_concept_mastery(concept_id, exercise_result)

        return exercise_result

    def _calculate_efficiency(self, difficulty_level: str, time_taken: int) -> float:
        """
        Calculate efficiency score based on time taken and difficulty.
        """
        difficulty_time_map = {
            "BASIC": 120,
            "INTERMEDIATE": 240,
            "ADVANCED": 360
        }
        expected_time = difficulty_time_map.get(difficulty_level, 180)
        efficiency = min(expected_time / max(time_taken, 1), 1.0)
        return efficiency

    def _update_concept_mastery(self, concept_id: str, exercise_result: Dict[str, Any]) -> None:
        """
        Update mastery metrics for a concept based on exercise result.
        """
        if concept_id not in self.concept_mastery:
            self.concept_mastery[concept_id] = {
                "concept_id": concept_id,
                "attempts": 0,
                "correct_attempts": 0,
                "incorrect_attempts": 0,
                "total_time_seconds": 0,
                "average_confidence": 0.0,
                "mastery_score": 0.0,
                "mastery_level": "NOT_STARTED",
                "last_attempted": None,
                "first_attempted": None,
                "exercises_completed": []
            }

        mastery = self.concept_mastery[concept_id]
        mastery["attempts"] += 1
        mastery["total_time_seconds"] += exercise_result["time_taken_seconds"]
        mastery["exercises_completed"].append(exercise_result["exercise_id"])

        if exercise_result["correct"]:
            mastery["correct_attempts"] += 1
        else:
            mastery["incorrect_attempts"] += 1

        mastery["last_attempted"] = exercise_result["timestamp"]
        if not mastery["first_attempted"]:
            mastery["first_attempted"] = exercise_result["timestamp"]

        # Update confidence with exponential moving average
        if exercise_result["confidence_self_report"]:
            old_confidence = mastery["average_confidence"]
            new_confidence = exercise_result["confidence_self_report"]
            mastery["average_confidence"] = 0.7 * old_confidence + 0.3 * new_confidence
        else:
            mastery["average_confidence"] = exercise_result["accuracy"] * 0.8 + \
                                          exercise_result.get("efficiency_score", 0.5) * 0.2

        # Calculate mastery score
        mastery["mastery_score"] = self._calculate_mastery_score(mastery)
        mastery["mastery_level"] = self._get_mastery_level(mastery["mastery_score"])

    def _calculate_mastery_score(self, mastery_data: Dict[str, Any]) -> float:
        """
        Calculate overall mastery score from accuracy and confidence.
        Formula: (accuracy * 0.6) + (confidence * 0.4)
        """
        if mastery_data["attempts"] == 0:
            return 0.0

        accuracy = mastery_data["correct_attempts"] / mastery_data["attempts"]
        confidence = mastery_data["average_confidence"]

        mastery_score = (accuracy * 0.6) + (confidence * 0.4)
        return round(mastery_score, 3)

    def _get_mastery_level(self, mastery_score: float) -> str:
        """
        Determine mastery level based on score.
        """
        if mastery_score < 0.5:
            return "NOVICE"
        elif mastery_score < 0.70:
            return "DEVELOPING"
        elif mastery_score < 0.80:
            return "PROFICIENT"
        elif mastery_score < 0.90:
            return "MASTERY"
        else:
            return "EXPERT"

    def detect_weak_areas(self, mastery_threshold: float = 0.70) -> List[Dict[str, Any]]:
        """
        Identify concepts where student mastery is below threshold.
        """
        weak_areas = []
        for concept_id, mastery in self.concept_mastery.items():
            if mastery["mastery_score"] < mastery_threshold:
                weak_areas.append({
                    "concept_id": concept_id,
                    "mastery_score": mastery["mastery_score"],
                    "mastery_level": mastery["mastery_level"],
                    "attempts": mastery["attempts"],
                    "correct_attempts": mastery["correct_attempts"],
                    "accuracy": mastery["correct_attempts"] / max(mastery["attempts"], 1),
                    "confidence": mastery["average_confidence"],
                    "priority": "HIGH" if mastery["mastery_score"] < 0.50 else "MEDIUM"
                })

        return sorted(weak_areas, key=lambda x: x["mastery_score"])

    def recommend_remediation(self, concept_id: str) -> Dict[str, Any]:
        """
        Generate remediation recommendation for a concept.
        """
        mastery = self.concept_mastery.get(concept_id)
        if not mastery:
            return {"status": "CONCEPT_NOT_ATTEMPTED"}

        remediation = {
            "concept_id": concept_id,
            "current_mastery_score": mastery["mastery_score"],
            "current_mastery_level": mastery["mastery_level"],
            "remediation_recommended": mastery["mastery_score"] < 0.80,
            "remediation_urgency": self._calculate_remediation_urgency(mastery),
            "recommended_actions": self._generate_remediation_actions(mastery),
            "estimated_remediation_hours": self._estimate_remediation_time(mastery),
            "success_probability": self._estimate_success_probability(mastery)
        }

        return remediation

    def _calculate_remediation_urgency(self, mastery: Dict[str, Any]) -> str:
        """
        Determine urgency level for remediation.
        """
        score = mastery["mastery_score"]
        if score < 0.40:
            return "CRITICAL"
        elif score < 0.60:
            return "HIGH"
        elif score < 0.80:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_remediation_actions(self, mastery: Dict[str, Any]) -> List[str]:
        """
        Generate specific remediation actions based on mastery patterns.
        """
        actions = []
        accuracy = mastery["correct_attempts"] / max(mastery["attempts"], 1)
        confidence = mastery["average_confidence"]

        if accuracy < 0.60:
            actions.append("Review foundational concepts")
            actions.append("Complete additional practice exercises")

        if confidence < 0.50:
            actions.append("Work with guided examples")
            actions.append("Increase practice with scaffolded support")

        if mastery["attempts"] < 3:
            actions.append("Complete minimum practice attempts")

        return actions

    def _estimate_remediation_time(self, mastery: Dict[str, Any]) -> float:
        """
        Estimate hours needed for remediation.
        """
        score = mastery["mastery_score"]
        if score >= 0.80:
            return 0.0
        elif score >= 0.60:
            return 1.0
        elif score >= 0.40:
            return 2.0
        else:
            return 3.0

    def _estimate_success_probability(self, mastery: Dict[str, Any]) -> float:
        """
        Estimate probability of reaching mastery with remediation.
        """
        accuracy_trend = self._calculate_accuracy_trend()
        current_score = mastery["mastery_score"]
        attempts = mastery["attempts"]

        # Higher probability if already improving, or if few attempts
        if accuracy_trend > 0 or attempts < 3:
            base_probability = 0.85
        else:
            base_probability = 0.70

        # Adjust based on current score
        adjustment = min(1.0 - current_score, 0.15)
        success_probability = base_probability + adjustment

        return round(success_probability, 2)

    def _calculate_accuracy_trend(self) -> float:
        """
        Calculate trend in accuracy over recent attempts.
        """
        if len(self.learning_history) < 2:
            return 0.0

        recent_attempts = self.learning_history[-5:]
        if len(recent_attempts) < 2:
            return 0.0

        early_accuracy = sum(1 for a in recent_attempts[:len(recent_attempts)//2] if a["correct"]) / \
                        max(len(recent_attempts)//2, 1)
        late_accuracy = sum(1 for a in recent_attempts[len(recent_attempts)//2:] if a["correct"]) / \
                       max(len(recent_attempts) - len(recent_attempts)//2, 1)

        trend = late_accuracy - early_accuracy
        return round(trend, 2)

    def get_student_progress_state(self) -> Dict[str, Any]:
        """
        Get complete snapshot of student progress.
        """
        weak_areas = self.detect_weak_areas()
        mastered_concepts = [
            c for c, m in self.concept_mastery.items()
            if m["mastery_score"] >= 0.90
        ]
        developing_concepts = [
            c for c, m in self.concept_mastery.items()
            if 0.70 <= m["mastery_score"] < 0.90
        ]

        return {
            "student_id": self.student_id,
            "snapshot_timestamp": datetime.now().isoformat(),
            "mastery_score": round(sum(m["mastery_score"] for m in self.concept_mastery.values()) / \
                                 max(len(self.concept_mastery), 1), 3),
            "mastery_level": self._get_student_overall_level(),
            "concepts_attempted": len(self.concept_mastery),
            "concepts_mastered": len(mastered_concepts),
            "concepts_developing": len(developing_concepts),
            "concepts_struggling": len(weak_areas),
            "weak_areas": weak_areas,
            "concept_strengths": mastered_concepts,
            "total_exercises_completed": len(self.learning_history),
            "learning_velocity": self._calculate_learning_velocity(),
            "recommended_next_steps": self._generate_next_steps(weak_areas),
            "estimated_time_to_grade_mastery": self._estimate_time_to_mastery()
        }

    def _get_student_overall_level(self) -> str:
        """Get overall mastery level for student."""
        if not self.concept_mastery:
            return "NOT_STARTED"

        avg_score = sum(m["mastery_score"] for m in self.concept_mastery.values()) / \
                   len(self.concept_mastery)
        return self._get_mastery_level(avg_score)

    def _calculate_learning_velocity(self) -> float:
        """Calculate rate of mastery improvement."""
        if len(self.learning_history) < 10:
            return 0.0

        early_accuracy = sum(1 for a in self.learning_history[:5] if a["correct"]) / 5
        late_accuracy = sum(1 for a in self.learning_history[-5:] if a["correct"]) / 5

        velocity = (late_accuracy - early_accuracy) / max(len(self.learning_history) / 100, 1)
        return round(velocity, 3)

    def _generate_next_steps(self, weak_areas: List[Dict[str, Any]]) -> List[str]:
        """Generate recommended next steps for student."""
        next_steps = []

        if len(weak_areas) > 0:
            next_steps.append(f"Focus on remediation for {weak_areas[0]['concept_id']}")

        if self._get_student_overall_level() == "MASTERY":
            next_steps.append("Ready for advanced topics")
        elif self._get_student_overall_level() == "DEVELOPING":
            next_steps.append("Continue current unit, increase practice")

        return next_steps

    def _estimate_time_to_mastery(self) -> Dict[str, Any]:
        """Estimate time until full grade mastery."""
        weak_areas = self.detect_weak_areas(0.90)
        
        if not weak_areas:
            return {"status": "ALREADY_MASTERED", "hours_needed": 0.0}

        total_remediation_hours = sum(
            self._estimate_remediation_time(self.concept_mastery[c["concept_id"]])
            for c in weak_areas
        )

        learning_rate = max(self._calculate_learning_velocity(), 0.1)
        estimated_weeks = total_remediation_hours / (3 * learning_rate)  # Assume 3 hours/week

        return {
            "status": "IN_PROGRESS",
            "hours_needed": round(total_remediation_hours, 1),
            "estimated_weeks": round(estimated_weeks, 1),
            "confidence": round(1.0 - len(weak_areas) / max(len(self.concept_mastery), 1), 2)
        }


def generate_mastery_demo() -> Dict[str, Any]:
    """Generate demo output showing mastery engine in action."""
    student_id = "STUDENT_001"
    engine = MasteryEngine(student_id)

    # Simulate student exercises
    exercises = [
        ("CONCEPT_NUMBER_RECOGNITION", "EX_001", True, 120, "BASIC", 0.8),
        ("CONCEPT_NUMBER_RECOGNITION", "EX_002", True, 110, "BASIC", 0.85),
        ("CONCEPT_COUNTING", "EX_001", True, 150, "BASIC", 0.7),
        ("CONCEPT_COUNTING", "EX_002", False, 180, "BASIC", 0.4),
        ("CONCEPT_COUNTING", "EX_003", True, 140, "BASIC", 0.75),
        ("CONCEPT_PLACE_VALUE", "EX_001", False, 250, "INTERMEDIATE", 0.5),
        ("CONCEPT_PLACE_VALUE", "EX_002", False, 280, "INTERMEDIATE", 0.45),
    ]

    for concept_id, exercise_id, correct, time, difficulty, confidence in exercises:
        engine.record_exercise_completion(
            concept_id=concept_id,
            exercise_id=exercise_id,
            correct=correct,
            time_taken_seconds=time,
            difficulty_level=difficulty,
            confidence_self_report=confidence
        )

    progress_state = engine.get_student_progress_state()

    return {
        "demo_id": "MASTERY_ENGINE_DEMO_001",
        "generated_at": datetime.now().isoformat(),
        "student_progress_state": progress_state,
        "concept_mastery_details": dict(engine.concept_mastery),
        "weak_areas_analysis": engine.detect_weak_areas(),
        "remediation_recommendations": {
            concept_id: engine.recommend_remediation(concept_id)
            for concept_id in engine.concept_mastery.keys()
        }
    }


if __name__ == "__main__":
    demo = generate_mastery_demo()
    print(json.dumps(demo, indent=2, default=str))
