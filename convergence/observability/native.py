"""
Native observer implementation.

Works standalone without Weave. Provides learning-specific metrics
for monitoring the MAB/RL optimization process.
"""

import json
import math
import threading
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from convergence.observability.metrics import Counter, Gauge, Histogram, MetricsRegistry
from convergence.observability.protocol import MetricEvent, MetricType


class NativeObserver:
    """
    Native observability implementation.

    Implements ObserverProtocol with learning-specific tracking:
    - Regret tracking for MAB evaluation
    - Arm selection distribution and entropy
    - Confidence calibration
    - Cost tracking by model
    - Cache hit rates
    - Episode tracking
    """

    def __init__(self) -> None:
        self._registry = MetricsRegistry()
        self._events: List[MetricEvent] = []
        self._lock = threading.Lock()

        # Learning-specific tracking
        self._regrets: List[float] = []
        self._arm_counts: Dict[str, int] = defaultdict(int)
        self._predictions: List[Dict[str, Any]] = []  # {confidence, actual_success}
        self._costs: Dict[str, float] = defaultdict(float)
        self._total_cost: float = 0.0
        self._cache_hits: int = 0
        self._cache_total: int = 0
        self._episodes: List[Dict[str, Any]] = []
        self._current_episode: Optional[Dict[str, Any]] = None

    # =========================================================================
    # ObserverProtocol implementation
    # =========================================================================

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a metric event."""
        event = MetricEvent(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,  # Default type for raw records
            labels=labels or {},
        )
        with self._lock:
            self._events.append(event)

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
        """Export all metrics and learning data as JSON."""
        with self._lock:
            # Compute values inline to avoid deadlock from nested lock acquisition
            cumulative_regret = sum(self._regrets)
            cache_hit_rate = (
                self._cache_hits / self._cache_total
                if self._cache_total > 0
                else 0.0
            )
            data = {
                "metrics": self._registry.export(),
                "summary": {
                    "cumulative_regret": cumulative_regret,
                    "arm_distribution": dict(self._arm_counts),
                    "total_cost": self._total_cost,
                    "cache_hit_rate": cache_hit_rate,
                    "episodes_count": len(self._episodes),
                },
            }
            return json.dumps(data, indent=2, default=str)

    # =========================================================================
    # Learning-specific methods
    # =========================================================================

    def get_events(self) -> List[MetricEvent]:
        """Get all recorded events."""
        with self._lock:
            return self._events.copy()

    def get_metric(
        self, name: str
    ) -> Optional[Union[Counter, Gauge, Histogram]]:
        """Get a metric by name."""
        return self._registry.get(name)

    def track_regret(self, optimal_reward: float, actual_reward: float) -> None:
        """
        Track regret for MAB evaluation.

        Regret = optimal_reward - actual_reward
        """
        regret = optimal_reward - actual_reward
        with self._lock:
            self._regrets.append(regret)

    def get_cumulative_regret(self) -> float:
        """Get cumulative regret across all selections."""
        with self._lock:
            return sum(self._regrets)

    def get_average_regret(self, window: Optional[int] = None) -> float:
        """
        Get average regret.

        Args:
            window: If provided, only consider the last N regrets.
        """
        with self._lock:
            if not self._regrets:
                return 0.0
            regrets = self._regrets[-window:] if window else self._regrets
            return sum(regrets) / len(regrets) if regrets else 0.0

    def track_arm_selection(self, arm_id: str) -> None:
        """Track which arm was selected."""
        with self._lock:
            self._arm_counts[arm_id] += 1

    def get_arm_distribution(self) -> Dict[str, int]:
        """Get arm selection distribution."""
        with self._lock:
            return dict(self._arm_counts)

    def get_selection_entropy(self) -> float:
        """
        Calculate Shannon entropy of arm selection distribution.

        Higher entropy = more exploration.
        Lower entropy = more exploitation (convergence).
        """
        with self._lock:
            if not self._arm_counts:
                return 0.0

            total = sum(self._arm_counts.values())
            if total == 0:
                return 0.0

            entropy = 0.0
            for count in self._arm_counts.values():
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)
            return entropy

    def track_prediction(self, confidence: float, actual_success: bool) -> None:
        """
        Track prediction for calibration analysis.

        Well-calibrated: 80% confident predictions succeed 80% of the time.
        """
        with self._lock:
            self._predictions.append({
                "confidence": confidence,
                "actual_success": actual_success,
            })

    def get_calibration_error(self) -> float:
        """
        Calculate Expected Calibration Error (ECE).

        Lower is better. 0 = perfectly calibrated.
        """
        with self._lock:
            if not self._predictions:
                return 0.0

            # Bin predictions by confidence
            bins: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
            for pred in self._predictions:
                bin_idx = int(pred["confidence"] * 10)  # 10 bins
                bins[bin_idx].append(pred)

            ece = 0.0
            total = len(self._predictions)

            for bin_idx, preds in bins.items():
                if not preds:
                    continue
                avg_confidence = sum(p["confidence"] for p in preds) / len(preds)
                accuracy = sum(1 for p in preds if p["actual_success"]) / len(preds)
                weight = len(preds) / total
                ece += weight * abs(avg_confidence - accuracy)

            return ece

    def track_cost(self, amount: float, model: str) -> None:
        """Track API cost by model."""
        with self._lock:
            self._costs[model] += amount
            self._total_cost += amount

    def get_total_cost(self) -> float:
        """Get total cost across all models."""
        with self._lock:
            return self._total_cost

    def get_cost_by_model(self) -> Dict[str, float]:
        """Get cost breakdown by model."""
        with self._lock:
            return dict(self._costs)

    def track_cache_access(self, hit: bool) -> None:
        """Track cache hit/miss."""
        with self._lock:
            self._cache_total += 1
            if hit:
                self._cache_hits += 1

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        with self._lock:
            if self._cache_total == 0:
                return 0.0
            return self._cache_hits / self._cache_total

    def start_episode(self) -> None:
        """Start a new learning episode."""
        with self._lock:
            self._current_episode = {
                "start_time": datetime.utcnow(),
                "events": [],
            }

    def end_episode(self, total_reward: float) -> None:
        """End current episode with final reward."""
        with self._lock:
            if self._current_episode is not None:
                self._current_episode["end_time"] = datetime.utcnow()
                self._current_episode["total_reward"] = total_reward
                self._episodes.append(self._current_episode)
                self._current_episode = None

    def get_episodes(self) -> List[Dict[str, Any]]:
        """Get all completed episodes."""
        with self._lock:
            return self._episodes.copy()
