"""
UniGuru 15-Question Retrieval Validation
Runs deterministic Kosha pipeline against 15 representative questions.
Reports: question, PASS/FAIL, retrieved KB/document, selected evidence, final answer.
No LLM, no embeddings, no vector DB.
"""
import sys
import json
import io
from pathlib import Path

# Force UTF-8 stdout on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(BACKEND))

from kosha.deterministic_pipeline import run_deterministic_pipeline
from kosha.kosha_enforcer import KoshaEnforcer
from kosha.kosha_loader import KoshaLoader
from kosha.kosha_retriever import KoshaRetriever
from kosha.deterministic_pipeline import _KOSHA_DIR

QUESTIONS = [
    ("Q01", "What is Dharma?", "dharma", "universal principle"),
    ("Q02", "What is Karma?", "karma", "action"),
    ("Q03", "What is Shakti?", "shakti", "power"),
    ("Q04", "What is Prana?", "prana", "vital"),
    ("Q05", "What is Atman?", "atman", "self"),
    ("Q06", "What is Brahman?", "brahman", "supreme"),
    ("Q07", "What is Yoga?", "yoga", "union"),
    ("Q08", "What is Moksha?", "moksha", "liberation"),
    ("Q09", "What is Om?", "om", "sacred"),
    ("Q10", "What is Maya?", "maya", "illusion"),
    ("Q11", "What is Number Recognition?", "number recognition", "number"),
    ("Q12", "What is Addition?", "addition", "add"),
    ("Q13", "What is Subtraction?", "subtraction", "subtract"),
    ("Q14", "What are Living and Non-Living things?", "living", "living"),
    ("Q15", "What is Place Value?", "place value", "place"),
]

# These four terms occur in related passages, but the current KB has no direct
# definition sentence for them. The correct behavior is a verified-evidence refusal.
EXPECTED_DIRECT_EVIDENCE = {
    "Q01": True, "Q02": True, "Q03": True, "Q04": True, "Q05": True,
    "Q06": True, "Q07": True, "Q08": True, "Q09": True, "Q10": True,
    "Q11": True, "Q12": True, "Q13": True, "Q14": True, "Q15": True,
}

NO_KNOWLEDGE = "i do not have verified knowledge to answer this question."

results = []
valid_entries = KoshaEnforcer.validate_existing_entries(
    KoshaLoader(data_sources=[str(_KOSHA_DIR)]).load_all()
)["valid_entries"]

for qid, question, keyword, expected_fragment in QUESTIONS:
    try:
        retrieved, _ = KoshaRetriever(valid_entries).retrieve(question)
        result = run_deterministic_pipeline(query=question)
        answer = str(result.get("answer") or "")
        verification = result.get("verification_status", "UNKNOWN")
        matched = result.get("matched_signals", [])
        rejected = result.get("rejected_signals", [])
        domain = (result.get("domain_resolution") or {}).get("domain", "unknown")

        retrieved_documents = [
            {"knowledge_id": s.get("trace", {}).get("knowledge_id"), "source": s.get("source")}
            for s in retrieved[:5]
        ]
        candidate_evidence = str(retrieved[0].get("content") or "")[:120] if retrieved else ""

        answer_lower = answer.lower()
        has_answer = bool(answer.strip()) and answer_lower != NO_KNOWLEDGE
        has_fragment = expected_fragment.lower() in answer_lower
        expects_direct = EXPECTED_DIRECT_EVIDENCE[qid]
        first_selected_sentence = answer.split(". ", 1)[0].strip() if has_answer else ""
        normalized_selected_sentence = " ".join(first_selected_sentence.split()).casefold()
        selected_sources = [
            s.get("source", "unknown") for s in matched
            if normalized_selected_sentence
            and normalized_selected_sentence in " ".join(str(s.get("content") or "").split()).casefold()
        ]
        passed = (has_answer and has_fragment and verification == "VERIFIED") if expects_direct else (
            not has_answer and verification == "NO_VERIFIED_KNOWLEDGE"
        )

        fail_reason = ""
        if not passed:
            if not answer.strip():
                fail_reason = "SYNTHESIS_ISSUE: empty answer"
            elif answer_lower == NO_KNOWLEDGE and not matched and expects_direct:
                fail_reason = "RETRIEVAL_ISSUE: no accepted evidence for a direct KB fact"
            elif answer_lower == NO_KNOWLEDGE and matched and expects_direct:
                fail_reason = "EVIDENCE_SELECTION_ISSUE: direct KB fact exists but synthesis rejected it"
            elif has_answer and not expects_direct:
                fail_reason = "EVIDENCE_SELECTION_ISSUE: returned related evidence without a direct KB definition"
            else:
                fail_reason = f"ANSWER_MISMATCH: expected direct evidence containing '{expected_fragment}'"

        results.append({
            "id": qid,
            "question": question,
            "status": "PASS" if passed else "FAIL",
            "verification_status": verification,
            "domain": domain,
            "retrieved_documents": retrieved_documents,
            "expected_direct_evidence": expects_direct,
            "genuine_kb_gap": not expects_direct,
            "selected_evidence": answer if has_answer else None,
            "selected_evidence_preview": answer[:120] if has_answer else "",
            "selected_evidence_source": selected_sources[0] if selected_sources else None,
            "candidate_evidence_preview": candidate_evidence,
            "final_answer": answer,
            "answer_preview": answer[:200],
            "signals_matched": len(matched),
            "signals_rejected": len(rejected),
            "fail_reason": fail_reason,
            "diagnosis": (
                "DIRECT_EVIDENCE_ANSWERED" if expects_direct and passed
                else "GENUINE_KB_GAP: no direct defining sentence exists; correctly abstained" if passed
                else fail_reason
            ),
        })

    except Exception as exc:
        results.append({
            "id": qid,
            "question": question,
            "status": "FAIL",
            "verification_status": "ERROR",
            "domain": "error",
            "retrieved_documents": [],
            "selected_evidence_preview": "",
            "selected_evidence": None,
            "selected_evidence_source": None,
            "candidate_evidence_preview": "",
            "final_answer": "",
            "answer_preview": "",
            "signals_matched": 0,
            "signals_rejected": 0,
            "fail_reason": f"RUNTIME_ERROR: {exc}",
        })

print("\n" + "=" * 80)
print("UNIGURU 15-QUESTION RETRIEVAL VALIDATION REPORT")
print("=" * 80)

passed_count = sum(1 for r in results if r["status"] == "PASS")
failed_count = sum(1 for r in results if r["status"] == "FAIL")

for r in results:
    marker = "PASS" if r["status"] == "PASS" else "FAIL"
    print(f"\n[{marker}] {r['id']}: {r['question']}")
    print(f"  Verification    : {r['verification_status']}")
    print(f"  Domain          : {r['domain']}")
    print(f"  Signals matched : {r['signals_matched']}  rejected: {r['signals_rejected']}")
    print(f"  Retrieved KB    : {r['retrieved_documents']}")
    print(f"  Selected evidence: {r['selected_evidence_preview'] or '(none; abstained)'}")
    print(f"  Selected source  : {r.get('selected_evidence_source') or '(none)'}")
    print(f"  Candidate preview: {r['candidate_evidence_preview']}")
    print(f"  Answer preview  : {r['answer_preview']}")
    if r["fail_reason"]:
        print(f"  FAIL REASON     : {r['fail_reason']}")

print("\n" + "=" * 80)
print(f"SUMMARY: {passed_count}/15 PASS  |  {failed_count}/15 FAIL")
print("=" * 80)

out_path = ROOT / "review_packets" / "validation_reports" / "15q_retrieval_report.json"
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(results, indent=2, ensure_ascii=True), encoding="utf-8")
print(f"\nReport saved: {out_path}")
