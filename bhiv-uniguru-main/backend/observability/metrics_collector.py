"""
Metrics Collector — Extended Production Metrics
================================================
Extends the existing counter-based metrics in api.py with:
  - Latency percentile histograms (p50, p95, p99) via rolling window
  - Per-route retrieval timing
  - Confidence score distribution (bucketed histogram)
  - Failure classification by error type

This module is fully thread-safe and designed as a drop-in companion
to the existing _METRICS dict in api.py.

Usage:
    from observability.metrics_collector import MetricsCollector
    collector = MetricsCollector.get_instance()
    collector.record_request_latency(latency_ms)
    collector.record_confidence(0.72)
    collector.record_failure("no_knowledge")
    collector.to_prometheus_lines()  # returns additional metric lines
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Rolling window percentile calculator
# ---------------------------------------------------------------------------

class _RollingPercentile:
    """
    Maintains a fixed-size rolling window of float values and computes
    approximate percentiles. Thread-safe.
    """

    def __init__(self, maxlen: int = 1000) -> None:
        self._window: Deque[float] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def record(self, value: float) -> None:
        with self._lock:
            self._window.append(value)

    def percentile(self, pct: float) -> float:
        """Compute the p-th percentile (e.g., 95.0 → p95)."""
        with self._lock:
            if not self._window:
                return 0.0
            sorted_vals = sorted(self._window)
            idx = math.ceil((pct / 100.0) * len(sorted_vals)) - 1
            return round(sorted_vals[max(0, idx)], 3)

    def count(self) -> int:
        with self._lock:
            return len(self._window)

    def mean(self) -> float:
        with self._lock:
            if not self._window:
                return 0.0
            return round(sum(self._window) / len(self._window), 3)


# ---------------------------------------------------------------------------
# Confidence histogram
# ---------------------------------------------------------------------------

_CONFIDENCE_BUCKETS: List[Tuple[float, float]] = [
    (0.0, 0.2),
    (0.2, 0.4),
    (0.4, 0.6),
    (0.6, 0.8),
    (0.8, 1.0),
]


def _bucket_label(lo: float, hi: float) -> str:
    return f"{lo:.1f}-{hi:.1f}"


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

class MetricsCollector:
    """
    Thread-safe extended metrics collector.
    Singleton — call MetricsCollector.get_instance() to access.
    """

    _instance: Optional["MetricsCollector"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        # Request latency (all routes)
        self._latency_all = _RollingPercentile(maxlen=2000)
        # Per-route latency
        self._latency_by_route: Dict[str, _RollingPercentile] = {}
        self._route_lock = threading.Lock()
        # Retrieval timing (internal pipeline step)
        self._retrieval_latency = _RollingPercentile(maxlen=2000)
        # Confidence distribution
        self._confidence_buckets: Dict[str, int] = {
            _bucket_label(lo, hi): 0 for lo, hi in _CONFIDENCE_BUCKETS
        }
        self._confidence_lock = threading.Lock()
        # Failure classification
        self._failure_counts: Dict[str, int] = {}
        self._failure_lock = threading.Lock()
        # Start time
        self._start_time = time.time()

    @classmethod
    def get_instance(cls) -> "MetricsCollector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Recording methods
    # ------------------------------------------------------------------

    def record_request_latency(self, latency_ms: float, route: str = "/ask") -> None:
        """Record end-to-end request latency."""
        self._latency_all.record(latency_ms)
        with self._route_lock:
            if route not in self._latency_by_route:
                self._latency_by_route[route] = _RollingPercentile(maxlen=500)
            self._latency_by_route[route].record(latency_ms)

    def record_retrieval_latency(self, latency_ms: float) -> None:
        """Record internal retrieval step latency (subset of total request time)."""
        self._retrieval_latency.record(latency_ms)

    def record_confidence(self, confidence: float) -> None:
        """Record a confidence score into its histogram bucket."""
        clamped = max(0.0, min(1.0, float(confidence)))
        with self._confidence_lock:
            for lo, hi in _CONFIDENCE_BUCKETS:
                if lo <= clamped < hi or (hi == 1.0 and clamped == 1.0):
                    label = _bucket_label(lo, hi)
                    self._confidence_buckets[label] = self._confidence_buckets.get(label, 0) + 1
                    break

    def record_failure(self, failure_class: str) -> None:
        """
        Record a failure by class. Standard classes:
          no_knowledge, schema_violation, auth_failure, timeout,
          rate_limited, invalid_request, internal_error
        """
        with self._failure_lock:
            self._failure_counts[failure_class] = self._failure_counts.get(failure_class, 0) + 1

    # ------------------------------------------------------------------
    # Snapshot / export
    # ------------------------------------------------------------------

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a dict of all extended metric values."""
        p50 = self._latency_all.percentile(50.0)
        p95 = self._latency_all.percentile(95.0)
        p99 = self._latency_all.percentile(99.0)
        r_p50 = self._retrieval_latency.percentile(50.0)
        r_p95 = self._retrieval_latency.percentile(95.0)

        with self._route_lock:
            per_route = {
                route: {
                    "p50_ms": rp.percentile(50.0),
                    "p95_ms": rp.percentile(95.0),
                    "count": rp.count(),
                }
                for route, rp in self._latency_by_route.items()
            }

        with self._confidence_lock:
            conf_dist = dict(self._confidence_buckets)

        with self._failure_lock:
            failures = dict(self._failure_counts)

        return {
            "uptime_seconds": round(time.time() - self._start_time, 1),
            "request_latency_ms": {
                "p50": p50,
                "p95": p95,
                "p99": p99,
                "mean": self._latency_all.mean(),
                "sample_count": self._latency_all.count(),
            },
            "retrieval_latency_ms": {
                "p50": r_p50,
                "p95": r_p95,
                "sample_count": self._retrieval_latency.count(),
            },
            "per_route_latency_ms": per_route,
            "confidence_distribution": conf_dist,
            "failure_classification": failures,
        }

    def to_prometheus_lines(self) -> List[str]:
        """
        Generate additional Prometheus-format metric lines for the /metrics endpoint.
        These supplement the existing counter lines in api.py.
        """
        snap = self.get_snapshot()
        lat = snap["request_latency_ms"]
        ret = snap["retrieval_latency_ms"]
        conf = snap["confidence_distribution"]
        fails = snap["failure_classification"]

        lines = [
            "# TYPE uniguru_request_latency_ms_p50 gauge",
            f"uniguru_request_latency_ms_p50 {lat['p50']}",
            "# TYPE uniguru_request_latency_ms_p95 gauge",
            f"uniguru_request_latency_ms_p95 {lat['p95']}",
            "# TYPE uniguru_request_latency_ms_p99 gauge",
            f"uniguru_request_latency_ms_p99 {lat['p99']}",
            "# TYPE uniguru_request_latency_ms_mean gauge",
            f"uniguru_request_latency_ms_mean {lat['mean']}",
            "# TYPE uniguru_retrieval_latency_ms_p50 gauge",
            f"uniguru_retrieval_latency_ms_p50 {ret['p50']}",
            "# TYPE uniguru_retrieval_latency_ms_p95 gauge",
            f"uniguru_retrieval_latency_ms_p95 {ret['p95']}",
            "# TYPE uniguru_confidence_distribution_total counter",
        ]
        for bucket_label, count in sorted(conf.items()):
            lines.append(
                f'uniguru_confidence_distribution_total{{bucket="{bucket_label}"}} {count}'
            )
        lines.append("# TYPE uniguru_failure_class_total counter")
        for cls_name, count in sorted(fails.items()):
            lines.append(
                f'uniguru_failure_class_total{{class="{cls_name}"}} {count}'
            )
        return lines

    def reset(self) -> None:
        """Reset all extended metrics (for testing)."""
        self._latency_all = _RollingPercentile(maxlen=2000)
        with self._route_lock:
            self._latency_by_route.clear()
        self._retrieval_latency = _RollingPercentile(maxlen=2000)
        with self._confidence_lock:
            self._confidence_buckets = {
                _bucket_label(lo, hi): 0 for lo, hi in _CONFIDENCE_BUCKETS
            }
        with self._failure_lock:
            self._failure_counts.clear()
        self._start_time = time.time()
