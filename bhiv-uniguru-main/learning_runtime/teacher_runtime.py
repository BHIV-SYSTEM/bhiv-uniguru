"""
Teacher Runtime Intelligence

Provides teacher-facing intelligence layer with:
- Class View (aggregate student metrics)
- Student Progress View (per-student mastery)
- Curriculum Completion View (unit/chapter status)
- Remediation View (intervention recommendations)
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict


class TeacherRuntime:
    """
    Provides aggregated intelligence for teachers across their classroom.
    """

    def __init__(self, teacher_id: str, class_id: str, grade: int):
        self.teacher_id = teacher_id
        self.class_id = class_id
        self.grade = grade
        self.students: Dict[str, Dict[str, Any]] = {}
        self.class_mastery_data: Dict[str, Any] = {}
        self.curriculum_progress: Dict[str, Any] = {}

    def add_student_progress(
        self,
        student_id: str,
        student_name: str,
        progress_state: Dict[str, Any]
    ) -> None:
        """Add or update student progress data."""
        self.students[student_id] = {
            "student_id": student_id,
            "student_name": student_name,
            "progress_state": progress_state,
            "timestamp": datetime.now().isoformat()
        }

    def generate_class_view(self) -> Dict[str, Any]:
        """
        Generate aggregate class-level view with overall metrics.
        """
        if not self.students:
            return {"status": "NO_DATA"}

        student_count = len(self.students)
        mastery_scores = [
            s["progress_state"]["mastery_score"]
            for s in self.students.values()
            if "mastery_score" in s["progress_state"]
        ]
        
        avg_mastery = sum(mastery_scores) / len(mastery_scores) if mastery_scores else 0

        class_view = {
            "view_id": "CLASS_VIEW_001",
            "view_type": "AGGREGATE_CLASS_METRICS",
            "generated_at": datetime.now().isoformat(),
            "class_info": {
                "class_id": self.class_id,
                "teacher_id": self.teacher_id,
                "grade": self.grade,
                "total_students": student_count
            },
            "class_metrics": {
                "average_mastery_score": round(avg_mastery, 3),
                "students_mastered": sum(
                    1 for s in self.students.values()
                    if s["progress_state"]["mastery_level"] in ["MASTERY", "EXPERT"]
                ),
                "students_developing": sum(
                    1 for s in self.students.values()
                    if s["progress_state"]["mastery_level"] in ["DEVELOPING", "PROFICIENT"]
                ),
                "students_struggling": sum(
                    1 for s in self.students.values()
                    if s["progress_state"]["mastery_level"] in ["NOVICE"]
                ),
                "total_exercises_completed": sum(
                    s["progress_state"].get("total_exercises_completed", 0)
                    for s in self.students.values()
                ),
                "average_learning_velocity": round(
                    sum(
                        s["progress_state"].get("learning_velocity", 0)
                        for s in self.students.values()
                    ) / student_count, 4
                )
            },
            "performance_distribution": {
                "mastered_percentage": round(
                    (sum(1 for s in self.students.values()
                         if s["progress_state"]["mastery_level"] in ["MASTERY", "EXPERT"]) / student_count) * 100, 1
                ),
                "developing_percentage": round(
                    (sum(1 for s in self.students.values()
                         if s["progress_state"]["mastery_level"] in ["DEVELOPING", "PROFICIENT"]) / student_count) * 100, 1
                ),
                "struggling_percentage": round(
                    (sum(1 for s in self.students.values()
                         if s["progress_state"]["mastery_level"] in ["NOVICE"]) / student_count) * 100, 1
                )
            },
            "interventions_needed": sum(
                len(s["progress_state"].get("weak_areas", []))
                for s in self.students.values()
            )
        }

        return class_view

    def generate_student_progress_view(self) -> List[Dict[str, Any]]:
        """
        Generate per-student progress view for teacher overview.
        """
        student_views = []

        for student_id, student_data in self.students.items():
            progress = student_data["progress_state"]
            
            student_view = {
                "student_id": student_id,
                "student_name": student_data["student_name"],
                "mastery_level": progress.get("mastery_level"),
                "mastery_score": progress.get("mastery_score"),
                "concepts_attempted": progress.get("concepts_attempted", 0),
                "concepts_mastered": progress.get("concepts_mastered", 0),
                "weak_areas_count": len(progress.get("weak_areas", [])),
                "learning_velocity": progress.get("learning_velocity", 0),
                "exercises_completed": progress.get("total_exercises_completed", 0),
                "intervention_needed": len(progress.get("weak_areas", [])) > 0,
                "top_weak_area": progress.get("weak_areas", [{}])[0].get("concept_id") if progress.get("weak_areas") else None,
                "estimated_time_to_mastery_weeks": progress.get("estimated_time_to_grade_mastery", {}).get("estimated_weeks", 0)
            }

            student_views.append(student_view)

        return sorted(student_views, key=lambda x: x["mastery_score"], reverse=True)

    def generate_curriculum_completion_view(self) -> Dict[str, Any]:
        """
        Generate curriculum unit/chapter completion status.
        """
        # Aggregate by concepts across all students
        concept_mastery_aggregates = defaultdict(lambda: {
            "students_mastered": 0,
            "students_developing": 0,
            "students_struggling": 0,
            "average_mastery": 0.0,
            "total_scores": 0,
            "student_count_attempted": 0
        })

        for student_data in self.students.values():
            progress = student_data["progress_state"]
            for weak_area in progress.get("weak_areas", []):
                concept_id = weak_area["concept_id"]
                concept_mastery_aggregates[concept_id]["students_struggling"] += 1
                concept_mastery_aggregates[concept_id]["total_scores"] += weak_area["mastery_score"]
                concept_mastery_aggregates[concept_id]["student_count_attempted"] += 1

            for strength in progress.get("concept_strengths", []):
                concept_mastery_aggregates[strength]["students_mastered"] += 1
                concept_mastery_aggregates[strength]["student_count_attempted"] += 1

        # Calculate averages
        for concept_id, agg in concept_mastery_aggregates.items():
            if agg["student_count_attempted"] > 0:
                agg["average_mastery"] = round(
                    agg["total_scores"] / agg["student_count_attempted"], 3
                )

        curriculum_view = {
            "view_id": "CURRICULUM_VIEW_001",
            "view_type": "CURRICULUM_COMPLETION_STATUS",
            "generated_at": datetime.now().isoformat(),
            "chapter": "Counting from 1 to 10",
            "chapter_id": "BALBHARTI_MATH_G1_MM_CH01",
            "concepts_in_chapter": [
                {
                    "concept_id": concept_id,
                    "average_mastery": agg["average_mastery"],
                    "students_mastered": agg["students_mastered"],
                    "students_developing": agg["students_developing"],
                    "students_struggling": agg["students_struggling"],
                    "completion_percentage": round(
                        (agg["students_mastered"] / max(len(self.students), 1)) * 100, 1
                    )
                }
                for concept_id, agg in concept_mastery_aggregates.items()
            ],
            "overall_chapter_completion": round(
                (sum(1 for agg in concept_mastery_aggregates.values() if agg["average_mastery"] >= 0.80) /
                 max(len(concept_mastery_aggregates), 1)) * 100, 1
            )
        }

        return curriculum_view

    def generate_remediation_view(self) -> Dict[str, Any]:
        """
        Generate interventions and remediation recommendations view.
        """
        remediation_items = []

        for student_id, student_data in self.students.items():
            progress = student_data["progress_state"]
            
            for weak_area in progress.get("weak_areas", []):
                remediation_items.append({
                    "remediation_id": f"{student_id}_{weak_area['concept_id']}",
                    "student_id": student_id,
                    "student_name": student_data["student_name"],
                    "concept_id": weak_area["concept_id"],
                    "current_mastery": weak_area["mastery_score"],
                    "priority": weak_area.get("priority", "MEDIUM"),
                    "attempts": weak_area.get("attempts", 0),
                    "accuracy": weak_area.get("accuracy", 0),
                    "confidence": weak_area.get("confidence", 0),
                    "recommended_action": self._get_remediation_action(weak_area),
                    "estimated_intervention_hours": self._estimate_intervention_hours(weak_area)
                })

        # Sort by priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        remediation_items.sort(
            key=lambda x: (priority_order.get(x["priority"], 4), -x["current_mastery"])
        )

        remediation_view = {
            "view_id": "REMEDIATION_VIEW_001",
            "view_type": "INTERVENTION_RECOMMENDATIONS",
            "generated_at": datetime.now().isoformat(),
            "total_interventions_needed": len(remediation_items),
            "interventions_by_priority": {
                "CRITICAL": sum(1 for r in remediation_items if r["priority"] == "CRITICAL"),
                "HIGH": sum(1 for r in remediation_items if r["priority"] == "HIGH"),
                "MEDIUM": sum(1 for r in remediation_items if r["priority"] == "MEDIUM"),
                "LOW": sum(1 for r in remediation_items if r["priority"] == "LOW")
            },
            "remediation_items": remediation_items,
            "total_intervention_hours_needed": round(
                sum(r["estimated_intervention_hours"] for r in remediation_items), 1
            ),
            "recommended_class_focus": self._get_class_focus(remediation_items)
        }

        return remediation_view

    def _get_remediation_action(self, weak_area: Dict[str, Any]) -> str:
        """Get recommended action for weak area."""
        if weak_area["mastery_score"] < 0.40:
            return "Provide foundational review with concrete manipulatives"
        elif weak_area["mastery_score"] < 0.60:
            return "Review prerequisites and provide guided practice"
        elif weak_area["mastery_score"] < 0.80:
            return "Increase practice with scaffolded support"
        else:
            return "Monitor progress; may be ready for advancement"

    def _estimate_intervention_hours(self, weak_area: Dict[str, Any]) -> float:
        """Estimate intervention hours needed."""
        if weak_area["mastery_score"] < 0.40:
            return 3.0
        elif weak_area["mastery_score"] < 0.60:
            return 2.0
        elif weak_area["mastery_score"] < 0.80:
            return 1.0
        else:
            return 0.5

    def _get_class_focus(self, remediation_items: List[Dict[str, Any]]) -> str:
        """Determine overall class focus based on remediation needs."""
        if not remediation_items:
            return "Ready to advance to next unit"
        
        critical_count = sum(1 for r in remediation_items if r["priority"] == "CRITICAL")
        
        if critical_count > len(self.students) * 0.3:  # >30% students critical
            return "Focus on foundational concepts for entire class"
        elif sum(1 for r in remediation_items if r["priority"] in ["HIGH", "CRITICAL"]) > len(self.students) * 0.5:
            return "Provide targeted small group instruction"
        else:
            return "Provide individualized remediation support"

    def generate_full_report(self) -> Dict[str, Any]:
        """Generate complete teacher intelligence report."""
        return {
            "report_id": "TEACHER_REPORT_001",
            "report_type": "COMPREHENSIVE_CLASS_INTELLIGENCE",
            "generated_at": datetime.now().isoformat(),
            "class_view": self.generate_class_view(),
            "student_progress_view": self.generate_student_progress_view(),
            "curriculum_view": self.generate_curriculum_completion_view(),
            "remediation_view": self.generate_remediation_view(),
            "summary": self._generate_summary()
        }

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate executive summary for teacher."""
        class_view = self.generate_class_view()
        
        return {
            "class_status": class_view["class_metrics"]["average_mastery_score"] >= 0.80 and "ON_TRACK" or "NEEDS_SUPPORT",
            "key_metrics": {
                "class_mastery": class_view["class_metrics"]["average_mastery_score"],
                "mastery_gap": round(0.90 - class_view["class_metrics"]["average_mastery_score"], 3),
                "students_needing_intervention": class_view["class_metrics"]["students_struggling"],
                "total_intervention_hours_needed": sum(
                    len(s["progress_state"].get("weak_areas", []))
                    for s in self.students.values()
                ) * 1.5  # Rough estimate
            },
            "actionable_insights": [
                "Monitor overall class progress against curriculum pace",
                "Provide small group remediation for struggling students",
                "Consider peer tutoring for advanced students",
                "Review mastery of prerequisite concepts before advancing"
            ]
        }


def generate_teacher_demo() -> Dict[str, Any]:
    """Generate demo teacher runtime output."""
    teacher = TeacherRuntime(
        teacher_id="TEACHER_001",
        class_id="CLASS_1A",
        grade=1
    )

    # Add sample students
    students = [
        {
            "id": "STUDENT_001",
            "name": "Aarav",
            "mastery_score": 0.85,
            "mastery_level": "PROFICIENT",
            "exercises": 8,
            "weak_areas": []
        },
        {
            "id": "STUDENT_002",
            "name": "Bhavi",
            "mastery_score": 0.72,
            "mastery_level": "DEVELOPING",
            "exercises": 7,
            "weak_areas": [
                {"concept_id": "CONCEPT_PLACE_VALUE", "mastery_score": 0.42, "priority": "HIGH"}
            ]
        },
        {
            "id": "STUDENT_003",
            "name": "Chinky",
            "mastery_score": 0.58,
            "mastery_level": "DEVELOPING",
            "exercises": 5,
            "weak_areas": [
                {"concept_id": "CONCEPT_PLACE_VALUE", "mastery_score": 0.35, "priority": "CRITICAL"},
                {"concept_id": "CONCEPT_COUNTING", "mastery_score": 0.55, "priority": "HIGH"}
            ]
        }
    ]

    for student in students:
        progress_state = {
            "mastery_score": student["mastery_score"],
            "mastery_level": student["mastery_level"],
            "total_exercises_completed": student["exercises"],
            "weak_areas": student["weak_areas"],
            "concept_strengths": ["CONCEPT_NUMBER_RECOGNITION"],
            "learning_velocity": 0.08,
            "concepts_attempted": 3
        }
        teacher.add_student_progress(student["id"], student["name"], progress_state)

    return teacher.generate_full_report()


if __name__ == "__main__":
    demo = generate_teacher_demo()
    print(json.dumps(demo, indent=2, default=str))
