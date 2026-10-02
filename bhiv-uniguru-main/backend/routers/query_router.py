from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body
try:
    from services.validation_service import validation_service
    from services.ontology_service import ontology_service
    from services.rag_service import rag_service
    from services.response_formatter import response_formatter
except ImportError:
    from backend.services.validation_service import validation_service
    from backend.services.ontology_service import ontology_service
    from backend.services.rag_service import rag_service
    from backend.services.response_formatter import response_formatter
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["Intelligence"])

from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    query: str = Field("", description="The user question or query.")
    question: str = Field("", description="Alternative key for the user question.")
    subject: Optional[str] = Field(None, description="Optional subject/topic selection from UI (e.g., Programming)")
    class_level: Optional[str] = Field(None, description="Target class level (e.g. '10')")
    language: Optional[str] = Field(None, description="Language for knowledge base filter")

@router.post("/ask")
async def ask_uniguru(request: QueryRequest):
    """
    Unified intelligence endpoint with deterministic priority and local LLM fallback.
    """
    try:
        # Support both 'query' and 'question' keys for better compatibility
        query = request.query or request.question
        logger.info(f"Received intelligence query: {query}")
        print(f"> Intelligence Request: {query}")

        clean_query = query.strip().strip("?!.,").lower()
        if clean_query in {"hello", "hi", "hey"}:
            return response_formatter.format_response(
                decision="answer",
                confidence=1.0,
                source="none",
                answer="Hello! How can I help you today?",
            )
        
        # 1. Run Validation
        validation = validation_service.validate_query(query)
        if not validation["is_valid"]:
            logger.warning(f"Query validation failed: {validation['error']}")
            return response_formatter.format_response(
                decision="reject",
                confidence=0.0,
                source="none",
                answer=validation["error"]
            )

        # 1.5 Query Classifier
        try:
            from services.query_classifier import query_classifier
        except ImportError:
            from backend.services.query_classifier import query_classifier
        classification = query_classifier.classify_query(query)
        logger.info(f"Query Classification: {classification}")
        
        c_domain = classification.get("domain")
        c_class = classification.get("class_level") or request.class_level
        c_subject = classification.get("subject") or request.subject
        c_topic = classification.get("topic")
        c_intent = classification.get("intent", "general")

        # 2. Intent-Based Deterministic Retrieval (Ontology / unified retriever)
        logger.info("Attempting deterministic ontology retrieval...")
        try:
            from retrieval.retriever import retrieve_knowledge_with_trace
        except ImportError:
            from backend.retrieval.retriever import retrieve_knowledge_with_trace

        content, trace = retrieve_knowledge_with_trace(
            query, 
            subject=c_subject,
            class_level=c_class,
            language=request.language,
            domain=c_domain
        )
        if content and trace.get("match_found") and float(trace.get("confidence") or 0) >= 0.30:
            logger.info("Unified retriever match with confidence %s", trace.get("confidence"))
            return response_formatter.format_response(
                decision="answer",
                confidence=float(trace.get("confidence") or 0.0),
                source=str(trace.get("method") or "ontology"),
                answer=content,
            )

        ontology_res = ontology_service.get_deterministic_answer(query)
        if ontology_res and ontology_res.get("confidence", 0) >= 0.85:
            logger.info(f"Ontology match found with confidence {ontology_res['confidence']}")
            return response_formatter.format_response(
                decision="answer",
                confidence=ontology_res["confidence"],
                source="ontology",
                answer=ontology_res["answer"]
            )

        # 3. Vector-Based Semantic Retrieval (RAG)
        logger.info("Attempting vector-based semantic retrieval...")
        rag_res = rag_service.search_vectorstore(
            query, 
            class_level=c_class, 
            subject=c_subject, 
            language=request.language,
            domain=c_domain,
            topic=c_topic
        )
        if rag_res and rag_res.get("confidence", 0) >= 0.75:
            retrieved_docs = rag_res.get("retrieved", [])
            is_valid = True
            
            # Retrieval Validation
            if c_domain:
                for doc in retrieved_docs:
                    doc_domain = doc.get("metadata", {}).get("domain", "")
                    if doc_domain and doc_domain.lower() != c_domain.lower():
                        is_valid = False
                        logger.warning(f"Validation failed: Expected domain {c_domain}, but got {doc_domain}")
                        break
            
            if is_valid:
                logger.info(f"Vectorstore match found with confidence {rag_res['confidence']}")
                
                # Debug Information Logging
                print(f"\n--- RAG DEBUG INFO ---")
                print(f"Query: {query}")
                print(f"Detected Intent: {c_intent}")
                print(f"Selected Knowledge Source: domain={c_domain}, class={c_class}, subject={c_subject}, topic={c_topic}")
                print(f"Retrieved Documents: {[d.get('metadata', {}).get('file_name') for d in retrieved_docs]}")
                print(f"Similarity Scores: {[d.get('score') for d in retrieved_docs]}")
                print(f"Final Context sent to LLM: {len(retrieved_docs)} documents.")
                print(f"----------------------\n")
                
                return response_formatter.format_response(
                    decision="answer",
                    confidence=rag_res["confidence"],
                    source="vectorstore",
                    answer=rag_res["answer"]
                )
            else:
                logger.warning("Rejecting context due to retrieval validation failure.")

        # 4. Final Rejection (No Knowledge Found)
        logger.info("No knowledge found in ontology or vectorstore.")
        return response_formatter.format_response(
            decision="reject",
            confidence=0.0,
            source="none",
            answer="I'm sorry, I couldn't find any verified information regarding your query in my knowledge base."
        )
    except Exception as e:
        logger.error(f"Critical error in intelligence router: {str(e)}", exc_info=True)
        print(f"!!! Router Error: {str(e)}")
        return response_formatter.format_response(
            decision="reject",
            confidence=0.0,
            source="none",
            answer=f"An internal error occurred: {str(e)}"
        )
