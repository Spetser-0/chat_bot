"""
tests/unit/test_metrics.py
──────────────────────────
Lesson 11.1 — MetricsRegistry counters, gauges, histograms.
"""
from __future__ import annotations

import pytest

from app.core.metrics import (
    MetricsRegistry,
    get_metrics,
    reset_metrics_for_tests,
)


class TestCounters:
    def test_inc_defaults_to_one(self):
        m = MetricsRegistry()
        m.inc("hits")
        m.inc("hits")
        assert m.get_counter("hits") == 2

    def test_inc_custom_value(self):
        m = MetricsRegistry()
        m.inc("tokens", 10)
        m.inc("tokens", 5)
        assert m.get_counter("tokens") == 15

    def test_negative_inc_rejected(self):
        m = MetricsRegistry()
        with pytest.raises(ValueError):
            m.inc("x", -1)

    def test_missing_counter_is_zero(self):
        m = MetricsRegistry()
        assert m.get_counter("nope") == 0


class TestGauges:
    def test_set_and_get(self):
        m = MetricsRegistry()
        m.set_gauge("queue", 3.5)
        assert m.get_gauge("queue") == 3.5

    def test_missing_gauge_is_none(self):
        m = MetricsRegistry()
        assert m.get_gauge("missing") is None


class TestHistograms:
    def test_observe_and_stats(self):
        m = MetricsRegistry()
        m.observe("lat", 10)
        m.observe("lat", 30)
        h = m.histogram("lat")
        assert h is not None
        assert h["count"] == 2
        assert h["avg_ms"] == 20.0
        assert h["min_ms"] == 10.0
        assert h["max_ms"] == 30.0

    def test_missing_histogram_is_none(self):
        m = MetricsRegistry()
        assert m.histogram("nope") is None


class TestRecordHelpers:
    def test_record_request(self):
        m = MetricsRegistry()
        m.record_request("GET", "/api/v1/health/live", 200, 5.0)
        assert m.get_counter("http_requests_total") == 1
        assert m.get_counter("http_requests_total.GET") == 1
        assert m.get_counter("http_requests_total.GET.200") == 1
        assert m.get_counter("http_server_errors_total") == 0
        assert m.histogram("http_request_latency_ms")["count"] == 1

    def test_record_request_server_error(self):
        m = MetricsRegistry()
        m.record_request("POST", "/x", 500, 12.0)
        assert m.get_counter("http_server_errors_total") == 1

    def test_record_request_rate_limited(self):
        m = MetricsRegistry()
        m.record_request("POST", "/x", 429, 1.0)
        assert m.get_counter("http_rate_limited_total") == 1

    def test_record_llm_call_success(self):
        m = MetricsRegistry()
        m.record_llm_call(provider="mock", success=True, latency_ms=100,
                          input_tokens=10, output_tokens=5)
        assert m.get_counter("llm_calls_total") == 1
        assert m.get_counter("llm_calls_success_total") == 1
        assert m.get_counter("llm_tokens_input_total") == 10
        assert m.get_counter("llm_tokens_output_total") == 5

    def test_record_llm_call_failure(self):
        m = MetricsRegistry()
        m.record_llm_call(provider=None, success=False, latency_ms=0)
        assert m.get_counter("llm_calls_failure_total") == 1


class TestSnapshotAndSingleton:
    def test_snapshot_serializable(self):
        m = MetricsRegistry()
        m.inc("a")
        m.set_gauge("g", 1.5)
        m.observe("h", 2.0)
        snap = m.snapshot()
        assert snap["counters"]["a"] == 1
        assert snap["gauges"]["g"] == 1.5
        assert snap["histograms"]["h"]["count"] == 1
        assert "uptime_seconds" in snap

    def test_reset(self):
        m = MetricsRegistry()
        m.inc("a")
        m.reset()
        assert m.get_counter("a") == 0

    def test_singleton(self):
        reset_metrics_for_tests()
        a = get_metrics()
        b = get_metrics()
        assert a is b
        reset_metrics_for_tests()
