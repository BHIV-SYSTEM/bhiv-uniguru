# Knowledge Authority Map — Review Packet Copy

**Owner:** Isha Singh  
**Layer:** Knowledge Convergence & Trust Validation

---

## Authority Classification Matrix

| Knowledge Source | Authority Tier | Active in Runtime? | Influences Output? | Rebuild Path | Governance Owner |
|---|---|---|---|---|---|
| **MASTERDB** | `CANONICAL` | YES | YES | Ground truth ingest pipeline | MDU / Isha |
| **AKASHIC** | `CANONICAL` | YES | YES | Ingest & purification script | MDU / Isha |
| **KNOWLEDGE_GRAPH** | `CANONICAL` | YES | YES | Ontology build & snapshot loader | Isha / Sanskar |
| **KOSHA_JSON** | `CANONICAL` | YES | YES | Kosha Enforcer | Isha |
| **MARKDOWN_CORPUS** | `CANONICAL` | YES | YES | Knowledge ingest parser | Isha |
| **FAISS_VECTOR_INDEX** | `DERIVED` | YES | YES (Candidates only) | `scripts/rebuild_faiss_index.py` | Vijay |
| **LLM_FALLBACK** | `FALLBACK` | CONDITIONAL | ONLY when unverified fallback allowed | N/A | Vijay / Isha |
| **TEST_FIXTURE** | `TEST_FIXTURE` | NO (Test only) | NO | `backend/tests/fixtures/` | Isha |
