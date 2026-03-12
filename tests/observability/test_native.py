"""
Tests for native observability implementation.

Watch the learning process, not just outputs.
Weave is optional — native implementation works standalone.
"""

import pytest
import json
from datetime import datetime, timedelta

from convergence.observability.protocol import (
    ObserverProtocol,
    MetricType,
    MetricEvent,
)
from convergence.observability.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
)
from convergence.observability.native import NativeObserver


# =============================================================================
# METRICS PRIMITIVES
# =============================================================================


class TestCounter:
    """Test Counter metric."""

    def test_increment(self):
        """Counter should increment."""
        counter = Counter("requests_total", "Total requests")

        counter.inc()
        counter.inc()
        counter.inc()

        assert counter.value == 3

    def test_increment_by(self):
        """Counter should increment by value."""
        counter = Counter("bytes_total", "Total bytes")

        counter.inc(100)
        counter.inc(50)

        assert counter.value == 150

    def test_counter_with_labels(self):
        """Counter should support labels."""
        counter = Counter("requests_total", "Total requests", labels=["method", "status"])

        counter.labels(method="GET", status="200").inc()
        counter.labels(method="GET", status="200").inc()
        counter.labels(method="POST", status="201").inc()

        assert counter.labels(method="GET", status="200").value == 2
        assert counter.labels(method="POST", status="201").value == 1

    def test_counter_cannot_decrease(self):
        """Counter should not allow negative increments."""
        counter = Counter("test", "test")

        with pytest.raises(ValueError):
            counter.inc(-1)

    def test_counter_serializable(self):
        """Counter should export to dict."""
        counter = Counter("test", "test")
        counter.inc(5)

        data = counter.to_dict()

        assert data["name"] == "test"
        assert data["value"] == 5
        assert data["type"] == "counter"


class TestGauge:
    """Test Gauge metric."""

    def test_set_value(self):
        """Gauge should set value."""
        gauge = Gauge("temperature", "Current temperature")

        gauge.set(25.5)

        assert gauge.value == 25.5

    def test_inc_dec(self):
        """Gauge should increment and decrement."""
        gauge = Gauge("active_connections", "Active connections")

        gauge.set(10)
        gauge.inc()
        gauge.inc(5)
        gauge.dec()
        gauge.dec(2)

        assert gauge.value == 13

    def test_gauge_with_labels(self):
        """Gauge should support labels."""
        gauge = Gauge("cpu_usage", "CPU usage", labels=["core"])

        gauge.labels(core="0").set(50.0)
        gauge.labels(core="1").set(75.0)

        assert gauge.labels(core="0").value == 50.0
        assert gauge.labels(core="1").value == 75.0

    def test_gauge_serializable(self):
        """Gauge should export to dict."""
        gauge = Gauge("test", "test")
        gauge.set(42)

        data = gauge.to_dict()

        assert data["name"] == "test"
        assert data["value"] == 42
        assert data["type"] == "gauge"


class TestHistogram:
    """Test Histogram metric."""

    def test_observe(self):
        """Histogram should record observations."""
        histogram = Histogram("response_time", "Response time", buckets=[0.1, 0.5, 1.0, 5.0])

        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(2.0)

        assert histogram.count == 4
        assert histogram.sum == pytest.approx(3.15, rel=0.01)

    def test_histogram_buckets(self):
        """Histogram should count observations per bucket."""
        histogram = Histogram("latency", "Latency", buckets=[0.1, 0.5, 1.0])

        histogram.observe(0.05)  # <= 0.1
        histogram.observe(0.3)   # <= 0.5
        histogram.observe(0.8)   # <= 1.0
        histogram.observe(2.0)   # > 1.0 (in +Inf bucket)

        buckets = histogram.get_buckets()

        assert buckets[0.1] == 1
        assert buckets[0.5] == 2
        assert buckets[1.0] == 3

    def test_histogram_percentiles(self):
        """Histogram should compute percentiles."""
        histogram = Histogram("latency", "Latency", buckets=[0.1, 0.5, 1.0, 5.0, 10.0])

        # Add observations
        for _ in range(50):
            histogram.observe(0.05)  # 50 fast
        for _ in range(40):
            histogram.observe(0.3)   # 40 medium
        for _ in range(10):
            histogram.observe(2.0)   # 10 slow

        p50 = histogram.percentile(50)
        p95 = histogram.percentile(95)
        p99 = histogram.percentile(99)

        # p50 should be in the 0.1 bucket range
        assert p50 <= 0.5
        # p95 should be higher
        assert p95 > p50

    def test_histogram_with_labels(self):
        """Histogram should support labels."""
        histogram = Histogram("request_duration", "Duration", labels=["endpoint"])

        histogram.labels(endpoint="/api/v1").observe(0.1)
        histogram.labels(endpoint="/api/v2").observe(0.2)

        assert histogram.labels(endpoint="/api/v1").count == 1
        assert histogram.labels(endpoint="/api/v2").count == 1

    def test_histogram_serializable(self):
        """Histogram should export to dict."""
        histogram = Histogram("test", "test", buckets=[1, 5, 10])
        histogram.observe(2)
        histogram.observe(7)

        data = histogram.to_dict()

        assert data["name"] == "test"
        assert data["count"] == 2
        assert data["sum"] == 9
        assert data["type"] == "histogram"


# =============================================================================
# METRICS REGISTRY
# =============================================================================


class TestMetricsRegistry:
    """Test metrics registry."""

    @pytest.fixture
    def registry(self):
        """Create fresh registry."""
        return MetricsRegistry()

    def test_register_counter(self, registry):
        """Should register counter."""
        counter = registry.counter("requests_total", "Total requests")

        assert counter is not None
        assert registry.get("requests_total") is counter

    def test_register_gauge(self, registry):
        """Should register gauge."""
        gauge = registry.gauge("active_users", "Active users")

        assert gauge is not None
        assert registry.get("active_users") is gauge

    def test_register_histogram(self, registry):
        """Should register histogram."""
        histogram = registry.histogram("latency", "Latency")

        assert histogram is not None
        assert registry.get("latency") is histogram

    def test_duplicate_registration_returns_same(self, registry):
        """Registering same metric twice returns same instance."""
        c1 = registry.counter("test", "test")
        c2 = registry.counter("test", "test")

        assert c1 is c2

    def test_export_all(self, registry):
        """Should export all metrics."""
        registry.counter("a", "A").inc(10)
        registry.gauge("b", "B").set(20)
        registry.histogram("c", "C", buckets=[1]).observe(0.5)

        data = registry.export()

        assert len(data) == 3
        assert any(m["name"] == "a" for m in data)

    def test_export_json(self, registry):
        """Should export as JSON string."""
        registry.counter("test", "test").inc()

        json_str = registry.export_json()

        # Should be valid JSON
        data = json.loads(json_str)
        assert len(data) >= 1

    def test_clear(self, registry):
        """Should clear all metrics."""
        registry.counter("a", "A")
        registry.gauge("b", "B")

        registry.clear()

        assert registry.get("a") is None
        assert registry.get("b") is None


# =============================================================================
# NATIVE OBSERVER
# =============================================================================


class TestNativeObserver:
    """Test native observer implementation."""

    @pytest.fixture
    def observer(self):
        """Create native observer."""
        return NativeObserver()

    def test_implements_protocol(self, observer):
        """NativeObserver should implement ObserverProtocol."""
        assert isinstance(observer, ObserverProtocol)

    def test_record_event(self, observer):
        """Should record metric events."""
        observer.record(
            name="arm_selected",
            value=1,
            labels={"arm": "gpt-4", "context": "code"},
        )

        events = observer.get_events()

        assert len(events) >= 1
        assert events[-1].name == "arm_selected"

    def test_get_metric(self, observer):
        """Should retrieve metrics by name."""
        observer.counter("test_counter").inc(5)

        metric = observer.get_metric("test_counter")

        assert metric.value == 5

    def test_track_regret(self, observer):
        """Should track regret trend."""
        observer.track_regret(optimal_reward=1.0, actual_reward=0.8)
        observer.track_regret(optimal_reward=1.0, actual_reward=0.9)
        observer.track_regret(optimal_reward=1.0, actual_reward=0.95)

        regret = observer.get_cumulative_regret()

        assert regret == pytest.approx(0.35, rel=0.01)

    def test_track_arm_selection(self, observer):
        """Should track arm selection distribution."""
        observer.track_arm_selection("gpt-4")
        observer.track_arm_selection("gpt-4")
        observer.track_arm_selection("claude-3")

        distribution = observer.get_arm_distribution()

        assert distribution["gpt-4"] == 2
        assert distribution["claude-3"] == 1

    def test_track_confidence_accuracy(self, observer):
        """Should track confidence calibration."""
        # 80% confidence predictions
        observer.track_prediction(confidence=0.8, actual_success=True)
        observer.track_prediction(confidence=0.8, actual_success=True)
        observer.track_prediction(confidence=0.8, actual_success=True)
        observer.track_prediction(confidence=0.8, actual_success=True)
        observer.track_prediction(confidence=0.8, actual_success=False)

        calibration = observer.get_calibration_error()

        # Should show good calibration (80% confidence, 80% success)
        assert calibration < 0.1  # Low error means well-calibrated

    def test_track_cost(self, observer):
        """Should track request costs."""
        observer.track_cost(0.05, model="gpt-4")
        observer.track_cost(0.01, model="gpt-3.5")
        observer.track_cost(0.03, model="gpt-4")

        total = observer.get_total_cost()
        by_model = observer.get_cost_by_model()

        assert total == pytest.approx(0.09, rel=0.01)
        assert by_model["gpt-4"] == pytest.approx(0.08, rel=0.01)

    def test_track_cache_hits(self, observer):
        """Should track cache hit rate."""
        observer.track_cache_access(hit=True)
        observer.track_cache_access(hit=True)
        observer.track_cache_access(hit=False)

        hit_rate = observer.get_cache_hit_rate()

        assert hit_rate == pytest.approx(0.667, rel=0.01)

    def test_export_to_json(self, observer):
        """Should export all metrics to JSON."""
        observer.counter("test").inc()
        observer.track_regret(1.0, 0.8)

        json_str = observer.export_json()

        data = json.loads(json_str)
        assert "metrics" in data
        assert "events" in data or "summary" in data


# =============================================================================
# LEARNING METRICS
# =============================================================================


class TestLearningMetrics:
    """Test learning-specific metrics."""

    @pytest.fixture
    def observer(self):
        return NativeObserver()

    def test_regret_trend_decreasing(self, observer):
        """Regret should decrease over time as MAB learns."""
        # Early: poor selections
        for _ in range(10):
            observer.track_regret(optimal_reward=1.0, actual_reward=0.5)

        early_regret = observer.get_average_regret(window=10)

        # Later: better selections
        for _ in range(10):
            observer.track_regret(optimal_reward=1.0, actual_reward=0.9)

        late_regret = observer.get_average_regret(window=10)

        assert late_regret < early_regret

    def test_arm_convergence(self, observer):
        """Should detect arm selection convergence."""
        # Initially explore
        for arm in ["a", "b", "c", "a", "b", "c"]:
            observer.track_arm_selection(arm)

        early_entropy = observer.get_selection_entropy()

        # Later converge on "a"
        for _ in range(20):
            observer.track_arm_selection("a")

        late_entropy = observer.get_selection_entropy()

        # Entropy should decrease as we converge
        assert late_entropy < early_entropy

    def test_episode_tracking(self, observer):
        """Should track learning episodes."""
        observer.start_episode()
        observer.track_arm_selection("gpt-4")
        observer.track_regret(1.0, 0.8)
        observer.end_episode(total_reward=0.8)

        episodes = observer.get_episodes()

        assert len(episodes) == 1
        assert episodes[0]["total_reward"] == 0.8


# =============================================================================
# OBSERVER PROTOCOL
# =============================================================================


class TestObserverProtocol:
    """Test observer protocol interface."""

    def test_protocol_methods(self):
        """Protocol should define required methods."""
        # These should be defined in the protocol
        assert hasattr(ObserverProtocol, "record")
        assert hasattr(ObserverProtocol, "counter")
        assert hasattr(ObserverProtocol, "gauge")
        assert hasattr(ObserverProtocol, "histogram")
        assert hasattr(ObserverProtocol, "export_json")

    def test_native_implements_all(self):
        """NativeObserver should implement all protocol methods."""
        observer = NativeObserver()

        # Should not raise
        observer.counter("test")
        observer.gauge("test2")
        observer.histogram("test3")
        observer.record("event", 1)
        observer.export_json()


# =============================================================================
# METRIC EVENTS
# =============================================================================


class TestMetricEvents:
    """Test metric event structure."""

    def test_event_has_timestamp(self):
        """Events should have timestamps."""
        event = MetricEvent(
            name="test",
            value=1,
            metric_type=MetricType.COUNTER,
        )

        assert event.timestamp is not None

    def test_event_serializable(self):
        """Events should be JSON serializable."""
        event = MetricEvent(
            name="test",
            value=42,
            metric_type=MetricType.GAUGE,
            labels={"key": "value"},
        )

        data = event.model_dump()
        json.dumps(data)  # Should not raise

    def test_event_labels(self):
        """Events should support labels."""
        event = MetricEvent(
            name="request",
            value=1,
            metric_type=MetricType.COUNTER,
            labels={"method": "GET", "status": "200"},
        )

        assert event.labels["method"] == "GET"


# =============================================================================
# WEAVE INTEGRATION (OPTIONAL)
# =============================================================================


class TestWeaveIntegration:
    """Test optional Weave adapter."""

    def test_weave_import_optional(self):
        """Weave should be importable but optional."""
        try:
            from convergence.observability.weave import WeaveObserver

            # If weave is installed, adapter should work
            observer = WeaveObserver()
            assert isinstance(observer, ObserverProtocol)
        except ImportError:
            # Weave not installed - this is fine
            pytest.skip("Weave not installed")

    def test_native_works_without_weave(self):
        """Native observer should work without Weave installed."""
        observer = NativeObserver()

        observer.counter("test").inc()
        observer.track_regret(1.0, 0.8)

        # Should work even if weave not installed
        assert observer.get_metric("test").value == 1


# =============================================================================
# EDGE CASES
# =============================================================================


class TestObservabilityEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def observer(self):
        return NativeObserver()

    def test_empty_export(self, observer):
        """Should handle export with no data."""
        json_str = observer.export_json()

        data = json.loads(json_str)
        # Should be valid JSON even if empty
        assert isinstance(data, dict)

    def test_concurrent_updates(self, observer):
        """Should handle concurrent metric updates."""
        import asyncio

        async def increment(n):
            for _ in range(n):
                observer.counter("concurrent").inc()

        async def run():
            await asyncio.gather(
                increment(100),
                increment(100),
                increment(100),
            )

        asyncio.run(run())

        # All increments should be counted
        assert observer.get_metric("concurrent").value == 300

    def test_large_histogram(self, observer):
        """Should handle large number of observations."""
        histogram = observer.histogram("large", buckets=[0.1, 0.5, 1.0, 5.0, 10.0])

        for i in range(10000):
            histogram.observe(i / 1000)  # 0 to 10 seconds

        assert histogram.count == 10000

    def test_unicode_labels(self, observer):
        """Should handle unicode in labels."""
        observer.counter("requests", labels=["endpoint"]).labels(endpoint="/api/日本語").inc()

        metric = observer.get_metric("requests")
        # Should not crash
        assert metric is not None

    def test_special_characters_in_names(self, observer):
        """Should handle special characters in metric names."""
        # These should work
        observer.counter("my_metric").inc()
        observer.counter("my.metric").inc()
        observer.counter("my-metric").inc()
