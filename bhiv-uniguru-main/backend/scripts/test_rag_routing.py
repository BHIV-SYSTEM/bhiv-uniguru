import sys
import os

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.query_classifier import query_classifier
from services.rag_service import rag_service
from retrieval.retriever import retrieve_knowledge_with_trace

queries = [
    "What are the rules of grammar?",
    "What are Newton's laws?",
    "Explain photosynthesis.",
    "Who is Rishabhadeva?",
    "What is the capital of India?"
]

def run_tests():
    print("Starting RAG Routing Tests...\n")
    for q in queries:
        print(f"--- Query: {q} ---")
        
        # 1. Test Classifier
        cls = query_classifier.classify_query(q)
        print(f"Classification: {cls}")
        
        # 2. Try Unified Ontology Retriever First
        content, trace = retrieve_knowledge_with_trace(
            q,
            class_level=cls.get("class_level"),
            subject=cls.get("subject"),
            domain=cls.get("domain")
        )
        
        if content and trace.get("match_found") and float(trace.get("confidence") or 0) >= 0.30:
            print(f"Unified Retriever Match (Confidence: {trace.get('confidence')})")
            print(f"Content length: {len(content)}")
        else:
            # 3. Test RAG Retrieval
            res = rag_service.search_vectorstore(
                q,
                class_level=cls.get("class_level"),
                subject=cls.get("subject"),
                domain=cls.get("domain")
            )
            
            if res:
                print(f"Vector Store Match (Confidence: {res['confidence']})")
                print(f"Answer snippet: {res['answer'][:150]}...")
            else:
                print("No match found in vector store.")
        print("\n")

if __name__ == "__main__":
    run_tests()
