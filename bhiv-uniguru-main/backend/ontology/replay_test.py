from __future__ import annotations

import json
import sys
from typing import Any, Dict

from ontology.graph import OntologyGraph
from ontology.schema import concept_from_dict
from ontology.snapshot_manager import SNAPSHOT_V1_PATH, SnapshotManager


def run_replay_validation() -> Dict[str, Any]:
    manager = SnapshotManager()
    snapshot = manager.load_snapshot(SNAPSHOT_V1_PATH)

    concepts = [concept_from_dict(row) for row in snapshot["concepts"]]
    OntologyGraph(concepts)

    rebuilt_hash = manager.hash_payload(snapshot)
    stored_hash = snapshot["snapshot_hash"]
    is_identical = rebuilt_hash == stored_hash

    return {
        "snapshot_path": str(SNAPSHOT_V1_PATH),
        "snapshot_version": snapshot["snapshot_version"],
        "stored_hash": stored_hash,
        "rebuilt_hash": rebuilt_hash,
        "replay_passed": is_identical,
    }


if __name__ == "__main__":
    report = run_replay_validation()
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["replay_passed"]:
        raise SystemExit(1)
    raise SystemExit(0)
