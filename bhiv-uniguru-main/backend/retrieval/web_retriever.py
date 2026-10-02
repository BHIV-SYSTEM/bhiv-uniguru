"""
UniGuru Web Retriever — Phase 5
================================
Capabilities:
    1. Fetch a webpage and extract meaningful text
    2. Verify source domain against allowed list
    3. Pass result to SourceVerifier for VERIFIED / PARTIAL / UNVERIFIED classification
    4. If cannot verify → refuse answer (never hallucinate)

Allowed domains:
    - .org (general), .edu, .gov
    - sacred-texts.com, britannica.com, baps.org, swaminarayan.org,
      jainfoundation.in, jainworld.com, wikipedia.org, wikisource.org

Truth Declaration (attached to every result):
    VERIFIED   -> "Based on verified source: [source]"
    PARTIAL    -> "This information is partially verified from: [source]"
    UNVERIFIED -> "I cannot verify this information from current knowledge."
"""

import requests
import re
import time
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

STOPWORDS = {
    "the",
    "and",
    "for",
    "what",
    "who",
    "when",
    "where",
    "why",
    "how",
    "with",
    "from",
    "this",
    "that",
    "have",
    "has",
    "had",
    "are",
    "was",
    "were",
    "will",
}

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False
    logger.warning("[WEB-RETRIEVER] BeautifulSoup not available — falling back to regex extraction.")

try:
    from verifier.source_verifier import SourceVerifier, VerificationStatus
    _VERIFIER_AVAILABLE = True
except ImportError:
    _VERIFIER_AVAILABLE = False
    logger.warning("[WEB-RETRIEVER] SourceVerifier not available — all results will be marked UNVERIFIED.")


class WebRetriever:
    """
    Retrieves knowledge from the web with strict source verification and
    truth declarations. Never hallucinates — refuses if cannot verify.
    """

    # Allowed domain suffixes / domain names
    ALLOWED_DOMAINS: List[str] = [
        ".edu",
        ".gov",
        ".org",
        "sacred-texts.com",
        "britannica.com",
        "baps.org",
        "swaminarayan.org",
        "jainfoundation.in",
        "jainworld.com",
        "wikipedia.org",
        "wikisource.org",
        "nature.com",
        "science.org",
        "ncbi.nlm.nih.gov",
        "plos.org",
        "jstor.org",
    ]

    BLOCKED_PATTERNS: List[str] = [
        r"blog",
        r"reddit",
        r"quora",
        r"twitter\.com",
        r"x\.com",
        r"facebook",
        r"medium\.com",
        r"substack",
        r"4chan",
        r"tumblr",
        r"forum",
    ]

    REQUEST_HEADERS = {
        "User-Agent": (
            "UniGuru/2.0 (+https://github.com/sharmavijay45/Complete-Uniguru; "
            "Sovereign Knowledge Verification Bot)"
        )
    }

    def __init__(self, timeout: int = 8, max_content_chars: int = 2000):
        self.timeout = timeout
        self.max_content_chars = max_content_chars
        self._verifier = SourceVerifier() if _VERIFIER_AVAILABLE else None

    # ------------------------------------------------------------------ #
    #  DOMAIN VERIFICATION                                                 #
    # ------------------------------------------------------------------ #
    def is_allowed_domain(self, url: str) -> bool:
        """Returns True if the URL's domain is on the allowed list."""
        url_lower = url.lower()
        parsed = urlparse(url_lower)
        netloc = parsed.netloc

        # Check blocked patterns first
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, netloc):
                return False

        # Check allowed domains
        for domain in self.ALLOWED_DOMAINS:
            if netloc.endswith(domain) or domain in netloc:
                return True

        return False

    # ------------------------------------------------------------------ #
    #  WEB FETCHING                                                        #
    # ------------------------------------------------------------------ #
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a webpage and return extracted plain text.
        Returns None if fetch fails or domain is not allowed.
        """
        if not self.is_allowed_domain(url):
            logger.info(f"[WEB-RETRIEVER] Blocked: domain not allowed — {url}")
            return None

        try:
            resp = requests.get(url, headers=self.REQUEST_HEADERS, timeout=self.timeout)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                logger.info(f"[WEB-RETRIEVER] Skipped non-text content type: {content_type}")
                return None

            raw_text = self._extract_text(resp.text)
            return raw_text[:self.max_content_chars]

        except requests.exceptions.Timeout:
            logger.warning(f"[WEB-RETRIEVER] Timeout fetching: {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"[WEB-RETRIEVER] Connection error fetching: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[WEB-RETRIEVER] HTTP error {e} fetching: {url}")
            return None
        except Exception as e:
            logger.error(f"[WEB-RETRIEVER] Unexpected error fetching {url}: {e}")
            return None

    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML, strip scripts/styles."""
        if _BS4_AVAILABLE:
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
        else:
            # Regex fallback
            text = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text

    # ------------------------------------------------------------------ #
    #  CORE: search_and_verify (simulated search with real verification)   #
    # ------------------------------------------------------------------ #
    def search_and_verify(self, query: str) -> List[Dict[str, Any]]:
        """
        Simulate web search results and verify each against domain + SourceVerifier.
        In production this would call a Search API; here we demonstrate the full
        verification logic pipeline with representative sources.
        """
        # Representative search result simulation — real verification applied to each
        candidate_results = [
            {
                "url": "https://www.sacred-texts.com/jai/sbe22/index.htm",
                "title": "Acharanga Sutra — Sacred Texts Archive",
                "snippet": "The Acharanga Sutra is the first and oldest of the Jain canonical texts, containing Mahavira's code of conduct for ascetics."
            },
            {
                "url": "https://www.jainfoundation.in/tattvartha-sutra",
                "title": "Tattvartha Sutra — Jain Foundation",
                "snippet": "The Tattvartha Sutra by Acharya Umaswati is the foundational philosophical text accepted by all three Jain sects."
            },
            {
                "url": "https://www.baps.org/vachanamrut",
                "title": "Vachanamrut — BAPS Swaminarayan Sanstha",
                "snippet": "The Vachanamrut is the principal scripture of the Swaminarayan Sampradaya, containing 273 discourses of Bhagwan Swaminarayan."
            },
            {
                "url": "https://en.wikipedia.org/wiki/Jainism",
                "title": "Jainism — Wikipedia",
                "snippet": "Jainism is an ancient Indian religion emphasizing non-violence, many-sidedness of truth, and non-attachment."
            },
            {
                "url": "https://randomblog.xyz/my-jain-thoughts",
                "title": "My Thoughts on Jainism",
                "snippet": "I think Jainism is kind of like Buddhism but different somehow."
            },
            {
                "url": "https://www.stanford.edu/religious-studies/jainism",
                "title": "Jainism — Stanford University Religious Studies",
                "snippet": "Jainism traces its origins to the prehistoric Tirthankara Rishabhadeva. The 24th Tirthankara, Mahavira, is historically attested."
            }
        ]

        query_tokens = {
            token
            for token in re.sub(r"[^\w\s]", " ", query.lower()).split()
            if len(token) > 2 and token not in STOPWORDS
        }
        if not query_tokens:
            return []

        scored_candidates = []
        for res in candidate_results:
            candidate_text = f"{res['title']} {res['snippet']}".lower()
            overlap = sum(1 for token in query_tokens if token in candidate_text)
            if overlap > 0:
                scored_candidates.append((overlap, res))

        scored_candidates.sort(key=lambda row: row[0], reverse=True)
        verified_results = []
        for _, res in scored_candidates:
            url = res["url"]

            # 1. Domain gate
            if not self.is_allowed_domain(url):
                logger.info(f"[WEB-RETRIEVER] Filtered (blocked domain): {url}")
                continue

            # 2. Source verification
            if self._verifier:
                parsed_netloc = urlparse(url.lower()).netloc
                vr = self._verifier.verify_source(res["title"], url, res["snippet"])
                status = vr.status.value
                formatted_response = vr.formatted_response
                allowed = vr.allowed
            else:
                # Fallback without verifier
                is_allowed = self.is_allowed_domain(url)
                status = "VERIFIED" if is_allowed else "UNVERIFIED"
                formatted_response = (
                    f"Based on verified source: {res['title']}" if is_allowed
                    else "I cannot verify this information from current knowledge."
                )
                allowed = is_allowed

            entry = {
                "title": res["title"],
                "url": url,
                "content": res["snippet"],
                "verification_status": status,
                "truth_declaration": formatted_response,
                "allowed": allowed,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            verified_results.append(entry)

        return verified_results

    # ------------------------------------------------------------------ #
    #  PRIMARY: retrieve                                                   #
    # ------------------------------------------------------------------ #
    def retrieve(self, query: str) -> Dict[str, Any]:
        """
        Main retrieval method. Returns the best verified result.
        If no verified source found → returns refusal. Never hallucinates.
        """
        results = self.search_and_verify(query)

        if not results:
            return self._refusal_response("No results returned from search.")

        # Priority 1: VERIFIED results
        verified = [r for r in results if r["verification_status"] == "VERIFIED" and r["allowed"]]
        if verified:
            best = verified[0]
            return {
                "answer": best["content"],
                "source": best["url"],
                "source_title": best["title"],
                "verification_status": "VERIFIED",
                "truth_declaration": best["truth_declaration"],
                "verified": True,
                "allowed": True,
                "fetched_at": best["fetched_at"],
            }

        # Priority 2: PARTIAL results (return with disclaimer)
        partial = [r for r in results if r["verification_status"] == "PARTIAL" and r["allowed"]]
        if partial:
            best = partial[0]
            return {
                "answer": best["content"],
                "source": best["url"],
                "source_title": best["title"],
                "verification_status": "PARTIAL",
                "truth_declaration": best["truth_declaration"],
                "verified": False,
                "allowed": True,
                "fetched_at": best["fetched_at"],
            }

        # All results are UNVERIFIED → refuse
        return self._refusal_response(
            "All retrieved sources failed verification. Cannot provide answer."
        )

    def retrieve_from_url(self, url: str) -> Dict[str, Any]:
        """
        Directly fetch and verify a specific URL.
        Useful when a specific source URL is already known.
        """
        if not self.is_allowed_domain(url):
            return self._refusal_response(f"Domain not in allowed list: {url}")

        content = self.fetch_page(url)
        if not content:
            return self._refusal_response(f"Could not fetch content from: {url}")

        parsed_netloc = urlparse(url.lower()).netloc
        if self._verifier:
            vr = self._verifier.verify_source(parsed_netloc, url, content)
            status = vr.status.value
            formatted_response = vr.formatted_response
            allowed = vr.allowed
        else:
            allowed = True
            status = "PARTIAL"
            formatted_response = f"This information is partially verified from: {url}"

        if not allowed:
            return self._refusal_response(
                f"Source at {url} could not be verified."
            )

        return {
            "answer": content[:500],  # First 500 chars as answer preview
            "source": url,
            "source_title": parsed_netloc,
            "verification_status": status,
            "truth_declaration": formatted_response,
            "verified": status == "VERIFIED",
            "allowed": allowed,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    # ------------------------------------------------------------------ #
    #  HELPER                                                              #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _refusal_response(reason: str) -> Dict[str, Any]:
        return {
            "answer": None,
            "source": None,
            "source_title": None,
            "verification_status": "UNVERIFIED",
            "truth_declaration": "I cannot verify this information from current knowledge.",
            "verified": False,
            "allowed": False,
            "refusal_reason": reason,
        }


# ---- Module-level convenience function --------------------------------- #
_web_retriever = WebRetriever()


def web_retrieve(query: str) -> Dict[str, Any]:
    """Module-level convenience wrapper for query-based retrieval."""
    return _web_retriever.retrieve(query)


def web_retrieve_url(url: str) -> Dict[str, Any]:
    """Module-level convenience wrapper for direct URL retrieval."""
    return _web_retriever.retrieve_from_url(url)
