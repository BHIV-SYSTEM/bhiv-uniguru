from __future__ import annotations

from typing import Any, Dict, List


def generate_learning_path(record: Dict[str, Any], curriculum_graph: Dict[str, Any]) -> Dict[str, Any]:
    if not record:
        return {
            "path": [],
            "recommendation": "Map the query to a grade-level Balbharti chapter and then sequence prerequisite and extension concepts.",
            "prerequisite_concept": None,
            "next_concept": None,
        }

    record_id = record.get("record_id")
    nodes = {node["id"]: node for node in curriculum_graph.get("nodes", [])}
    if record_id not in nodes:
        return {
            "path": [record.get("concept")],
            "recommendation": "Use the matched curriculum record as the base learning step.",
            "prerequisite_concept": None,
            "next_concept": None,
        }

    edges = curriculum_graph.get("edges", [])
    prereq = None
    next_concept = None
    path: List[str] = [record.get("concept")]

    for edge in edges:
        if edge.get("to") == record_id and edge.get("type") == "grade_progression":
            source = nodes.get(edge.get("from"))
            if source:
                prereq = source.get("concept")
                path.insert(0, prereq)
                break

    for edge in edges:
        if edge.get("from") == record_id and edge.get("type") == "grade_progression":
            target = nodes.get(edge.get("to"))
            if target:
                next_concept = target.get("concept")
                path.append(next_concept)
                break

    recommendation = (
        "Begin with the matched concept and then review the earlier grade-level foundation before moving to the next linked curriculum topic."
        if prereq or next_concept
        else "Use this matched concept as the core lesson and expand with related chapter topics."
    )

    return {
        "path": path,
        "recommendation": recommendation,
        "prerequisite_concept": prereq,
        "next_concept": next_concept,
    }
