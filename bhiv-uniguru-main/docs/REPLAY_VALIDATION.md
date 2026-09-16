# Replay Validation Protocol

**Version:** 1.0.0  
**Owner:** Isha Singh  
**Protocol Purpose:** Deterministic Historical Reproduction

---

## 1. Governance Rule: Replay vs. Legitimacy

> **IMPORTANT:**  
> Replay proves **historical reproduction** of exact execution outputs, NOT semantic legitimacy. Legitimacy is governed by GC and MDU authority rules.

---

## 2. Replay Verification Hash

```
replay_id = SHA-256(
    query_id + "|" +
    trace_id + "|" +
    canonical_concept_id + "|" +
    selected_evidence_hashes + "|" +
    claim_binding_hashes + "|" +
    status
)
```

If two runs of the same query produce identical `replay_id` values, the execution is declared `replay_safe: true`.

---

## 3. Verification Protocol Steps

1. Execute query and capture `RetrievalRunRecord_1`.
2. Re-run identical query with saved seed/state and capture `RetrievalRunRecord_2`.
3. Compare:
   - `retrieval_run_id` matching rules
   - `selected_evidence` candidate ordering and counts
   - `claim_bindings` verification statuses
   - `replay_id` exact string equality.
4. Output boolean `replay_safe` status.
