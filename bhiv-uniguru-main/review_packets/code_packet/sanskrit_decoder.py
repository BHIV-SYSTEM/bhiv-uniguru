"""Deterministic, provenance-aware Sanskrit civilizational knowledge decoder.

This module deliberately does not turn retrieved material into new prose.  The
small Sanskrit markdown documents are lexical/source records; the knowledge
layer retrieves the existing UniGuru Kosha and exposes the records, their
source lineage, and graph relations verbatim.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from memory.constitutional_semantic_memory import stable_hash
from ontology.sanskrit.evidence import EvidenceType
from ontology.sanskrit.provenance import Provenance
from ontology.sanskrit.registry import SanskritRegistry
from ontology.sanskrit.schema import SanskritConcept, sanskrit_concept_from_dict, sanskrit_concept_to_dict

DECODER_VERSION = "uniguru_civilizational_enrichment_v2"
REGISTRY_VERSION = "uniguru_sanskrit_knowledge_ecosystem_v2"
BACKEND_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = BACKEND_DIR / "knowledge" / "sanskrit"
KOSHA_DIR = BACKEND_DIR / "data" / "kosha"
STAGES = (("śabda", "shabda"), ("dhātu", "dhatu"), ("vyākaraṇa", "vyakarana"), ("nirukta", "nirukta"), ("bīja", "beeja"), ("tattva", "tattva"), ("śakti", "shakti"), ("functional_meaning", "functional_meaning"))
KNOWLEDGE_LAYERS = (
    "sanskrit", "shabda", "dhatu", "vyakarana", "nirukta", "beeja", "tattva", "shakti",
    "literal_meaning", "functional_meaning", "ontology", "cosmology", "psychology", "governance",
    "medicine", "engineering", "mathematics", "astronomy", "metallurgy", "ritual", "symbolism",
    "related_deities", "related_lokas", "related_koshas", "related_chakras", "related_yantras",
    "related_mantras", "related_vidyas", "related_shastras", "traditional_interpretations",
    "historical_evolution", "cross_references", "open_research_questions", "experimental_hypotheses",
)
_HEADERS = {
    "canonical name": "canonical_name", "sanskrit": "sanskrit", "transliteration": "transliteration",
    "śabda": "shabda", "sabda": "shabda", "dhātu": "dhatu", "dhatu": "dhatu",
    "vyākaraṇa": "vyakarana", "vyakarana": "vyakarana", "nirukta": "nirukta", "bīja": "beeja",
    "bija": "beeja", "tattva": "tattva", "śakti": "shakti", "shakti": "shakti",
    "literal meaning": "literal_meaning", "functional meaning": "functional_meaning",
    "ontology": "ontology", "cosmology": "cosmology", "psychology": "psychology",
    "governance": "governance", "medicine": "medicine", "engineering": "engineering",
    "mathematics": "mathematics", "astronomy": "astronomy", "metallurgy": "metallurgy",
    "ritual": "ritual", "symbolism": "symbolism",
    "related deities": "related_deities", "related lokas": "related_lokas",
    "related koshas": "related_koshas", "related chakras": "related_chakras",
    "related yantras": "related_yantras", "related mantras": "related_mantras",
    "related vidyās": "related_vidyas", "related vidyas": "related_vidyas",
    "related śāstras": "related_shastras", "related shastras": "related_shastras",
    "traditional interpretations": "traditional_interpretations",
    "historical evolution": "historical_evolution",
    "cross references": "related_concepts", "canonical sources": "sources",
    "open research questions": "open_research_questions",
    "experimental hypotheses": "experimental_hypotheses",
}


def _normal(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value or "").strip().casefold()
    deaccent = "".join(c for c in unicodedata.normalize("NFD", normalized) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", deaccent).strip()


def _section_map(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    matches = list(re.finditer(r"^##\s+(.+?)\s*$", text, flags=re.MULTILINE))
    for index, match in enumerate(matches):
        key = _HEADERS.get(_normal(match.group(1)))
        if key:
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[key] = text[match.end():end].strip()
    return sections


def _list(value: str) -> List[str]:
    return [line[2:].strip() for line in value.splitlines() if line.strip().startswith("- ")]


def _evidence_type(source: str) -> EvidenceType:
    token = _normal(source)
    if "gita" in token or "bhagavad" in token:
        return EvidenceType.BHAGAVAD_GITA
    if "upanishad" in token or "upanisad" in token or "taittiriya" in token or "katha" in token or "chandogya" in token or "kena" in token:
        return EvidenceType.UPANISHAD
    if "veda" in token or "rigveda" in token or "atharvaveda" in token or "samaveda" in token or "yajurveda" in token:
        return EvidenceType.VEDA
    if "sutra" in token or "brahma sutra" in token or "yoga sutra" in token or "sulbasutra" in token:
        return EvidenceType.PRIMARY_CANON
    if "panini" in token or "ashtadhyayi" in token:
        return EvidenceType.PANINI
    if "nirukta" in token or "yaska" in token:
        return EvidenceType.NIRUKTA
    if "bhasya" in token or "commentary" in token or "tika" in token or "sankara" in token or "ramanuja" in token or "abhinavagupta" in token:
        return EvidenceType.COMMENTARY
    return EvidenceType.TRADITION


def load_sanskar_registry() -> Tuple[SanskritRegistry, Dict[str, Dict[str, Any]]]:
    """Load lexical records only; enrichment is performed at decode time."""
    registry = SanskritRegistry()
    metadata: Dict[str, Dict[str, Any]] = {}
    for path in sorted(SOURCE_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        raw = path.read_text(encoding="utf-8")
        sections = _section_map(raw)
        required = ("canonical_name", "sanskrit", "transliteration", "shabda", "dhatu", "vyakarana", "nirukta", "functional_meaning")
        if any(not sections.get(field) for field in required):
            raise ValueError(f"Invalid Sanskrit lexical record: {path}")
        name = sections["canonical_name"].strip().lower()
        concept = sanskrit_concept_from_dict({
            "concept_id": "sanskar:sanskrit:" + name, "canonical_name": name,
            "sanskrit": sections["sanskrit"], "transliteration": sections["transliteration"],
            "shabda": sections["shabda"], "dhatu": sections["dhatu"], "vyakarana": sections["vyakarana"],
            "nirukta": sections["nirukta"], "beeja": None if sections.get("beeja", "").strip() in {"", "—"} else sections["beeja"],
            "tattva": sections.get("tattva") or None, "shakti": sections.get("shakti") or None,
            "functional_meaning": sections["functional_meaning"], "related_concepts": [item.lower() for item in _list(sections.get("related_concepts", ""))],
            "ontology_version": REGISTRY_VERSION, "semantic_version": DECODER_VERSION,
        })
        registry.register(concept)
        metadata[concept.concept_id] = {
            "path": str(path.relative_to(BACKEND_DIR).as_posix()), "sources": _list(sections.get("sources", "")),
            "content_hash": stable_hash(raw), "sections": sections,
        }
    return registry, metadata


def _resolve(query: str, registry: SanskritRegistry) -> Optional[SanskritConcept]:
    needle = _normal(query)
    matches = []
    for concept in registry.list_concepts():
        name = concept.canonical_name.lower()
        sanskrit = concept.sanskrit
        translit = concept.transliteration
        aliases = {
            _normal(name),
            _normal(sanskrit),
            _normal(translit),
            _normal(translit.replace("ṣ", "sh").replace("ā", "a").replace("ṛ", "r").replace("ī", "i").replace("ū", "u").replace("ṅ", "n").replace("ñ", "n")),
        }
        if name.endswith("s"):
            aliases.add(_normal(name[:-1]))
        else:
            aliases.add(_normal(name + "s"))
        if name == "prakrti":
            aliases.add("prakriti")
        if name == "samskara":
            aliases.add("samkara")
            aliases.add("sanskar")
        if needle in aliases:
            matches.append(concept)
    return matches[0] if len(matches) == 1 else None


def _lexical_provenance(concept: SanskritConcept, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    sources = metadata["sources"] or [metadata["path"]]
    return [{
        "source_id": stable_hash({"concept": concept.concept_id, "source": source})[:16],
        "evidence_type": _evidence_type(source).value,
        "provenance": Provenance(source_text=source).__dict__,
        "source_path": metadata["path"], "content_hash": metadata["content_hash"], "retrieval_system": "sanskrit_lexical_records",
    } for source in sources]


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\w'-]+", _normal(value)) if len(token) > 1}


def _kosha_records(concept: SanskritConcept) -> List[Dict[str, Any]]:
    """Retrieve local UniGuru Kosha records deterministically, never synthesize them."""
    query_terms = _tokens(" ".join((concept.canonical_name, concept.transliteration, concept.sanskrit)))
    records: List[Tuple[int, str, Dict[str, Any], str]] = []
    for path in sorted(KOSHA_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows: Iterable[Dict[str, Any]] = raw.get("entries", []) if isinstance(raw, dict) and "entries" in raw else [raw]
        for row in rows:
            if not isinstance(row, dict):
                continue
            searchable = " ".join(str(row.get(key, "")) for key in ("content", "clean_content", "domain", "source")) + " " + " ".join(map(str, row.get("tags", [])))
            overlap = query_terms & _tokens(searchable)
            if overlap:
                records.append((len(overlap), str(row.get("knowledge_id", path.stem)), row, str(path.relative_to(BACKEND_DIR).as_posix())))
    records.sort(key=lambda item: (-item[0], item[1], item[3]))
    result = []
    seen = set()
    for score, knowledge_id, row, relative_path in records:
        if knowledge_id in seen:
            continue
        seen.add(knowledge_id)
        content = str(row.get("clean_content") or row.get("content") or "").strip()
        source = str(row.get("source") or relative_path)
        result.append({
            "knowledge_id": knowledge_id, "content": content, "source": source, "domain": row.get("domain"), "tags": row.get("tags", []),
            "match_terms": sorted(query_terms & _tokens(" ".join((content, source, " ".join(map(str, row.get("tags", []))))))),
            "provenance": {"source_path": relative_path, "content_hash": stable_hash(row), "retrieval_system": "uniguru_kosha", "evidence_type": _evidence_type(source).value},
        })
    return result


def _claim(value: Any, provenance: List[Dict[str, Any]], classification: str = "SOURCE_SCOPED") -> Dict[str, Any]:
    return {"value": value, "classification": classification, "provenance": provenance}


# Map from KNOWLEDGE_LAYERS field names to _HEADERS parsed section keys
_LAYER_TO_SECTION: Dict[str, str] = {
    "literal_meaning": "literal_meaning", "ontology": "ontology", "cosmology": "cosmology",
    "psychology": "psychology", "governance": "governance", "medicine": "medicine",
    "engineering": "engineering", "mathematics": "mathematics", "astronomy": "astronomy",
    "metallurgy": "metallurgy", "ritual": "ritual", "symbolism": "symbolism",
    "related_deities": "related_deities", "related_lokas": "related_lokas",
    "related_koshas": "related_koshas", "related_chakras": "related_chakras",
    "related_yantras": "related_yantras", "related_mantras": "related_mantras",
    "related_vidyas": "related_vidyas", "related_shastras": "related_shastras",
    "traditional_interpretations": "traditional_interpretations",
    "historical_evolution": "historical_evolution",
    "open_research_questions": "open_research_questions",
    "experimental_hypotheses": "experimental_hypotheses",
}


def _knowledge_object(concept: SanskritConcept, metadata: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    lexical = _lexical_provenance(concept, metadata)
    canonical = sanskrit_concept_to_dict(concept)
    sections = metadata.get("sections", {})
    layers: Dict[str, Dict[str, Any]] = {}
    lexical_fields = {"sanskrit", "shabda", "dhatu", "vyakarana", "nirukta", "beeja", "tattva", "shakti", "functional_meaning"}
    for field in KNOWLEDGE_LAYERS:
        if field in lexical_fields and canonical.get(field):
            layers[field] = {"status": "EVIDENCE_BACKED", "claims": [_claim(canonical[field], lexical)]}
        elif field == "cross_references":
            layers[field] = {"status": "EVIDENCE_BACKED" if concept.related_concepts else "NO_RETRIEVED_EVIDENCE", "claims": [_claim(sorted(concept.related_concepts), lexical)] if concept.related_concepts else []}
        elif field == "experimental_hypotheses":
            section_text = sections.get(_LAYER_TO_SECTION.get(field, ""), "")
            if section_text and "[EXPERIMENTAL" in section_text:
                layers[field] = {"status": "EXPLICITLY_MARKED_EXPERIMENTAL", "claims": [_claim(section_text.strip(), lexical, "EXPERIMENTAL")], "policy": "Marked EXPERIMENTAL in source document."}
            else:
                layers[field] = {"status": "NOT_ASSERTED", "claims": [], "policy": "No experimental hypothesis is emitted without an explicitly classified source."}
        elif field in _LAYER_TO_SECTION:
            section_key = _LAYER_TO_SECTION[field]
            section_text = sections.get(section_key, "")
            if section_text and section_text.strip():
                layers[field] = {"status": "EVIDENCE_BACKED", "claims": [_claim(section_text.strip(), lexical)]}
            else:
                layers[field] = {"status": "NO_RETRIEVED_EVIDENCE", "claims": []}
        else:
            layers[field] = {"status": "NO_RETRIEVED_EVIDENCE", "claims": []}
    # Count how many layers have evidence
    backed = sum(1 for v in layers.values() if v["status"] == "EVIDENCE_BACKED")
    return {
        "schema_version": "UNIGURU_CIVILIZATIONAL_KNOWLEDGE_OBJECT_V2", "concept_id": concept.concept_id,
        "canonical_name": concept.canonical_name, "lexical_record": canonical, "layers": layers,
        "retrieved_evidence": records,
        "retrieval": {"system": "uniguru_kosha", "strategy": "deterministic_token_overlap", "records_found": len(records)},
        "coverage": {"total_layers": len(KNOWLEDGE_LAYERS), "evidence_backed_layers": backed, "coverage_pct": round(backed / len(KNOWLEDGE_LAYERS) * 100, 1)},
    }


def _graph(concept: SanskritConcept, registry: SanskritRegistry, metadata: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    nodes = [{"id": concept.concept_id, "type": "sanskrit_concept", "label": concept.canonical_name, "address": metadata["path"], "provenance": metadata["path"]}]
    edges: List[Dict[str, Any]] = []
    known = {row.concept_id for row in registry.list_concepts()}
    for related in sorted(concept.related_concepts):
        target = "sanskar:sanskrit:" + related
        if target in known:
            nodes.append({"id": target, "type": "sanskrit_concept", "label": related, "address": "backend/knowledge/sanskrit/" + related + ".md"})
            edges.append({"from": concept.concept_id, "to": target, "type": "canonical_cross_reference", "evidence_type": EvidenceType.DERIVED.value, "provenance": metadata["path"]})
    # Add tradition-level edges from related sections
    sections = metadata.get("sections", {})
    for shastra in _list(sections.get("related_shastras", "")):
        shastra_id = "shastra:" + stable_hash(shastra)[:12]
        nodes.append({"id": shastra_id, "type": "shastra", "label": shastra, "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": shastra_id, "type": "referenced_in_shastra", "evidence_type": EvidenceType.PRIMARY_CANON.value, "provenance": metadata["path"]})
    for deity in _list(sections.get("related_deities", "")):
        deity_id = "deity:" + _normal(deity.split("(")[0]).replace(" ", "_")
        nodes.append({"id": deity_id, "type": "deity", "label": deity.split("(")[0].strip(), "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": deity_id, "type": "related_deity", "evidence_type": EvidenceType.TRADITION.value, "provenance": metadata["path"]})
    for loka in _list(sections.get("related_lokas", "")):
        loka_id = "loka:" + _normal(loka.split("(")[0]).replace(" ", "_")
        nodes.append({"id": loka_id, "type": "loka", "label": loka.split("(")[0].strip(), "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": loka_id, "type": "related_loka", "evidence_type": EvidenceType.TRADITION.value, "provenance": metadata["path"]})
    for kosha in _list(sections.get("related_koshas", "")):
        kosha_id = "kosha_ref:" + _normal(kosha.split("(")[0]).replace(" ", "_")
        nodes.append({"id": kosha_id, "type": "kosha", "label": kosha.split("(")[0].strip(), "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": kosha_id, "type": "related_kosha", "evidence_type": EvidenceType.TRADITION.value, "provenance": metadata["path"]})
    for chakra in _list(sections.get("related_chakras", "")):
        chakra_id = "chakra_ref:" + _normal(chakra.split("(")[0]).replace(" ", "_")
        nodes.append({"id": chakra_id, "type": "chakra", "label": chakra.split("(")[0].strip(), "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": chakra_id, "type": "related_chakra", "evidence_type": EvidenceType.TRADITION.value, "provenance": metadata["path"]})
    for yantra in _list(sections.get("related_yantras", "")):
        yantra_id = "yantra:" + _normal(yantra.split("(")[0]).replace(" ", "_")
        nodes.append({"id": yantra_id, "type": "yantra", "label": yantra.split("(")[0].strip(), "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": yantra_id, "type": "related_yantra", "evidence_type": EvidenceType.TRADITION.value, "provenance": metadata["path"]})
    for vidya in _list(sections.get("related_vidyas", "")):
        vidya_id = "vidya:" + _normal(vidya.split("(")[0]).replace(" ", "_")
        nodes.append({"id": vidya_id, "type": "vidya", "label": vidya.split("(")[0].strip(), "provenance": metadata["path"]})
        edges.append({"from": concept.concept_id, "to": vidya_id, "type": "related_vidya", "evidence_type": EvidenceType.TRADITION.value, "provenance": metadata["path"]})
    for record in records:
        record_id = "kosha:" + record["knowledge_id"]
        nodes.append({"id": record_id, "type": "knowledge_record", "label": record["knowledge_id"], "address": record["provenance"]["source_path"], "provenance": record["provenance"]})
        edges.append({"from": concept.concept_id, "to": record_id, "type": "retrieved_evidence", "match_terms": record["match_terms"], "evidence_type": record["provenance"]["evidence_type"], "provenance": record["provenance"]})
    # Deduplicate nodes by id
    seen_nodes: Dict[str, Any] = {}
    for node in nodes:
        seen_nodes[node["id"]] = node
    nodes = list(seen_nodes.values())
    node_ids = {node["id"] for node in nodes}
    if any(edge["from"] not in node_ids or edge["to"] not in node_ids for edge in edges):
        raise ValueError("Civilizational graph consistency validation failed")
    return {"graph_id": "UNIGURU_CIVILIZATIONAL_KNOWLEDGE_GRAPH_V2", "schema_version": "2.0.0", "nodes": nodes, "edges": edges, "metadata": {"adapter": "uniguru_civilizational_enrichment_v2", "consistency_valid": True, "orphaned_nodes": [], "source_snapshot_hash": metadata["content_hash"], "node_count": len(nodes), "edge_count": len(edges)}}


def decode_sanskrit_concept(query: str) -> Dict[str, Any]:
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    registry, metadata_by_id = load_sanskar_registry()
    concept = _resolve(query, registry)
    if concept is None:
        result = {"canonical_concept": None, "civilizational_knowledge": None, "pipeline": [], "cross_text_synthesis": {"status": "NO_CANONICAL_EVIDENCE", "claims": []}, "knowledge_graph": {"nodes": [], "edges": [], "metadata": {"consistency_valid": True, "orphaned_nodes": []}}, "provenance": {"registry_version": REGISTRY_VERSION, "lineage": [], "replay_safe": True}, "governed_response": {"evidence_classification": {"classification": "UNVERIFIED", "evidence_types": [], "notes": "No source-backed Sanskrit lexical record matched this query."}, "research_classification": "UNVERIFIED", "governance_state": "no_inference"}}
        result["result_hash"] = stable_hash(result)
        return result
    metadata = metadata_by_id[concept.concept_id]
    records = _kosha_records(concept)
    lexical = _lexical_provenance(concept, metadata)
    canonical = sanskrit_concept_to_dict(concept)
    pipeline = [{"stage": stage, "schema_field": field, "value": canonical[field], "evidence": lexical, "classification": [item["evidence_type"] for item in lexical], "lineage": {"concept_id": concept.concept_id, "source_path": metadata["path"], "content_hash": metadata["content_hash"]}} for stage, field in STAGES]
    graph = _graph(concept, registry, metadata, records)
    evidence_types = sorted({item["evidence_type"] for item in lexical} | {item["provenance"]["evidence_type"] for item in records})
    result = {"canonical_concept": canonical, "civilizational_knowledge": _knowledge_object(concept, metadata, records), "pipeline": pipeline, "cross_references": [{"target": related, "claim": f"{concept.canonical_name} is cross-referenced with {related} by the lexical record.", "classification": EvidenceType.DERIVED.value, "source_path": metadata["path"], "status": "DERIVED_FROM_CANONICAL_CROSS_REFERENCE"} for related in sorted(concept.related_concepts)], "cross_text_synthesis": {"status": "RETRIEVED_SOURCE_RECORDS_ONLY", "canonical_claims": [{"claim": concept.functional_meaning, "classification": [item["evidence_type"] for item in lexical], "source_path": metadata["path"]}], "retrieved_records": records, "conflicts": [], "uncertainty": "Retrieved records are preserved as source-scoped evidence; the decoder does not merge them into an untraceable summary."}, "knowledge_graph": graph, "functional_meaning": {"summary": concept.functional_meaning, "classification": "SOURCE_SCOPED_CANONICAL_TEXT"}, "provenance": {"registry_version": REGISTRY_VERSION, "schema_version": DECODER_VERSION, "source_documents": lexical, "retrieved_records": [{"knowledge_id": item["knowledge_id"], "provenance": item["provenance"]} for item in records], "lineage": {"concept_id": concept.concept_id, "source_path": metadata["path"], "content_hash": metadata["content_hash"]}, "replay_safe": True}, "governed_response": {"evidence_classification": {"classification": "SOURCE_SCOPED", "evidence_types": evidence_types, "notes": "Claims are either lexical source fields or verbatim retrieved UniGuru records; no generative canonical summary is used."}, "research_classification": "civilizational_knowledge", "governance_state": "read_only_observation"}}
    result["result_hash"] = stable_hash(result)
    return result
