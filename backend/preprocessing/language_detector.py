"""
High-accuracy Language Detector for UniGuru Educational Substrates.
Specialized for: Marathi, Hindi, English, and Sanskrit.
Uses script distribution analysis and linguistic marker weighting.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Tuple


class LanguageDetector:
    """
    Deterministically detects whether text is Marathi, Hindi, English, or Sanskrit.
    Fast, completely offline, and requires no heavy external NLP models.
    """

    # Devanagari Unicode Block: U+0900 to U+097F
    DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")
    LATIN_REGEX = re.compile(r"[a-zA-Z]")

    # Characteristic Marathi tokens and morphemes
    MARATHI_TOKENS = {
        "आहे", "नाही", "आहेत", "झाला", "झाली", "झाले", "केले", "केली", "केला",
        "त्यांच्या", "त्यांना", "म्हणून", "येथे", "होते", "होती", "आणि", "करणे",
        "यांचा", "यांची", "यांचे", "मध्ये", "पासून", "खालील", "पुढील", "इयत्ता",
        "स्वाध्याय", "पाठ", "प्रश्नोत्तरे", "करा", "असा", "अशी", "असे", "त्यामुळे",
        "आपल्या", "काही", "सर्व", "एकदा", "नंतर", "सांगा", "पहा", "वाचा",
    }

    # Characteristic Hindi tokens and morphemes
    HINDI_TOKENS = {
        "है", "हैं", "था", "थी", "थे", "नहीं", "और", "का", "के", "की", "से", "में",
        "पर", "को", "यह", "वह", "होता", "होती", "होते", "करना", "करता", "करती",
        "कहा", "दिया", "लिया", "लेकिन", "किन्तु", "परन्तु", "अगर", "यदि", "तो",
        "बहुत", "कुछ", "सब", "एक", "दो", "इनका", "उनकी", "उनके", "द्वारा", "सकता",
        "सकते", "सकती", "वाले", "वाली", "गया", "गई", "गए", "भी", "ही", "तक",
    }

    # Characteristic Sanskrit tokens and morphemes
    SANSKRIT_TOKENS = {
        "अहम्", "त्वम्", "तस्य", "अस्ति", "भवति", "सत्यम्", "धर्मः", "विद्या",
        "नमः", "स्वाहा", "उपनिषद्", "वेद", "श्लोक", "सूक्त", "ऋषि", "ब्रह्मन्",
        "मोक्ष", "इति", "च", "एव", "अपि", "तु", "यथा", "तथा", "कुरु", "पश्य",
        "गच्छति", "उवाच", "वदति", "शान्तिः", "सर्वे", "भवन्तु", "सुखिनः", "तस्मै",
        "श्री", "गुरवे", "नमस्कृत्य", "ज्ञानम्", "यज्ञ", "पुरुष", "प्रकृति",
    }

    @classmethod
    def detect(cls, text: str) -> Dict[str, Any]:
        """
        Detects primary language of the text.
        Returns dict with keys: 'language', 'confidence', 'details'.
        Possible language values: 'marathi', 'hindi', 'english', 'sanskrit', 'multilingual', 'unknown'.
        """
        if not text or not text.strip():
            return {
                "language": "unknown",
                "confidence": 0.0,
                "details": {"reason": "empty_input"},
            }

        normalized = unicodedata.normalize("NFKC", text)

        # Count script occurrences
        devanagari_count = len(cls.DEVANAGARI_REGEX.findall(normalized))
        latin_count = len(cls.LATIN_REGEX.findall(normalized))
        total_chars = devanagari_count + latin_count

        if total_chars == 0:
            return {
                "language": "unknown",
                "confidence": 0.0,
                "details": {"reason": "no_alphabetic_characters"},
            }

        # Check for Latin dominance -> English
        if latin_count / total_chars > 0.75:
            conf = round(latin_count / total_chars, 2)
            return {
                "language": "english",
                "confidence": conf,
                "details": {"script": "latin", "latin_ratio": conf},
            }

        # If Devanagari is dominant (> 30% of total or higher than Latin)
        if devanagari_count > 0:
            return cls._classify_devanagari(normalized, devanagari_count, total_chars)

        return {
            "language": "unknown",
            "confidence": 0.0,
            "details": {"latin_count": latin_count, "devanagari_count": devanagari_count},
        }

    @classmethod
    def _classify_devanagari(
        cls, text: str, dev_count: int, total_chars: int
    ) -> Dict[str, Any]:
        """Disambiguate among Marathi, Sanskrit, and Hindi within Devanagari script."""
        # 1. Phonetic character-level markers
        has_marathi_la = "ळ" in text  # U+0933 is characteristic of Marathi (and Vedic Sanskrit)
        visarga_count = text.count("ः")  # U+0903 characteristic of Sanskrit
        avagraha_count = text.count("ऽ")  # U+093D characteristic of Sanskrit

        # Tokenize Devanagari words
        words = re.findall(r"[\u0900-\u097F]+", text)
        word_count = len(words)

        if word_count == 0:
            return {
                "language": "hindi",
                "confidence": 0.5,
                "details": {"reason": "script_only_devanagari"},
            }

        marathi_hits = sum(1 for w in words if w in cls.MARATHI_TOKENS)
        hindi_hits = sum(1 for w in words if w in cls.HINDI_TOKENS)
        sanskrit_hits = sum(1 for w in words if w in cls.SANSKRIT_TOKENS)

        # Sanskrit structural indicators: words ending in visarga (ः) or halanta (्)
        sanskrit_visarga_words = sum(1 for w in words if w.endswith("ः"))
        sanskrit_halanta_words = sum(1 for w in words if w.endswith("्"))
        sanskrit_inflections = sum(1 for w in words if w.endswith("स्य") or w.endswith("आम्") or w.endswith("यात्"))

        sanskrit_score = (
            sanskrit_hits * 3.0
            + sanskrit_visarga_words * 2.0
            + sanskrit_halanta_words * 1.5
            + sanskrit_inflections * 2.5
            + avagraha_count * 3.0
            + (visarga_count * 1.5)
        )

        marathi_score = (
            marathi_hits * 3.0
            + (5.0 if has_marathi_la else 0.0)
            + text.count("च्या") * 1.5
            + text.count("साठी") * 1.5
        )

        hindi_score = (
            hindi_hits * 3.0
            + (3.0 if "है" in text or "हैं" in text else 0.0)
            + (2.0 if "नहीं" in text else 0.0)
            + (2.0 if "और" in text else 0.0)
        )

        scores = {
            "sanskrit": sanskrit_score,
            "marathi": marathi_score,
            "hindi": hindi_score,
        }

        # Select highest score
        best_lang, best_score = max(scores.items(), key=lambda kv: kv[1])

        # If zero or tied with near zero signal
        if best_score < 1.5:
            # Default to Hindi for generic Devanagari if no explicit Sanskrit/Marathi markers
            if has_marathi_la:
                return {
                    "language": "marathi",
                    "confidence": 0.70,
                    "details": {"feature": "marathi_la_detected"},
                }
            if visarga_count >= 2:
                return {
                    "language": "sanskrit",
                    "confidence": 0.70,
                    "details": {"feature": "frequent_visarga_detected"},
                }
            return {
                "language": "hindi",
                "confidence": 0.60,
                "details": {"feature": "default_devanagari_no_specific_markers"},
            }

        total_signal = sum(scores.values()) or 1.0
        confidence = round(min(0.99, max(0.65, best_score / total_signal)), 2)

        return {
            "language": best_lang,
            "confidence": confidence,
            "details": {
                "scores": scores,
                "has_marathi_la": has_marathi_la,
                "visarga_count": visarga_count,
                "avagraha_count": avagraha_count,
            },
        }

