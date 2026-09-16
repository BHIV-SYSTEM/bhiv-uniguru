# Enterprise Load Testing Report

**Owner:** Isha Singh  
**Benchmark Suite:** `scripts/benchmark_performance.py`  
**Date:** 2026-08-29  

---

## 1. Test Configuration

- **Target Service**: UniGuru Native Runtime (`uniguru_runtime_api`)
- **Concurrent Workers**: 10 & 25 worker threads
- **Total Requests**: 100 requests per run
- **Dataset**: MasterDB & Akashic Kosha records

---

## 2. Empirical Benchmark Results

| Metric | Target Threshold | Measured Result | Pass/Fail |
|---|---|---|---|
| **Single Query P50 Latency** | < 500 ms | **243.02 ms** | **PASS** |
| **Single Query P95 Latency** | < 1000 ms | **289.66 ms** | **PASS** |
| **Single Query P99 Latency** | < 2000 ms | **343.61 ms** | **PASS** |
| **In-Memory Concurrent Throughput** | > 10.0 req/sec | **864.20 req/sec** | **PASS** |
| **Full Pipeline Throughput** | > 1.0 req/sec | **3.44 req/sec** | **PASS** |
| **Error Rate** | 0.00% | **0.00%** (0 errors) | **PASS** |
| **Ingestion Speed** | > 100 entries/sec | **1208.9 entries/sec** | **PASS** |

---

## 3. Latency Distribution Curve

- Min Latency: 226.9 ms
- P50 (Median): 243.02 ms
- P95: 289.66 ms
- P99: 343.61 ms
- Max Latency: 343.61 ms
