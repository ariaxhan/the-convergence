"""
Metric primitives for the observability layer.

Thread-safe implementations of Counter, Gauge, and Histogram.
"""

import json
import threading
from typing import Any, Dict, List, Optional, Union


# Default histogram buckets (Prometheus-style)
DEFAULT_BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]


class Counter:
    """
    A counter metric that can only increase.

    Thread-safe.
    """

    def __init__(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> None:
        self._name = name
        self._help = help
        self._label_names = labels or []
        self._value: float = 0.0
        self._labeled_values: Dict[tuple, "Counter"] = {}
        self._lock = threading.Lock()

    @property
    def value(self) -> float:
        """Current counter value."""
        with self._lock:
            return self._value

    def inc(self, value: float = 1) -> None:
        """Increment counter by value (must be non-negative)."""
        if value < 0:
            raise ValueError("Counter can only increase (value must be >= 0)")
        with self._lock:
            self._value += value

    def labels(self, **kwargs: str) -> "Counter":
        """Return counter with specific label values."""
        key = tuple(sorted(kwargs.items()))
        with self._lock:
            if key not in self._labeled_values:
                child = Counter(self._name, self._help)
                child._label_names = self._label_names
                self._labeled_values[key] = child
            return self._labeled_values[key]

    def to_dict(self) -> Dict[str, Any]:
        """Export counter to dictionary."""
        with self._lock:
            result: Dict[str, Any] = {
                "name": self._name,
                "type": "counter",
                "value": self._value,
            }
            if self._help:
                result["help"] = self._help
            if self._labeled_values:
                result["labeled"] = {
                    str(k): v._value for k, v in self._labeled_values.items()
                }
            return result


class Gauge:
    """
    A gauge metric that can go up and down.

    Thread-safe.
    """

    def __init__(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> None:
        self._name = name
        self._help = help
        self._label_names = labels or []
        self._value: float = 0.0
        self._labeled_values: Dict[tuple, "Gauge"] = {}
        self._lock = threading.Lock()

    @property
    def value(self) -> float:
        """Current gauge value."""
        with self._lock:
            return self._value

    def set(self, value: float) -> None:
        """Set gauge to specific value."""
        with self._lock:
            self._value = value

    def inc(self, value: float = 1) -> None:
        """Increment gauge by value."""
        with self._lock:
            self._value += value

    def dec(self, value: float = 1) -> None:
        """Decrement gauge by value."""
        with self._lock:
            self._value -= value

    def labels(self, **kwargs: str) -> "Gauge":
        """Return gauge with specific label values."""
        key = tuple(sorted(kwargs.items()))
        with self._lock:
            if key not in self._labeled_values:
                child = Gauge(self._name, self._help)
                child._label_names = self._label_names
                self._labeled_values[key] = child
            return self._labeled_values[key]

    def to_dict(self) -> Dict[str, Any]:
        """Export gauge to dictionary."""
        with self._lock:
            result: Dict[str, Any] = {
                "name": self._name,
                "type": "gauge",
                "value": self._value,
            }
            if self._help:
                result["help"] = self._help
            if self._labeled_values:
                result["labeled"] = {
                    str(k): v._value for k, v in self._labeled_values.items()
                }
            return result


class Histogram:
    """
    A histogram metric that tracks distributions.

    Thread-safe.
    """

    def __init__(
        self,
        name: str,
        help: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ) -> None:
        self._name = name
        self._help = help
        self._buckets = sorted(buckets) if buckets else DEFAULT_BUCKETS.copy()
        self._label_names = labels or []
        self._count: int = 0
        self._sum: float = 0.0
        self._bucket_counts: Dict[float, int] = {b: 0 for b in self._buckets}
        self._observations: List[float] = []  # For percentile calculation
        self._labeled_values: Dict[tuple, "Histogram"] = {}
        self._lock = threading.Lock()

    @property
    def count(self) -> int:
        """Number of observations."""
        with self._lock:
            return self._count

    @property
    def sum(self) -> float:
        """Sum of all observations."""
        with self._lock:
            return self._sum

    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self._count += 1
            self._sum += value
            self._observations.append(value)
            # Update bucket counts (cumulative)
            for bucket in self._buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1

    def get_buckets(self) -> Dict[float, int]:
        """Get bucket counts (cumulative)."""
        with self._lock:
            return self._bucket_counts.copy()

    def percentile(self, p: float) -> float:
        """
        Calculate percentile from observations.

        Uses linear interpolation between bucket boundaries.
        """
        with self._lock:
            if not self._observations:
                return 0.0

            sorted_obs = sorted(self._observations)
            n = len(sorted_obs)
            idx = (p / 100.0) * (n - 1)
            lower = int(idx)
            upper = min(lower + 1, n - 1)
            weight = idx - lower

            return sorted_obs[lower] * (1 - weight) + sorted_obs[upper] * weight

    def labels(self, **kwargs: str) -> "Histogram":
        """Return histogram with specific label values."""
        key = tuple(sorted(kwargs.items()))
        with self._lock:
            if key not in self._labeled_values:
                child = Histogram(self._name, self._help, self._buckets.copy())
                child._label_names = self._label_names
                self._labeled_values[key] = child
            return self._labeled_values[key]

    def to_dict(self) -> Dict[str, Any]:
        """Export histogram to dictionary."""
        with self._lock:
            result: Dict[str, Any] = {
                "name": self._name,
                "type": "histogram",
                "count": self._count,
                "sum": self._sum,
                "buckets": self._bucket_counts.copy(),
            }
            if self._help:
                result["help"] = self._help
            if self._labeled_values:
                result["labeled"] = {
                    str(k): {"count": v._count, "sum": v._sum}
                    for k, v in self._labeled_values.items()
                }
            return result


class MetricsRegistry:
    """
    Registry for all metrics.

    Thread-safe container for metrics.
    """

    def __init__(self) -> None:
        self._metrics: Dict[str, Union[Counter, Gauge, Histogram]] = {}
        self._lock = threading.Lock()

    def counter(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """Create or get a counter."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if isinstance(metric, Counter):
                    return metric
                raise ValueError(f"Metric {name} already exists with different type")
            counter = Counter(name, help, labels)
            self._metrics[name] = counter
            return counter

    def gauge(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """Create or get a gauge."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if isinstance(metric, Gauge):
                    return metric
                raise ValueError(f"Metric {name} already exists with different type")
            gauge = Gauge(name, help, labels)
            self._metrics[name] = gauge
            return gauge

    def histogram(
        self,
        name: str,
        help: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ) -> Histogram:
        """Create or get a histogram."""
        with self._lock:
            if name in self._metrics:
                metric = self._metrics[name]
                if isinstance(metric, Histogram):
                    return metric
                raise ValueError(f"Metric {name} already exists with different type")
            histogram = Histogram(name, help, buckets, labels)
            self._metrics[name] = histogram
            return histogram

    def get(self, name: str) -> Optional[Union[Counter, Gauge, Histogram]]:
        """Get a metric by name."""
        with self._lock:
            return self._metrics.get(name)

    def export(self) -> List[Dict[str, Any]]:
        """Export all metrics as list of dicts."""
        with self._lock:
            return [m.to_dict() for m in self._metrics.values()]

    def export_json(self) -> str:
        """Export all metrics as JSON string."""
        return json.dumps(self.export(), indent=2)

    def clear(self) -> None:
        """Clear all metrics."""
        with self._lock:
            self._metrics.clear()
