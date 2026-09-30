import os, sys
os.environ["UNIGURU_API_AUTH_REQUIRED"] = "false"
sys.path.insert(0, os.path.dirname(__file__))

from retrieval.retriever import AdvancedRetriever

queries = [
    "What is Brahman?",
    "Name any one Upanishad.",
    "Which text is related to Ayurveda?",
    "What is the purpose of the Puranas?",
    "Translate: ahimsa paramo dharmah",
]

retriever = AdvancedRetriever()
print("Retriever type:", type(retriever).__name__)
print("Retriever module:", type(retriever).__module__)
print("top_n:", retriever.top_n)
print("KB files loaded:", len(retriever.knowledge_map))
print()

for q in queries:
    results = retriever.retrieve_multi(q)
    print(f"Q: {q}")
    print(f"  Results retrieved: {len(results)}")
    for i, r in enumerate(results):
        print(f"  [{i+1}] file={r['file']}  source={r['source']}  confidence={r['confidence']:.3f}")
    combined = retriever.reason_and_compare(results)
    content = combined.get("content") or ""
    print(f"  Combined context chars: {len(content)}")
    print(f"  docs_combined: {combined.get('metadata', {}).get('docs_combined', 'N/A')}")
    preview = content[:300].strip().encode('ascii', errors='replace').decode('ascii')
    print(f"  Answer preview: {preview}")
    print()
