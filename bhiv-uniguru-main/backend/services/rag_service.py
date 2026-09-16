try:
    from RAG.new_rag_query import get_engine
except ImportError:
    from backend.RAG.new_rag_query import get_engine
import logging
import os

logger = logging.getLogger(__name__)
TOP_K = int(os.getenv("UNIGURU_RAG_TOP_K", "5"))

class RAGService:
    def __init__(self):
        try:
            self.engine = get_engine()
        except Exception as e:
            logger.warning(f"RAG engine not available: {e}")
            self.engine = None

    def search_vectorstore(self, query: str, class_level: str = None, subject: str = None, language: str = None, domain: str = None, doc_type: str = None, topic: str = None):
        """
        Searches the semantic vector store for relevant context.
        """
        if not self.engine:
            return None

        try:
            result = self.engine.answer_question(query, top_k=TOP_K, class_level=class_level, subject=subject, language=language, domain=domain, doc_type=doc_type, topic=topic)
            if not result or not result.get("retrieved"):
                return None

            retrieved = result["retrieved"]
            top_score = max((float(chunk.get("score") or 0.0) for chunk in retrieved), default=0.0)
            return {
                "answer": result.get("answer", ""),
                "confidence": top_score,
                "source": "vectorstore",
                "retrieved": retrieved
            }
        except Exception as e:
            logger.error(f"RAG search error: {str(e)}")
            return None

rag_service = RAGService()
