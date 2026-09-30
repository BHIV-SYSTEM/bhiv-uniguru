import os, sys
os.environ["UNIGURU_API_AUTH_REQUIRED"] = "false"
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Patch retrieve_knowledge_with_trace to print diagnostics before it runs
import retrieval.retriever as _ret_module

_original_retrieve = _ret_module.retrieve_knowledge_with_trace

def _patched_retrieve(query):
    retriever = _ret_module.AdvancedRetriever()
    print("=" * 60)
    print(f"[DIAGNOSTIC] retrieve_knowledge_with_trace called")
    print(f"[DIAGNOSTIC] Using retriever: {retriever}")
    print(f"[DIAGNOSTIC] Type(retriever): {type(retriever)}")
    print(f"[DIAGNOSTIC] Retriever class: {type(retriever).__name__}")
    print(f"[DIAGNOSTIC] Retriever module: {type(retriever).__module__}")
    print(f"[DIAGNOSTIC] __file__: {_ret_module.__file__}")
    print("=" * 60)
    return _original_retrieve(query)

_ret_module.retrieve_knowledge_with_trace = _patched_retrieve

# Also patch RetrievalRule to confirm it calls our patched function
import core.rules.retrieval as _rule_module
_rule_module.retrieve_knowledge_with_trace = _patched_retrieve

from service.live_service import LiveUniGuruService

svc = LiveUniGuruService()

print("\n>>> Calling LiveUniGuruService.ask('What is Brahman?')\n")
result = svc.ask("What is Brahman?")
print(f"\n[RESULT] decision: {result.get('decision')}")
print(f"[RESULT] verification_status: {result.get('verification_status')}")
answer = str(result.get("answer") or "")
print(f"[RESULT] answer (first 200 chars): {answer[:200].encode('ascii', errors='replace').decode('ascii')}")
