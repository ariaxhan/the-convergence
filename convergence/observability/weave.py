"""
Optional Weave adapter for observability.

Only works if weave is installed. Raises ImportError otherwise.
"""

import threading
from typing import Any, Dict, List, Optional

try:
    import weave

    WEAVE_AVAILABLE = True
except ImportError:
    WEAVE_AVAILABLE = False

from convergence.observability.metrics import Counter, Gauge, Histogram, MetricsRegistry
from convergence.observability.protocol import MetricEvent, MetricType


class WeaveObserver:
    """
    Weave-backed observer implementation.

    Integrates with Weights & Biases Weave for experiment tracking.
    Requires weave to be installed.
    """

    def __init__(self) -> None:
        if not WEAVE_AVAILABLE:
            raise ImportError(
                "weave is not installed. Install it with: pip install weave"
            )

        self._registry = MetricsRegistry()
        self._events: List[MetricEvent] = []
        self._lock = threading.Lock()  # Thread-safety for events list

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric event to Weave."""
        event = MetricEvent(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {},
        )
        with self._lock:
            self._events.append(event)

        # Log to Weave
        if WEAVE_AVAILABLE:
            weave.log({name: value, **(labels or {})})

    def counter(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """Create or get a counter metric."""
        return self._registry.counter(name, help, labels)

    def gauge(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """Create or get a gauge metric."""
        return self._registry.gauge(name, help, labels)

    def histogram(
        self,
        name: str,
        help: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ) -> Histogram:
        """Create or get a histogram metric."""
        return self._registry.histogram(name, help, buckets, labels)

    def export_json(self) -> str:
        """Export all metrics as JSON."""
        import json

        return json.dumps(
            {
                "metrics": self._registry.export(),
                "events": [e.model_dump() for e in self._events],
            },
            indent=2,
            default=str,
        )
