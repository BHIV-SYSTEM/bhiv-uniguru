"""Sanskrit Meter (Vṛtta) Detection according to Classical Chandashastra."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from .schemas import MeterAnalysis

# Devanagari Unicode ranges & characters
SWARAS_SHORT = {"अ", "इ", "उ", "ऋ", "ऌ"}
SWARAS_LONG = {"आ", "ई", "ऊ", "ॠ", "ॡ", "ए", "ऐ", "ओ", "औ"}
MATRAS_SHORT = {"\u093F", "\u0941", "\u0943", "\u0944"}  # i, u, ri, lri
MATRAS_LONG = {"\u093E", "\u0940", "\u0942", "\u0947", "\u0948", "\u094B", "\u094C"}  # aa, ii, uu, e, ai, o, au
VIRAMA = "\u094D"
ANUSVARA = "\u0902"
VISARGA = "\u0903"

KNOWN_METERS: Dict[str, Dict[str, Any]] = {
    "Anuṣṭubh": {
        "pada_syllables": 8,
        "total_syllables": 32,
        "description": "8 syllables per pāda. The most celebrated classical Sanskrit śloka meter.",
    },
    "Indravajrā": {
        "pada_syllables": 11,
        "total_syllables": 44,
        "pattern": "GGLGGLLGLGG",
        "description": "11 syllables per pāda starting with two gurus (G G L G G L L G L G G).",
    },
    "Upendravajrā": {
        "pada_syllables": 11,
        "total_syllables": 44,
        "pattern": "LGLGGLLGLGG",
        "description": "11 syllables per pāda starting with a laghu (L G L G G L L G L G G).",
    },
    "Upajāti": {
        "pada_syllables": 11,
        "total_syllables": 44,
        "description": "11 syllables per pāda, combining Indravajrā and Upendravajrā pādas.",
    },
    "Vaṃśastha": {
        "pada_syllables": 12,
        "total_syllables": 48,
        "pattern": "LGLGGLLGLGLG",
        "description": "12 syllables per pāda with pattern (Jatara: L G L G G L L G L G L G).",
    },
    "Bhujangaprayāta": {
        "pada_syllables": 12,
        "total_syllables": 48,
        "pattern": "LGGLGGLGGLGG",
        "description": "12 syllables per pāda formed of four ya-gaṇas (L G G L G G L G G L G G).",
    },
    "Vasantatilakā": {
        "pada_syllables": 14,
        "total_syllables": 56,
        "pattern": "GGLGLLLGLLGLGG",
        "description": "14 syllables per pāda (Ta-Bha-Ja-Ja-Ga-Ga).",
    },
    "Mālinī": {
        "pada_syllables": 15,
        "total_syllables": 60,
        "pattern": "LLLLLLGGGLGGLGG",
        "description": "15 syllables per pāda (Na-Na-Ma-Ya-Ya) with pause at 8 and 7.",
    },
    "Śikhariṇī": {
        "pada_syllables": 17,
        "total_syllables": 68,
        "pattern": "LGGGGLLLLLLGGLGG",
        "description": "17 syllables per pāda (Ya-Ma-Na-Sa-Bha-La-Ga) with pause at 6 and 11.",
    },
    "Mandākrāntā": {
        "pada_syllables": 17,
        "total_syllables": 68,
        "pattern": "GGGGLLLLLLGGLGLGG",
        "description": "17 syllables per pāda (Ma-Bha-Na-Ta-Ta-Ga-Ga) famous in Kālidāsa's Meghadūta.",
    },
    "Śārdūlavikrīḍita": {
        "pada_syllables": 19,
        "total_syllables": 76,
        "pattern": "GGGLLGLGLLLGGGLGGLG",
        "description": "19 syllables per pāda (Ma-Sa-Ja-Sa-Ta-Ta-Ga) with pause at 12 and 7.",
    },
    "Sragdharā": {
        "pada_syllables": 21,
        "total_syllables": 84,
        "pattern": "GGGGGLGGLLLLLLGGLGGLGG",
        "description": "21 syllables per pāda with pauses at every 7 syllables.",
    },
}


def normalize_sanskrit(text: str) -> str:
    """Normalize Sanskrit Unicode safely while preserving Devanagari and punctuation."""
    norm = unicodedata.normalize("NFC", str(text or "").strip())
    # Remove Latin punctuation except danda
    norm = re.sub(r"[!?,;:\"'()\[\]{}]+", " ", norm)
    norm = re.sub(r"\s+", " ", norm)
    return norm.strip()


def extract_padas(text: str) -> List[str]:
    """Split shloka into constituent padas based on dandas, line breaks, or commas."""
    # Split by double danda first, then single danda, then newlines
    lines = re.split(r"[॥\n]+", text)
    padas: List[str] = []
    for line in lines:
        parts = re.split(r"[।;,]+", line)
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                padas.append(cleaned)
    return padas


def split_into_aksharas(text: str) -> List[str]:
    """Tokenize Sanskrit text into classical aksharas (syllables)."""
    clean = re.sub(r"[॥।0-9\s]+", "", text)
    if not clean:
        return []

    aksharas = []
    i = 0
    n = len(clean)

    while i < n:
        akshara = clean[i]
        i += 1
        # Gather conjuncts
        while i < n and clean[i] == VIRAMA:
            akshara += clean[i]
            i += 1
            if i < n:
                akshara += clean[i]
                i += 1
        # Gather vowel matras
        while i < n and (clean[i] in MATRAS_SHORT or clean[i] in MATRAS_LONG or clean[i] in (ANUSVARA, VISARGA)):
            akshara += clean[i]
            i += 1
        aksharas.append(akshara)

    return aksharas


def analyze_syllables(text: str) -> Tuple[int, str]:
    """
    Count syllables and compute approximate Laghu (L) / Guru (G) pattern for Devanagari Sanskrit.
    Returns (syllable_count, lg_pattern).
    """
    aksharas = split_into_aksharas(text)
    if not aksharas:
        return 0, ""

    syllable_count = len(aksharas)
    lg_pattern: List[str] = []

    for idx, ak in enumerate(aksharas):
        is_guru = False
        # If has long vowel or long matra
        if any(c in SWARAS_LONG or c in MATRAS_LONG for c in ak):
            is_guru = True
        # If followed by anusvara or visarga
        elif any(c in (ANUSVARA, VISARGA) for c in ak):
            is_guru = True
        # If next akshara has a conjunct (virama)
        elif idx + 1 < len(aksharas) and VIRAMA in aksharas[idx + 1]:
            is_guru = True
        # End of pada is usually considered guru (पादbilled laghu can be counted guru)
        elif idx == len(aksharas) - 1:
            is_guru = True

        lg_pattern.append("G" if is_guru else "L")

    return syllable_count, "".join(lg_pattern)


def detect_sanskrit_meter(text: str) -> MeterAnalysis:
    """Analyze a Sanskrit verse and detect its meter (vṛtta)."""
    norm = normalize_sanskrit(text)
    if not norm:
        return MeterAnalysis(confidence=0.0)

    padas = extract_padas(norm)
    total_syllables = 0
    pada_counts = []
    full_pattern = []

    for pada in padas:
        count, pattern = analyze_syllables(pada)
        if count > 0:
            total_syllables += count
            pada_counts.append(count)
            full_pattern.append(pattern)

    combined_pattern = "-".join(full_pattern)
    avg_pada_syllables = (sum(pada_counts) / len(pada_counts)) if pada_counts else 0

    # 1. Match Anustubh (typically 4 padas of ~8 syllables or 2 lines of ~16 syllables)
    if (len(pada_counts) in {2, 4} and all(7 <= c <= 9 for c in pada_counts)) or (len(pada_counts) == 2 and all(14 <= c <= 18 for c in pada_counts)) or (28 <= total_syllables <= 36 and round(avg_pada_syllables) in {8, 16}):
        return MeterAnalysis(
            detected_meter="Anuṣṭubh",
            confidence=0.95,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS["Anuṣṭubh"]["description"],
        )

    # 2. Match 11-syllable meters (Indravajra, Upendravajra, Upajati)
    if round(avg_pada_syllables) == 11 or (40 <= total_syllables <= 48 and len(pada_counts) == 4):
        # Inspect first syllable of each pada
        starts = [p[0] for p in full_pattern if p]
        if all(s == "G" for s in starts):
            m_name = "Indravajrā"
        elif all(s == "L" for s in starts):
            m_name = "Upendravajrā"
        else:
            m_name = "Upajāti"
        return MeterAnalysis(
            detected_meter=m_name,
            confidence=0.90,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS[m_name]["description"],
        )

    # 3. Match 12-syllable meters (Vamsastha, Bhujangaprayata)
    if round(avg_pada_syllables) == 12 or (46 <= total_syllables <= 50 and len(pada_counts) == 4):
        m_name = "Bhujangaprayāta" if "LGGLGG" in combined_pattern else "Vaṃśastha"
        return MeterAnalysis(
            detected_meter=m_name,
            confidence=0.88,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS[m_name]["description"],
        )

    # 4. Match 14-syllable Vasantatilaka
    if round(avg_pada_syllables) == 14 or (54 <= total_syllables <= 58):
        return MeterAnalysis(
            detected_meter="Vasantatilakā",
            confidence=0.92,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS["Vasantatilakā"]["description"],
        )

    # 5. Match 15-syllable Malini
    if round(avg_pada_syllables) == 15 or (58 <= total_syllables <= 62):
        return MeterAnalysis(
            detected_meter="Mālinī",
            confidence=0.92,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS["Mālinī"]["description"],
        )

    # 6. Match 17-syllable Mandakranta or Shikharini
    if round(avg_pada_syllables) == 17 or (66 <= total_syllables <= 70):
        # Mandakranta starts with four gurus (G G G G)
        m_name = "Mandākrāntā" if any(p.startswith("GGGG") for p in full_pattern) else "Śikhariṇī"
        return MeterAnalysis(
            detected_meter=m_name,
            confidence=0.90,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS[m_name]["description"],
        )

    # 7. Match 19-syllable Shardulavikridita
    if round(avg_pada_syllables) == 19 or (74 <= total_syllables <= 78):
        return MeterAnalysis(
            detected_meter="Śārdūlavikrīḍita",
            confidence=0.94,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS["Śārdūlavikrīḍita"]["description"],
        )

    # 8. Match 21-syllable Sragdhara
    if round(avg_pada_syllables) == 21 or (82 <= total_syllables <= 86):
        return MeterAnalysis(
            detected_meter="Sragdharā",
            confidence=0.94,
            syllable_count=total_syllables,
            pada_syllable_counts=pada_counts,
            laghu_guru_pattern=combined_pattern,
            meter_description=KNOWN_METERS["Sragdharā"]["description"],
        )

    # Default fallback: approximate matching
    fallback_name = "Anuṣṭubh" if total_syllables <= 36 else None
    return MeterAnalysis(
        detected_meter=fallback_name,
        confidence=0.5 if fallback_name else 0.0,
        syllable_count=total_syllables,
        pada_syllable_counts=pada_counts,
        laghu_guru_pattern=combined_pattern,
        meter_description=KNOWN_METERS[fallback_name]["description"] if fallback_name else "Unknown meter",
    )


def classify_syllable_weight(akshara: str) -> str:
    """Classify a single akshara as 'G' (guru) or 'L' (laghu)."""
    if any(c in SWARAS_LONG or c in MATRAS_LONG for c in akshara):
        return "G"
    if any(c in (ANUSVARA, VISARGA) for c in akshara):
        return "G"
    return "L"


# Backward-compatible convenience aliases
analyze_meter = detect_sanskrit_meter
syllabify_sanskrit = split_into_aksharas

