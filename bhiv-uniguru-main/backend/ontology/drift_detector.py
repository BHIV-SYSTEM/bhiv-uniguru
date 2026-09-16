from __future__ import annotations

from typing import Any, Dict, List


def _index_concepts(snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["concept_id"]: row for row in snapshot.get("concepts", [])}


def detect_semantic_drift(
    previous_snapshot: Dict[str, Any],
    current_snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    previous_version = int(previous_snapshot.get("snapshot_version", 0))
    current_version = int(current_snapshot.get("snapshot_version", 0))
    version_bumped = current_version > previous_version

    previous_index = _index_concepts(previous_snapshot)
    current_index = _index_concepts(current_snapshot)

    violations: List[Dict[str, Any]] = []
    rejected = False

    for concept_id, previous in previous_index.items():
        current = current_index.get(concept_id)
        if current is None:
            continue

        if bool(previous.get("immutable")):
            immutable_changes = []
            if previous["parent_id"] != current["parent_id"]:
                immutable_changes.append("parent_change")
            if previous["canonical_name"] != current["canonical_name"]:
                immutable_changes.append("canonical_name_change")
            if str(previous["domain"]) != str(current["domain"]):
                immutable_changes.append("domain_reassignment")
            if int(current["truth_level"]) < int(previous["truth_level"]):
                immutable_changes.append("truth_downgrade")

            if immutable_changes:
                rejected = True
                violations.append(
                    {
                        "type": "immutable_concept_violation",
                        "concept_id": concept_id,
                        "fields": immutable_changes,
                        "previous": {
                            "parent_id": previous["parent_id"],
                            "canonical_name": previous["canonical_name"],
                            "truth_level": previous["truth_level"],
                            "domain": previous["domain"],
                        },
                        "current": {
                            "parent_id": current["parent_id"],
                            "canonical_name": current["canonical_name"],
                            "truth_level": current["truth_level"],
                            "domain": current["domain"],
                        },
                    }
                )
                continue

        if previous["parent_id"] != current["parent_id"] and not version_bumped:
            violations.append(
                {
                    "type": "parent_change_requires_version_bump",
                    "concept_id": concept_id,
                    "previous_parent_id": previous["parent_id"],
                    "current_parent_id": current["parent_id"],
                }
            )

        if int(current["truth_level"]) < int(previous["truth_level"]):
            rejected = True
            violations.append(
                {
                    "type": "truth_downgrade_rejected",
                    "concept_id": concept_id,
                    "previous_truth_level": previous["truth_level"],
                    "current_truth_level": current["truth_level"],
                }
            )

        if previous["canonical_name"] != current["canonical_name"] and not version_bumped:
            violations.append(
                {
                    "type": "canonical_name_change_requires_version_bump",
                    "concept_id": concept_id,
                    "previous_canonical_name": previous["canonical_name"],
                    "current_canonical_name": current["canonical_name"],
                }
            )

    accepted = (not rejected) and (len(violations) == 0 or version_bumped)
    return {
        "previous_snapshot_version": previous_version,
        "current_snapshot_version": current_version,
        "version_bumped": version_bumped,
        "accepted": accepted,
        "rejected": rejected,
        "violations": violations,
    }
