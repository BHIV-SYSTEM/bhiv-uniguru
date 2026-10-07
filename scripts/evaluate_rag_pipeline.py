"""
Comprehensive RAG Evaluation and Benchmark Test Suite
======================================================
Runs the 20 mandated test queries against:
  1. /ask (Core Router API)
  2. /chat/new (Frontend Interactive Chat API)
  3. /rag/debug (Developer Trace Inspection API)

Outputs results in structured JSON and markdown format for auditing.
"""

import sys
import json
import urllib.request
from typing import Dict, Any, List

# Ensure UTF-8 output encoding on Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

TEST_QUESTIONS = [
    {"id": 1, "category": "Sanskrit Core", "query": "What is Dharma?", "has_kb_answer": True},
    {"id": 2, "category": "Sanskrit Core", "query": "What is Karma?", "has_kb_answer": True},
    {"id": 3, "category": "Sanskrit Core", "query": "Explain Karma Yoga.", "has_kb_answer": True},
    {"id": 4, "category": "Sanskrit Core", "query": "What is the meaning of Yoga?", "has_kb_answer": True},
    {"id": 5, "category": "Sanskrit Core", "query": "What is Atman?", "has_kb_answer": True},
    {"id": 6, "category": "Sanskrit Core", "query": "What is Brahman?", "has_kb_answer": True},
    {"id": 7, "category": "Sanskrit Core", "query": "Explain the concept of Moksha.", "has_kb_answer": True},
    {"id": 8, "category": "Unrelated Negative", "query": "Who won the 2022 FIFA World Cup?", "has_kb_answer": False},
    {"id": 9, "category": "Programming", "query": "How do I create a FastAPI route with Pydantic validation in Python?", "has_kb_answer": False},
    {"id": 10, "category": "Mathematics Curriculum", "query": "What is Number Recognition in Mathematics?", "has_kb_answer": True},
    {"id": 11, "category": "Science Curriculum", "query": "What is Photosynthesis in Science?", "has_kb_answer": True},
    {"id": 12, "category": "Education Curriculum", "query": "What are the learning outcomes for Grade 1 Mathematics in Balbharati?", "has_kb_answer": True},
    {"id": 13, "category": "Class-Specific Curriculum", "query": "What is taught in Class 8 Science for Balbharati?", "has_kb_answer": True},
    {"id": 14, "category": "Source-Specific (Jain)", "query": "What does the Tattvartha Sutra state about the nature of the soul?", "has_kb_answer": True},
    {"id": 15, "category": "Marathi Multilingual", "query": "धर्म म्हणजे काय?", "has_kb_answer": True},
    {"id": 16, "category": "Hindi Multilingual", "query": "कर्म क्या है?", "has_kb_answer": True},
    {"id": 17, "category": "English Core", "query": "What is the concept of Purusha and Prakriti?", "has_kb_answer": True},
    {"id": 18, "category": "Mixed Language", "query": "Karma Yoga का practical meaning काय आहे?", "has_kb_answer": True},
    {"id": 19, "category": "In-KB Verification", "query": "What is the definition of Dharma according to Sanskrit texts?", "has_kb_answer": True},
    {"id": 20, "category": "Out-of-KB Negative", "query": "What is the capital of Peru?", "has_kb_answer": False},
]


def post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 80)
    print("UNIGURU RAG EVALUATION BENCHMARK SUITE")
    print("=" * 80)

    results = []
    passed_count = 0

    for item in TEST_QUESTIONS:
        q_id = item["id"]
        query = item["query"]
        expected_kb = item["has_kb_answer"]
        cat = item["category"]

        print(f"\n--- [Test Q{q_id}] ({cat}) '{query}' ---")

        # 1. Test /chat/new (Frontend API)
        chat_res = post_json("http://localhost:8000/chat/new", {"message": query, "chatbotId": "guru-test"})
        ai_resp = chat_res.get("aiResponse", {})
        chat_answer = ai_resp.get("content", "")
        chat_meta = ai_resp.get("metadata", {})
        chat_ver = chat_meta.get("verification_status", "UNKNOWN")

        # 2. Test /ask (Core Router API)
        ask_res = post_json("http://localhost:8000/ask", {"query": query})
        ask_answer = ask_res.get("answer", "")
        ask_ver = ask_res.get("verification_status", "UNKNOWN")

        # 3. Test /rag/debug (Inspection API)
        debug_res = post_json("http://localhost:8000/rag/debug", {"query": query})
        max_sim = debug_res.get("max_similarity", 0.0)
        is_grounded = debug_res.get("is_grounded", False)
        citations = debug_res.get("citations", [])

        # Evaluate correctness
        if expected_kb:
            # Should be verified and grounded
            is_correct = (chat_ver == "VERIFIED" or is_grounded) and ("I don't have enough verified" not in chat_answer)
        else:
            # Should abstain cleanly without hallucinating
            is_correct = (chat_ver == "NO_VERIFIED_KNOWLEDGE" or not is_grounded or "I don't have enough verified" in chat_answer or "not verify" in ask_answer)

        if is_correct:
            passed_count += 1
            status_label = "[PASS]"
        else:
            status_label = "[FAIL]"

        print(f"  {status_label} Expected KB: {expected_kb} | Grounded: {is_grounded} | Max Sim: {max_sim:.4f}")
        print(f"  /chat/new: Status={chat_ver} | Answer: {chat_answer[:120].replace(chr(10), ' ')}...")
        print(f"  /ask:      Status={ask_ver} | Answer: {ask_answer[:120].replace(chr(10), ' ')}...")
        if citations:
            print(f"  Citations: {citations[:2]}")

        results.append({
            "id": q_id,
            "category": cat,
            "query": query,
            "expected_in_kb": expected_kb,
            "is_grounded": is_grounded,
            "max_similarity": max_sim,
            "chat_status": chat_ver,
            "chat_answer": chat_answer,
            "ask_status": ask_ver,
            "ask_answer": ask_answer,
            "citations": citations,
            "passed": is_correct,
        })

    accuracy = (passed_count / len(TEST_QUESTIONS)) * 100
    print("\n" + "=" * 80)
    print(f"BENCHMARK SUMMARY: {passed_count}/{len(TEST_QUESTIONS)} Passed ({accuracy:.1f}%)")
    print("=" * 80)

    # Save benchmark artifact
    out_file = ROOT_DIR / "curriculum" / "audits" / "rag_benchmark_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({"accuracy": accuracy, "passed": passed_count, "total": len(TEST_QUESTIONS), "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved results to {out_file}")


if __name__ == "__main__":
    main()
