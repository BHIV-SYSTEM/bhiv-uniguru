from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set


_SEED_PATH = Path(__file__).with_name("seed_entities.json")


def _tokens(text: str) -> Set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", str(text or "").lower())
        if len(token) > 2
    }


class CanonicalEntityResolver:
    """Deterministic canonical entity and synonym resolver for retrieval contracts."""

    def __init__(self, seed_path: Path | None = None) -> None:
        self.seed_path = seed_path or _SEED_PATH
        self.entities = self._load_entities()
        self.alias_index: Dict[str, Dict[str, Any]] = {}
        self.domain_index: Dict[str, List[str]] = {}
        for entity in self.entities:
            canonical = str(entity["canonical"])
            self.domain_index.setdefault(str(entity.get("domain") or "general"), []).append(canonical)
            for alias in [canonical, *entity.get("aliases", [])]:
                self.alias_index[self._normalize(alias)] = entity

    def _load_entities(self) -> List[Dict[str, Any]]:
        with self.seed_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list) or len(data) < 100:
            raise ValueError("Ontology seed must contain at least 100 canonical entities.")
        return data

    @staticmethod
    def _normalize(value: str) -> str:
        value = str(value or "").lower()
        value = re.sub(r"[^a-zA-Z0-9\u0900-\u097F]+", " ", value)
        return " ".join(value.split())

    def extract(self, text: str) -> List[Dict[str, Any]]:
        normalized_text = f" {self._normalize(text)} "
        matches: Dict[str, Dict[str, Any]] = {}
        for alias, entity in self.alias_index.items():
            if not alias:
                continue
            if f" {alias} " in normalized_text:
                canonical = str(entity["canonical"])
                current = matches.get(canonical)
                if current is None or len(alias) > len(str(current.get("matched_alias") or "")):
                    matches[canonical] = {
                        "canonical": canonical,
                        "matched_alias": alias,
                        "domain": entity.get("domain", "general"),
                        "entity_type": entity.get("type", "concept"),
                        "concepts": list(entity.get("concepts", [])),
                    }
        return sorted(matches.values(), key=lambda row: row["canonical"])

    def expand_terms(self, text: str) -> Set[str]:
        terms = _tokens(text)
        for entity in self.extract(text):
            canonical = str(entity["canonical"])
            terms.update(_tokens(canonical))
            terms.update(_tokens(" ".join(entity.get("concepts", []))))
            seed = self.alias_index.get(self._normalize(canonical))
            if seed:
                for alias in seed.get("aliases", []):
                    terms.update(_tokens(alias))
        return terms

    def resolve_domain(self, query: str, domain_hint: str | None = None) -> Dict[str, Any]:
        hinted = str(domain_hint or "").strip()
        entities = self.extract(query)
        if hinted:
            return {
                "domain": hinted.lower(),
                "method": "domain_hint",
                "entities": entities,
                "confidence": 1.0,
            }
        if not entities:
            return {
                "domain": "general",
                "method": "no_canonical_entity",
                "entities": [],
                "confidence": 0.0,
            }
        text_entities = [entity for entity in entities if entity.get("entity_type") in {"text", "text_group"}]
        if text_entities:
            primary = sorted(text_entities, key=lambda row: row["canonical"])[0]
            return {
                "domain": str(primary.get("domain") or "general"),
                "method": "canonical_text_entity",
                "entities": entities,
                "confidence": 1.0,
            }
        domain_counts: Dict[str, int] = {}
        for entity in entities:
            domain = str(entity.get("domain") or "general")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        domain = sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
        return {
            "domain": domain,
            "method": "canonical_entity_majority",
            "entities": entities,
            "confidence": round(domain_counts[domain] / len(entities), 4),
        }

    def semantic_scores(self, query: str, content: str, tags: List[str], source: str, domain: str) -> Dict[str, Any]:
        query_entities = self.extract(query)
        candidate_text = " ".join([content, " ".join(tags or []), source, domain])
        candidate_entities = self.extract(candidate_text)
        query_entity_names = {entity["canonical"] for entity in query_entities}
        candidate_entity_names = {entity["canonical"] for entity in candidate_entities}

        entity_overlap = (
            len(query_entity_names & candidate_entity_names) / len(query_entity_names)
            if query_entity_names
            else 0.0
        )

        query_terms = self.expand_terms(query)
        candidate_terms = self.expand_terms(candidate_text)
        concept_overlap = len(query_terms & candidate_terms) / len(query_terms) if query_terms else 0.0

        domain_resolution = self.resolve_domain(query)
        expected_domain = domain_resolution["domain"]
        candidate_domain = str(domain or "").lower()
        candidate_entity_domains = {str(entity.get("domain") or "general") for entity in candidate_entities}
        domain_consistency = 1.0
        if expected_domain != "general":
            domain_consistency = 1.0 if expected_domain == candidate_domain or expected_domain in candidate_entity_domains else 0.0

        required_query_entities = {
            entity["canonical"]
            for entity in query_entities
            if entity.get("entity_type") not in {"text", "text_group"}
        }
        missing_required_entities = sorted(required_query_entities - candidate_entity_names)

        query_terms_ordered = [term for term in query_terms if term in candidate_terms]
        content_lower = candidate_text.lower()
        positions = [content_lower.find(term.lower()) for term in query_terms_ordered if content_lower.find(term.lower()) >= 0]
        contextual_proximity = 0.0
        if len(positions) >= 2:
            spread = max(positions) - min(positions)
            contextual_proximity = 1.0 if spread <= 240 else max(0.0, 1.0 - (spread / 1600))
        elif positions:
            contextual_proximity = 0.5

        weighted = (
            0.35 * concept_overlap
            + 0.35 * entity_overlap
            + 0.2 * domain_consistency
            + 0.1 * contextual_proximity
        )
        return {
            "query_entities": query_entities,
            "candidate_entities": candidate_entities,
            "concept_overlap": round(concept_overlap, 4),
            "entity_overlap": round(entity_overlap, 4),
            "domain_consistency": round(domain_consistency, 4),
            "contextual_proximity": round(contextual_proximity, 4),
            "semantic_score": round(weighted, 4),
            "domain_resolution": domain_resolution,
            "missing_required_entities": missing_required_entities,
        }
