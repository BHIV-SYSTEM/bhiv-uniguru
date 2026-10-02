# Integration Map — Seam Boundaries & Collaboration

**Owner:** Isha Singh  
**Collaborators:** Vijay Dhawan (Search Engine & Deduplication), Shivam Pal (ML/DS Measurement)

---

## 1. Collaboration Seams

```
Vijay (Retrieval & Reranking) ──> Isha (Convergence & Evidence Binding) ──> Shivam (ML/DS Benchmarks)
```

- **Vijay's Input to Isha**: Raw & reranked candidate signals (`content`, `source`, `concept`, `score`).
- **Isha's Contract with Vijay**: Enforces candidate deduplication by text content hash, assigns `AuthorityTier`, and constructs `CanonicalKnowledgeObject`.
- **Isha's Output to Shivam**: `RetrievalRunRecord` containing `candidate_count`, `deduplicated_candidate_count`, `selected_evidence`, and `claim_bindings`.
- **Shivam's Role**: Consumes `RetrievalRunRecord` to compute before/after retrieval precision, recall, and hallucination reduction benchmarks.

---

## 2. Platform Governance Seams

- **MDU**: Canonical object schemas (`UNIGURU_CANONICAL_OBJECT_V1`) and hash algorithms.
- **GC**: Operational trust ceiling enforcement and policy seals.
- **TMS**: Knowledge strategy alignment.
