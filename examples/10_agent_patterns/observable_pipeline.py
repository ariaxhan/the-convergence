"""
Multi-Step Pipeline with Structured Observability.

What this demonstrates:
- Pipeline with named steps, each backed by Thompson Sampling
- JSON-structured trace logging with trace_id propagation
- Error budgets per step with alerting threshold
- Step-level retries and timeouts
- Partial completion on mid-pipeline failure
- Per-step latency percentiles (p50, p95), success rate, avg reward

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Run 50 items to see arm convergence"
- "Lower timeout to trigger more failures"
- "Adjust error budget threshold to 5%"
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional

from convergence import configure_runtime, runtime_select, runtime_update
from convergence.storage.memory import MemoryRuntimeStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig, SelectionStrategyConfig

logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_STEP_TIMEOUT_SECONDS: float = 5.0
DEFAULT_STEP_RETRIES: int = 2
ERROR_BUDGET_THRESHOLD: float = 0.10  # 10% error rate triggers alert

StepFn = Callable[[Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]


@dataclass
class StepMetrics:
    """Latency and success tracking for a single pipeline step."""

    step_name: str
    latencies: List[float] = field(default_factory=list)
    successes: int = 0
    failures: int = 0
    total_reward: float = 0.0
    reward_count: int = 0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 1.0

    @property
    def error_rate(self) -> float:
        return 1.0 - self.success_rate

    @property
    def avg_reward(self) -> float:
        return self.total_reward / self.reward_count if self.reward_count > 0 else 0.0

    @property
    def latency_p50(self) -> float:
        return self._percentile(50)

    @property
    def latency_p95(self) -> float:
        return self._percentile(95)

    def _percentile(self, p: int) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(math.ceil(p / 100.0 * len(sorted_lat))) - 1
        return sorted_lat[max(0, idx)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_name,
            "success_rate": round(self.success_rate, 3),
            "error_rate": round(self.error_rate, 3),
            "avg_reward": round(self.avg_reward, 3),
            "latency_p50_ms": round(self.latency_p50 * 1000, 2),
            "latency_p95_ms": round(self.latency_p95 * 1000, 2),
            "total_runs": self.successes + self.failures,
        }


@dataclass
class PipelineStep:
    """Definition of a single pipeline step."""

    name: str
    fn: StepFn
    runtime_system: str
    timeout_seconds: float = DEFAULT_STEP_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_STEP_RETRIES


class Pipeline:
    """
    Multi-step async pipeline with observability baked in.

    Each step selects strategy via Thompson Sampling, executes with retries
    and timeout, propagates trace_id, and reports reward. Partial results
    are returned if a step fails after all retries.

    Args:
        name: Pipeline name for logging.
        user_id: User identifier for runtime selection.

    Raises:
        ValueError: If name or user_id is empty.
    """

    def __init__(self, *, name: str, user_id: str) -> None:
        if not name or not name.strip():
            raise ValueError("Pipeline name cannot be empty")
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")
        self._name = name
        self._user_id = user_id
        self._steps: List[PipelineStep] = []
        self._step_metrics: Dict[str, StepMetrics] = {}
        self._trace_log: List[Dict[str, Any]] = []

    def add_step(
        self,
        *,
        name: str,
        fn: StepFn,
        runtime_system: str,
        timeout_seconds: float = DEFAULT_STEP_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_STEP_RETRIES,
    ) -> None:
        """
        Register a pipeline step.

        Args:
            name: Step name (must be unique within pipeline).
            fn: Async callable taking and returning a dict.
            runtime_system: Convergence system name for MAB selection.
            timeout_seconds: Max execution time before timeout.
            max_retries: Number of retry attempts on failure.

        Raises:
            ValueError: If step name is empty or duplicate.
        """
        if not name or not name.strip():
            raise ValueError("Step name cannot be empty")
        if name in self._step_metrics:
            raise ValueError(f"Duplicate step name: {name}")
        step = PipelineStep(
            name=name,
            fn=fn,
            runtime_system=runtime_system,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self._steps.append(step)
        self._step_metrics[name] = StepMetrics(step_name=name)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the pipeline. Returns partial results on mid-pipeline failure.

        Args:
            input_data: Initial data dict passed to the first step.

        Returns:
            Dict with: completed_steps, failed_step (if any), result, trace_id, error.
        """
        trace_id = str(uuid.uuid4())[:8]
        current_data = dict(input_data)
        current_data["trace_id"] = trace_id
        completed: List[str] = []

        for step in self._steps:
            metrics = self._step_metrics[step.name]
            step_start = time.monotonic()
            success = False
            last_error: Optional[str] = None

            # Runtime selection for this step's strategy
            selection_result: Optional[Dict[str, Any]] = None
            try:
                selection = await runtime_select(
                    step.runtime_system, user_id=self._user_id
                )
                selection_result = {
                    "decision_id": selection.decision_id,
                    "arm_id": selection.arm_id,
                    "params": selection.params,
                }
                current_data["step_params"] = selection.params
            except Exception as exc:
                logger.warning({
                    "event": "step_select_failed",
                    "trace_id": trace_id,
                    "step": step.name,
                    "error": str(exc),
                })

            # Retry loop
            for attempt in range(step.max_retries + 1):
                try:
                    result = await asyncio.wait_for(
                        step.fn(current_data),
                        timeout=step.timeout_seconds,
                    )
                    current_data = result
                    current_data["trace_id"] = trace_id
                    success = True
                    break
                except asyncio.TimeoutError:
                    last_error = f"Timeout after {step.timeout_seconds}s"
                    logger.warning({
                        "event": "step_timeout",
                        "trace_id": trace_id,
                        "step": step.name,
                        "attempt": attempt + 1,
                    })
                except Exception as exc:
                    last_error = str(exc)
                    logger.warning({
                        "event": "step_error",
                        "trace_id": trace_id,
                        "step": step.name,
                        "attempt": attempt + 1,
                        "error": last_error,
                    })

            elapsed = time.monotonic() - step_start
            metrics.latencies.append(elapsed)

            # Compute reward and update runtime
            if success:
                metrics.successes += 1
                reward = min(1.0, max(0.0, 1.0 - elapsed))  # Faster = higher reward
                metrics.total_reward += reward
                metrics.reward_count += 1
            else:
                metrics.failures += 1
                reward = 0.0

            if selection_result and selection_result.get("decision_id"):
                try:
                    await runtime_update(
                        step.runtime_system,
                        user_id=self._user_id,
                        decision_id=selection_result["decision_id"],
                        reward=reward,
                    )
                except Exception as exc:
                    logger.warning({
                        "event": "step_update_failed",
                        "trace_id": trace_id,
                        "step": step.name,
                        "error": str(exc),
                    })

            # Structured trace entry
            self._trace_log.append({
                "trace_id": trace_id,
                "step": step.name,
                "status": "success" if success else "failed",
                "latency_ms": round(elapsed * 1000, 2),
                "arm_id": selection_result["arm_id"] if selection_result else None,
                "reward": round(reward, 3),
                "error": last_error if not success else None,
            })

            if success:
                completed.append(step.name)
            else:
                # Partial completion: return what we have
                return {
                    "completed_steps": completed,
                    "failed_step": step.name,
                    "result": current_data,
                    "trace_id": trace_id,
                    "error": last_error,
                }

        return {
            "completed_steps": completed,
            "failed_step": None,
            "result": current_data,
            "trace_id": trace_id,
            "error": None,
        }

    def get_step_metrics(self) -> List[Dict[str, Any]]:
        """Return per-step metrics."""
        return [m.to_dict() for m in self._step_metrics.values()]

    def get_error_budget_status(self) -> List[Dict[str, Any]]:
        """Check error budgets. Returns list of steps with budget status."""
        statuses: List[Dict[str, Any]] = []
        for name, metrics in self._step_metrics.items():
            over_budget = metrics.error_rate > ERROR_BUDGET_THRESHOLD
            statuses.append({
                "step": name,
                "error_rate": round(metrics.error_rate, 3),
                "threshold": ERROR_BUDGET_THRESHOLD,
                "over_budget": over_budget,
            })
            if over_budget:
                logger.warning({
                    "event": "error_budget_exceeded",
                    "step": name,
                    "error_rate": round(metrics.error_rate, 3),
                })
        return statuses

    def get_trace_log(self) -> List[Dict[str, Any]]:
        """Return the full trace log."""
        return list(self._trace_log)


# --- Step implementations ---

async def classify_step(data: Dict[str, Any]) -> Dict[str, Any]:
    """Classify input into a category."""
    await asyncio.sleep(random.uniform(0.005, 0.02))
    categories = ["billing", "support", "sales", "general"]
    data["category"] = random.choice(categories)
    data["classify_confidence"] = round(random.uniform(0.6, 0.99), 2)
    return data


async def enrich_step(data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich data with additional context."""
    await asyncio.sleep(random.uniform(0.005, 0.02))
    data["enriched"] = True
    data["priority"] = "high" if data.get("classify_confidence", 0) > 0.8 else "normal"
    return data


async def generate_step(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a response based on classification."""
    await asyncio.sleep(random.uniform(0.01, 0.03))
    data["response"] = f"Generated response for {data.get('category', 'unknown')} query."
    data["tokens_used"] = random.randint(50, 200)
    return data


async def validate_step(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the generated response."""
    await asyncio.sleep(random.uniform(0.005, 0.015))
    data["valid"] = True
    data["quality_score"] = round(random.uniform(0.7, 1.0), 2)
    return data


# Failure-injectable wrappers
_fail_at_item: Dict[str, int] = {}

async def _failing_generate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate step that fails on specific items."""
    item_idx = data.get("item_index", -1)
    if item_idx in _fail_at_item.get("generate", []):
        raise RuntimeError(f"Simulated generation failure at item {item_idx}")
    return await generate_step(data)

async def _failing_validate(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate step that times out on specific items."""
    item_idx = data.get("item_index", -1)
    if item_idx in _fail_at_item.get("validate", []):
        await asyncio.sleep(20)  # Will hit timeout
    return await validate_step(data)


# --- Execution ---
async def main() -> None:
    storage = MemoryRuntimeStorage()
    arms = [
        RuntimeArmTemplate(arm_id="strategy_fast", params={"mode": "fast"}),
        RuntimeArmTemplate(arm_id="strategy_balanced", params={"mode": "balanced"}),
        RuntimeArmTemplate(arm_id="strategy_thorough", params={"mode": "thorough"}),
    ]
    # Configure all step systems with the same arms
    for system_name in ["pipeline_classify", "pipeline_enrich", "pipeline_generate", "pipeline_validate"]:
        cfg = RuntimeConfig(
            system=system_name,
            default_arms=arms,
            selection_strategy=SelectionStrategyConfig(exploration_bonus=0.05),
        )
        await configure_runtime(system_name, config=cfg, storage=storage)

    # Set up failure injection: item 12 errors in generate, item 22 times out in validate
    _fail_at_item["generate"] = [12]
    _fail_at_item["validate"] = [22]

    pipeline = Pipeline(name="query_pipeline", user_id="pipeline_user")
    pipeline.add_step(name="classify", fn=classify_step, runtime_system="pipeline_classify")
    pipeline.add_step(name="enrich", fn=enrich_step, runtime_system="pipeline_enrich")
    pipeline.add_step(
        name="generate",
        fn=_failing_generate,
        runtime_system="pipeline_generate",
        max_retries=2,
    )
    pipeline.add_step(
        name="validate",
        fn=_failing_validate,
        runtime_system="pipeline_validate",
        timeout_seconds=0.5,
        max_retries=1,
    )

    # Process 30 items
    full_success = 0
    partial = 0
    for i in range(30):
        result = await pipeline.run({"query": f"User query {i}", "item_index": i})
        if result["failed_step"] is None:
            full_success += 1
        else:
            partial += 1
            print(f"  Item {i}: partial failure at '{result['failed_step']}' -> {result['error']}")

    print(f"\nCompleted: {full_success}/30 full, {partial} partial")

    # Per-step metrics
    print("\n--- Step Metrics ---")
    for m in pipeline.get_step_metrics():
        print(f"  {m['step']}: success={m['success_rate']:.1%} "
              f"p50={m['latency_p50_ms']:.1f}ms p95={m['latency_p95_ms']:.1f}ms "
              f"reward={m['avg_reward']:.3f}")

    # Error budget status
    print("\n--- Error Budget Status ---")
    for status in pipeline.get_error_budget_status():
        flag = " ** OVER BUDGET **" if status["over_budget"] else ""
        print(f"  {status['step']}: error_rate={status['error_rate']:.1%} "
              f"threshold={status['threshold']:.0%}{flag}")

    # Trace log sample
    print("\n--- Trace Log (last 4 entries) ---")
    for entry in pipeline.get_trace_log()[-4:]:
        print(f"  [{entry['trace_id']}] {entry['step']}: {entry['status']} "
              f"{entry['latency_ms']:.1f}ms arm={entry['arm_id']}"
              f"{' ERROR: ' + entry['error'] if entry['error'] else ''}")


if __name__ == "__main__":
    asyncio.run(main())
