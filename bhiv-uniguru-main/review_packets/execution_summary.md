# Execution Summary — UniGuru Knowledge Runtime

**Owner:** Isha Singh  
**Architecture:** Unified Sanskrit Decoder & Knowledge Convergence Engine  

---

## 1. Request Execution Lifecycle

```
User Query
    │
    ▼
1. Query Normalization & Language Adapter
    │
    ▼
2. Candidate Retrieval & Source Scope Resolution
    │
    ▼
3. Candidate Deduplication & Authority Tiering [AuthorityTier]
    │
    ▼
4. Epistemological Pipeline / Sanskrit Decoder (Śabda → Dhātu → Vyākaraṇa → Nirukta → Bīja → Tattva → Śakti → Functional Meaning)
    │
    ▼
5. Knowledge Graph Multi-Hop Traversal (BFS outward walk)
    │
    ▼
6. Claim-to-Evidence Binding [ClaimEvidenceBinding]
    │
    ▼
7. Deterministic Replay ID & Provenance Hash Sealing
    │
    ▼
8. Governed Response Output
```

---

## 2. Execution Guarantees

- **No Hidden Fallback**: Every response is either backed by canonical evidence (`VERIFIED`/`DERIVED`) or explicitly marked `NO_VERIFIED_KNOWLEDGE` / `UNVERIFIED_FALLBACK`.
- **Deterministic Hash**: `result_hash` and `replay_id` remain identical across multiple runs.
- **Traceability**: Every output sentence is bound to a `canonical_object_id` and SHA-256 `provenance_hash`.
