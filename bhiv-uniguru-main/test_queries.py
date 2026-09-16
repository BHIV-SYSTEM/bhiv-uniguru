import urllib.request
import json
import time
import os

queries = [
    {"domain": "Agriculture", "query": "What agricultural practices are mentioned in the Padma Purana and how do they relate to seasonal cycles and dharma?"},
    {"domain": "Urban / Society", "query": "How were cities and settlements described in ancient texts like the Puranas and Smritis? What were the key features of an ideal city?"},
    {"domain": "Water Management", "query": "What is the importance of rivers, lakes, and water conservation in Puranic literature? Provide references to sacred rivers and their uses."},
    {"domain": "Infrastructure", "query": "Describe infrastructure systems (roads, temples, irrigation) mentioned in ancient Indian scriptures and how they supported society."},
    {"domain": "History / Puranas", "query": "How does the Padma Purana describe the process of creation and the structure of the universe?"},
    {"domain": "Bhagavad Gita", "query": "What does the Bhagavad Gita say about duty (dharma) and action (karma yoga) in daily life?"},
    {"domain": "Philosophy + Society", "query": "Compare the concept of dharma in the Bhagavad Gita and Puranas with respect to social responsibilities."},
    {"domain": "Mixed (Infra + Water + Society)", "query": "How did ancient Indian texts integrate water systems, agriculture, and settlements for sustainable living?"},
    {"domain": "Sanskrit Queries", "query": "किं पद्मपुराणे धर्मस्य स्वरूपं वर्णितम्?"},
    {"domain": "Sanskrit Queries", "query": "गीता मध्ये कर्मयोगस्य महत्वं किम्?"},
    {"domain": "Agriculture + Ecology", "query": "What role do forests, plants, and agriculture play in sustaining life according to the Padma Purana and other Puranas?"},
    {"domain": "Urban Planning", "query": "What principles of urban planning and governance are described in ancient Indian texts like Smritis and Puranas?"},
    {"domain": "Water + Ritual + Society", "query": "How are rivers like Ganga River described in Puranic texts in terms of spiritual and practical importance?"},
    {"domain": "Infrastructure + Temples", "query": "What is the significance of temple construction and architecture in ancient scriptures, and how did it influence society?"},
    {"domain": "Cosmology + Time", "query": "How do Puranas describe time cycles (yugas) and their impact on human life and society?"},
    {"domain": "Gita + Decision Making", "query": "How does the Bhagavad Gita guide decision-making in morally complex situations?"},
    {"domain": "Dharma + Governance", "query": "What guidance do ancient texts provide about kingship, governance, and responsibilities of rulers?"},
    {"domain": "Sustainability (Ancient vs Modern)", "query": "Can principles from Puranas and Gita be applied to modern sustainability and environmental management?"},
    {"domain": "Sanskrit Queries", "query": "पुराणेषु जलस्य महत्वं कथं निरूपितम्?"},
    {"domain": "Sanskrit Queries", "query": "धर्मः किम्? गीता अनुसारं वर्णय।"}
]

URL = "http://localhost:8000/new_query"
TOKEN = "uniguru_secret_123"

results = []

for q in queries:
    print(f"Testing query in domain: {q['domain']}")
    req_data = {
        "query": q['query'],
        "context": {"domain": q['domain']},
        "allow_generated_verse": True
    }
    req = urllib.request.Request(URL, data=json.dumps(req_data).encode('utf-8'))
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {TOKEN}')
    
    try:
        response = urllib.request.urlopen(req)
        res_data = json.loads(response.read().decode('utf-8'))
        results.append({"query": q, "response": res_data, "status": "success"})
    except Exception as e:
        print(f"Failed: {e}")
        try:
            results.append({"query": q, "response": e.read().decode('utf-8'), "status": "error"})
        except:
            results.append({"query": q, "response": str(e), "status": "error"})

out_dir = r"C:\Users\Yashika\uniguru_v2\review_packets"
os.makedirs(out_dir, exist_ok=True)

test_logs_path = os.path.join(out_dir, "test_logs.json")
with open(test_logs_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

kosha_logs = []
review_md = ["# REVIEW PACKET - `/new_query` Pipeline Evaluation\n"]

for r in results:
    q_str = r['query']['query']
    domain = r['query']['domain']
    review_md.append(f"## Domain: {domain}")
    review_md.append(f"**Query**: {q_str}")
    if r['status'] == 'success':
        ans = r['response'].get('final_answer', 'N/A')
        signals = len(r['response'].get('signals', []))
        verse = r['response'].get('verse_sanskrit', 'None')
        note = r['response'].get('note', '')
        kosha_entry = r['response'].get('kosha_entry', {})
        kosha_logs.append(kosha_entry)

        review_md.append(f"**Final Answer**:\n{ans}\n")
        review_md.append(f"- **Signals used**: {signals}")
        if verse and verse != 'None':
            review_md.append(f"- **Sanskrit Verse**: {verse}")
        if note:
            review_md.append(f"- **Note**: {note}")
        if kosha_entry:
            review_md.append(f"- **Confidence**: {kosha_entry.get('confidence', 'N/A')}")
            review_md.append(f"- **Source**: {kosha_entry.get('source', 'N/A')}")
    else:
        review_md.append(f"**Error**: {r['response']}")
    review_md.append("\n--------------------------------------------------------------\n")

with open(os.path.join(out_dir, "KOSHA_VALIDATION_LOGS.json"), "w", encoding="utf-8") as f:
    json.dump(kosha_logs, f, ensure_ascii=False, indent=2)

with open(os.path.join(out_dir, "REVIEW_PACKET.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(review_md))

print("Completed testing. All files written to review_packets.")

