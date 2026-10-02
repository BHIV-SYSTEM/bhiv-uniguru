"""
Retrieval + abstention test for UniGuru deterministic pipeline.
Tests 10 positive Sanskrit/Kosha queries and 4 negative/abstention queries.
"""
import sys
import os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from kosha.deterministic_pipeline import run_deterministic_pipeline

import unicodedata

def _normalize(text):
    """Normalize diacritics for comparison."""
    raw = unicodedata.normalize("NFKD", str(text or "").casefold())
    return "".join(c for c in raw if not unicodedata.combining(c))

POSITIVE = [
    ("What is Dharma?",   "dharma"),
    ("What is Karma?",    "karma"),
    ("What is Shakti?",   "sakti"),   # Śakti normalizes to sakti
    ("What is AUM?",      "om"),       # AUM -> Om alias
    ("What is Atman?",    "atman"),
    ("What is Brahman?",  "brahman"),
    ("What is Prana?",    "prana"),
    ("What is Yoga?",     "yoga"),
    ("What is Moksha?",   "moksha"),
    ("What is Maya?",     "maya"),
]

NEGATIVE = [
    "Who won the FIFA World Cup in 2022?",
    "What is the capital of France?",
    "Tell me today's stock price.",
    "What is the weather today?",
]

print("=" * 70)
print("POSITIVE RETRIEVAL TESTS")
print("=" * 70)
pos_pass = 0
for query, expected_term in POSITIVE:
    result = run_deterministic_pipeline(query=query, trace_id="test_pos")
    status = result.get("verification_status", "")
    answer = result.get("answer", "")
    signals = result.get("matched_signals", [])
    source = (signals[0].get("source", "") if signals else result.get("selected_source", ""))
    ok = (
        status == "VERIFIED"
        and expected_term.lower() in _normalize(answer)
        and answer != "I do not have verified knowledge to answer this question."
    )
    icon = "PASS" if ok else "FAIL"
    if ok:
        pos_pass += 1
    print(f"[{icon}] {query}")
    print(f"       status={status}  term_found={expected_term.lower() in answer.lower()}")
    print(f"       source={source[:80]}")
    print(f"       answer={answer[:120]}")
    print()

print("=" * 70)
print("NEGATIVE / ABSTENTION TESTS (allow_web_retrieval=false)")
print("=" * 70)
neg_pass = 0
for query in NEGATIVE:
    result = run_deterministic_pipeline(query=query, trace_id="test_neg")
    status = result.get("verification_status", "")
    answer = result.get("answer", "")
    # Must NOT return a Sanskrit/Kosha answer for off-topic queries
    is_no_knowledge = status in {"NO_VERIFIED_KNOWLEDGE", "UNVERIFIED"} or \
                      "do not have verified knowledge" in answer.lower()
    # Specifically: FIFA query must NOT return Maya answer
    fifa_false_positive = (
        "fifa" in query.lower() and
        "maya" in answer.lower() and
        status == "VERIFIED"
    )
    ok = is_no_knowledge and not fifa_false_positive
    icon = "PASS" if ok else "FAIL"
    if ok:
        neg_pass += 1
    print(f"[{icon}] {query}")
    print(f"       status={status}")
    print(f"       answer={answer[:120]}")
    print()

print("=" * 70)
print(f"POSITIVE: {pos_pass}/10  |  NEGATIVE: {neg_pass}/4")
print("=" * 70)
sys.exit(0 if (pos_pass == 10 and neg_pass == 4) else 1)
