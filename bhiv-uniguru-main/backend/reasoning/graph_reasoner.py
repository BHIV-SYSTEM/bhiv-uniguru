from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Dict, List, Optional

from ontology.snapshot_manager import SNAPSHOT_V1_PATH, SnapshotManager


class GraphReasoner:
    """Deterministic BFS reasoner over ontology concepts."""

    def __init__(self, snapshot_path: Optional[Path] = None):
        self.snapshot_manager = SnapshotManager()
        self.snapshot_path = snapshot_path or SNAPSHOT_V1_PATH
        self.snapshot = self.snapshot_manager.load_snapshot(self.snapshot_path)
        self.concepts = list(self.snapshot.get("concepts", []))
        self.by_id = {row["concept_id"]: row for row in self.concepts}
        self.by_name = {str(row["canonical_name"]).lower(): row["concept_id"] for row in self.concepts}
        self.adj: Dict[str, List[str]] = {}
        self._build_adjacency()

    def _build_adjacency(self) -> None:
        for row in self.concepts:
            concept_id = row["concept_id"]
            self.adj.setdefault(concept_id, [])
            parent_id = row.get("parent_id")
            if parent_id is None:
                continue
            self.adj.setdefault(parent_id, [])
            self.adj[parent_id].append(concept_id)
            self.adj[concept_id].append(parent_id)

        for concept_id in self.adj:
            self.adj[concept_id] = sorted(set(self.adj[concept_id]))

    def _root_id(self) -> str:
        roots = sorted(row["concept_id"] for row in self.concepts if row.get("parent_id") is None)
        if not roots:
            raise ValueError("No root concept found in ontology graph.")
        return roots[0]

    def shortest_path(self, start_concept_id: str, end_concept_id: str) -> List[Dict[str, object]]:
        if start_concept_id not in self.by_id or end_concept_id not in self.by_id:
            return []

        queue = deque([start_concept_id])
        prev: Dict[str, Optional[str]] = {start_concept_id: None}

        while queue:
            current = queue.popleft()
            if current == end_concept_id:
                break
            for neighbor in self.adj.get(current, []):
                if neighbor in prev:
                    continue
                prev[neighbor] = current
                queue.append(neighbor)

        if end_concept_id not in prev:
            return []

        chain_ids: List[str] = []
        cursor: Optional[str] = end_concept_id
        while cursor is not None:
            chain_ids.append(cursor)
            cursor = prev[cursor]
        chain_ids.reverse()

        return [
            {
                "concept_id": concept_id,
                "canonical_name": self.by_id[concept_id]["canonical_name"],
                "truth_level": self.by_id[concept_id]["truth_level"],
                "domain": self.by_id[concept_id]["domain"],
            }
            for concept_id in chain_ids
        ]

    def reasoning_path_from_root(self, concept_id: str) -> List[Dict[str, object]]:
        return self.shortest_path(self._root_id(), concept_id)

    def reasoning_path_from_domain_root(self, concept_id: str, domain: str) -> List[Dict[str, object]]:
        expected_root_name = f"{domain.strip().title()} Root"
        if domain.strip().lower() == "swaminarayan":
            expected_root_name = "Swaminarayan Root"
        domain_root_id = self.by_name.get(expected_root_name.lower())
        if not domain_root_id:
            return self.reasoning_path_from_root(concept_id)
        return self.shortest_path(domain_root_id, concept_id)
