import sys
import os
import json
import time
from fastapi.testclient import TestClient

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
backend_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(backend_path)

from service.api import app

client = TestClient(app)

questions = [
    "Name any one Upanishad.",
    "Which text is related to Ayurveda?",
    "What type of text is the Kama Sutra?",
    "Which texts describe stories of gods and creation?",
    "Name one Smriti text.",
    "Translate “अहिंसा परमो धर्मः”",
    "Translate “कर्म करो”",
    "Name one text related to Dharma Shastra.",
    "Which text explains law and social rules?",
    "Name one Agama text.",
    "Which text is related to Vedas?",
    "How is disease defined in Charaka Samhita?",
    "Which text discusses both law and punishment systems?",
    "How do Agamas differ from Vedas?",
    "How does the Taittiriya Upanishad explain Brahman?",
]

def run_tests(questions, endpoint):
    results = []
    for q in questions:
        print(f"Testing on {endpoint}: {q}")
        payload = {
            "query": q,
            "intent": "information_retrieval",
            "context": {},
            "allow_generated_verse": True
        }
        
        try:
            response = client.post(endpoint, json=payload, headers={"Authorization": "Bearer uniguru_secret_123"})
            if response.status_code == 200:
                results.append({"endpoint": endpoint, "query": q, "response": response.json()})
            else:
                results.append({"endpoint": endpoint, "query": q, "error": response.text})
        except Exception as e:
            results.append({"endpoint": endpoint, "query": q, "error": str(e)})
        time.sleep(12)
    return results

print("Running /new_query tests...")
query_results = run_tests(questions, "/new_query")

print("Running /new_rag tests...")
rag_results = run_tests(questions, "/new_rag")

all_results = query_results + rag_results

out_path = r"C:\Users\Yashika\uniguru_v2\review_packets\test_logs.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=4, ensure_ascii=False)

print(f"Testing complete. Results saved to {out_path}.")
