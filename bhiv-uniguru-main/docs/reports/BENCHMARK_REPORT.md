# UniGuru Performance Benchmark Report

**Generated:** 2026-06-29  
**Version:** 1.1.0  
**Pipeline:** `signal_first_ontology_kosha_v3`  
**Verdict:** ✅ ALL BENCHMARKS PASS

---

## Summary Table

| Benchmark | Result | Target | Status |
|-----------|--------|--------|--------|
| Curriculum ingestion speed | 7.55 ms | < 5,000 ms | ✅ PASS |
| Single-query p50 latency | ~103 ms | < 500 ms | ✅ PASS |
| Single-query p95 latency | ~111 ms | < 1,000 ms | ✅ PASS |
| Single-query p99 latency | ~111 ms | < 2,000 ms | ✅ PASS |
| Concurrent throughput | 10–13 qps | > 1 qps | ✅ PASS |
| Concurrent errors (50 queries, 10 workers) | 0 | 0 | ✅ PASS |
| Peak memory (20 query batch) | 1.88–2.96 MB | < 512 MB | ✅ PASS |
| Replay consistency (5 identical runs) | All identical | Identical outputs | ✅ PASS |
| Module startup time | 196 ms total | < 2,000 ms | ✅ PASS |

---

## Benchmark 1: Module Startup Time

| Module | Import Time |
|--------|------------|
| `kosha.kosha_loader` | 186.86 ms |
| `kosha.kosha_retriever` | 0.005 ms (cached) |
| `kosha.deterministic_pipeline` | 9.02 ms |
| `retrieval.ontology_retriever` | 0.004 ms (cached) |
| `ontology.entity_resolver` | 0.002 ms |
| `governance.source_governance` | 0.002 ms |
| **Total** | **195.9 ms** |

> Note: Most startup cost is loading the first `kosha` module (~187ms). All subsequent imports are cached.

---

## Benchmark 2: Curriculum Ingestion Speed

```
Entries loaded    : 37 (Balbharti Kosha entries)
Elapsed           : 7.55 – 11.08 ms
Throughput        : 3,340 – 4,900 entries/second
Peak memory       : 227 – 230 KB
```

> **Target met with 663× margin.** Ingestion is dominated by JSON parsing; scales linearly with dataset size.

---

## Benchmark 3: Single-Query Retrieval Latency (20 queries)

```
p50:  91 – 103 ms
p95: 105 – 111 ms
p99: 105 – 111 ms
mean:  93 – 97 ms
```

**Per-query breakdown:**

| Query | Latency | Status |
|-------|---------|--------|
| What is the Bhagavad Gita? | 105 ms | NO_VERIFIED_KNOWLEDGE |
| Karma Yoga teachings | 91 ms | NO_VERIFIED_KNOWLEDGE |
| Vishnu in Narada Purana | 102 ms | VERIFIED |
| What is the Padma Purana? | 98 ms | VERIFIED |
| Upanishadic concept of Brahman | 91 ms | VERIFIED |
| Dharma question (Mahabharata) | 86 ms | NO_VERIFIED_KNOWLEDGE |
| Temple construction (Agni Purana) | 88 ms | NO_VERIFIED_KNOWLEDGE |
| Kingship / Rajadharma | 93 ms | VERIFIED |
| Taittiriya Upanishad | 88 ms | VERIFIED |
| Quantum entanglement (out of scope) | 103 ms | NO_VERIFIED_KNOWLEDGE |
| Cricket match yesterday (out of scope) | 92 ms | NO_VERIFIED_KNOWLEDGE |

> Verification rate: 5/20 (25%) — reflects limited current corpus size (37 entries from 4 textbooks). Out-of-scope queries correctly rejected.

---

## Benchmark 4: Concurrent Query Throughput

```
Workers:    10 concurrent threads
Total:      50 queries
Completed:  50/50 (0 errors)
Wall time:  3,820 ms
Throughput: 10 – 13 queries/second
p50:        730 ms (under concurrency)
p95:        841 ms (under concurrency)
```

> **0 errors under full concurrency load.** p50 latency increases from 103ms (single-thread) to 730ms under 10 concurrent workers — expected due to GIL and threading overhead in Python.

---

## Benchmark 5: Memory Usage Under Load

```
Peak memory (20-query batch): 1.88 – 2.96 MB
Net allocation per query batch: 100 KB
```

> **2.96 MB peak is well within production limits.** The pipeline is memory-efficient — Kosha entries loaded once, shared across queries.

---

## Benchmark 6: Replay Consistency

```
Query: "Explain the Upanishadic concept of Brahman"
Runs:  5 identical executions

Run 1: VERIFIED  confidence=0.6000  signals=3
Run 2: VERIFIED  confidence=0.6000  signals=3
Run 3: VERIFIED  confidence=0.6000  signals=3
Run 4: VERIFIED  confidence=0.6000  signals=3
Run 5: VERIFIED  confidence=0.6000  signals=3

Status consistent:     TRUE (all VERIFIED)
Confidence consistent: TRUE (all 0.6000)
```

> **Deterministic pipeline confirmed.** The same query always produces the same verification status and confidence score — required for auditability and replay-safe proof generation.

---

## Retrieval Quality Metrics (IR Evaluation)

Evaluated across 8 labelled queries using standard IR metrics:

| Metric | Baseline (Keyword) | Enhanced (Ontology) | Delta |
|--------|--------------------|---------------------|-------|
| Precision@1 | 1.00 | 1.00 | 0.00 |
| Precision@3 | 0.92 | 0.92 | 0.00 |
| Recall@1 | 1.00 | 1.00 | 0.00 |
| MRR | 1.00 | 1.00 | 0.00 |
| NDCG@3 | 1.00 | 1.00 | 0.00 |
| Avg Score | 0.36 | **0.61** | +0.25 |
| Cross-domain rejection | — | 100% | — |
| Avg retrieval latency | — | 65 ms | — |

> **Interpretation:** Both baseline and ontology-enhanced retrieval achieve perfect domain-level precision and MRR on the 8-query evaluation set. The ontology enhancer raises the average confidence score by +0.25 (0.36 → 0.61) and correctly rejects 100% of cross-domain queries.

---

## Evidence Artifacts

| Artifact | Location |
|----------|----------|
| `benchmark_report.json` | `review_packets/proof_logs/benchmark_report.json` |
| `retrieval_quality_report.json` | `review_packets/proof_logs/retrieval_quality_report.json` |
| `proof_log_summary.json` | `review_packets/proof_logs/proof_log_summary.json` |
| `retrieval_benchmark.json` | `review_packets/proof_logs/retrieval_benchmark.json` |
| `validation_capture_latest.json` | `review_packets/proof_logs/validation_capture_latest.json` |

---

*Report generated from live benchmark execution — 2026-06-29*
