"""
UniGuru Source Verification Engine - Hardened v3
================================================
Classifies sources into three tiers:
    VERIFIED   - Official, authoritative, confirmed source
    PARTIAL    - Source exists but is not fully canonical
    UNVERIFIED - Unknown, anonymous, or non-authoritative

Truth policy:
    VERIFIED   -> allowed
    PARTIAL    -> allowed only with explicit disclaimer
    UNVERIFIED -> always refused
"""

import re
from typing import Optional, Dict, Any
from enum import Enum


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"


class SourceVerificationResult:
    """Encapsulates the outcome of a source verification check."""

    def __init__(
        self,
        status: VerificationStatus,
        source_name: str,
        reason: str,
        formatted_response: str,
        allowed: bool,
    ):
        self.status = status
        self.source_name = source_name
        self.reason = reason
        self.formatted_response = formatted_response
        self.allowed = allowed

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "source_name": self.source_name,
            "reason": self.reason,
            "formatted_response": self.formatted_response,
            "allowed": self.allowed,
        }

    def __repr__(self) -> str:
        return (
            f"SourceVerificationResult(status={self.status}, "
            f"source={self.source_name!r}, allowed={self.allowed})"
        )


class SourceVerifier:
    """
    Hardened Source Verification Engine v3.

    Rules:
    - VERIFIED   -> Allowed with verified prefix.
    - PARTIAL    -> Allowed only with disclaimer.
    - UNVERIFIED -> Must refuse answer.

    Also maintains backward-compatible static methods used by retrieval.
    """

    VERIFIED_DOMAINS = [
        ".edu",
        ".gov",
        "sacred-texts.com",
        "britannica.com",
        "baps.org",
        "swaminarayan.org",
        "jainfoundation.in",
        "jainworld.com",
        "nature.com",
        "science.org",
        "plos.org",
        "ncbi.nlm.nih.gov",
        "jstor.org",
        "wikipedia.org",
        "wikisource.org",
    ]

    VERIFIED_SOURCE_NAMES = [
        "tattvartha sutra",
        "acharanga sutra",
        "uttaradhyayana sutra",
        "sutrakritanga",
        "kalpa sutra",
        "adi purana",
        "karmagranthas",
        "vachanamrut",
        "shikshapatri",
        "swamini vato",
        "bhaktachintamani",
        "purushottam prakash",
        "chosath pad",
        "sacred books of the east",
        "encyclopaedia britannica",
        "encyclopaedia of jainism",
        "baps akshar-purushottam darshan",
        "uniguru kb",
        "gurukul curriculum",
        "gurukul verified text",
    ]

    PARTIAL_INDICATORS = [
        "secondary source",
        "commentary",
        "interpretation",
        "translation note",
        "oral tradition",
        "tradition holds",
    ]

    UNCERTAIN_INDICATORS = [
        "maybe",
        "possibly",
        "uncertain",
        "unconfirmed",
        "might be",
        "not sure",
        "probably",
        "i think",
        "guesstimate",
        "not certain",
        "likely",
        "perhaps",
    ]

    UNVERIFIED_PATTERNS = [
        r"blog",
        r"reddit",
        r"quora",
        r"twitter",
        r"x\.com",
        r"facebook",
        r"anonymous",
        r"unknown",
        r"unconfirmed",
        r"forum",
        r"4chan",
        r"tumblr",
        r"medium\.com",
        r"substack",
    ]

    def verify_source(
        self,
        source_name: str,
        source_url: Optional[str] = None,
        content: Optional[str] = None,
    ) -> SourceVerificationResult:
        """Verify a source by name and optional URL/content."""
        name_lower = source_name.lower().strip()
        url_lower = (source_url or "").lower().strip()
        content_lower = (content or "").lower()

        if self._is_unverified(name_lower, url_lower):
            return self._make_result(
                VerificationStatus.UNVERIFIED,
                source_name,
                "Source matches unverified domain or pattern.",
            )

        if self._is_uncertain(content_lower):
            return self._make_result(
                VerificationStatus.UNVERIFIED,
                source_name,
                "Verification uncertain. Refusing answer by truth-gate policy.",
            )

        if self._is_verified_canonical(name_lower, url_lower):
            return self._make_result(
                VerificationStatus.VERIFIED,
                source_name,
                "Source matches canonical verified list.",
            )

        if self._is_partial(name_lower, content_lower):
            return self._make_result(
                VerificationStatus.PARTIAL,
                source_name,
                "Source is plausible but not fully verified.",
            )

        return self._make_result(
            VerificationStatus.UNVERIFIED,
            source_name,
            "Source could not be matched to any known classification.",
        )

    def verify_from_kb_file(self, kb_file_path: str) -> SourceVerificationResult:
        """Verify a source from YAML frontmatter of a KB markdown file."""
        try:
            with open(kb_file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            return self._make_result(
                VerificationStatus.UNVERIFIED, kb_file_path, "File not found."
            )

        frontmatter = self._extract_frontmatter(content)
        vs_raw = frontmatter.get("verification_status", "").upper()
        source_name = str(frontmatter.get("source") or frontmatter.get("title") or "Unknown Source")
        source_url = str(frontmatter.get("url") or "")

        if vs_raw == "VERIFIED":
            return self._make_result(
                VerificationStatus.VERIFIED,
                source_name,
                "KB file declares VERIFIED status.",
            )
        if vs_raw == "PARTIAL":
            return self._make_result(
                VerificationStatus.PARTIAL,
                source_name,
                "KB file declares PARTIAL status.",
            )
        if vs_raw == "UNVERIFIED":
            return self._make_result(
                VerificationStatus.UNVERIFIED,
                source_name,
                "KB file declares UNVERIFIED status.",
            )

        return self.verify_source(source_name, source_url, content)

    def build_answer_with_disclaimer(
        self, answer_content: str, verification_result: SourceVerificationResult
    ) -> str:
        """Prepend the verification prefix to answer content."""
        if not verification_result.allowed:
            raise ValueError("Cannot build answer for UNVERIFIED source. Must refuse answer.")
        prefix = self.verification_prefix(verification_result.status, verification_result.source_name)
        return f"{prefix}\n\n{answer_content}"

    @staticmethod
    def verification_prefix(status: VerificationStatus, source_name: str) -> str:
        if status == VerificationStatus.VERIFIED:
            return f"Based on verified source: {source_name}"
        if status == VerificationStatus.PARTIAL:
            return f"This information is partially verified from: {source_name}"
        return "Verification status: UNVERIFIED"

    @staticmethod
    def verify(retrieval_result: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy static interface: enhances retrieval result with verification metadata."""
        if not retrieval_result.get("verified"):
            retrieval_result["truth_declaration"] = "UNVERIFIED"
            retrieval_result["verification_status"] = VerificationStatus.UNVERIFIED.value
            retrieval_result["formatted_response"] = "Verification status: UNVERIFIED"
            retrieval_result["allowed"] = False
            return retrieval_result

        source = retrieval_result.get("source_file")
        author = retrieval_result.get("author", "Unknown")

        if source and author != "Unknown":
            retrieval_result["truth_declaration"] = "VERIFIED"
            retrieval_result["verification_level"] = "HIGH"
            retrieval_result["verification_status"] = VerificationStatus.VERIFIED.value
            retrieval_result["formatted_response"] = f"Based on verified source: {source}"
            retrieval_result["allowed"] = True
        elif source:
            retrieval_result["truth_declaration"] = "VERIFIED_PARTIAL"
            retrieval_result["verification_level"] = "MEDIUM"
            retrieval_result["verification_status"] = VerificationStatus.PARTIAL.value
            retrieval_result["formatted_response"] = (
                f"This information is partially verified from: {source}"
            )
            retrieval_result["allowed"] = True
        else:
            retrieval_result["truth_declaration"] = "UNVERIFIED"
            retrieval_result["verification_level"] = "LOW"
            retrieval_result["verification_status"] = VerificationStatus.UNVERIFIED.value
            retrieval_result["formatted_response"] = "Verification status: UNVERIFIED"
            retrieval_result["allowed"] = False

        return retrieval_result

    @staticmethod
    def verify_retrieval_trace(trace: Dict[str, Any], min_confidence: float = 0.5) -> Dict[str, Any]:
        """Normalizes retrieval trace output and runs verification with confidence gate."""
        confidence = float(trace.get("confidence", 0.0) or 0.0)
        source_file = trace.get("kb_file") or trace.get("source") or trace.get("source_file")
        payload = {
            "verified": bool(trace.get("match_found")) and confidence >= min_confidence and bool(source_file),
            "source_file": source_file,
            "author": "UniGuru KB",
            "confidence": confidence,
            "confidence_threshold": min_confidence,
        }
        return SourceVerifier.verify(payload)

    def _is_unverified(self, name_lower: str, url_lower: str) -> bool:
        combined = name_lower + " " + url_lower
        return any(re.search(p, combined) for p in self.UNVERIFIED_PATTERNS)

    def _is_verified_canonical(self, name_lower: str, url_lower: str) -> bool:
        for src in self.VERIFIED_SOURCE_NAMES:
            if src in name_lower:
                return True
        for domain in self.VERIFIED_DOMAINS:
            if domain in url_lower:
                return True
        return False

    def _is_partial(self, name_lower: str, content_lower: str) -> bool:
        if not name_lower and not content_lower:
            return False
        for indicator in self.PARTIAL_INDICATORS:
            if indicator in name_lower or indicator in content_lower:
                return True
        return False

    def _is_uncertain(self, content_lower: str) -> bool:
        return any(indicator in content_lower for indicator in self.UNCERTAIN_INDICATORS)

    def _make_result(
        self, status: VerificationStatus, source_name: str, reason: str
    ) -> SourceVerificationResult:
        if status == VerificationStatus.VERIFIED:
            formatted = f"Based on verified source: {source_name}"
            allowed = True
        elif status == VerificationStatus.PARTIAL:
            formatted = f"This information is partially verified from: {source_name}"
            allowed = True
        else:
            formatted = "Verification status: UNVERIFIED. I cannot verify this information from current knowledge."
            allowed = False

        return SourceVerificationResult(
            status=status,
            source_name=source_name,
            reason=reason,
            formatted_response=formatted,
            allowed=allowed,
        )

    @staticmethod
    def _extract_frontmatter(content: str) -> dict:
        result = {}
        lines = content.splitlines()
        in_fm = False
        for line in lines:
            stripped = line.strip()
            if stripped == "---":
                if not in_fm:
                    in_fm = True
                    continue
                break
            if in_fm and ":" in stripped:
                key, _, value = stripped.partition(":")
                result[key.strip().lower()] = value.strip()
        return result


_verifier_instance = SourceVerifier()


def verify_source(
    source_name: str,
    source_url: Optional[str] = None,
    content: Optional[str] = None,
) -> SourceVerificationResult:
    """Module-level convenience wrapper."""
    return _verifier_instance.verify_source(source_name, source_url, content)


def verify_kb_file(kb_file_path: str) -> SourceVerificationResult:
    """Verify a KB file's source from its frontmatter."""
    return _verifier_instance.verify_from_kb_file(kb_file_path)
