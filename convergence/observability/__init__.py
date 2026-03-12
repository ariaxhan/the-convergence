"""Observability layer — watch the learning process."""

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

__all__ = [
    "ObserverProtocol",
    "MetricType",
    "MetricEvent",
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "NativeObserver",
]

# Optional Weave export (only if installed)
try:
    from convergence.observability.weave import WeaveObserver

    __all__.append("WeaveObserver")
except ImportError:
    pass
