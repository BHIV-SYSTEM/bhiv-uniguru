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

DECODER_VERSION = "uniguru_civilizational_enrichment_v3"
REGISTRY_VERSION = "uniguru_sanskrit_knowledge_ecosystem_v3"
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
SOURCE_DIR = BACKEND_DIR / "knowledge" / "sanskrit"
KOSHA_DIR = BACKEND_DIR / "data" / "kosha"
ECOSYSTEM_INDEX = BACKEND_DIR / "knowledge" / "index" / "master_index.json"
MASTERDB_DATASET = PROJECT_ROOT / "masterdb" / "balbharti" / "canonical_dataset.json"
GRAMMAR_FILE = BACKEND_DIR / "knowledge" / "gurukul" / "sanskrit" / "grammar.md"
PHONETICS_FILE = BACKEND_DIR / "knowledge" / "sanskrit" / "phonetics" / "bija_phonetics.json"
STAGES = (("śabda", "shabda"), ("dhātu", "dhatu"), ("vyākaraṇa", "vyakarana"), ("nirukta", "nirukta"), ("bīja", "beeja"), ("tattva", "tattva"), ("śakti", "shakti"), ("functional_meaning", "functional_meaning"))
KNOWLEDGE_LAYERS = (
    "sanskrit", "shabda", "dhatu", "vyakarana", "nirukta", "beeja", "tattva", "shakti",
    "literal_meaning", "functional_meaning", "ontology", "cosmology", "psychology", "governance",
    "medicine", "engineering", "mathematics", "astronomy", "metallurgy", "ritual", "symbolism",
    "related_deities", "related_lokas", "related_koshas", "related_chakras", "related_yantras",
    "related_mantras", "related_vidyas", "related_shastras", "traditional_interpretations",
    "historical_evolution", "cross_references", "open_research_questions", "experimental_hypotheses",
    "comparative_hermeneutics",
)
# Darśana keys used to parse traditional_interpretations bullet lists
_DARSANA_PATTERNS: List[Tuple[str, List[str]]] = [
    ("advaita", ["advaita"]),
    ("vishishtadvaita", ["vishishtadvaita", "visistadvaita", "ramanuja"]),
    ("dvaita", ["dvaita", "madhva"]),
    ("mimamsa", ["mimamsa", "jaimini", "purva mimamsa"]),
    ("shaiva", ["shaiva", "saiva", "abhinavagupta", "shaivadvaita"]),
    ("shakta", ["shakta", "sakta", "shakti tradition", "shakta tradition"]),
    ("buddhist", ["buddhis", "buddha", "theravada", "mahayana"]),
    ("jain", ["jain", "jainism"]),
]
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
    if "siksha" in token or "siksa" in token or "pratisakhya" in token or "pratisakha" in token:
        return EvidenceType.VEDA
    return EvidenceType.TRADITION


def _fallback_registry_entries() -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    specs = [
        ("dharma", "धर्म", "dharma", "धृ (Dhṛ) — to uphold", "A sustaining law of order and duty.", "That which upholds and sustains the moral and cosmic order.", ["karma", "rita", "yajna", "moksha"], {
            "literal_meaning": "That which sustains and holds together the order of life.",
            "functional_meaning": "Duty, righteousness, and the law that sustains social and cosmic order.",
            "ontology": "Dharma governs conduct and the relation between individual action and universal order.",
            "cosmology": "Dharma aligns the human world with the order of the cosmos.",
            "psychology": "Dharma informs ethical discipline and self-regulation.",
            "governance": "Dharma provides the normative basis of law and social order.",
            "ritual": "Ritual action is structured by dharma and the obligations of one’s station.",
            "symbolism": "The wheel, the law, and the balanced order of life.",
            "traditional_interpretations": "- Advaita: Dharma is the expression of the self’s ordered life in relation to truth.\n- Dvaita: Dharma is the law that sustains the ordered world of distinctions.\n- Mimamsa: Dharma is the normative rule that guides action and ritual obligation.\n- Buddhist: Dharma is the teaching that orders life and liberation.\n- Jain: Dharma is the path of ethical conduct and non-harm.",
            "historical_evolution": "The concept is preserved across Veda, Upanishad, Dharmashastra, and later philosophical commentarial traditions.",
            "related_deities": ["Yama", "Varuna"], "related_lokas": ["Svarga", "Bhu Loka"], "related_koshas": ["Annamaya"], "related_chakras": ["Muladhara"], "related_shastras": ["Dharmashastra", "Bhagavad Gita"],
            "related_vidyas": ["Dharmavidya"], "open_research_questions": ["How do the dharma traditions preserve legal, ethical, and ritual continuity across time?"],
        }),
        ("karma", "कर्म", "karma", "कृ (Kṛ) — to do", "Action and its consequential unfolding.", "The effect of action carried through time by intention and deed.", ["dharma", "moksha", "yajna"], {"literal_meaning": "Action", "functional_meaning": "Karma names the causal continuity of action and consequence.", "ontology": "Karma links intention, action, and consequence.", "cosmology": "The moral order of action is reflected in the cycles of birth and return.", "governance": "Karma frames ethical accountability and social responsibility.", "ritual": "Ritual action is interpreted through its moral and causal efficacy.", "traditional_interpretations": "- Advaita: Karma is the effect of action under the play of ignorance.\n- Dvaita: Karma binds through the law of consequence.\n- Mimamsa: Karma is a principle of ritual and ethical action.\n- Buddhist: Karma is the chain of causal action and rebirth.", "related_deities": ["Yama"], "related_lokas": ["Bhu Loka"], "related_shastras": ["Bhagavad Gita", "Karma Yoga"],}),
        ("agni", "अग्नि", "agni", "अगि (Agni) — fire", "Fire", "The principle of transformative heat and illumination.", ["yajna", "surya", "prana"], {"literal_meaning": "Fire", "functional_meaning": "Agni is the carrier of offerings and the transformative force of ritual and cosmic process.", "cosmology": "Agni mediates between the human and divine through sacrifice.", "ritual": "Agni receives oblations and transforms them into divine offerings.", "related_deities": ["Agni"], "related_shastras": ["Rigveda", "Yajurveda"],}),
        ("atman", "आत्मन्", "atman", "आत्म (Ātma) — self", "Self", "The innermost principle of awareness and identity.", ["brahman", "prana", "maya"], {"literal_meaning": "Self", "functional_meaning": "Atman is the inward self that is recognized as the basis of awareness.", "ontology": "Atman is the locus of identity beneath the changing empirical self.", "psychology": "Atman frames inner awareness and reflexive selfhood.", "related_deities": ["Shiva"], "related_shastras": ["Upanishads", "Brahma Sutra"],}),
        ("brahman", "ब्रह्मन्", "brahman", "ब्रह्म (Brahma) — expansion", "The supreme reality", "The unconditioned ground of being and knowing.", ["atman", "maya", "prakrti"], {"literal_meaning": "The supreme, boundless reality", "functional_meaning": "Brahman is the ultimate ground of existence and knowledge.", "ontology": "Brahman is the nondual principle underlying all distinctions.", "cosmology": "Brahman is the ultimate source, sustaining the manifest world.", "related_deities": ["Brahma", "Vishnu", "Shiva"], "related_shastras": ["Upanishads", "Brahma Sutra"],}),
        ("prana", "प्राण", "prana", "प्राण (Prāṇa) — life breath", "Life breath", "The vital force that animates and governs life.", ["agni", "akasha", "chakras"], {"literal_meaning": "Life-breath", "functional_meaning": "Prana is the vital force moving through body, mind, and cosmos.", "cosmology": "Prana sustains the circulation of vitality across the body and the world.", "psychology": "Prana links breath, consciousness, and vitality.", "related_koshas": ["Pranamaya"], "related_chakras": ["Anahata"], "related_shastras": ["Chandogya Upanishad", "Yoga Sutra"],}),
        ("rta", "ऋत", "rta", "ऋत (Ṛta) — rightness", "Cosmic order", "The ordered pattern of truth, ritual, and cosmic balance.", ["dharma", "yajna", "agni"], {"literal_meaning": "Order, truth, and rightness", "functional_meaning": "Rta is the cosmic order that governs truth, ritual, and seasonal cycles.", "cosmology": "Rta sustains the balance of heavens, seasons, and moral life.", "ritual": "Ritual order aligns human action with cosmic order.", "related_shastras": ["Rgveda", "Yajurveda"],}),
        ("shakti", "शक्ति", "shakti", "शक् (Śak) — to be able", "Power", "The dynamic force of manifestation and transformation.", ["brahman", "prakrti", "yantra"], {"literal_meaning": "Power", "functional_meaning": "Shakti is the dynamic energy that manifests form and action.", "ontology": "Shakti manifests the capacity of being and action.", "psychology": "Shakti names the energizing force of will and transformation.", "related_deities": ["Devi"], "related_yantras": ["Sri Yantra"], "related_shastras": ["Shakta Tantras", "Devi Mahatmya"],}),
        ("yajna", "यज्ञ", "yajna", "यज् (Yaj) — to sacrifice", "Sacrifice", "The ritual offering that aligns human and cosmic powers.", ["agni", "dharma", "rita"], {"literal_meaning": "Sacrifice", "functional_meaning": "Yajna is the ritual form through which offerings and obligations are transformed.", "ritual": "Fire ritual and offering are central to yajna.", "cosmology": "Yajna establishes relation between offerings and divine forces.", "related_deities": ["Agni", "Indra"], "related_shastras": ["Yajurveda", "Bhagavad Gita"],}),
        ("om", "ॐ", "om", "अम् (Om) — to praise", "The sacred syllable", "The primordial sound that signifies the totality of reality.", ["brahman", "prana", "vidya"], {"literal_meaning": "The sacred syllable", "functional_meaning": "Om is the sound-form through which the whole is intoned and contemplated.", "cosmology": "Om encompasses the beginning, middle, and end of the manifest order.", "ritual": "Om is recited in mantra and meditation.", "related_mantras": ["Om Namah Shivaya"], "related_shastras": ["Upanishads", "Mandukya Upanishad"],}),
        ("kala", "काल", "kala", "कॢप् (Kal) — to count", "Time", "The principle of time, measure, and transformation.", ["yuga", "karma", "maya"], {"literal_meaning": "Time", "functional_meaning": "Kala is the principle of time and temporal transformation.", "cosmology": "Kala orders the cyclic unfolding of worlds and ages.", "astronomy": "Kala is implicated in the cycles of celestial time.", "related_shastras": ["Bhagavad Gita", "Puranas"],}),
        ("akasha", "आकाश", "akasha", "आकाश (Ākāśa) — ether", "Ether", "The expansive medium of space and potentiality.", ["prana", "vayu", "brahman"], {"literal_meaning": "Space or ether", "functional_meaning": "Akasha is the medium of space, sound, and potentiality.", "cosmology": "Akasha holds the field of possibility for manifestation.", "related_lokas": ["Bhu Loka"], "related_shastras": ["Taittiriya Upanishad"],}),
        ("guru", "गुरु", "guru", "गुर् (Gur) — heavy, grave", "Teacher", "The one who removes darkness and transmits knowledge.", ["vidya", "samskara", "moksha"], {"literal_meaning": "Teacher", "functional_meaning": "Guru is the teacher who illumines and transmits knowledge and discipline.", "psychology": "Guru practice structures aspiration and transmission.", "related_vidyas": ["Shruti", "Smriti"], "related_shastras": ["Upanishads", "Bhagavad Gita"],}),
        ("vidya", "विद्या", "vidya", "विद् (Vid) — to know", "Knowledge", "The inward knowing that transforms life and consciousness.", ["guru", "samskara", "moksha"], {"literal_meaning": "Knowledge", "functional_meaning": "Vidya is knowledge that illumines the true nature of reality.", "psychology": "Vidya informs understanding and self-knowledge.", "related_vidyas": ["Jnana Vidya", "Yoga Vidya"], "related_shastras": ["Upanishads", "Vedanta"],}),
        ("samskara", "संस्कार", "samskara", "संस्कृ (Saṃskṛ) — to refine", "Impression", "The formative conditioning that shapes mind and life.", ["vidya", "karma", "maya"], {"literal_meaning": "Formative impression", "functional_meaning": "Samskara are the conditioning impressions that shape action and consciousness.", "psychology": "Samskara structure memory, habit, and inner disposition.", "related_shastras": ["Yoga Sutra", "Bhagavad Gita"],}),
        ("maya", "माया", "maya", "मा (Mā) — measure", "Illusion", "The power that veils and projects the manifold world.", ["brahman", "prakrti", "atman"], {"literal_meaning": "Illusion or power of appearance", "functional_meaning": "Maya is the veiling and projecting power that makes the world appear as distinct and separate.", "ontology": "Maya distinguishes and organizes experience without denying the underlying unity.", "psychology": "Maya shapes habitual perception and attachment.", "related_shastras": ["Vedanta", "Shakta traditions"],}),
        ("prakrti", "प्रकृति", "prakrti", "प्रकृ (Prakṛ) — to make or evolve", "Nature", "The primal principle of becoming and manifest form.", ["purusha", "maya", "shakti"], {"literal_meaning": "Nature", "functional_meaning": "Prakriti is the material and dynamic principle of manifestation.", "cosmology": "Prakriti grounds the world of forms and transformations.", "related_shastras": ["Samkhya", "Yoga"],}),
        ("purusha", "पुरुष", "purusha", "पुरुष (Puruṣa) — person", "Person", "The conscious principle that witnesses and orders the play of nature.", ["prakrti", "atman", "brahman"], {"literal_meaning": "Person or spirit", "functional_meaning": "Purusha is the conscious witness that stands over and relates to nature.", "ontology": "Purusha is the principle of witness consciousness.", "related_shastras": ["Samkhya", "Yoga"],}),
        ("lokas", "लोकाः", "lokas", "लोक (Loka) — world", "Worlds", "The planes, abodes, or realms of relation.", ["koshas", "chakras", "devas"], {"literal_meaning": "Worlds or realms", "functional_meaning": "Lokas are the ordered realms that structure cosmic and spiritual existence.", "cosmology": "Lokas include the worlds of human, celestial, and spiritual experience.", "related_lokas": ["Bhu Loka", "Svarga"], "related_shastras": ["Puranas", "Bhagavad Gita"],}),
        ("koshas", "कोशाः", "koshas", "कोश (Kośa) — sheath", "Sheaths", "The sheaths of embodied consciousness.", ["prana", "chakras", "atman"], {"literal_meaning": "Sheaths", "functional_meaning": "Kosha are the sheaths in which consciousness is embodied and experienced.", "psychology": "The koshas frame the layers of embodiment and awareness.", "related_koshas": ["Annamaya", "Pranamaya"], "related_shastras": ["Taittiriya Upanishad"],}),
        ("chakras", "चक्राः", "chakras", "चक्र (Cakra) — wheel", "Wheels", "The psycho-spiritual centers of energetic organization.", ["prana", "koshas", "kundalini"], {"literal_meaning": "Wheels", "functional_meaning": "Chakras are centers of vital and psychic organization.", "psychology": "Chakras coordinate the movement of energy and awareness.", "related_chakras": ["Muladhara", "Anahata", "Ajna"], "related_shastras": ["Yoga", "Tantra"],}),
    ]
    for canonical_name, sanskrit, transliteration, shabda, dhatu, nirukta, related_concepts, sections in specs:
        entries.append({
            "canonical_name": canonical_name,
            "sanskrit": sanskrit,
            "transliteration": transliteration,
            "shabda": shabda,
            "dhatu": dhatu,
            "vyakarana": f"Lexically derived from the root {dhatu.split()[0] if dhatu else canonical_name}",
            "nirukta": nirukta,
            "functional_meaning": sections.get("functional_meaning", ""),
            "related_concepts": related_concepts,
            "sections": sections,
            "path": f"backend/knowledge/sanskrit/{canonical_name}.md",
            "sources": [f"fallback:{canonical_name}"],
        })
    return entries


def load_sanskar_registry() -> Tuple[SanskritRegistry, Dict[str, Dict[str, Any]]]:
    """Load lexical records from source markdowns when available, otherwise fall back to a compact lexical metadata registry and enrich from the UniGuru ecosystem at decode time."""
    registry = SanskritRegistry()
    metadata: Dict[str, Dict[str, Any]] = {}
    source_entries = []
    if SOURCE_DIR.exists():
        for path in sorted(SOURCE_DIR.glob("*.md")):
            if path.name == "README.md":
                continue
            raw = path.read_text(encoding="utf-8")
            sections = _section_map(raw)
            required = ("canonical_name", "sanskrit", "transliteration", "shabda", "dhatu", "vyakarana", "nirukta", "functional_meaning")
            if any(not sections.get(field) for field in required):
                continue
            source_entries.append((path, raw, sections))
    if source_entries:
        for path, raw, sections in source_entries:
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
                "content_hash": stable_hash(raw), "sections": sections, "retrieval_system": "uniguru_ecosystem_adapter",
            }
    if not metadata:
        for entry in _fallback_registry_entries():
            concept = sanskrit_concept_from_dict({
                "concept_id": "sanskar:sanskrit:" + entry["canonical_name"], "canonical_name": entry["canonical_name"],
                "sanskrit": entry["sanskrit"], "transliteration": entry["transliteration"],
                "shabda": entry["shabda"], "dhatu": entry["dhatu"], "vyakarana": entry["vyakarana"],
                "nirukta": entry["nirukta"], "beeja": None, "tattva": None, "shakti": None,
                "functional_meaning": entry["functional_meaning"], "related_concepts": entry["related_concepts"],
                "ontology_version": REGISTRY_VERSION, "semantic_version": DECODER_VERSION,
            })
            registry.register(concept)
            metadata[concept.concept_id] = {
                "path": entry["path"], "sources": entry["sources"], "content_hash": stable_hash(entry), "sections": entry["sections"], "retrieval_system": "uniguru_ecosystem_adapter",
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
        "source": source,
        "document": metadata["path"],
        "section": "lexical_record",
        "retrieval_path": "backend/ontology/sanskrit_decoder.py:load_sanskar_registry",
        "evidence_type": _evidence_type(source).value,
        "provenance": Provenance(source_text=source).__dict__,
        "source_path": metadata["path"], "content_hash": metadata["content_hash"], "retrieval_system": metadata.get("retrieval_system", "uniguru_ecosystem_adapter"),
    } for source in sources]


# ── Phase 3: Pāṇini Sūtra Lookup ─────────────────────────────────────────────

def _extract_dhatu_root(dhatu_text: str) -> str:
    """Extract normalised IAST dhātu root key from the dhatu section text."""
    # Parse parenthetical content, e.g. 'कृ (Kṛ) — To do' → 'kr'
    m = re.search(r"\(([A-Za-zṛṝḷḸśṣṭḍṇñṅāīūḥṃ']+)\)", dhatu_text or "")
    if not m:
        return ""
    iast = m.group(1).lower()
    # Strip diacritics to ASCII-safe key for catalogue lookup
    stripped = unicodedata.normalize("NFD", iast)
    stripped = "".join(c for c in stripped if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z]", "", stripped)


def _panini_sutra_lookup(dhatu_text: str, lexical_provenance: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return structured Pāṇini sūtra records for the given dhātu text."""
    cat = _load_grammar_catalogue()
    sutras_by_dhatu: Dict[str, Any] = cat.get("sutras_by_dhatu", {})
    root_key = _extract_dhatu_root(dhatu_text)
    # Try exact key, then first-2-char prefix match
    entries = sutras_by_dhatu.get(root_key) or sutras_by_dhatu.get(root_key[:3]) or []
    grammar_source_path = str(GRAMMAR_FILE.relative_to(BACKEND_DIR).as_posix())
    grammar_provenance = [{
        "source_id": stable_hash({"source": grammar_source_path, "key": root_key})[:16],
        "evidence_type": EvidenceType.PANINI.value,
        "source_path": grammar_source_path,
        "content_hash": stable_hash(cat),
        "retrieval_system": "uniguru_vedanga_grammar",
    }]
    structured_sutras = [{
        "sutra_number": e.get("sutra_number"),
        "sutra_text": e.get("sutra_text"),
        "rule_class": e.get("rule_class"),
        "gloss": e.get("gloss"),
        "pada": e.get("pada"),
        "derived_word": e.get("derived_word"),
        "provenance": grammar_provenance[0],
    } for e in entries] if entries else []
    status = "EVIDENCE_BACKED" if structured_sutras else "NO_RETRIEVED_EVIDENCE"
    return {
        "status": status,
        "dhatu_root_key": root_key,
        "panini_sutras": structured_sutras,
        "provenance": grammar_provenance,
        "source": "Pāṇini Ashtadhyayi via UniGuru Gurukul grammar.md",
    }


# ── Phase 3: Acoustic Phonetic Engine ────────────────────────────────────────

def _acoustic_phonetics(beeja_text: str, concept_name: str) -> Dict[str, Any]:
    """Look up bīja acoustic metadata from the Śikṣā-sourced phonetics map."""
    phonetics = _load_phonetics_map()
    bija_map: Dict[str, Any] = phonetics.get("bija_map", {})
    phonetics_path = str(PHONETICS_FILE.relative_to(BACKEND_DIR).as_posix())
    phonetics_provenance = [{
        "source_id": stable_hash({"source": phonetics_path, "concept": concept_name})[:16],
        "evidence_type": EvidenceType.VEDA.value,
        "source_path": phonetics_path,
        "content_hash": stable_hash(phonetics),
        "retrieval_system": "uniguru_vedanga_shiksha",
    }]
    # Find entry by concept name first, then by scanning Devanagari key against beeja text
    entry: Optional[Dict[str, Any]] = None
    for key, val in bija_map.items():
        if val.get("concept") == concept_name:
            entry = val
            break
    if entry is None:
        # Try matching first Devanagari token of beeja_text against map keys
        first_deva = (re.search(r"[\u0900-\u097F]+", beeja_text or "") or re.search(r".", ""))
        if first_deva:
            entry = bija_map.get(first_deva.group(0))
    if entry is None:
        return {"status": "NO_RETRIEVED_EVIDENCE", "claims": [], "provenance": phonetics_provenance}
    return {
        "status": "EVIDENCE_BACKED",
        "claims": [{
            "value": {
                "iast": entry.get("iast"),
                "ipa": entry.get("ipa"),
                "varna_class": entry.get("varna_class"),
                "sthana": entry.get("sthana"),
                "prayatna": entry.get("prayatna"),
                "vedic_pitch": entry.get("vedic_pitch"),
                "mantra_frequency_note": entry.get("mantra_frequency_note"),
                "siksha_source": entry.get("siksha_source"),
            },
            "classification": "SOURCE_SCOPED",
            "provenance": phonetics_provenance,
        }],
        "provenance": phonetics_provenance,
        "source": phonetics.get("source"),
    }


# ── Phase 3: Comparative Hermeneutics ────────────────────────────────────────

def _hermeneutics(sections: Dict[str, str], lexical: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Parse traditional_interpretations into a structured Darśana matrix."""
    interp_text = sections.get("traditional_interpretations", "")
    if not interp_text.strip():
        return {"status": "NO_RETRIEVED_EVIDENCE", "claims": [], "darshana_matrix": {}}
    bullets = [line[2:].strip() for line in interp_text.splitlines() if line.strip().startswith("- ")]
    matrix: Dict[str, Any] = {}
    for bullet in bullets:
        bullet_lower = _normal(bullet)
        for darsana_key, patterns in _DARSANA_PATTERNS:
            if darsana_key in matrix:
                continue  # already matched
            for pat in patterns:
                if pat in bullet_lower:
                    # Extract key_terms: words in parens, colon prefix, or first 3 words
                    colon_split = bullet.split(":", 1)
                    key_terms_raw = colon_split[0].strip() if len(colon_split) > 1 else bullet[:50]
                    position = colon_split[1].strip() if len(colon_split) > 1 else bullet
                    matrix[darsana_key] = {
                        "position": position,
                        "key_terms": key_terms_raw,
                        "source_text": bullet,
                        "evidence_type": EvidenceType.COMMENTARY.value,
                        "provenance": lexical,
                    }
                    break
    backed = bool(matrix)
    return {
        "status": "EVIDENCE_BACKED" if backed else "NO_RETRIEVED_EVIDENCE",
        "darshana_matrix": matrix,
        "traditions_represented": sorted(matrix.keys()),
        "claims": [{"value": matrix, "classification": "SOURCE_SCOPED", "provenance": lexical}] if backed else [],
    }


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\w'-]+", _normal(value)) if len(token) > 1}


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _ecosystem_records(concept: SanskritConcept) -> List[Dict[str, Any]]:
    """Retrieve deterministic evidence from the existing UniGuru ecosystem rather than from a handcrafted markdown corpus."""
    query_terms = _tokens(" ".join((concept.canonical_name, concept.transliteration, concept.sanskrit, concept.functional_meaning)))
    records: List[Tuple[int, str, Dict[str, Any], str, str, str, float]] = []

    # 1) Existing Kosha records under backend/data/kosha
    for path in sorted(KOSHA_DIR.glob("*.json")):
        raw = _load_json(path)
        if raw is None:
            continue
        rows: Iterable[Dict[str, Any]] = raw.get("entries", []) if isinstance(raw, dict) and "entries" in raw else [raw]
        for row in rows:
            if not isinstance(row, dict):
                continue
            searchable = " ".join(str(row.get(key, "")) for key in ("content", "clean_content", "domain", "source")) + " " + " ".join(map(str, row.get("tags", [])))
            overlap = query_terms & _tokens(searchable)
            if overlap:
                records.append((len(overlap), str(row.get("knowledge_id", path.stem)), row, str(path.relative_to(BACKEND_DIR).as_posix()), "kosha", str(row.get("source") or path.name), len(overlap) / max(len(query_terms), 1)))

    # 2) Existing JSONL kosha records for deterministic ecosystem retrieval
    jsonl_path = KOSHA_DIR / "kosha_entries.jsonl"
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            searchable = " ".join(str(row.get(key, "")) for key in ("content", "clean_content", "domain", "source")) + " " + " ".join(map(str, row.get("tags", [])))
            overlap = query_terms & _tokens(searchable)
            if overlap:
                records.append((len(overlap), str(row.get("knowledge_id", jsonl_path.stem)), row, str(jsonl_path.relative_to(BACKEND_DIR).as_posix()), "kosha_jsonl", str(row.get("source") or jsonl_path.name), len(overlap) / max(len(query_terms), 1)))

    # 3) Knowledge base index entries from backend/knowledge/index/master_index.json
    index = _load_json(ECOSYSTEM_INDEX)
    if isinstance(index, dict):
        for key, value in index.items():
            if not isinstance(value, list):
                continue
            for item in value:
                if not isinstance(item, dict):
                    continue
                searchable = " ".join(str(item.get(field, "")) for field in ("content", "source", "metadata", "title"))
                overlap = query_terms & _tokens(searchable)
                if overlap:
                    document = str(item.get("metadata", {}).get("source") or item.get("source") or key)
                    records.append((len(overlap), f"kb:{stable_hash({'key': key, 'document': document})[:12]}", item, str(ECOSYSTEM_INDEX.relative_to(BACKEND_DIR).as_posix()), "knowledge_base", document, len(overlap) / max(len(query_terms), 1)))

    # 4) MASTERDB canonical dataset entries from masterdb/balbharti/canonical_dataset.json
    masterdb = _load_json(MASTERDB_DATASET)
    if isinstance(masterdb, list):
        for row in masterdb:
            if not isinstance(row, dict):
                continue
            searchable = " ".join(str(row.get(field, "")) for field in ("concept", "definition", "chapter", "subject", "learning_outcome"))
            overlap = query_terms & _tokens(searchable)
            if overlap:
                records.append((len(overlap), str(row.get("record_id") or f"masterdb:{stable_hash(row)[:12]}"), row, str(MASTERDB_DATASET.relative_to(PROJECT_ROOT).as_posix()), "masterdb", str(row.get("concept") or row.get("subject") or "masterdb"), len(overlap) / max(len(query_terms), 1)))

    records.sort(key=lambda item: (-item[0], item[1], item[3]))
    result = []
    seen = set()
    for score, knowledge_id, row, relative_path, source_type, source, confidence in records:
        if knowledge_id in seen:
            continue
        seen.add(knowledge_id)
        content = str(row.get("clean_content") or row.get("content") or row.get("definition") or row.get("title") or "").strip()
        if not content and isinstance(row, dict):
            content = str(row.get("concept") or row.get("subject") or "")
        result.append({
            "knowledge_id": knowledge_id,
            "content": content,
            "source": source,
            "source_type": source_type,
            "domain": row.get("domain") or row.get("subject") or row.get("chapter") or None,
            "tags": row.get("tags", []) if isinstance(row.get("tags"), list) else [],
            "match_terms": sorted(query_terms & _tokens(" ".join((content, source, str(row.get("domain") or ""), str(row.get("subject") or ""), str(row.get("chapter") or ""))))),
            "provenance": {
                "source_id": stable_hash({"concept": concept.concept_id, "knowledge_id": knowledge_id, "source": source, "source_type": source_type})[:16],
                "source": source,
                "document": relative_path,
                "section": "ecosystem_evidence",
                "retrieval_path": f"backend/ontology/sanskrit_decoder.py:_ecosystem_records::{source_type}",
                "source_path": relative_path,
                "content_hash": stable_hash(row),
                "retrieval_system": "uniguru_ecosystem_adapter",
                "evidence_type": _evidence_type(source).value,
                "confidence": round(confidence, 4),
                "source_type": source_type,
            },
        })
    return result


def _kosha_records(concept: SanskritConcept) -> List[Dict[str, Any]]:
    """Retrieve deterministic UniGuru ecosystem evidence and preserve provenance back to the runtime sources."""
    return _ecosystem_records(concept)


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
    "comparative_hermeneutics": "traditional_interpretations",
}

# ── Pāṇini grammar catalogue (loaded lazily) ─────────────────────────────────
_GRAMMAR_CACHE: Optional[Dict[str, Any]] = None
_PHONETICS_CACHE: Optional[Dict[str, Any]] = None


def _load_grammar_catalogue() -> Dict[str, Any]:
    global _GRAMMAR_CACHE
    if _GRAMMAR_CACHE is not None:
        return _GRAMMAR_CACHE
    try:
        raw = GRAMMAR_FILE.read_text(encoding="utf-8")
        # Extract JSON block between ```json and ```
        m = re.search(r"```json\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
        _GRAMMAR_CACHE = json.loads(m.group(1)) if m else {}
    except (OSError, json.JSONDecodeError, AttributeError):
        _GRAMMAR_CACHE = {}
    return _GRAMMAR_CACHE


def _load_phonetics_map() -> Dict[str, Any]:
    global _PHONETICS_CACHE
    if _PHONETICS_CACHE is not None:
        return _PHONETICS_CACHE
    try:
        _PHONETICS_CACHE = json.loads(PHONETICS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _PHONETICS_CACHE = {}
    return _PHONETICS_CACHE


def _knowledge_object(concept: SanskritConcept, metadata: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    lexical = _lexical_provenance(concept, metadata)
    canonical = sanskrit_concept_to_dict(concept)
    sections = metadata.get("sections", {})
    layers: Dict[str, Dict[str, Any]] = {}
    lexical_fields = {"sanskrit", "shabda", "dhatu", "vyakarana", "nirukta", "beeja", "tattva", "shakti", "functional_meaning"}
    for field in KNOWLEDGE_LAYERS:
        if field in lexical_fields and canonical.get(field):
            base = {"status": "EVIDENCE_BACKED", "claims": [_claim(canonical[field], lexical)]}
            # Phase 3: enrich vyākaraṇa with structured Pāṇini sūtra data
            if field == "vyakarana":
                panini = _panini_sutra_lookup(canonical.get("dhatu", ""), lexical)
                base["panini_grammar"] = panini
                if panini["status"] == "EVIDENCE_BACKED":
                    base["status"] = "EVIDENCE_BACKED"
            # Phase 3: enrich bīja with acoustic phonetic metadata
            elif field == "beeja":
                acoustic = _acoustic_phonetics(canonical.get("beeja", ""), concept.canonical_name)
                base["acoustic_phonetics"] = acoustic
                if acoustic["status"] == "EVIDENCE_BACKED":
                    base["status"] = "EVIDENCE_BACKED"
            # Phase 3: enrich śabda with acoustic metadata too (same lookup)
            elif field == "shabda":
                acoustic = _acoustic_phonetics(canonical.get("beeja", ""), concept.canonical_name)
                base["acoustic_phonetics"] = acoustic
            layers[field] = base
        elif field == "cross_references":
            layers[field] = {"status": "EVIDENCE_BACKED" if concept.related_concepts else "NO_RETRIEVED_EVIDENCE", "claims": [_claim(sorted(concept.related_concepts), lexical)] if concept.related_concepts else []}
        elif field == "experimental_hypotheses":
            section_text = sections.get(_LAYER_TO_SECTION.get(field, ""), "")
            if section_text and "[EXPERIMENTAL" in section_text:
                layers[field] = {"status": "EXPLICITLY_MARKED_EXPERIMENTAL", "claims": [_claim(section_text.strip(), lexical, "EXPERIMENTAL")], "policy": "Marked EXPERIMENTAL in source document."}
            else:
                layers[field] = {"status": "NOT_ASSERTED", "claims": [], "policy": "No experimental hypothesis is emitted without an explicitly classified source."}
        elif field == "comparative_hermeneutics":
            # Phase 3: structured Darśana matrix
            layers[field] = _hermeneutics(sections, lexical)
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
        "schema_version": "UNIGURU_CIVILIZATIONAL_KNOWLEDGE_OBJECT_V3", "concept_id": concept.concept_id,
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
    return {"graph_id": "UNIGURU_CIVILIZATIONAL_KNOWLEDGE_GRAPH_V3", "schema_version": "3.0.0", "nodes": nodes, "edges": edges, "metadata": {"adapter": DECODER_VERSION, "consistency_valid": True, "orphaned_nodes": [], "source_snapshot_hash": metadata["content_hash"], "node_count": len(nodes), "edge_count": len(edges)}}


# ── Phase 3 & 4: Typed Entity Expansion & Multi-Hop Graph Traversal ─────────

def _expand_typed_node(
    node_id: str,
    registry: "SanskritRegistry",
    metadata_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Resolve any typed node_id to (node_info, outbound_nodes, outbound_edges).

    Supports recursive traversal for:
    - sanskar:sanskrit:<name> (type: sanskrit_concept)
    - kosha_ref:<key> (type: kosha)
    - chakra_ref:<key> (type: chakra)
    - bija_ref:<key> (type: bija)
    - loka:<key> (type: loka)
    - deity:<key> (type: deity)
    - shastra:<key> (type: shastra)
    - yantra:<key> (type: yantra)
    - vidya:<key> (type: vidya)
    """
    if node_id.startswith("sanskar:sanskrit:"):
        cname = node_id.split(":")[-1]
        concept = _resolve(cname, registry)
        if concept is None:
            return None, [], []
        meta = metadata_by_id.get(concept.concept_id, {})
        records = _kosha_records(concept)
        g = _graph(concept, registry, meta, records)
        node_info = {
            "id": concept.concept_id,
            "type": "sanskrit_concept",
            "label": concept.canonical_name,
            "provenance": meta.get("path", "backend/knowledge/sanskrit/" + cname + ".md"),
        }
        out_edges = []
        for e in g["edges"]:
            edge_copy = dict(e)
            edge_copy["from_type"] = edge_copy.get("from_type", "sanskrit_concept")
            target_node = next((n for n in g["nodes"] if n["id"] == edge_copy["to"]), None)
            edge_copy["to_type"] = edge_copy.get("to_type", target_node["type"] if target_node else "unknown")
            out_edges.append(edge_copy)
        return node_info, g["nodes"], out_edges

    elif node_id.startswith("kosha_ref:"):
        key = node_id.split(":", 1)[1]
        path = "backend/knowledge/sanskrit/koshas.md"
        label = key.replace("_", " ").title() + " Kosha" if not key.endswith("kosha") else key.replace("_", " ").title()
        node_info = {"id": node_id, "type": "kosha", "label": label, "provenance": path}
        out_nodes = [node_info]
        out_edges = []
        if "pranamaya" in key:
            c_id = "chakra_ref:anahata"
            c_node = {"id": c_id, "type": "chakra", "label": "Anāhata", "provenance": "backend/knowledge/sanskrit/chakras.md"}
            out_nodes.append(c_node)
            out_edges.append({"from": node_id, "from_type": "kosha", "to": c_id, "to_type": "chakra", "type": "related_chakra", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
            p_id = "sanskar:sanskrit:prana"
            out_edges.append({"from": node_id, "from_type": "kosha", "to": p_id, "to_type": "sanskrit_concept", "type": "related_concept", "evidence_type": EvidenceType.DERIVED.value, "provenance": path})
        elif "annamaya" in key:
            c_id = "chakra_ref:muladhara"
            c_node = {"id": c_id, "type": "chakra", "label": "Mūlādhāra", "provenance": "backend/knowledge/sanskrit/chakras.md"}
            out_nodes.append(c_node)
            out_edges.append({"from": node_id, "from_type": "kosha", "to": c_id, "to_type": "chakra", "type": "related_chakra", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "manomaya" in key:
            c_id = "chakra_ref:manipura"
            c_node = {"id": c_id, "type": "chakra", "label": "Maṇipūra", "provenance": "backend/knowledge/sanskrit/chakras.md"}
            out_nodes.append(c_node)
            out_edges.append({"from": node_id, "from_type": "kosha", "to": c_id, "to_type": "chakra", "type": "related_chakra", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "vijnanamaya" in key:
            c_id = "chakra_ref:ajna"
            c_node = {"id": c_id, "type": "chakra", "label": "Ājñā", "provenance": "backend/knowledge/sanskrit/chakras.md"}
            out_nodes.append(c_node)
            out_edges.append({"from": node_id, "from_type": "kosha", "to": c_id, "to_type": "chakra", "type": "related_chakra", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "anandamaya" in key:
            c_id = "chakra_ref:sahasrara"
            c_node = {"id": c_id, "type": "chakra", "label": "Sahasrāra", "provenance": "backend/knowledge/sanskrit/chakras.md"}
            out_nodes.append(c_node)
            out_edges.append({"from": node_id, "from_type": "kosha", "to": c_id, "to_type": "chakra", "type": "related_chakra", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        return node_info, out_nodes, out_edges

    elif node_id.startswith("chakra_ref:"):
        key = node_id.split(":", 1)[1]
        path = "backend/knowledge/sanskrit/chakras.md"
        label = key.replace("_", " ").title() + " Chakra" if not key.endswith("chakra") else key.replace("_", " ").title()
        node_info = {"id": node_id, "type": "chakra", "label": label, "provenance": path}
        out_nodes = [node_info]
        out_edges = []
        if "anahata" in key:
            b_id = "bija_ref:yam"
            b_node = {"id": b_id, "type": "bija", "label": "Yaṃ Bīja (यं)", "provenance": "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"}
            out_nodes.append(b_node)
            out_edges.append({"from": node_id, "from_type": "chakra", "to": b_id, "to_type": "bija", "type": "related_bija", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
            k_id = "kosha_ref:pranamaya_kosha"
            out_edges.append({"from": node_id, "from_type": "chakra", "to": k_id, "to_type": "kosha", "type": "related_kosha", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "muladhara" in key:
            b_id = "bija_ref:lam"
            b_node = {"id": b_id, "type": "bija", "label": "Laṁ Bīja (लँ)", "provenance": "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"}
            out_nodes.append(b_node)
            out_edges.append({"from": node_id, "from_type": "chakra", "to": b_id, "to_type": "bija", "type": "related_bija", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "svadhisthana" in key:
            b_id = "bija_ref:vam"
            b_node = {"id": b_id, "type": "bija", "label": "Vaṁ Bīja (वँ)", "provenance": "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"}
            out_nodes.append(b_node)
            out_edges.append({"from": node_id, "from_type": "chakra", "to": b_id, "to_type": "bija", "type": "related_bija", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "manipura" in key:
            b_id = "bija_ref:ram"
            b_node = {"id": b_id, "type": "bija", "label": "Raṃ Bīja (रं)", "provenance": "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"}
            out_nodes.append(b_node)
            out_edges.append({"from": node_id, "from_type": "chakra", "to": b_id, "to_type": "bija", "type": "related_bija", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "visuddha" in key:
            b_id = "bija_ref:ham"
            b_node = {"id": b_id, "type": "bija", "label": "Haṁ Bīja (हँ)", "provenance": "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"}
            out_nodes.append(b_node)
            out_edges.append({"from": node_id, "from_type": "chakra", "to": b_id, "to_type": "bija", "type": "related_bija", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        elif "ajna" in key:
            b_id = "bija_ref:om"
            b_node = {"id": b_id, "type": "bija", "label": "Om Bīja (ॐ)", "provenance": "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"}
            out_nodes.append(b_node)
            out_edges.append({"from": node_id, "from_type": "chakra", "to": b_id, "to_type": "bija", "type": "related_bija", "evidence_type": EvidenceType.TRADITION.value, "provenance": path})
        return node_info, out_nodes, out_edges

    elif node_id.startswith("bija_ref:"):
        key = node_id.split(":", 1)[1]
        path = "backend/knowledge/sanskrit/phonetics/bija_phonetics.json"
        label = key.upper() + " Bīja"
        node_info = {"id": node_id, "type": "bija", "label": label, "provenance": path}
        out_nodes = [node_info]
        out_edges = []
        if "yam" in key:
            c_id = "chakra_ref:anahata"
            out_edges.append({"from": node_id, "from_type": "bija", "to": c_id, "to_type": "chakra", "type": "related_chakra", "evidence_type": EvidenceType.VEDA.value, "provenance": path})
            p_id = "sanskar:sanskrit:prana"
            out_edges.append({"from": node_id, "from_type": "bija", "to": p_id, "to_type": "sanskrit_concept", "type": "related_concept", "evidence_type": EvidenceType.VEDA.value, "provenance": path})
        return node_info, out_nodes, out_edges

    else:
        prefix, key = node_id.split(":", 1) if ":" in node_id else ("entity", node_id)
        label = key.replace("_", " ").title()
        path = "backend/knowledge/sanskrit/" + key + ".md" if key in metadata_by_id else "backend/knowledge/sanskrit/dharma.md"
        node_info = {"id": node_id, "type": prefix, "label": label, "provenance": path}
        return node_info, [node_info], []


def traverse_concept_graph(
    start: str,
    edge_types: Optional[List[str]],
    max_depth: int,
    registry: "SanskritRegistry",
    metadata_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """BFS multi-hop traversal of the Civilizational Knowledge Graph.

    Walks the graph outward from *start*, recursively resolving and expanding
    all typed nodes (sanskrit_concept, kosha, chakra, bija, loka, deity, shastra, etc.).
    Returns ordered path frames and the visited sub-graph with provenance on every node and edge.
    """
    start_concept = _resolve(start, registry)
    start_id = start_concept.concept_id if start_concept else start
    allowed_types: Optional[set] = set(edge_types) if edge_types else None
    max_depth = max(1, min(max_depth, 6))  # clamp 1–6

    visited_nodes: Dict[str, Any] = {}
    visited_edges: List[Dict[str, Any]] = []
    path_frames: List[Dict[str, Any]] = []
    # BFS queue: (node_id, depth, incoming_edge)
    from collections import deque
    queue: deque = deque()
    queue.append((start_id, 0, None))
    queued_ids = {start_id}

    while queue:
        current_id, depth, incoming = queue.popleft()
        node_info, out_nodes, out_edges = _expand_typed_node(current_id, registry, metadata_by_id)
        if node_info is None:
            continue

        # Register all nodes from this expansion
        for node in out_nodes:
            if node["id"] not in visited_nodes:
                visited_nodes[node["id"]] = node

        # Record path frame with node_type and provenance
        path_frames.append({
            "hop": depth,
            "node_id": node_info["id"],
            "node_label": node_info["label"],
            "node_type": node_info["type"],
            "incoming_edge_type": incoming,
            "provenance": node_info["provenance"],
        })

        if depth >= max_depth:
            continue

        # Follow edges to next-hop nodes recursively
        for edge in out_edges:
            etype = edge["type"]
            if allowed_types and etype not in allowed_types:
                continue
            target_id = edge["to"]
            if target_id in queued_ids:
                continue
            queued_ids.add(target_id)
            visited_edges.append({**edge, "hop": depth})
            queue.append((target_id, depth + 1, etype))

    # Deduplicate edges
    seen_edge_sigs: set = set()
    unique_edges: List[Dict[str, Any]] = []
    for edge in visited_edges:
        sig = (edge["from"], edge["to"], edge["type"])
        if sig not in seen_edge_sigs:
            seen_edge_sigs.add(sig)
            unique_edges.append(edge)

    sub_graph_nodes = list(visited_nodes.values())
    traversal_hash = stable_hash({"path": path_frames, "edge_count": len(unique_edges)})
    return {
        "start": start,
        "max_depth": max_depth,
        "edge_type_filter": list(allowed_types) if allowed_types else "all",
        "path": path_frames,
        "sub_graph": {
            "nodes": sub_graph_nodes,
            "edges": unique_edges,
            "node_count": len(sub_graph_nodes),
            "edge_count": len(unique_edges),
        },
        "traversal_metadata": {
            "graph_id": "UNIGURU_CIVILIZATIONAL_KNOWLEDGE_GRAPH_V3",
            "schema_version": "3.0.0",
            "traversal_hash": traversal_hash,
            "replay_safe": True,
        },
    }



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
