from typing import Dict, Any, List, Optional

from retrieval.kb_engine import retrieve as local_retrieve
from retrieval.web_retriever import web_retrieve

class TruthValidator:
    """
    Final Truth Enforcement Layer for UniGuru.
    Ensures zero hallucination and strict source citation.
    """
    
    @staticmethod
    def validate_and_format(query: str) -> Dict[str, Any]:
        """
        Coordinates between local KB and web retrieval to ensure truth.
        """
        # 1. Try local KB first (Highest Truth Priority)
        local_result = local_retrieve(query)
        
        if local_result.get("verified") and local_result.get("answer") != "I do not have verified knowledge to answer this question.":
            return {
                "response": local_result["answer"],
                "source": local_result["source_file"],
                "author": local_result.get("author", "Verified Text"),
                "status": "VERIFIED_LOCAL_KB",
                "confidence": local_result.get("confidence_level")
            }
            
        # 2. Try Web retrieval if local fails
        web_result = web_retrieve(query)
        
        if web_result.get("verified"):
            return {
                "response": web_result["answer"],
                "source": web_result["source"],
                "status": "VERIFIED_WEB",
                "declaration": "This information is retrieved from a verified academic/governmental source."
            }
            
        if web_result.get("found"):
            return {
                "response": web_result["answer"], # This includes the "could not be fully verified" warning
                "source": web_result["source"],
                "status": "UNVERIFIED_WEB"
            }
            
        # 3. Refusal if NO verified source is found
        return {
            "response": "I do not have verified knowledge to answer this question.",
            "source": None,
            "status": "REFUSED",
            "reason": "No matches found in internal Knowledge Base or verified web sources."
        }

def ask_uniguru(query: str) -> Dict[str, Any]:
    return TruthValidator.validate_and_format(query)
