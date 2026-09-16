# Retrieval Provenance & Claim Binding Model Specification

**Version:** 1.0.0  
**Owner:** Isha Singh  
**Layer:** Provenance & Lineage Verification

---

## 1. Purpose

The Retrieval Provenance Model ensures that every sentence or claim emitted in a UniGuru answer is bound to an explicit `canonical_object_id` and content hash. Unbacked assertions are automatically flagged as `UNVERIFIED_FALLBACK`.

---

## 2. Claim-to-Evidence Binding Protocol

1. **Sentence Tokenization**: The synthesized output text is segmented into distinct claim sentences.
2. **Token Match Alignment**: Sentences are aligned against the `selected_evidence` text spans using exact token overlap and concept affinity.
3. **Status Assignment**:
   - `VERIFIED`: Sentence matches a `CANONICAL` evidence object.
   - `DERIVED`: Sentence matches a `DERIVED` evidence object (e.g. FAISS candidate index).
   - `UNVERIFIED_FALLBACK`: Sentence matches no verified candidate, or matches a `FALLBACK` generative output.
   - `CONTRADICTED`: Sentence conflicts with another matched candidate in a different Darśana/tradition.

---

## 3. Cryptographic Provenance Hash Construction

```
provenance_hash = SHA-256(
    concept_id + "|" +
    ksml_id + "|" +
    source_id + "|" +
    authority_tier + "|" +
    text_span + "|" +
    knowledge_version
)
```

The `provenance_hash` guarantees that any tampering with text spans or source metadata will break historical replay validation.
