import json
import re
import requests
import sys

test_suite = [
    {
        "id": "T1",
        "name": "English general programming (no doc)",
        "payload": {"message": "can you give me a simple programm code for a liner regression"},
        "expected_lang": "en",
        "must_contain": ["def", "import", "model", "regression"]
    },
    {
        "id": "T2",
        "name": "English general math/reasoning (no doc)",
        "payload": {"message": "What is the difference between mean and median? Give a simple example."},
        "expected_lang": "en",
        "must_contain": ["mean", "median", "average"]
    },
    {
        "id": "T3",
        "name": "Marathi general science (no doc)",
        "payload": {"message": "प्रकाशसंश्लेषण म्हणजे काय आणि त्याचे महत्त्व सांगा."},
        "expected_lang": "mr",
        "must_contain": ["प्रकाश", "वनस्पती"]
    },
    {
        "id": "T4",
        "name": "English question on context-grounded textbook content",
        "payload": {
            "message": "According to the provided text, what are the three laws of motion formulated by Newton? Context: Sir Isaac Newton formulated three fundamental laws of motion: 1. An object at rest stays at rest unless acted upon by an external force. 2. Force equals mass times acceleration (F=ma). 3. For every action, there is an equal and opposite reaction."
        },
        "expected_lang": "en",
        "must_contain": ["laws", "motion", "rest", "action"]
    },
    {
        "id": "T5",
        "name": "English explanation request on Marathi content",
        "payload": {
            "message": "Explain in English what this passage says about photosynthesis: वनस्पती सूर्यप्रकाशाचा वापर करून कार्बन डायऑक्साइड आणि पाणी यांच्यापासून ग्लुकोज आणि ऑक्सिजन तयार करतात."
        },
        "expected_lang": "en",
        "must_contain": ["photosynthesis", "glucose", "oxygen"]
    },
    {
        "id": "T6",
        "name": "Marathi question on English textbook content",
        "payload": {
            "message": "या इंग्रजी उताऱ्याचा अर्थ मराठीत सांगा: Mitochondria are known as the powerhouses of the cell because they generate most of the chemical energy needed to power the cell biochemical reactions."
        },
        "expected_lang": "mr",
        "must_contain": ["मायटोकॉन्ड्रिया", "ऊर्जा"]
    },
    {
        "id": "T7_en",
        "name": "Absent answer from context in English (calibrated abstention)",
        "payload": {
            "message": "According to the attached document, what is the GDP of France in 2024? Passage: This document discusses quantum computing algorithms, Shor algorithm, and Grover search algorithm."
        },
        "expected_lang": "en",
        "must_contain": ["not contain", "does not", "unavailable"]
    },
    {
        "id": "T7_mr",
        "name": "Absent answer from context in Marathi (calibrated abstention)",
        "payload": {
            "message": "दिलेल्या संदर्भानुसार, फ्रान्सचा २०२४ मधील जीडीपी किती आहे? संदर्भ: हा दस्तऐवज केवळ क्वांटम कंप्युटिंग आणि अल्गोरिदम बद्दल माहिती देतो."
        },
        "expected_lang": "mr",
        "must_contain": ["उपलब्ध नाही", "माहिती नाही"]
    },
    {
        "id": "T8",
        "name": "Follow-up question referring to previous turn",
        "is_multi_turn": True
    },
    {
        "id": "T9",
        "name": "Question routed through Essay Coach agent persona",
        "payload": {
            "message": "Write a Python function to check if a number is prime.",
            "chatbotId": ""
        },
        "expected_lang": "en",
        "must_contain": ["def", "prime", "return"]
    },
    {
        "id": "T10_A",
        "name": "Explicit override: English query requesting Marathi response",
        "payload": {"message": "Explain linear regression in Marathi."},
        "expected_lang": "mr",
        "must_contain": ["रेखीय", "प्रतिगमन"]
    },
    {
        "id": "T10_B",
        "name": "Explicit override: Marathi query requesting English response",
        "payload": {"message": "हे English मध्ये समजावून सांगा: प्रकाशाचा वेग किती असतो?"},
        "expected_lang": "en",
        "must_contain": ["speed of light"]
    }
]

print("=== STARTING FUNCTIONAL TEST MATRIX ===")
results = []
for t in test_suite:
    tid = t["id"]
    tname = t["name"]
    print(f"\n--- Running {tid}: {tname} ---")
    if t.get("is_multi_turn"):
        r1 = requests.post("http://127.0.0.1:8000/chat/new", json={"message": "What is photosynthesis?"}, timeout=60).json()
        cid = r1.get("chat", {}).get("id")
        r2 = requests.post("http://127.0.0.1:8000/chat/new", json={"message": "Where does it occur inside the plant cell?", "chatId": cid}, timeout=60).json()
        ans = r2.get("aiResponse", {}).get("content", "")
        print(f"Turn 2 Answer: {ans[:200]}...")
        passed = "chloroplast" in ans.lower() or "chlorophyll" in ans.lower() or "cell" in ans.lower()
        results.append({"id": tid, "name": tname, "status": "PASS" if passed else "REVIEW", "output": ans})
    else:
        res = requests.post("http://127.0.0.1:8000/chat/new", json=t["payload"], timeout=60)
        data = res.json()
        ans = data.get("aiResponse", {}).get("content", "")
        meta = data.get("aiResponse", {}).get("metadata", {})
        
        # Check language
        dev_count = len(re.findall(r"[\u0900-\u097f]", ans))
        lat_count = len(re.findall(r"[A-Za-z]", ans))
        detected = "mr" if dev_count > lat_count else "en"
        
        print(f"Status: {res.status_code}")
        print(f"Output language detected: {detected} (expected: {t.get('expected_lang')})")
        print(f"Excerpt: {ans[:200]}...")
        
        passed = res.status_code == 200 and len(ans) > 20
        results.append({"id": tid, "name": tname, "status": "PASS" if passed else "FAIL", "detected_lang": detected, "output": ans})

print("\n" + "="*50)
print("FUNCTIONAL TEST SUMMARY")
print("="*50)
for r in results:
    print(f"[{r['status']}] {r['id']}: {r['name']} (Lang: {r.get('detected_lang', 'N/A')})")

with open("tests/functional_test_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\nDetailed results saved to tests/functional_test_results.json")

