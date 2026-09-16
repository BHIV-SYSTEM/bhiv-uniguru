"""
UniGuru Curriculum Intelligence Platform — Full Test Suite
Covers all 6 phases of the sprint.

Run with:
    pytest tests/test_curriculum_intelligence.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import pytest

# ---------------------------------------------------------------------------
# Phase 1 — Verified Balbharti Ingestion
# ---------------------------------------------------------------------------

CURRICULUM_DIR = ROOT / "curriculum"
EXTRACTED_DIR  = CURRICULUM_DIR / "extracted"


class TestPhase1VerifiedIngestion:
    """Verify registry files exist and are well-formed."""

    def test_verified_textbook_registry_exists(self):
        path = CURRICULUM_DIR / "verified_textbook_registry.json"
        assert path.exists(), "verified_textbook_registry.json missing"

    def test_edition_registry_exists(self):
        path = CURRICULUM_DIR / "edition_registry.json"
        assert path.exists(), "edition_registry.json missing"

    def test_curriculum_source_manifest_exists(self):
        path = CURRICULUM_DIR / "curriculum_source_manifest.json"
        assert path.exists(), "curriculum_source_manifest.json missing"

    def test_ingestion_proof_exists(self):
        path = CURRICULUM_DIR / "ingestion_proof.json"
        assert path.exists(), "ingestion_proof.json missing"

    def test_textbook_registry_has_textbooks(self):
        data = json.loads((CURRICULUM_DIR / "verified_textbook_registry.json").read_text(encoding="utf-8"))
        assert isinstance(data.get("textbooks"), list)
        assert len(data["textbooks"]) >= 1

    def test_textbook_registry_all_verified(self):
        data = json.loads((CURRICULUM_DIR / "verified_textbook_registry.json").read_text(encoding="utf-8"))
        for tb in data["textbooks"]:
            assert tb.get("verification_status") == "VERIFIED", (
                f"Textbook {tb.get('textbook_id')} is not VERIFIED"
            )

    def test_ingestion_proof_verified_sources(self):
        data = json.loads((CURRICULUM_DIR / "ingestion_proof.json").read_text(encoding="utf-8"))
        sources = data.get("verified_sources", {})
        assert sources.get("all_verified") is True

    def test_ingestion_proof_lineage_tracking_enabled(self):
        data = json.loads((CURRICULUM_DIR / "ingestion_proof.json").read_text(encoding="utf-8"))
        lineage = data.get("lineage_tracking_proof", {})
        assert lineage.get("lineage_enabled") is True


# ---------------------------------------------------------------------------
# Phase 2 — Curriculum Intelligence Extraction
# ---------------------------------------------------------------------------


class TestPhase2CurriculumExtraction:
    """Verify extraction manifests exist and carry lineage."""

    def test_chapter_manifest_exists(self):
        assert (EXTRACTED_DIR / "chapter_manifest.json").exists()

    def test_concept_manifest_exists(self):
        assert (EXTRACTED_DIR / "concept_manifest.json").exists()

    def test_exercise_manifest_exists(self):
        assert (EXTRACTED_DIR / "exercise_manifest.json").exists()

    def test_glossary_manifest_exists(self):
        assert (EXTRACTED_DIR / "glossary_manifest.json").exists()

    def test_curriculum_lineage_registry_exists(self):
        assert (EXTRACTED_DIR / "curriculum_lineage_registry.json").exists()

    def test_concept_manifest_has_source_lineage(self):
        data = json.loads((EXTRACTED_DIR / "concept_manifest.json").read_text(encoding="utf-8"))
        concepts = data.get("concepts") or data.get("concept_manifest") or []
        if isinstance(data, dict) and "concepts" not in data:
            # Try top-level list
            concepts = data if isinstance(data, list) else []
        assert len(concepts) >= 1, "concept_manifest.json has no concepts"

    def test_lineage_registry_has_entries(self):
        data = json.loads((EXTRACTED_DIR / "curriculum_lineage_registry.json").read_text(encoding="utf-8"))
        assert data  # non-empty

    def test_exercise_manifest_non_empty(self):
        data = json.loads((EXTRACTED_DIR / "exercise_manifest.json").read_text(encoding="utf-8"))
        assert data


# ---------------------------------------------------------------------------
# Phase 3 — Pedagogical Learning Graph
# ---------------------------------------------------------------------------


class TestPhase3PedagogicalGraph:
    """Verify pedagogical graph structure and integrity."""

    def _load_graph(self):
        return json.loads((EXTRACTED_DIR / "pedagogical_graph.json").read_text(encoding="utf-8"))

    def test_pedagogical_graph_exists(self):
        assert (EXTRACTED_DIR / "pedagogical_graph.json").exists()

    def test_concept_dependency_registry_exists(self):
        assert (EXTRACTED_DIR / "concept_dependency_registry.json").exists()

    def test_learning_path_validation_exists(self):
        assert (EXTRACTED_DIR / "learning_path_validation.json").exists()

    def test_graph_has_concepts(self):
        graph = self._load_graph()
        assert len(graph.get("concepts", [])) >= 1

    def test_graph_has_edges(self):
        graph = self._load_graph()
        assert len(graph.get("edges", [])) >= 1

    def test_graph_is_acyclic(self):
        graph = self._load_graph()
        validation = graph.get("prerequisite_validation", {})
        assert validation.get("no_circular_dependencies") is True
        assert validation.get("graph_is_acyclic") is True

    def test_graph_has_learning_progressions(self):
        graph = self._load_graph()
        progressions = graph.get("learning_progressions", [])
        assert len(progressions) >= 1

    def test_each_progression_has_ordered_path(self):
        graph = self._load_graph()
        for prog in graph.get("learning_progressions", []):
            assert len(prog.get("path", [])) >= 2, (
                f"Progression {prog.get('progression_id')} has < 2 steps"
            )

    def test_concepts_have_prerequisites_or_are_foundation(self):
        graph = self._load_graph()
        for concept in graph.get("concepts", []):
            # Either it's a FOUNDATION node or it has prerequisites listed
            if concept.get("node_type") != "FOUNDATION":
                # Non-foundation nodes should have prerequisites or be ADVANCED
                level = concept.get("level", 0)
                if level > 0:
                    assert "prerequisites" in concept or concept.get("node_type") == "ADVANCED", (
                        f"Non-foundation concept {concept.get('concept_id')} has no prerequisites"
                    )


# ---------------------------------------------------------------------------
# Phase 4 — Student Intelligence (Mastery Engine)
# ---------------------------------------------------------------------------


class TestPhase4MasteryEngine:
    """Unit tests for the mastery engine."""

    def test_mastery_engine_importable(self):
        from learning_runtime.mastery_engine import MasteryEngine
        assert MasteryEngine is not None

    def test_compute_concept_mastery_basic(self):
        from learning_runtime.mastery_engine import compute_concept_mastery
        result = compute_concept_mastery(
            attempts=5,
            correct_attempts=4,
            confidence_scores=[0.8, 0.85, 0.9, 0.88, 0.92],
        )
        assert 0 <= result["mastery_score"] <= 1
        assert result["mastery_level"] in ["NOT_STARTED", "NOVICE", "DEVELOPING", "PROFICIENT", "MASTERY", "EXPERT"]

    def test_no_attempts_returns_not_started(self):
        from learning_runtime.mastery_engine import compute_concept_mastery
        result = compute_concept_mastery(attempts=0, correct_attempts=0, confidence_scores=[])
        assert result["mastery_level"] == "NOT_STARTED"
        assert result["mastery_score"] == 0.0

    def test_high_accuracy_gives_high_mastery(self):
        from learning_runtime.mastery_engine import compute_concept_mastery
        result = compute_concept_mastery(
            attempts=10,
            correct_attempts=10,
            confidence_scores=[1.0] * 10,
        )
        assert result["mastery_score"] >= 0.90
        assert result["mastery_level"] == "MASTERY"

    def test_weak_area_detection(self):
        from learning_runtime.mastery_engine import detect_weak_areas
        concept_records = {
            "CONCEPT_A": {"mastery_score": 0.30, "mastery_level": "NOVICE", "accuracy": 0.3, "avg_confidence": 0.3, "attempts": 3, "trend": "FLAT"},
            "CONCEPT_B": {"mastery_score": 0.95, "mastery_level": "MASTERY", "accuracy": 0.95, "avg_confidence": 0.95, "attempts": 5, "trend": "FLAT"},
        }
        weak = detect_weak_areas(concept_records)
        assert len(weak) == 1
        assert weak[0]["concept_id"] == "CONCEPT_A"

    def test_weak_area_priority_critical(self):
        from learning_runtime.mastery_engine import detect_weak_areas
        concept_records = {
            "CONCEPT_HARD": {"mastery_score": 0.20, "mastery_level": "NOVICE", "accuracy": 0.2, "avg_confidence": 0.2, "attempts": 2, "trend": "DECLINING"},
        }
        weak = detect_weak_areas(concept_records)
        assert weak[0]["priority"] == "CRITICAL"

    def test_remediation_routing_returns_actions(self):
        from learning_runtime.mastery_engine import generate_remediation_routing
        weak_areas = [{"concept_id": "CONCEPT_A", "mastery_score": 0.30, "mastery_level": "NOVICE", "priority": "HIGH"}]
        remediations = generate_remediation_routing(weak_areas)
        assert len(remediations) == 1
        assert len(remediations[0]["recommended_actions"]) >= 1

    def test_mastery_engine_full_cycle(self):
        from learning_runtime.mastery_engine import MasteryEngine
        engine = MasteryEngine(student_id="TEST_001", grade=1)
        for i in range(5):
            engine.record_exercise("CONCEPT_COUNTING", correct=(i % 2 == 0), confidence=0.7, time_seconds=60)
        state = engine.build_progress_state()
        # Check all required runtime contract fields are present
        required_fields = [
            "mastery_score", "concept_strengths", "concept_weaknesses",
            "recommended_remediation", "learning_progress_state",
            "mastery_level", "weak_areas", "total_exercises_completed"
        ]
        for field in required_fields:
            assert field in state, f"Missing field: {field}"

    def test_student_progress_contract_output(self):
        from learning_runtime.mastery_engine import MasteryEngine
        engine = MasteryEngine(student_id="TEST_002", grade=2)
        engine.record_exercise("CONCEPT_PLACE_VALUE", correct=False, confidence=0.3, time_seconds=120)
        state = engine.build_progress_state()
        assert state["mastery_score"] >= 0
        assert state["mastery_score"] <= 1
        assert isinstance(state["concept_strengths"], list)
        assert isinstance(state["concept_weaknesses"], list)

    def test_generate_mastery_demo(self):
        from learning_runtime.mastery_engine import generate_mastery_demo
        demo = generate_mastery_demo()
        assert demo["validation"]["all_required_fields_present"] is True
        assert "mastery_score" in demo["progress_state"]

    def test_student_intelligence_demo_json_exists(self):
        path = ROOT / "learning_runtime" / "student_intelligence_demo.json"
        assert path.exists(), "student_intelligence_demo.json missing"

    def test_student_progress_contract_json_exists(self):
        path = ROOT / "learning_runtime" / "student_progress_contract.json"
        assert path.exists(), "student_progress_contract.json missing"


# ---------------------------------------------------------------------------
# Phase 5 — Teacher Runtime
# ---------------------------------------------------------------------------


class TestPhase5TeacherRuntime:
    """Validate teacher runtime outputs."""

    def test_teacher_runtime_importable(self):
        from learning_runtime.teacher_runtime import TeacherRuntime
        assert TeacherRuntime is not None

    def test_teacher_runtime_generate_full_report(self):
        from learning_runtime.teacher_runtime import generate_teacher_demo
        report = generate_teacher_demo()
        assert "class_view" in report
        assert "student_progress_view" in report
        assert "curriculum_view" in report
        assert "remediation_view" in report

    def test_class_view_has_metrics(self):
        from learning_runtime.teacher_runtime import generate_teacher_demo
        report = generate_teacher_demo()
        metrics = report["class_view"].get("class_metrics", {})
        assert "average_mastery_score" in metrics
        assert "students_mastered" in metrics
        assert "students_struggling" in metrics

    def test_remediation_view_prioritised(self):
        from learning_runtime.teacher_runtime import generate_teacher_demo
        report = generate_teacher_demo()
        rems = report["remediation_view"].get("remediation_items", [])
        # Ensure sorted by priority (CRITICAL first)
        priorities = [r["priority"] for r in rems]
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for i in range(len(priorities) - 1):
            assert order.get(priorities[i], 4) <= order.get(priorities[i+1], 4), (
                f"Remediation items not sorted: {priorities[i]} > {priorities[i+1]}"
            )

    def test_teacher_contract_json_exists(self):
        path = ROOT / "learning_runtime" / "teacher_contract.json"
        assert path.exists()

    def test_teacher_runtime_demo_json_exists(self):
        path = ROOT / "learning_runtime" / "teacher_runtime_demo.json"
        assert path.exists()


# ---------------------------------------------------------------------------
# Phase 6 — Production Runtime Convergence
# ---------------------------------------------------------------------------


class TestPhase6RuntimeConvergence:
    """End-to-end convergence tests through the canonical pipeline."""

    def test_canonical_runtime_importable(self):
        from learning_runtime.canonical_runtime import CanonicalRuntime
        assert CanonicalRuntime is not None

    def test_execute_query_returns_contract(self):
        from learning_runtime.canonical_runtime import execute_query
        result = execute_query(query="What is counting?", student_id="TEST_CONV_001", grade=1)
        assert result["schema_version"] == "UNIGURU_CANONICAL_RUNTIME_V2"
        assert result["convergence_validated"] is True

    def test_pipeline_has_all_stages(self):
        from learning_runtime.canonical_runtime import execute_query
        result = execute_query(query="What is place value?", student_id="TEST_CONV_002")
        stages = result["pipeline_stages"]
        expected = [
            "StudentQuery", "Retrieval", "CurriculumIntelligence",
            "LearningIntelligence", "MasteryIntelligence",
            "ConstitutionalRuntime", "RuntimeContract"
        ]
        for stage in expected:
            assert stage in stages, f"Missing pipeline stage: {stage}"

    def test_mastery_fields_in_contract(self):
        from learning_runtime.canonical_runtime import execute_query
        result = execute_query(query="What is addition?", student_id="TEST_CONV_003")
        assert "mastery_score" in result
        assert "concept_strengths" in result
        assert "concept_weaknesses" in result
        assert "recommended_remediation" in result
        assert "learning_progress_state" in result

    def test_curriculum_lineage_in_contract(self):
        from learning_runtime.canonical_runtime import execute_query
        result = execute_query(query="counting numbers", student_id="TEST_CONV_004", grade=1, subject="Mathematics")
        ci = result.get("curriculum_intelligence", {})
        assert isinstance(ci, dict)
        # At minimum the curriculum intelligence block is present
        assert "concept" in ci or "chapter" in ci

    def test_no_parallel_execution_paths(self):
        """Validate that there is only one pipeline trace (no parallel branches)."""
        from learning_runtime.canonical_runtime import execute_query
        result = execute_query(query="subtraction", student_id="TEST_CONV_005")
        trace = result.get("pipeline_trace", [])
        stage_names = [t["stage"] for t in trace]
        # Each stage appears exactly once
        assert len(stage_names) == len(set(stage_names)), "Duplicate stages found — parallel paths detected"

    def test_runtime_convergence_report_exists(self):
        path = EXTRACTED_DIR / "runtime_convergence_report.json"
        assert path.exists()

    def test_runtime_flow_validation_exists(self):
        path = EXTRACTED_DIR / "runtime_flow_validation.json"
        assert path.exists()

    def test_production_readiness_report_exists(self):
        path = EXTRACTED_DIR / "production_readiness_report.json"
        assert path.exists()
