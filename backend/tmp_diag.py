import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from retrieval.retriever import AdvancedRetriever, STOPWORDS
import re

retriever = AdvancedRetriever()

queries = [
    "What is the purpose of the Puranas?",
    "Translate: ahimsa paramo dharmah",
]

for q in queries:
    query_lower = q.lower()
    clean_query = re.sub(r"[^\w\s]", "", query_lower)
    tokens = [t for t in clean_query.split() if t and t not in STOPWORDS]
    print(f"\nQ: {q}")
    print(f"  Tokens after stopword removal: {tokens}")

    # Show top candidates with scores
    candidates = []
    for keyword, content in retriever.knowledge_map.items():
        kw_tokens = keyword.split()
        content_lower = content.lower()
        keyword_match = sum(1 for t in kw_tokens if t in tokens)
        content_match = sum(1 for t in tokens if t in content_lower)
        if keyword_match > 0 or content_match >= 1:
            kw_cov = keyword_match / len(kw_tokens) if kw_tokens else 0.0
            cont_den = min(content_match / len(tokens), 1.0) if tokens else 0.0
            conf = min((0.7 * kw_cov) + (0.3 * cont_den), 1.0)
            candidates.append((conf, keyword_match, content_match, keyword, retriever.file_map.get(keyword)))
    candidates.sort(reverse=True)
    print(f"  Top candidates (conf, kw_match, content_match, keyword, file):")
    for c in candidates[:8]:
        print(f"    {c}")
    if not candidates:
        print("  NO candidates at all")
