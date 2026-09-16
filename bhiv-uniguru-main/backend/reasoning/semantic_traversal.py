from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


SEED_PATH = Path(__file__).resolve().parents[1] / "ontology" / "seed_entities.json"


def _node_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


class SemanticTraversalEngine:
    """Deterministic multi-hop traversal over canonical ontology seed entities."""

    def __init__(self, seed_path: Optional[Path] = None) -> None:
        self.seed_path = seed_path or SEED_PATH
        self.entities = json.loads(self.seed_path.read_text(encoding="utf-8"))
        self.alias_to_canonical: Dict[str, str] = {}
        self.adj: Dict[str, List[Dict[str, str]]] = {}
        self._build_graph()

    def _add_edge(self, source: str, target: str, edge_type: str) -> None:
        source_key = _node_key(source)
        target_key = _node_key(target)
        if not source_key or not target_key or source_key == target_key:
            return
        self.adj.setdefault(source_key, [])
        edge = {"target": target_key, "relationship": edge_type}
        if edge not in self.adj[source_key]:
            self.adj[source_key].append(edge)

    def _build_graph(self) -> None:
        canonicals: Set[str] = set()
        for row in self.entities:
            canonical = str(row.get("canonical") or "")
            canonical_key = _node_key(canonical)
            canonicals.add(canonical_key)
            self.alias_to_canonical[canonical_key] = canonical_key
            for alias in row.get("aliases") or []:
                self.alias_to_canonical[_node_key(alias)] = canonical_key
            for concept in row.get("concepts") or []:
                self._add_edge(canonical, concept, "has_concept")
                self._add_edge(concept, canonical, "concept_of")

        for left in sorted(canonicals):
            for right in sorted(canonicals):
                if left == right:
                    continue
                if left in right or right in left:
                    self._add_edge(left, right, "lexical_containment")

        for row in self.entities:
            canonical = _node_key(str(row.get("canonical") or ""))
            concepts = [_node_key(concept) for concept in row.get("concepts") or []]
            for concept in concepts:
                if concept in canonicals:
                    self._add_edge(concept, canonical, "canonical_concept_bridge")

        for node in self.adj:
            self.adj[node] = sorted(self.adj[node], key=lambda item: (item["target"], item["relationship"]))

    def resolve_nodes(self, text: str) -> List[str]:
        haystack = _node_key(text)
        matches = []
        for alias, canonical in self.alias_to_canonical.items():
            if alias and re.search(rf"\b{re.escape(alias)}\b", haystack):
                matches.append(canonical)
        return sorted(set(matches))

    def traverse(self, query: str, target: Optional[str] = None, max_hops: int = 5) -> Dict[str, Any]:
        starts = self.resolve_nodes(query)
        target_nodes = self.resolve_nodes(target or query)
        if target:
            target_nodes = self.resolve_nodes(target)
        if not target_nodes and "governance" in _node_key(query):
            target_nodes = ["governance"]
        if not starts:
            return {"paths": [], "start_nodes": [], "target_nodes": target_nodes, "max_hops": max_hops}

        paths = []
        for start in starts:
            queue = deque([(start, [{"node": start, "relationship": "start"}])])
            seen = {start}
            while queue:
                current, path = queue.popleft()
                if current in target_nodes and len(path) > 1:
                    paths.append(path)
                    break
                if len(path) > max_hops + 1:
                    continue
                for edge in self.adj.get(current, []):
                    next_node = edge["target"]
                    if next_node in seen:
                        continue
                    seen.add(next_node)
                    queue.append((next_node, path + [{"node": next_node, "relationship": edge["relationship"]}]))

        return {
            "paths": paths,
            "start_nodes": starts,
            "target_nodes": target_nodes,
            "max_hops": max_hops,
            "deterministic": True,
            "source": str(self.seed_path.as_posix()),
        }
