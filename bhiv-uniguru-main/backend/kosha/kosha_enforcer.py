import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from kosha.ocr_purifier import OCRPurifier
from kosha.kosha_validator import KoshaEntry

logger = logging.getLogger(__name__)

VALID_DOMAINS = {
    "puranas", "gitas", "upanishads", "vedas", "itihasa", "smriti",
    "agamas", "tantra", "history", "geography", "maths", "physics",
    "chemistry", "biology", "agricultural", "general",
    # Legacy domains from existing Kosha entries
    "agriculture", "urban", "water / rivers", "infrastructure",
}

DOMAIN_KEYWORDS: List[Tuple[str, tuple]] = [
    ("puranas", ("purana", "bhagavata", "narada", "padma purana", "vayu purana")),
    ("gitas", ("gita", "bhagavad gita", "uddhava", "anugita")),
    ("upanishads", ("upanishad", "ishavasya", "taittiriya", "prashna", "brahman")),
    ("vedas", ("veda", "rigveda", "samaveda", "yajurveda", "atharvaveda")),
    ("itihasa", ("mahabharata", "ramayana", "itihasa", "pandava", "kurukshetra")),
    ("smriti", ("smriti", "dharma sutra", "manu", "yajnavalkya")),
    ("agamas", ("agama", "saiva", "shaiva", "vaishnava", "pancharatra")),
    ("tantra", ("tantra", "tripura", "bhairava", "tantrasara")),
    ("history", ("history", "ancient", "medieval", "historical", "dynasty")),
    ("geography", ("geography", "river", "mountain", "continent", "climate")),
    ("maths", ("math", "algebra", "geometry", "calculus", "equation", "theorem")),
    ("physics", ("physics", "force", "energy", "quantum", "momentum", "velocity")),
    ("chemistry", ("chemistry", "chemical", "molecule", "atom", "acid", "reaction")),
    ("biology", ("biology", "cell", "genetics", "evolution", "organism")),
    ("agricultural", ("agri", "crop", "farm", "soil", "irrigation", "harvest")),
]

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "to", "of", "in", "on", "at", "by", "for", "from", "as", "with",
    "about", "into", "over", "under", "who", "what", "which", "when",
    "where", "why", "how", "tell", "explain", "does", "have", "this",
    "that", "chapter", "verse",
}


class KoshaEnforcer:
    """
    Phase 3: Kosha Enforcement Layer
    Converts OCR outputs into structured Kosha entries.
    Rejects any unstructured or low-quality data.
    """

    MIN_CONTENT_LENGTH = 30
    MIN_CONFIDENCE = 0.1

    @staticmethod
    def infer_domain(content: str, source: str = "", hint: str = "") -> str:
        """Deterministic domain inference from content + source"""
        hint_clean = str(hint or "").strip().lower()
        if hint_clean and hint_clean not in {"", "string", "general", "misc", "unknown", "null", "none"}:
            if hint_clean in VALID_DOMAINS:
                return hint_clean

        text = f"{content} {source}".lower()
        for domain_name, keywords in DOMAIN_KEYWORDS:
            if any(kw in text for kw in keywords):
                return domain_name

        return "general"

    @staticmethod
    def extract_tags(content: str, source: str = "") -> List[str]:
        """Extract meaningful tags from content and source"""
        text = f"{content} {source}".lower()
        terms = re.findall(r'[a-zA-Z0-9]+', text)
        tags = sorted({t for t in terms if len(t) > 3 and t not in STOPWORDS})
        return tags[:8]  # Cap at 8 tags

    @staticmethod
    def compute_confidence(
        content: str,
        source: str,
        ocr_quality: float = 1.0,
        tag_match: float = 0.0,
        domain_match: bool = False,
    ) -> float:
        """
        Phase 5: Real Confidence Scoring
        Based on: content clarity + OCR quality + tag match + domain match
        No arbitrary values.
        """
        if not content or len(content.strip()) < KoshaEnforcer.MIN_CONTENT_LENGTH:
            return 0.0

        # Content clarity score (0.0 - 0.4)
        words = content.split()
        if not words:
            return 0.0
        avg_word_len = sum(len(w) for w in words) / len(words)
        # Ideal word length 4-8 chars
        clarity = min(1.0, max(0.0, 1.0 - abs(avg_word_len - 6) / 10))
        content_score = clarity * 0.4

        # OCR quality score (0.0 - 0.3)
        ocr_score = max(0.0, min(1.0, ocr_quality)) * 0.3

        # Tag match score (0.0 - 0.2)
        tag_score = max(0.0, min(1.0, tag_match)) * 0.2

        # Domain match bonus (0.0 - 0.1)
        domain_score = 0.1 if domain_match else 0.0

        total = content_score + ocr_score + tag_score + domain_score
        return round(min(1.0, max(0.0, total)), 4)

    @staticmethod
    def measure_ocr_quality(text: str) -> float:
        """Measure OCR quality of text (0.0 = garbage, 1.0 = clean)"""
        if not text:
            return 0.0

        total = len(text)
        if total == 0:
            return 0.0

        # Count readable chars
        readable = sum(c.isalnum() or c.isspace() or c in '.,;:!?()-\'"' for c in text)
        base_ratio = readable / total

        # Penalize for noise markers
        noise_markers = ['', '|', '@', '~', 'digitized', 'public domain']
        noise_hits = sum(text.lower().count(m) for m in noise_markers)
        noise_penalty = min(0.5, noise_hits * 0.1)

        # Penalize for broken line structure (many single-word lines)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if lines:
            single_word_lines = sum(1 for l in lines if len(l.split()) <= 1)
            fragmentation_penalty = min(0.3, (single_word_lines / len(lines)) * 0.3)
        else:
            fragmentation_penalty = 0.3

        quality = base_ratio - noise_penalty - fragmentation_penalty
        return round(max(0.0, min(1.0, quality)), 4)

    @classmethod
    def build_entry(
        cls,
        content: str,
        source: str,
        domain_hint: str = "",
        query: str = "",
        tag_match_score: float = 0.0,
    ) -> Optional[KoshaEntry]:
        """
        Build a validated KoshaEntry from raw content.
        Returns None if content fails quality checks.
        """
        # Step 1: Purify OCR
        clean = OCRPurifier.clean(content)
        if not clean:
            logger.warning(f"OCR purification rejected content from {source}")
            return None

        # Step 2: Enforce minimum length
        if len(clean) < cls.MIN_CONTENT_LENGTH:
            logger.warning(f"Content too short ({len(clean)} chars) from {source}")
            return None

        # Step 3: Reject "I don't know" content
        if cls._is_non_answer(clean):
            logger.warning(f"Non-answer content rejected from {source}")
            return None

        # Step 4: Infer domain
        domain = cls.infer_domain(clean, source, domain_hint)

        # Step 5: Extract tags
        tags = cls.extract_tags(clean, source)

        # Step 6: Compute real confidence
        ocr_quality = cls.measure_ocr_quality(content)  # Use original for quality measure
        domain_match = domain != "general"
        confidence = cls.compute_confidence(
            content=clean,
            source=source,
            ocr_quality=ocr_quality,
            tag_match=tag_match_score,
            domain_match=domain_match,
        )

        if confidence < cls.MIN_CONFIDENCE:
            logger.warning(f"Confidence too low ({confidence}) for content from {source}")
            return None

        try:
            entry = KoshaEntry(
                knowledge_id=f"KOSHA_{uuid.uuid4().hex[:12]}",
                domain=domain,
                content=clean,
                source=source,
                confidence=confidence,
                timestamp=datetime.now(timezone.utc).isoformat(),
                tags=tags,
                clean_content=clean,
            )
            return entry
        except Exception as e:
            logger.error(f"KoshaEntry schema validation failed: {e}")
            return None

    @staticmethod
    def _is_non_answer(text: str) -> bool:
        """Detect content that is not a real answer"""
        lower = text.strip().lower()
        non_answer_phrases = [
            "i don't know",
            "i dont know",
            "not provided in the given context",
            "not provided in the context",
            "no relevant context found",
            "cannot be answered from the provided context",
            "context does not contain",
        ]
        return any(phrase in lower for phrase in non_answer_phrases)

    @classmethod
    def validate_existing_entries(cls, entries: List[KoshaEntry]) -> Dict[str, Any]:
        """
        Validate existing Kosha entries and report quality.
        Returns stats on valid vs rejected entries.
        """
        valid = []
        rejected = []

        for entry in entries:
            issues = []

            # Check content quality
            if not entry.content or len(entry.content.strip()) < cls.MIN_CONTENT_LENGTH:
                issues.append("content_too_short")

            if cls._is_non_answer(entry.content or ""):
                issues.append("non_answer_content")

            # Check OCR quality
            ocr_q = cls.measure_ocr_quality(entry.content or "")
            if ocr_q < 0.3:
                issues.append(f"low_ocr_quality:{ocr_q}")

            # Check domain validity
            if entry.domain not in VALID_DOMAINS:
                issues.append(f"invalid_domain:{entry.domain}")

            # Check confidence is real (not arbitrary)
            if entry.confidence <= 0.0:
                issues.append("zero_confidence")

            if issues:
                rejected.append({"knowledge_id": entry.knowledge_id, "issues": issues})
            else:
                valid.append(entry)

        return {
            "total": len(entries),
            "valid": len(valid),
            "rejected": len(rejected),
            "valid_entries": valid,
            "rejection_details": rejected,
        }
