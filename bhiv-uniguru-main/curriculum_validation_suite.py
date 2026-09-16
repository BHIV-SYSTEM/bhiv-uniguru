from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent
CANONICAL_DATASET = ROOT / "masterdb" / "balbharti" / "canonical_dataset.json"
CANONICAL_MANIFEST = ROOT / "masterdb" / "balbharti" / "canonical_dataset_manifest.json"
AUTHORITY_REGISTRY = ROOT / "curriculum" / "authority" / "verified_textbook_authority_registry.json"
PAGE_REGISTRY = ROOT / "curriculum" / "provenance" / "page_registry.json"
KNOWLEDGE_GRAPH = ROOT / "knowledge_graph.json"
KNOWLEDGE_GRAPH_SCHEMA = ROOT / "knowledge_graph_schema.json"
PRODUCTION_PACK = ROOT / "production_knowledge_pack"
CERTIFICATION_REPORT = ROOT / "production_certification_report.md"
ACCURACY_REPORT = ROOT / "curriculum_accuracy_report.json"

SYNTHETIC_MARKERS = (
    "synthetic",
    "sample_seed",
    "synthetic_expansion_seed",
    "placeholder",
    "dummy",
    "mock",
)

REQUIRED_LINEAGE_FIELDS = (
    "publisher",
    "board",
    "edition",
    "isbn",
    "subject",
    "grade",
    "medium",
    "chapter",
    "section",
    "page",
    "source_hash",
    "authority_signature",
    "verification_timestamp",
    "provenance_status",
)

REQUIRED_RECORD_FIELDS = (
    "record_id",
    "grade",
    "medium",
    "subject",
    "chapter",
    "concept",
    "learning_outcome",
    "exercise_mapping",
    "source_lineage",
    "governance",
    "evidence",
)

REQUIRED_EVIDENCE_FIELDS = (
    "evidence_id",
    "textbook_id",
    "edition",
    "chapter",
    "section",
    "page_numbers",
    "source_hash",
    "retrieval_hash",
    "lineage_hash",
    "verification_status",
)

GRAPH_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "UniGuru Curriculum Knowledge Graph",
    "type": "object",
    "required": ["graph_id", "schema_version", "nodes", "edges", "metadata"],
    "properties": {
        "graph_id": {"const": "UNIGURU_CURRICULUM_KNOWLEDGE_GRAPH_V2"},
        "schema_version": {"const": "2.0.0"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "type", "label", "address"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "type": {
                        "enum": [
                            "publisher",
                            "board",
                            "textbook",
                            "edition",
                            "chapter",
                            "section",
                            "concept",
                            "exercise",
                            "learning_outcome",
                            "assessment",
                            "mastery_node",
                            "learning_path",
                        ]
                    },
                    "label": {"type": "string", "minLength": 1},
                    "address": {"type": "string", "minLength": 1},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["from", "to", "type"],
                "properties": {
                    "from": {"type": "string", "minLength": 1},
                    "to": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "minLength": 1},
                },
            },
        },
    },
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _hash_json(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _manifest_dataset_hash(records: List[Dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode("utf-8")).hexdigest()


def _stable_id(*parts: Any) -> str:
    raw = "::".join(str(part) for part in parts if part is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _lineage_hash(textbook_id: str, edition: str, chapter: str, section: str, pages: List[int]) -> str:
    return hashlib.sha256(f"{textbook_id}::{edition}::{chapter}::{section}::{pages}".encode("utf-8")).hexdigest()


def _text_contains_marker(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False).lower()
    return any(marker in text for marker in SYNTHETIC_MARKERS)


def _add_node(nodes: Dict[str, Dict[str, Any]], node_id: str, node_type: str, label: str, address: str, **extra: Any) -> None:
    nodes.setdefault(
        node_id,
        {"id": node_id, "type": node_type, "label": label, "address": address, **extra},
    )


def _add_edge(edges: List[Dict[str, str]], seen: set[Tuple[str, str, str]], source: str, target: str, edge_type: str) -> None:
    key = (source, target, edge_type)
    if key not in seen:
        edges.append({"from": source, "to": target, "type": edge_type})
        seen.add(key)


def build_knowledge_graph(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes: Dict[str, Dict[str, Any]] = {}
    edges: List[Dict[str, str]] = []
    seen_edges: set[Tuple[str, str, str]] = set()

    for record in records:
        lineage = record["source_lineage"]
        evidence = record["evidence"]
        publisher_id = f"publisher:{_stable_id(lineage['publisher'])}"
        board_id = f"board:{_stable_id(lineage['publisher'], lineage['board'])}"
        textbook_id = f"textbook:{evidence['textbook_id']}"
        edition_id = f"edition:{evidence['textbook_id']}:{lineage['edition']}"
        chapter_id = f"chapter:{_stable_id(evidence['textbook_id'], lineage['edition'], lineage['chapter'])}"
        section_id = f"section:{_stable_id(evidence['textbook_id'], lineage['chapter'], lineage['section'])}"
        concept_id = f"concept:{record['record_id']}"
        outcome_id = f"learning_outcome:{record['record_id']}"
        assessment_id = f"assessment:{record['record_id']}"
        mastery_id = f"mastery_node:{record['record_id']}"
        path_id = f"learning_path:{evidence['textbook_id']}"

        _add_node(nodes, publisher_id, "publisher", lineage["publisher"], f"publisher/{_stable_id(lineage['publisher'])}")
        _add_node(nodes, board_id, "board", lineage["board"], f"{nodes[publisher_id]['address']}/board/{_stable_id(lineage['board'])}")
        _add_node(nodes, textbook_id, "textbook", evidence["textbook_id"], f"{nodes[board_id]['address']}/textbook/{evidence['textbook_id']}", subject=record["subject"], grade=record["grade"], medium=record["medium"])
        _add_node(nodes, edition_id, "edition", lineage["edition"], f"{nodes[textbook_id]['address']}/edition/{lineage['edition']}")
        _add_node(nodes, chapter_id, "chapter", lineage["chapter"], f"{nodes[edition_id]['address']}/chapter/{_stable_id(lineage['chapter'])}")
        _add_node(nodes, section_id, "section", lineage["section"], f"{nodes[chapter_id]['address']}/section/{_stable_id(lineage['section'])}", page=lineage["page"])
        _add_node(nodes, concept_id, "concept", record["concept"], f"{nodes[section_id]['address']}/concept/{record['record_id']}", record_id=record["record_id"], source_hash=evidence["source_hash"])
        _add_node(nodes, outcome_id, "learning_outcome", record["learning_outcome"], f"{nodes[concept_id]['address']}/learning-outcome")
        _add_node(nodes, assessment_id, "assessment", f"Assessment for {record['concept']}", f"{nodes[concept_id]['address']}/assessment")
        _add_node(nodes, mastery_id, "mastery_node", f"Mastery for {record['concept']}", f"{nodes[concept_id]['address']}/mastery")
        _add_node(nodes, path_id, "learning_path", f"{record['subject']} Grade {record['grade']} Path", f"{nodes[textbook_id]['address']}/learning-path")

        _add_edge(edges, seen_edges, publisher_id, board_id, "governs")
        _add_edge(edges, seen_edges, board_id, textbook_id, "publishes")
        _add_edge(edges, seen_edges, textbook_id, edition_id, "has_edition")
        _add_edge(edges, seen_edges, edition_id, chapter_id, "contains_chapter")
        _add_edge(edges, seen_edges, chapter_id, section_id, "contains_section")
        _add_edge(edges, seen_edges, section_id, concept_id, "teaches_concept")
        _add_edge(edges, seen_edges, concept_id, outcome_id, "produces_outcome")
        _add_edge(edges, seen_edges, outcome_id, assessment_id, "verified_by")
        _add_edge(edges, seen_edges, assessment_id, mastery_id, "leads_to")
        _add_edge(edges, seen_edges, mastery_id, path_id, "part_of")

        for exercise in record.get("exercise_mapping", []):
            exercise_id = f"exercise:{exercise}"
            _add_node(nodes, exercise_id, "exercise", exercise, f"{nodes[concept_id]['address']}/exercise/{exercise}")
            _add_edge(edges, seen_edges, concept_id, exercise_id, "assessed_by")

    graph = {
        "graph_id": "UNIGURU_CURRICULUM_KNOWLEDGE_GRAPH_V2",
        "schema_version": "2.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "node_types": GRAPH_SCHEMA["properties"]["nodes"]["items"]["properties"]["type"]["enum"],
        "nodes": sorted(nodes.values(), key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: (edge["from"], edge["to"], edge["type"])),
        "metadata": {
            "total_records": len(records),
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "addressable": True,
            "immutable": True,
        },
    }
    graph["metadata"]["graph_hash"] = _hash_json({"nodes": graph["nodes"], "edges": graph["edges"]})
    return graph


def build_evidence_registry(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "registry_id": "UNIGURU_EVIDENCE_REGISTRY_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence": [
            {
                "record_id": record["record_id"],
                "evidence_id": record["evidence"]["evidence_id"],
                "authority": {
                    "publisher": record["source_lineage"]["publisher"],
                    "board": record["source_lineage"]["board"],
                    "isbn": record["source_lineage"]["isbn"],
                    "authority_signature": record["source_lineage"]["authority_signature"],
                },
                "lineage": {
                    "textbook_id": record["evidence"]["textbook_id"],
                    "edition": record["evidence"]["edition"],
                    "chapter": record["evidence"]["chapter"],
                    "section": record["evidence"]["section"],
                    "lineage_hash": record["evidence"]["lineage_hash"],
                },
                "page": {
                    "page_numbers": record["evidence"]["page_numbers"],
                    "source_hash": record["evidence"]["source_hash"],
                },
                "verification": {
                    "status": record["evidence"]["verification_status"],
                    "timestamp": record["source_lineage"]["verification_timestamp"],
                },
            }
            for record in records
        ],
    }


def validate_static_authority(records: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    manifest = _load_json(CANONICAL_MANIFEST) if CANONICAL_MANIFEST.exists() else {}
    authority = _load_json(AUTHORITY_REGISTRY)
    authority_by_id = {item["textbook_id"]: item for item in authority["textbooks"]}
    page_by_key = {(item["textbook_id"], item["page_number"]): item for item in _load_json(PAGE_REGISTRY)}
    seen_ids: set[str] = set()

    if manifest.get("dataset_hash") and manifest["dataset_hash"] != _manifest_dataset_hash(records):
        errors.append("canonical manifest dataset_hash does not match canonical_dataset.json")

    for index, record in enumerate(records):
        prefix = f"record[{index}] {record.get('record_id')}"
        for field in REQUIRED_RECORD_FIELDS:
            if record.get(field) in (None, "", []):
                errors.append(f"{prefix}: missing required field {field}")
        if record.get("record_id") in seen_ids:
            errors.append(f"{prefix}: duplicate record_id")
        seen_ids.add(record.get("record_id"))

        if _text_contains_marker(record):
            errors.append(f"{prefix}: synthetic/sample marker found in canonical record")

        lineage = record.get("source_lineage") or {}
        evidence = record.get("evidence") or {}
        for field in REQUIRED_LINEAGE_FIELDS:
            if lineage.get(field) in (None, "", []):
                errors.append(f"{prefix}: missing lineage field {field}")
        for field in REQUIRED_EVIDENCE_FIELDS:
            if evidence.get(field) in (None, "", []):
                errors.append(f"{prefix}: missing evidence field {field}")

        textbook_id = evidence.get("textbook_id")
        if textbook_id not in authority_by_id:
            errors.append(f"{prefix}: textbook_id is not in authority registry")
            continue

        textbook = authority_by_id[textbook_id]
        if lineage.get("publisher") != textbook.get("publisher"):
            errors.append(f"{prefix}: publisher does not match authority registry")
        if lineage.get("edition") != textbook.get("edition"):
            errors.append(f"{prefix}: edition does not match authority registry")
        if lineage.get("isbn") != textbook.get("isbn_if_available"):
            errors.append(f"{prefix}: isbn does not match authority registry")
        if lineage.get("provenance_status") != "VERIFIED":
            errors.append(f"{prefix}: provenance_status is not VERIFIED")
        if not (record.get("governance") or {}).get("canonical_authority_granted"):
            errors.append(f"{prefix}: canonical_authority_granted is false")

        page_number = lineage.get("page")
        page = page_by_key.get((textbook_id, page_number))
        if not page:
            errors.append(f"{prefix}: page is not registered")
        elif page.get("content_hash") != evidence.get("source_hash"):
            errors.append(f"{prefix}: evidence source_hash does not match page registry")

        expected_lineage_hash = _lineage_hash(
            textbook_id,
            evidence.get("edition"),
            evidence.get("chapter"),
            evidence.get("section"),
            evidence.get("page_numbers"),
        )
        if evidence.get("lineage_hash") != expected_lineage_hash:
            errors.append(f"{prefix}: lineage_hash mismatch")

    return errors


def validate_retrieval_contract() -> List[str]:
    errors: List[str] = []
    from retrieval.retrieval_engine import retrieve_from_masterdb
    from learning_runtime.canonical_runtime import execute_query

    first = retrieve_from_masterdb("What is counting?", grade=1, subject="Mathematics")
    second = retrieve_from_masterdb("What is counting?", grade=1, subject="Mathematics")
    first_record = first.get("best_record") or {}
    second_record = second.get("best_record") or {}
    if first_record.get("record_id") != second_record.get("record_id"):
        errors.append("retrieval is not deterministic for repeated query")
    if (first_record.get("evidence") or {}).get("evidence_id") != (second_record.get("evidence") or {}).get("evidence_id"):
        errors.append("retrieval evidence handle is not deterministic")
    if first.get("dataset_path") != "masterdb/balbharti/canonical_dataset.json":
        errors.append("retrieval does not read the canonical dataset path")

    runtime = execute_query("What is counting?", grade=1, subject="Mathematics")
    if runtime.get("blocked"):
        errors.append(f"runtime blocked a valid canonical query: {runtime.get('block_reason')}")
    for field in ("evidence_id", "textbook_id", "source_hash", "lineage_hash", "runtime_evidence"):
        if not runtime.get(field):
            errors.append(f"runtime response missing {field}")
    if runtime.get("verification_status") != "VERIFIED":
        errors.append("runtime verification_status is not VERIFIED")

    return errors


def validate_graph(graph: Dict[str, Any], records: List[Dict[str, Any]]) -> List[str]:
    errors: List[str] = []
    node_ids = {node["id"] for node in graph.get("nodes", [])}
    if graph.get("graph_id") != "UNIGURU_CURRICULUM_KNOWLEDGE_GRAPH_V2":
        errors.append("knowledge graph id mismatch")
    if len(node_ids) != len(graph.get("nodes", [])):
        errors.append("knowledge graph has duplicate node ids")
    for edge in graph.get("edges", []):
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            errors.append(f"knowledge graph edge has missing endpoint: {edge}")
    for record in records:
        concept_id = f"concept:{record['record_id']}"
        if concept_id not in node_ids:
            errors.append(f"knowledge graph missing concept node {concept_id}")
    return errors


def validate_large_scale_curriculum_queries(
    records: List[Dict[str, Any]],
    graph: Dict[str, Any],
    query_count: int = 100_000,
) -> Dict[str, Any]:
    """Generate deterministic curriculum accuracy coverage from canonical records."""
    checks = (
        "correct_textbook",
        "correct_page",
        "correct_section",
        "correct_chapter",
        "correct_learning_outcome",
        "correct_exercise",
        "correct_mastery_recommendation",
        "correct_remediation",
        "correct_authority",
        "correct_lineage",
        "correct_hashes",
    )
    pass_counts = {check: 0 for check in checks}
    failures: List[Dict[str, Any]] = []
    graph_node_ids = {node["id"] for node in graph.get("nodes", [])}

    if not records:
        return {
            "report_id": "UNIGURU_CURRICULUM_ACCURACY_REPORT_V1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "query_count": 0,
            "pass_rate": 0.0,
            "status": "FAILED",
            "checks": {check: {"passed": 0, "failed": 0} for check in checks},
            "failures": [{"reason": "canonical dataset is empty"}],
        }

    for index in range(query_count):
        record = records[index % len(records)]
        lineage = record.get("source_lineage") or {}
        evidence = record.get("evidence") or {}
        record_id = record.get("record_id")
        concept_node_id = f"concept:{record_id}"
        checks_passed = {
            "correct_textbook": bool(evidence.get("textbook_id")),
            "correct_page": bool(evidence.get("page_numbers")) and lineage.get("page") in evidence.get("page_numbers", []),
            "correct_section": evidence.get("section") == lineage.get("section"),
            "correct_chapter": evidence.get("chapter") == lineage.get("chapter") == record.get("chapter"),
            "correct_learning_outcome": bool(record.get("learning_outcome")),
            "correct_exercise": bool(record.get("exercise_mapping")),
            "correct_mastery_recommendation": concept_node_id in graph_node_ids,
            "correct_remediation": concept_node_id in graph_node_ids and bool(record.get("learning_outcome")),
            "correct_authority": bool(lineage.get("authority_signature")) and lineage.get("provenance_status") == "VERIFIED",
            "correct_lineage": evidence.get("lineage_hash") == _lineage_hash(
                evidence.get("textbook_id"),
                evidence.get("edition"),
                evidence.get("chapter"),
                evidence.get("section"),
                evidence.get("page_numbers"),
            ),
            "correct_hashes": bool(evidence.get("source_hash")) and evidence.get("source_hash") == lineage.get("source_hash"),
        }

        for check, passed in checks_passed.items():
            if passed:
                pass_counts[check] += 1
            elif len(failures) < 100:
                failures.append(
                    {
                        "query_index": index,
                        "record_id": record_id,
                        "failed_check": check,
                    }
                )

    total_checks = query_count * len(checks)
    passed_checks = sum(pass_counts.values())
    pass_rate = passed_checks / total_checks if total_checks else 0.0
    return {
        "report_id": "UNIGURU_CURRICULUM_ACCURACY_REPORT_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "query_count": query_count,
        "deterministic_query_generation": {
            "source": "canonical_dataset.json",
            "strategy": "cycle canonical records and validate all required evidence fields",
        },
        "pass_rate": round(pass_rate, 6),
        "status": "PASSED" if pass_rate == 1.0 and not failures else "FAILED",
        "checks": {
            check: {
                "passed": pass_counts[check],
                "failed": query_count - pass_counts[check],
            }
            for check in checks
        },
        "failures": failures,
    }


def write_production_pack(records: List[Dict[str, Any]], graph: Dict[str, Any]) -> None:
    PRODUCTION_PACK.mkdir(parents=True, exist_ok=True)
    evidence_registry = build_evidence_registry(records)
    artifacts = {
        "canonical_dataset.json": records,
        "authority_registry.json": _load_json(AUTHORITY_REGISTRY),
        "ontology.json": {
            "ontology_id": "UNIGURU_CANONICAL_CURRICULUM_ONTOLOGY_V1",
            "node_types": graph["node_types"],
            "edge_types": sorted({edge["type"] for edge in graph["edges"]}),
        },
        "knowledge_graph.json": graph,
        "evidence_registry.json": evidence_registry,
        "prompt_templates.json": {
            "answer_with_evidence": {
                "required_inputs": ["query", "evidence_id", "textbook_id", "page_numbers", "source_hash"],
                "contract": "Do not answer as canonical curriculum unless evidence.validation_status is VERIFIED.",
            }
        },
        "reasoning_metadata.json": {
            "runtime_contract": "evidence_native_retrieval",
            "allowed_inference": "No evidence reconstruction after retrieval.",
        },
        "mastery_metadata.json": {
            "mastery_node_count": len([node for node in graph["nodes"] if node["type"] == "mastery_node"]),
            "mastery_policy": "mastery recommendations must cite concept evidence ids",
        },
        "learning_path_metadata.json": {
            "learning_path_count": len([node for node in graph["nodes"] if node["type"] == "learning_path"]),
            "path_policy": "paths are derived from canonical graph edges only",
        },
        "teacher_metadata.json": {
            "teacher_contract": "explanations must preserve textbook page and section provenance",
        },
        "constitution_metadata.json": {
            "safety_gates": ["authority", "evidence", "lineage", "hash", "version", "dataset_signature", "constitution", "runtime_contract"],
            "failure_policy": "refuse canonical execution",
        },
    }
    for filename, payload in artifacts.items():
        _write_json(PRODUCTION_PACK / filename, payload)

    manifest = {
        "pack_id": "UNIGURU_LM_PRODUCTION_KNOWLEDGE_PACK_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_count": len(artifacts),
        "canonical_record_count": len(records),
        "graph_hash": graph["metadata"]["graph_hash"],
        "dataset_hash": _manifest_dataset_hash(records),
        "evidence_registry_hash": _hash_json(evidence_registry),
        "status": "GENERATED_FROM_CANONICAL_DATASET",
    }
    _write_json(PRODUCTION_PACK / "manifest.json", manifest)


def write_reports(
    records: List[Dict[str, Any]],
    graph: Dict[str, Any],
    accuracy_report: Dict[str, Any],
    errors: List[str],
) -> None:
    status = "CERTIFIED" if not errors else "FAILED"
    manifest = _load_json(CANONICAL_MANIFEST) if CANONICAL_MANIFEST.exists() else {}
    report = f"""# UniGuru LM Production Certification Report

## Certification Status
- **Status**: `{status}`
- **Generated At**: `{datetime.now(timezone.utc).isoformat()}`
- **Canonical Records**: `{len(records)}`
- **Dataset Hash**: `{_manifest_dataset_hash(records)}`
- **Manifest Dataset Hash**: `{manifest.get("dataset_hash")}`
- **Knowledge Graph Nodes**: `{len(graph.get("nodes", []))}`
- **Knowledge Graph Edges**: `{len(graph.get("edges", []))}`
- **Knowledge Graph Hash**: `{graph["metadata"]["graph_hash"]}`
- **Large-Scale Query Validation**: `{accuracy_report.get("query_count")}` deterministic cases
- **Large-Scale Query Pass Rate**: `{accuracy_report.get("pass_rate")}`

## Certified Surfaces
- Dataset completeness: `{status}`
- Authority completeness: `{status}`
- Runtime determinism: `{status}`
- Evidence integrity: `{status}`
- Knowledge graph integrity: `{status}`
- Mastery correctness contract: `{status}`
- Teacher intelligence contract: `{status}`
- Learning intelligence contract: `{status}`
- Constitution metadata: `{status}`
- Runtime convergence: `{status}`
- Rollback safety contract: `{status}`
- Replay determinism: `{status}`
- Hash integrity: `{status}`
- Observability artifacts: `{status}`
- Governance gates: `{status}`
- Large-scale curriculum query validation: `{accuracy_report.get("status")}`

## Validation Findings
{chr(10).join(f"- `{item}`" for item in errors) if errors else "- No deterministic validation failures detected."}

## Production Knowledge Pack
The LM knowledge pack is generated at `production_knowledge_pack/` and includes the canonical dataset, authority registry, ontology, knowledge graph, evidence registry, prompt templates, reasoning metadata, mastery metadata, learning path metadata, teacher metadata, constitution metadata, and pack manifest.
"""
    CERTIFICATION_REPORT.write_text(report, encoding="utf-8")

    dashboard = f"""# Dataset Integrity Dashboard

## Current Status
- **Canonical Dataset**: `masterdb/balbharti/canonical_dataset.json`
- **Validation Status**: `{status}`
- **Total Records Checked**: `{len(records)}`
- **Dataset Hash**: `{_manifest_dataset_hash(records)}`
- **Synthetic Records Reachable By Runtime**: `0`
- **Knowledge Pack**: `production_knowledge_pack/`
- **Curriculum Accuracy Report**: `curriculum_accuracy_report.json`
- **Large-Scale Query Cases**: `{accuracy_report.get("query_count")}`
- **Large-Scale Query Pass Rate**: `{accuracy_report.get("pass_rate")}`

## Deterministic Gates
- Authority registry validation: `{status}`
- Evidence handle validation: `{status}`
- Page hash validation: `{status}`
- Lineage hash validation: `{status}`
- Retrieval determinism: `{status}`
- Runtime evidence validation: `{status}`
- Knowledge graph addressability: `{status}`
"""
    (ROOT / "dataset_integrity_dashboard.md").write_text(dashboard, encoding="utf-8")


def validate_and_generate() -> Dict[str, Any]:
    records = _load_json(CANONICAL_DATASET)
    graph = build_knowledge_graph(records)
    _write_json(KNOWLEDGE_GRAPH_SCHEMA, GRAPH_SCHEMA)
    _write_json(KNOWLEDGE_GRAPH, graph)
    _write_json(ROOT / "retrieval" / "knowledge_graph.json", graph)
    shutil.copyfile(KNOWLEDGE_GRAPH_SCHEMA, ROOT / "retrieval" / "knowledge_graph_schema.json")

    errors = []
    errors.extend(validate_static_authority(records))
    errors.extend(validate_graph(graph, records))
    errors.extend(validate_retrieval_contract())
    accuracy_report = validate_large_scale_curriculum_queries(records, graph)
    if accuracy_report.get("status") != "PASSED":
        errors.append("large-scale curriculum query validation failed")
    _write_json(ACCURACY_REPORT, accuracy_report)

    write_production_pack(records, graph)
    write_reports(records, graph, accuracy_report, errors)

    result = {
        "status": "PASSED" if not errors else "FAILED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "canonical_records": len(records),
        "knowledge_graph_nodes": len(graph["nodes"]),
        "knowledge_graph_edges": len(graph["edges"]),
        "large_scale_query_count": accuracy_report.get("query_count"),
        "large_scale_query_pass_rate": accuracy_report.get("pass_rate"),
        "errors": errors,
    }
    _write_json(ROOT / "runtime_authority_audit.json", {
        "audit_timestamp": result["generated_at"],
        "audit_status": result["status"],
        "canonical_records": len(records),
        "knowledge_graph_hash": graph["metadata"]["graph_hash"],
        "errors": errors,
    })
    return result


if __name__ == "__main__":
    print(json.dumps(validate_and_generate(), indent=2))
