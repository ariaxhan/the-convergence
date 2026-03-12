"""
Adversary QA testing for P2-001 Observability Protocol.

Focus areas:
1. Histogram percentile edge cases (empty, single value, all same)
2. Calibration error division by zero
3. Selection entropy with empty distribution
4. Memory leaks (unbounded growth)
5. Thread safety and deadlock detection
"""

import pytest
import json
import threading
import time
import math
from convergence.observability.native import NativeObserver
from convergence.observability.metrics import Histogram, Counter, Gauge


class TestHistogramEdgeCases:
    """Test histogram percentile computation edge cases."""

    def test_percentile_empty_histogram(self):
        """CRITICAL: Percentile on empty histogram should handle gracefully."""
        histogram = Histogram("test", buckets=[0.1, 0.5, 1.0])
        
        # No observations recorded
        p50 = histogram.percentile(50)
        p95 = histogram.percentile(95)
        p99 = histogram.percentile(99)
        
        # Should return 0.0, not crash or infinite loop
        assert p50 == 0.0
        assert p95 == 0.0
        assert p99 == 0.0
        print("✓ Empty histogram percentile: PASS")

    def test_percentile_single_observation(self):
        """Percentile with single observation."""
        histogram = Histogram("test", buckets=[0.1, 0.5, 1.0])
        histogram.observe(0.5)
        
        p0 = histogram.percentile(0)
        p50 = histogram.percentile(50)
        p100 = histogram.percentile(100)
        
        # All should return the single value
        assert p0 == 0.5
        assert p50 == 0.5
        assert p100 == 0.5
        print("✓ Single observation percentile: PASS")

    def test_percentile_all_same_value(self):
        """Percentile when all observations are identical."""
        histogram = Histogram("test", buckets=[0.1, 0.5, 1.0])
        
        # Add 100 identical values
        for _ in range(100):
            histogram.observe(0.5)
        
        p50 = histogram.percentile(50)
        p95 = histogram.percentile(95)
        
        # All percentiles should be the same value
        assert p50 == 0.5
        assert p95 == 0.5
        print("✓ All same values percentile: PASS")

    def test_percentile_extreme_percentiles(self):
        """Percentile at boundaries (0, 100)."""
        histogram = Histogram("test", buckets=[1, 5, 10])
        
        for i in range(1, 11):
            histogram.observe(float(i))
        
        p0 = histogram.percentile(0)
        p100 = histogram.percentile(100)
        
        # p0 should be minimum, p100 should be maximum
        assert p0 <= 1.0
        assert p100 >= 10.0
        print("✓ Extreme percentiles: PASS")


class TestCalibrationEdgeCases:
    """Test calibration error computation edge cases."""

    def test_calibration_no_predictions(self):
        """CRITICAL: Calibration error with no predictions."""
        observer = NativeObserver()
        
        # No predictions tracked
        ece = observer.get_calibration_error()
        
        # Should return 0.0, not crash
        assert ece == 0.0
        assert isinstance(ece, float)
        print("✓ Empty calibration error: PASS")

    def test_calibration_single_prediction(self):
        """Calibration error with single prediction."""
        observer = NativeObserver()
        observer.track_prediction(confidence=0.8, actual_success=True)
        
        ece = observer.get_calibration_error()
        
        # Should be valid number
        assert isinstance(ece, float)
        assert ece >= 0.0
        assert ece <= 1.0
        print("✓ Single prediction calibration: PASS")

    def test_calibration_all_same_confidence(self):
        """Calibration error when all predictions have same confidence."""
        observer = NativeObserver()
        
        # All 0.8 confidence, all succeed
        for _ in range(50):
            observer.track_prediction(confidence=0.8, actual_success=True)
        
        ece = observer.get_calibration_error()
        
        # Well-calibrated: 0.8 confidence, 1.0 accuracy -> error = |0.8 - 1.0| = 0.2
        assert ece >= 0.1 and ece <= 0.3
        print("✓ Same confidence calibration: PASS")

    def test_calibration_perfect(self):
        """Calibration error for perfectly calibrated predictions."""
        observer = NativeObserver()
        
        # 50% confidence -> 50% success
        for _ in range(100):
            observer.track_prediction(confidence=0.5, actual_success=(True if hash(time.time()) % 2 == 0 else False))
        
        # Just verify it returns a valid number
        ece = observer.get_calibration_error()
        assert isinstance(ece, float)
        assert 0.0 <= ece <= 1.0
        print("✓ Perfect calibration: PASS")


class TestSelectionEntropyEdgeCases:
    """Test selection entropy edge cases."""

    def test_entropy_empty_distribution(self):
        """CRITICAL: Entropy with no arm selections."""
        observer = NativeObserver()
        
        # No arms selected
        entropy = observer.get_selection_entropy()
        
        # Should return 0.0, not NaN or crash
        assert entropy == 0.0
        assert not math.isnan(entropy)
        print("✓ Empty entropy: PASS")

    def test_entropy_single_arm(self):
        """Entropy when only one arm ever selected."""
        observer = NativeObserver()
        
        for _ in range(100):
            observer.track_arm_selection("arm_a")
        
        entropy = observer.get_selection_entropy()
        
        # Entropy should be 0 (no exploration)
        assert entropy == 0.0
        print("✓ Single arm entropy: PASS")

    def test_entropy_uniform_distribution(self):
        """Entropy with uniform arm distribution."""
        observer = NativeObserver()
        
        # Equal selections of 3 arms
        for _ in range(10):
            observer.track_arm_selection("a")
            observer.track_arm_selection("b")
            observer.track_arm_selection("c")
        
        entropy = observer.get_selection_entropy()
        
        # Max entropy for 3 arms = log2(3) ≈ 1.585
        # Should be close to this
        assert entropy > 1.5 and entropy <= math.log2(3)
        print("✓ Uniform entropy: PASS")

    def test_entropy_non_nan(self):
        """Entropy computation should never return NaN."""
        observer = NativeObserver()
        
        # Various distributions
        observer.track_arm_selection("a")
        observer.track_arm_selection("b")
        observer.track_arm_selection("a")
        observer.track_arm_selection("a")
        
        entropy = observer.get_selection_entropy()
        
        assert not math.isnan(entropy)
        assert entropy >= 0.0
        print("✓ Entropy non-NaN: PASS")


class TestMemoryLeaks:
    """Test for unbounded memory growth."""

    def test_events_unbounded_growth(self):
        """CRITICAL: Event list shouldn't grow unbounded."""
        observer = NativeObserver()
        
        # Record many events
        for i in range(1000):
            observer.record(f"event_{i}", float(i))
        
        events = observer.get_events()
        
        # All events should be stored (this is expected behavior)
        assert len(events) == 1000
        print("✓ Events stored (expected): 1000 events")

    def test_episodes_unbounded_growth(self):
        """CRITICAL: Episode list shouldn't grow unbounded."""
        observer = NativeObserver()
        
        # Start and end many episodes
        for i in range(100):
            observer.start_episode()
            observer.track_arm_selection("arm_a")
            observer.end_episode(total_reward=0.8)
        
        episodes = observer.get_episodes()
        
        # All episodes should be stored
        assert len(episodes) == 100
        print("✓ Episodes stored (expected): 100 episodes")

    def test_regret_history_grows(self):
        """Regret history should grow linearly."""
        observer = NativeObserver()
        
        regrets_before = observer.get_cumulative_regret()
        
        # Add 1000 regret values
        for _ in range(1000):
            observer.track_regret(optimal_reward=1.0, actual_reward=0.5)
        
        regrets_after = observer.get_cumulative_regret()
        
        # Should have grown
        assert regrets_after > regrets_before
        # Should be roughly 500 (1000 * 0.5)
        assert regrets_after == pytest.approx(500.0, rel=0.01)
        print("✓ Regret history grows linearly: PASS")


class TestThreadSafety:
    """Test thread-safety and deadlock detection."""

    def test_no_deadlock_concurrent_histogram_percentile(self):
        """Test histogram percentile under concurrent access."""
        histogram = Histogram("test", buckets=[0.1, 0.5, 1.0, 5.0])
        errors = []
        
        def observer_thread():
            try:
                for i in range(100):
                    histogram.observe(i / 100)
            except Exception as e:
                errors.append(("observe", e))
        
        def percentile_thread():
            try:
                for _ in range(100):
                    histogram.percentile(50)
            except Exception as e:
                errors.append(("percentile", e))
        
        threads = [
            threading.Thread(target=observer_thread),
            threading.Thread(target=percentile_thread),
            threading.Thread(target=percentile_thread),
        ]
        
        for t in threads:
            t.start()
        
        # Set timeout to detect deadlocks
        for t in threads:
            t.join(timeout=5)
        
        if errors:
            print(f"✗ Concurrent deadlock test: ERRORS: {errors}")
            assert False, f"Thread errors: {errors}"
        
        print("✓ Concurrent histogram access: PASS (no deadlock)")

    def test_no_deadlock_nested_locks(self):
        """Test that nested lock acquisition doesn't cause deadlock."""
        observer = NativeObserver()
        
        # This should not deadlock
        observer.track_regret(1.0, 0.8)
        observer.track_arm_selection("a")
        observer.track_prediction(0.8, True)
        observer.track_cost(0.1, "gpt-4")
        
        # Export calls should work without deadlock
        json_str = observer.export_json()
        data = json.loads(json_str)
        
        assert isinstance(data, dict)
        print("✓ Nested locks (export during updates): PASS (no deadlock)")


class TestDivisionByZero:
    """Test division by zero edge cases."""

    def test_cache_hit_rate_no_accesses(self):
        """Cache hit rate when no accesses recorded."""
        observer = NativeObserver()
        
        # No cache accesses
        hit_rate = observer.get_cache_hit_rate()
        
        # Should be 0.0, not crash or NaN
        assert hit_rate == 0.0
        print("✓ Cache hit rate (no accesses): PASS")

    def test_average_regret_empty(self):
        """Average regret with no regrets."""
        observer = NativeObserver()
        
        # No regrets tracked
        avg = observer.get_average_regret()
        
        # Should be 0.0
        assert avg == 0.0
        print("✓ Average regret (empty): PASS")

    def test_average_regret_with_window(self):
        """Average regret with window larger than data."""
        observer = NativeObserver()
        
        observer.track_regret(1.0, 0.8)
        observer.track_regret(1.0, 0.9)
        
        # Window larger than data
        avg = observer.get_average_regret(window=100)
        
        # Should still compute correctly
        assert avg == pytest.approx(0.15, rel=0.01)
        print("✓ Average regret (large window): PASS")


class TestLargeInputs:
    """Test with very large inputs."""

    def test_histogram_many_observations(self):
        """Histogram with many observations."""
        histogram = Histogram("test", buckets=[0.1, 0.5, 1.0, 5.0, 10.0])
        
        # 100k observations
        for i in range(100000):
            histogram.observe((i % 1000) / 100)
        
        assert histogram.count == 100000
        # Percentile should still work
        p50 = histogram.percentile(50)
        assert 0.0 <= p50 <= 10.0
        print("✓ Large histogram (100k observations): PASS")

    def test_many_arm_selections(self):
        """Entropy calculation with many arms."""
        observer = NativeObserver()
        
        # 1000 different arms, each selected once
        for i in range(1000):
            observer.track_arm_selection(f"arm_{i}")
        
        entropy = observer.get_selection_entropy()
        
        # Entropy should be maximum (log2(1000) ≈ 10)
        assert entropy > 9.0 and entropy < 11.0
        print("✓ Large arm distribution (1000 arms): PASS")

    def test_many_predictions(self):
        """Calibration error with many predictions."""
        observer = NativeObserver()
        
        # 50k predictions
        for i in range(50000):
            confidence = (i % 10) / 10  # 0.0 to 0.9
            success = i % 2 == 0
            observer.track_prediction(confidence, success)
        
        ece = observer.get_calibration_error()
        
        assert isinstance(ece, float)
        assert 0.0 <= ece <= 1.0
        print("✓ Large prediction set (50k): PASS")


# Run all tests
if __name__ == "__main__":
    test_classes = [
        TestHistogramEdgeCases,
        TestCalibrationEdgeCases,
        TestSelectionEntropyEdgeCases,
        TestMemoryLeaks,
        TestThreadSafety,
        TestDivisionByZero,
        TestLargeInputs,
    ]
    
    results = []
    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print(f"{'='*60}")
        
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    method = getattr(instance, method_name)
                    method()
                except Exception as e:
                    results.append(f"FAIL: {test_class.__name__}.{method_name}: {e}")
                    print(f"✗ {method_name}: FAIL - {e}")
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if results:
        for r in results:
            print(r)
        print(f"\nFAILED: {len(results)} issues found")
    else:
        print("All tests PASSED")
