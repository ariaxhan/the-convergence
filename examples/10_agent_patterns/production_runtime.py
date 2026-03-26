"""
Enterprise Runtime Manager with Production Safeguards.

What this demonstrates:
- Circuit breaker pattern for storage failures
- Exponential backoff retry logic
- Graceful degradation to deterministic fallback
- Health checks, structured logging, metrics collection
- Idempotent initialization and clean shutdown

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- "Run with different arm configurations"
- "Inject storage failures to see circuit breaker"
- "Monitor metrics dashboard across 100+ cycles"
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from armature import configure_runtime, runtime_select, runtime_update
from armature.storage.memory import MemoryRuntimeStorage
from armature.types import RuntimeArmTemplate, RuntimeConfig, SelectionStrategyConfig

logger = logging.getLogger(__name__)

# --- Constants ---
MAX_RETRIES: int = 3
RETRY_BASE_DELAY_SECONDS: float = 1.0
CIRCUIT_BREAKER_THRESHOLD: int = 5
CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = 60.0
STORAGE_TIMEOUT_SECONDS: float = 5.0
DEFAULT_ARM_ID: str = "fallback_default"


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"


@dataclass
class CircuitBreaker:
    """Tracks consecutive failures and opens circuit when threshold is exceeded."""

    threshold: int = CIRCUIT_BREAKER_THRESHOLD
    cooldown_seconds: float = CIRCUIT_BREAKER_COOLDOWN_SECONDS
    consecutive_failures: int = 0
    state: CircuitState = CircuitState.CLOSED
    opened_at: float = 0.0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            logger.warning({"event": "circuit_opened", "failures": self.consecutive_failures})

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if self.state == CircuitState.OPEN:
            self.state = CircuitState.CLOSED
            logger.info({"event": "circuit_closed"})

    def is_open(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return False
        elapsed = time.monotonic() - self.opened_at
        if elapsed >= self.cooldown_seconds:
            # Half-open: allow one attempt
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0
            logger.info({"event": "circuit_half_open", "elapsed_seconds": round(elapsed, 1)})
            return False
        return True


@dataclass
class Metrics:
    """Collects runtime operation metrics."""

    select_count: int = 0
    update_count: int = 0
    error_count: int = 0
    fallback_count: int = 0
    latencies: List[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies) * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "select_count": self.select_count,
            "update_count": self.update_count,
            "error_count": self.error_count,
            "fallback_count": self.fallback_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "total_operations": self.select_count + self.update_count,
        }


class ProductionRuntime:
    """
    Enterprise wrapper around armature runtime with production safeguards.

    Provides retry logic, circuit breaking, graceful degradation, health checks,
    structured logging, and metrics collection. Designed so swapping storage
    backends (e.g., to PostgreSQL) requires changing only the storage parameter.

    Args:
        system: System identifier for the runtime.
        config: RuntimeConfig with arm templates and strategy.
        storage: Storage backend implementing RuntimeStorageProtocol.

    Raises:
        ValueError: If system name is empty.
    """

    def __init__(
        self,
        *,
        system: str,
        config: RuntimeConfig,
        storage: Any,
    ) -> None:
        if not system or not system.strip():
            raise ValueError("System name cannot be empty")
        self._system = system
        self._config = config
        self._storage = storage
        self._circuit = CircuitBreaker()
        self._metrics = Metrics()
        self._initialized = False
        self._shutdown = False

    async def initialize(self) -> None:
        """
        Configure the runtime. Safe to call multiple times (idempotent).

        Raises:
            RuntimeError: If runtime has been shut down.
        """
        if self._shutdown:
            raise RuntimeError("Runtime has been shut down")
        if self._initialized:
            return
        await configure_runtime(
            self._system, config=self._config, storage=self._storage
        )
        self._initialized = True
        logger.info({"event": "runtime_initialized", "system": self._system})

    async def select(
        self,
        *,
        user_id: str,
        agent_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Select an arm with retry, circuit breaker, and fallback.

        Args:
            user_id: Non-empty user identifier.
            agent_type: Optional agent type tag.
            context: Optional context dict for selection.

        Returns:
            Dict with decision_id, arm_id, params, sampled_value, fallback (bool).

        Raises:
            ValueError: If user_id is empty.
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        await self.initialize()
        start = time.monotonic()

        # Circuit breaker: if open, return deterministic fallback immediately
        if self._circuit.is_open():
            self._metrics.fallback_count += 1
            logger.warning({
                "event": "circuit_open_fallback",
                "user_id": user_id,
                "arm_id": DEFAULT_ARM_ID,
            })
            return self._deterministic_fallback(user_id)

        # Retry loop with exponential backoff
        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                selection = await asyncio.wait_for(
                    runtime_select(
                        self._system,
                        user_id=user_id,
                        agent_type=agent_type,
                        context=context,
                    ),
                    timeout=STORAGE_TIMEOUT_SECONDS,
                )
                elapsed = time.monotonic() - start
                self._metrics.select_count += 1
                self._metrics.latencies.append(elapsed)
                self._circuit.record_success()

                logger.info({
                    "event": "select_success",
                    "user_id": user_id,
                    "arm_id": selection.arm_id,
                    "decision_id": selection.decision_id,
                    "latency_ms": round(elapsed * 1000, 2),
                })
                return {
                    "decision_id": selection.decision_id,
                    "arm_id": selection.arm_id,
                    "params": selection.params,
                    "sampled_value": selection.sampled_value,
                    "fallback": False,
                }
            except (asyncio.TimeoutError, Exception) as exc:
                last_error = exc
                self._metrics.error_count += 1
                delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                logger.warning({
                    "event": "select_retry",
                    "attempt": attempt + 1,
                    "delay_seconds": delay,
                    "error": str(exc),
                })
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        # All retries exhausted
        self._circuit.record_failure()
        self._metrics.fallback_count += 1
        logger.error({
            "event": "select_exhausted",
            "user_id": user_id,
            "error": str(last_error),
        })
        return self._deterministic_fallback(user_id)

    async def update(
        self,
        *,
        user_id: str,
        decision_id: str,
        reward: Optional[float] = None,
        signals: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Update arm performance with retry and circuit breaker.

        Args:
            user_id: Non-empty user identifier.
            decision_id: Decision ID from a prior select call.
            reward: Direct reward signal (0.0-1.0).
            signals: Multi-signal reward dict.

        Returns:
            Dict with success status and computed reward.

        Raises:
            ValueError: If user_id or decision_id is empty.
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")
        if not decision_id or not decision_id.strip():
            raise ValueError("decision_id cannot be empty")

        await self.initialize()
        start = time.monotonic()

        if self._circuit.is_open():
            logger.warning({"event": "circuit_open_skip_update", "decision_id": decision_id})
            return {"success": False, "reason": "circuit_open"}

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                result = await asyncio.wait_for(
                    runtime_update(
                        self._system,
                        user_id=user_id,
                        decision_id=decision_id,
                        reward=reward,
                        signals=signals,
                    ),
                    timeout=STORAGE_TIMEOUT_SECONDS,
                )
                elapsed = time.monotonic() - start
                self._metrics.update_count += 1
                self._metrics.latencies.append(elapsed)
                self._circuit.record_success()

                logger.info({
                    "event": "update_success",
                    "decision_id": decision_id,
                    "reward": reward,
                    "latency_ms": round(elapsed * 1000, 2),
                })
                return dict(result)
            except (asyncio.TimeoutError, Exception) as exc:
                last_error = exc
                self._metrics.error_count += 1
                delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(delay)

        self._circuit.record_failure()
        logger.error({
            "event": "update_exhausted",
            "decision_id": decision_id,
            "error": str(last_error),
        })
        return {"success": False, "reason": "retries_exhausted", "error": str(last_error)}

    async def health_check(self) -> Dict[str, Any]:
        """
        Verify storage connectivity and return status.

        Returns:
            Dict with status, circuit_state, storage_reachable, metrics.
        """
        storage_reachable = False
        try:
            # Probe storage with a benign read
            await asyncio.wait_for(
                self._storage.get_arms(user_id="__health__", agent_type="__probe__"),
                timeout=STORAGE_TIMEOUT_SECONDS,
            )
            storage_reachable = True
        except Exception as exc:
            logger.warning({"event": "health_check_storage_fail", "error": str(exc)})

        return {
            "status": "healthy" if storage_reachable and not self._circuit.is_open() else "degraded",
            "circuit_state": self._circuit.state.value,
            "circuit_consecutive_failures": self._circuit.consecutive_failures,
            "storage_reachable": storage_reachable,
            "initialized": self._initialized,
            "metrics": self._metrics.to_dict(),
        }

    async def shutdown(self) -> None:
        """Release resources. Safe to call multiple times."""
        self._shutdown = True
        logger.info({"event": "runtime_shutdown", "system": self._system})

    def _deterministic_fallback(self, user_id: str) -> Dict[str, Any]:
        """Return a stable fallback arm -- deterministic, not random."""
        if self._config.default_arms:
            arm = self._config.default_arms[0]
            return {
                "decision_id": None,
                "arm_id": arm.arm_id,
                "params": arm.params,
                "sampled_value": 0.5,
                "fallback": True,
            }
        return {
            "decision_id": None,
            "arm_id": DEFAULT_ARM_ID,
            "params": {},
            "sampled_value": 0.0,
            "fallback": True,
        }


# --- Execution ---
async def main() -> None:
    import random

    config = RuntimeConfig(
        system="prod_demo",
        default_arms=[
            RuntimeArmTemplate(arm_id="model_a", params={"model": "fast", "temperature": 0.3}),
            RuntimeArmTemplate(arm_id="model_b", params={"model": "balanced", "temperature": 0.7}),
            RuntimeArmTemplate(arm_id="model_c", params={"model": "quality", "temperature": 0.9}),
        ],
        selection_strategy=SelectionStrategyConfig(exploration_bonus=0.1),
    )

    # Swap this single line for PostgreSQL, Redis, etc.
    storage = MemoryRuntimeStorage()

    runtime = ProductionRuntime(system="prod_demo", config=config, storage=storage)

    # Health check
    health = await runtime.health_check()
    print(f"Health: {health['status']}")

    # Run 50 select/update cycles
    arm_counts: Dict[str, int] = {}
    for i in range(50):
        user_id = f"user_{i % 5}"
        result = await runtime.select(user_id=user_id)
        arm_id = result["arm_id"]
        arm_counts[arm_id] = arm_counts.get(arm_id, 0) + 1

        if result["decision_id"]:
            reward = random.uniform(0.3, 1.0) if arm_id == "model_b" else random.uniform(0.1, 0.7)
            await runtime.update(
                user_id=user_id,
                decision_id=result["decision_id"],
                reward=reward,
            )

    # Final dashboard
    health = await runtime.health_check()
    print("\n--- Metrics Dashboard ---")
    for key, val in health["metrics"].items():
        print(f"  {key}: {val}")
    print("\n--- Circuit Breaker ---")
    print(f"  state: {health['circuit_state']}")
    print(f"  consecutive_failures: {health['circuit_consecutive_failures']}")
    print("\n--- Arm Selection Distribution ---")
    for arm, count in sorted(arm_counts.items()):
        print(f"  {arm}: {count} selections")

    await runtime.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
