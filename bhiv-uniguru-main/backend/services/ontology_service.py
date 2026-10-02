try:
    from retrieval.retriever import AdvancedRetriever
except ImportError:
    from backend.retrieval.retriever import AdvancedRetriever
import logging

logger = logging.getLogger(__name__)

class OntologyService:
    def __init__(self):
        self.retriever = AdvancedRetriever()

    def get_deterministic_answer(self, query: str):
        """
        Attempts to find an answer in the verified knowledge ontology.
        """
        try:
            results = self.retriever.retrieve_multi(query)
            if not results:
                return None
            
            # Use the reason_and_compare logic to find the best match
            best_match = self.retriever.reason_and_compare(results)
            
            if best_match.get("decision") == "answer":
                return {
                    "answer": best_match.get("content"),
                    "confidence": float(best_match.get("metadata", {}).get("top_confidence", 0.0)),
                    "source": "ontology"
                }
            return None
        except Exception as e:
            logger.error(f"Ontology retrieval error: {str(e)}")
            return None

ontology_service = OntologyService()
