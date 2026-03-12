"""
Protocol definitions for the observability layer.

Defines the contract that all observers must implement.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics supported."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class MetricEvent(BaseModel):
    """A recorded metric event."""

    name: str
    value: float
    metric_type: MetricType
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "frozen": False,
        "use_enum_values": True,  # Serialize enums as their values
    }

    def model_dump(self, **kwargs: Any) -> Dict[str, Any]:
        """Override to ensure JSON-serializable output."""
        data = super().model_dump(**kwargs)
        # Ensure timestamp is serializable
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data


@runtime_checkable
class Counter(Protocol):
    """Protocol for counter metrics."""

    @property
    def value(self) -> float:
        """Current counter value."""
        ...

    def inc(self, value: float = 1) -> None:
        """Increment counter."""
        ...

    def labels(self, **kwargs: str) -> "Counter":
        """Return counter with labels."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        ...


@runtime_checkable
class Gauge(Protocol):
    """Protocol for gauge metrics."""

    @property
    def value(self) -> float:
        """Current gauge value."""
        ...

    def set(self, value: float) -> None:
        """Set gauge value."""
        ...

    def inc(self, value: float = 1) -> None:
        """Increment gauge."""
        ...

    def dec(self, value: float = 1) -> None:
        """Decrement gauge."""
        ...

    def labels(self, **kwargs: str) -> "Gauge":
        """Return gauge with labels."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        ...


@runtime_checkable
class Histogram(Protocol):
    """Protocol for histogram metrics."""

    @property
    def count(self) -> int:
        """Number of observations."""
        ...

    @property
    def sum(self) -> float:
        """Sum of observations."""
        ...

    def observe(self, value: float) -> None:
        """Record an observation."""
        ...

    def get_buckets(self) -> Dict[float, int]:
        """Get bucket counts."""
        ...

    def percentile(self, p: float) -> float:
        """Get percentile value."""
        ...

    def labels(self, **kwargs: str) -> "Histogram":
        """Return histogram with labels."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        ...


@runtime_checkable
class ObserverProtocol(Protocol):
    """Protocol that all observers must implement."""

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric event."""
        ...

    def counter(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> Counter:
        """Create or get a counter metric."""
        ...

    def gauge(
        self,
        name: str,
        help: str = "",
        labels: Optional[List[str]] = None,
    ) -> Gauge:
        """Create or get a gauge metric."""
        ...

    def histogram(
        self,
        name: str,
        help: str = "",
        buckets: Optional[List[float]] = None,
        labels: Optional[List[str]] = None,
    ) -> Histogram:
        """Create or get a histogram metric."""
        ...

    def export_json(self) -> str:
        """Export all metrics as JSON."""
        ...
