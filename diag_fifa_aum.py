import sys, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from ontology.entity_resolver import CanonicalEntityResolver
from kosha.signal_validator import SignalValidator

resolver = CanonicalEntityResolver()

# Test AUM resolution
print("=== AUM entity resolution ===")
entities = resolver.extract("What is AUM?")
print(f"Entities: {entities}")

# Test FIFA vs Maya signal
print("\n=== FIFA vs Maya domain_consistency ===")
fifa_query = "Who won the FIFA World Cup in 2022?"
maya_signal = {
    "signal_id": "test",
    "content": "Maya is the concept of illusion or the power that causes the world to appear as it is, concealing the true nature of Brahman.",
    "source": "Svetasvatara Upanishad - sanskrit and English.pdf",
    "confidence": 0.8,
    "domain": "general",
    "tags": ["maya", "illusion", "brahman", "world"],
}
is_valid, reason, details = SignalValidator.validate_signal(maya_signal, fifa_query)
print(f"Valid: {is_valid}, Reason: {reason}")
print(f"domain_consistency: {details['domain_consistency']}")
print(f"entity_overlap: {details['entity_overlap']}")
print(f"semantic_score: {details['semantic_score']}")
print(f"tag_match_score: {details['tag_match_score']}")
print(f"content_overlap: {details['content_overlap']}")
print(f"matched_tags: {details['matched_tags']}")
print(f"query_entities: {details['query_entities']}")
