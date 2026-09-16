import requests
import json
import time

url = "http://localhost:8000/new_rag"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer uniguru_secret_123"
}

queries = [
    # Agriculture
    "reduce water consumption", "organic crop nitrogen legumes", "soil health maintenance",
    "drip irrigation arid", "synthetic fertilizers alternatives", "crop rotation mechanics",
    "harvest yields methods", "rural farming water usage", "plant seed distribution", "legumes vs fertilizers",
    # Urban
    "transit oriented carbon", "urban density traffic reduction", "public transit zoning parameters",
    "high-density metropolitan housing", "carbon footprint urban sprawl", "metropolitan pollution reduction",
    "city building density", "traffic street optimization", "urban pollution controls", "metropolitan building zoning",
    # Water / Rivers
    "riparian runoff systems", "water runoff mitigation", "riparian buffers 50m",
    "river basin authority guidelines", "aquifer depletion rates", "pollution in major river systems",
    "agricultural runoff mitigation", "ocean stream interaction", "lake riparian zones", "marine runoff pollution",
    # Infrastructure
    "electrical loads blackouts", "smart grids peak load blackout", "IoT bridge sensor limits",
    "telecom infrastructure fiber optics", "electrical grid localized stress", "national grid load balancing",
    "peak hours electrical sensor", "infrastructure energy grid", "telecom road bridges", "smart blackout prevention",
    # LLM Out of Bounds Fallbacks
    "history of the roman empire", "quantum physics strings", "space travel galaxies", "blockchain cryptography", "who wrote romeo and juliet"
]

results = []
print(f"Testing {len(queries)} queries against live running API on localhost:8000...")

for i, q in enumerate(queries):
    try:
        res = requests.post(url, json={"query": q}, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            domain = data.get("domain")
            conf = data.get("confidence", 0.0)
            status = "LLM_FALLBACK" if not data.get("signals") else "SUCCESS_KOSHA"
            
            results.append({
                "run": i + 1,
                "query": q,
                "status": status,
                "domain": domain,
                "confidence": conf,
                "api_response_snippet": data.get("answer", "")[:100] + "..."
            })
            print(f"OK {i+1}: {q} -> {status} (Conf: {conf})")
        else:
            print(f"ERR {i+1}: {q} -> ERROR HTTP {res.status_code} {res.text}")
            results.append({"run": i + 1, "query": q, "status": "HTTP_ERROR", "error": res.text})
            
    except Exception as e:
        print(f"FAIL {i+1}: {q} -> FAILURE {e}")
        results.append({"run": i + 1, "query": q, "status": "NETWORK_FAILURE", "error": str(e)})

# Dump Real Results into file 5
with open("5_VALIDATION_LOGS.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4)
    
print("Successfully generated 5_VALIDATION_LOGS.json using REAL server responses!")
