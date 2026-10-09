"""
app/core/metrics.py
───────────────────
In-process observability counters and simple latency histograms (Phase 11).

Design notes:
- No external metrics backend required (Prometheus can be layered later by
  scraping the JSON snapshot or replacing this registry).
- Thread-safety: FastAPI asyncio runs single-threaded per event loop; a plain
  dict is sufficient for counters. For multi-worker production, each process
  keeps its own counters (documented) — Redis aggregation is future work.
- Never store secrets or PII in metric names/labels.
"""
from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class MetricsRegistry:
    """Process-wide counters, gauges, and simple latency summaries."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        # key -> {"count", "sum_ms", "min_ms", "max_ms"}
        self._histograms: dict[str, dict[str, float]] = {}
        self._started_at = time.time()

    # ── Counters ────────────────────────────────────────────────────────────

    def inc(self, name: str, value: int = 1) -> None:
        """Increment a monotonically increasing counter."""
        if value < 0:
            raise ValueError("counters only increase")
        self._counters[name] = self._counters.get(name, 0) + value

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    # ── Gauges ──────────────────────────────────────────────────────────────

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = float(value)

    def get_gauge(self, name: str) -> float | None:
        return self._gauges.get(name)

    # ── Histograms (latency) ────────────────────────────────────────────────

    def observe(self, name: str, value_ms: float) -> None:
        """Record one latency sample (milliseconds)."""
        h = self._histograms.get(name)
        if h is None:
            self._histograms[name] = {
                "count": 1,
                "sum_ms": float(value_ms),
                "min_ms": float(value_ms),
                "max_ms": float(value_ms),
            }
            return
        h["count"] += 1
        h["sum_ms"] += float(value_ms)
        h["min_ms"] = min(h["min_ms"], float(value_ms))
        h["max_ms"] = max(h["max_ms"], float(value_ms))

    def histogram(self, name: str) -> dict[str, float] | None:
        h = self._histograms.get(name)
        if h is None:
            return None
        count = h["count"]
        return {
            "count": count,
            "avg_ms": round(h["sum_ms"] / count, 3) if count else 0.0,
            "min_ms": round(h["min_ms"], 3),
            "max_ms": round(h["max_ms"], 3),
        }

    # ── Convenience ─────────────────────────────────────────────────────────

    def record_request(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        """HTTP request metrics. Path should be the route template when known."""
        self.inc("http_requests_total")
        self.inc(f"http_requests_total.{method}")
        self.inc(f"http_requests_total.{method}.{status_code}")
        if status_code >= 500:
            self.inc("http_server_errors_total")
        elif status_code == 429:
            self.inc("http_rate_limited_total")
        self.observe("http_request_latency_ms", latency_ms)
        self.observe(f"http_request_latency_ms.{method}", latency_ms)

    def record_llm_call(
        self,
        *,
        provider: str | None,
        success: bool,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """LLM usage metrics (Phase 11, Lesson 11.1)."""
        self.inc("llm_calls_total")
        if success:
            self.inc("llm_calls_success_total")
        else:
            self.inc("llm_calls_failure_total")
        if provider:
            self.inc(f"llm_calls_total.provider.{provider}")
        self.inc("llm_tokens_input_total", max(0, int(input_tokens)))
        self.inc("llm_tokens_output_total", max(0, int(output_tokens)))
        self.observe("llm_latency_ms", latency_ms)

    # ── Snapshot / reset ────────────────────────────────────────────────────

    def snapshot(self) -> dict[str, Any]:
        """JSON-serializable view of all metrics (for /admin/metrics)."""
        return {
            "uptime_seconds": round(time.time() - self._started_at, 3),
            "counters": dict(sorted(self._counters.items())),
            "gauges": dict(sorted(self._gauges.items())),
            "histograms": {
                name: self.histogram(name)
                for name in sorted(self._histograms)
            },
        }

    def reset(self) -> None:
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._started_at = time.time()


# ── Singleton ────────────────────────────────────────────────────────────────

_registry: MetricsRegistry | None = None


def get_metrics() -> MetricsRegistry:
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


def reset_metrics_for_tests() -> None:
    global _registry
    if _registry is not None:
        _registry.reset()
    _registry = None
