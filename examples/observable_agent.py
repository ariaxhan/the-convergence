"""
Observable Agent Example

Demonstrates full observability: metrics, regret tracking, calibration,
and learning visualization.

Run:
    python examples/observable_agent.py
"""

import asyncio
import json
import random

from convergence.observability import NativeObserver
from convergence.runtime.online import configure, select, update
from convergence.storage.sqlite import SQLiteStorage
from convergence.types import RuntimeArmTemplate, RuntimeConfig


async def simulate_llm_call(model: str) -> tuple[float, float]:
    """
    Simulate calling an LLM.

    Returns:
        tuple: (quality_score, cost)
    """
    # True performance of each model
    true_performance = {
        "gpt-4": 0.90,
        "gpt-3.5": 0.70,
        "claude-3": 0.85,
    }

    costs = {
        "gpt-4": 0.05,
        "gpt-3.5": 0.01,
        "claude-3": 0.03,
    }

    # Add some noise to simulate real-world variance
    quality = true_performance.get(model, 0.5) + random.gauss(0, 0.1)
    quality = max(0.0, min(1.0, quality))

    return quality, costs.get(model, 0.02)


async def main():
    # 1. Initialize storage and observer
    storage = SQLiteStorage(db_path=":memory:")  # In-memory for demo
    await storage.initialize()

    observer = NativeObserver()

    # 2. Configure runtime
    config = RuntimeConfig(
        system="observable-agent",
        default_arms=[
            RuntimeArmTemplate(arm_id="gpt-4", name="GPT-4", params={}),
            RuntimeArmTemplate(arm_id="gpt-3.5", name="GPT-3.5", params={}),
            RuntimeArmTemplate(arm_id="claude-3", name="Claude 3", params={}),
        ],
    )
    await configure("observable-agent", config=config, storage=storage)

    # Create metrics
    requests_counter = observer.counter("requests_total", "Total requests")
    latency_histogram = observer.histogram(
        "request_latency",
        "Request latency in seconds",
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
    )

    # 3. Run learning episodes
    print("Running 50 learning iterations...\n")

    # The optimal reward is always from gpt-4 (0.90)
    optimal_reward = 0.90

    observer.start_episode()

    for i in range(50):
        # Select best arm
        selection = await select("observable-agent", user_id="demo-user")
        model = selection.arm_id

        # Track selection
        observer.track_arm_selection(model)
        requests_counter.labels(model=model).inc()

        # Simulate LLM call with latency
        start_time = asyncio.get_event_loop().time()
        quality, cost = await simulate_llm_call(model)
        latency = asyncio.get_event_loop().time() - start_time + random.uniform(0.1, 0.5)

        # Track metrics
        observer.track_cost(cost, model=model)
        observer.track_regret(optimal_reward=optimal_reward, actual_reward=quality)
        observer.track_prediction(confidence=selection.sampled_value, actual_success=quality > 0.7)
        latency_histogram.labels(model=model).observe(latency)

        # Simulate cache access
        observer.track_cache_access(hit=random.random() < 0.7)

        # Update learning
        await update(
            "observable-agent",
            user_id="demo-user",
            decision_id=selection.decision_id,
            reward=quality,
        )

        # Progress indicator
        if (i + 1) % 10 == 0:
            print(f"  Completed {i + 1} iterations")

    observer.end_episode(total_reward=quality)

    # 4. Display results
    print("\n" + "=" * 60)
    print("OBSERVABILITY REPORT")
    print("=" * 60)

    # Arm distribution
    print("\n--- Arm Selection Distribution ---")
    distribution = observer.get_arm_distribution()
    total_selections = sum(distribution.values())
    for arm_id, count in sorted(distribution.items(), key=lambda x: -x[1]):
        pct = count / total_selections * 100
        bar = "#" * int(pct / 2)
        print(f"  {arm_id:10s}: {count:3d} ({pct:5.1f}%) {bar}")

    # Selection entropy
    entropy = observer.get_selection_entropy()
    print(f"\n  Selection entropy: {entropy:.3f}")
    print(f"  (0 = fully converged, higher = more exploration)")

    # Regret
    print("\n--- Regret Analysis ---")
    cumulative_regret = observer.get_cumulative_regret()
    avg_regret = observer.get_average_regret(window=10)
    print(f"  Cumulative regret: {cumulative_regret:.3f}")
    print(f"  Average regret (last 10): {avg_regret:.3f}")

    # Calibration
    print("\n--- Calibration ---")
    ece = observer.get_calibration_error()
    print(f"  Expected Calibration Error: {ece:.3f}")
    if ece < 0.05:
        print("  Status: GOOD (well-calibrated)")
    elif ece < 0.15:
        print("  Status: WARNING (needs attention)")
    else:
        print("  Status: CRITICAL (poorly calibrated)")

    # Costs
    print("\n--- Cost Analysis ---")
    total_cost = observer.get_total_cost()
    cost_by_model = observer.get_cost_by_model()
    print(f"  Total cost: ${total_cost:.3f}")
    for model, model_cost in sorted(cost_by_model.items(), key=lambda x: -x[1]):
        print(f"    {model:10s}: ${model_cost:.3f}")

    # Cache
    print("\n--- Cache Performance ---")
    hit_rate = observer.get_cache_hit_rate()
    print(f"  Cache hit rate: {hit_rate * 100:.1f}%")

    # Export full metrics
    print("\n--- Full Metrics Export ---")
    metrics_json = observer.export_json()
    metrics_data = json.loads(metrics_json)
    print(f"  Total metrics collected: {len(metrics_data.get('metrics', []))}")
    print(f"  Summary keys: {list(metrics_data.get('summary', {}).keys())}")

    # Show convergence
    print("\n" + "=" * 60)
    print("LEARNING SUMMARY")
    print("=" * 60)

    # Get final arm states
    final_selection = await select("observable-agent", user_id="demo-user")
    print("\nFinal arm performance estimates:")
    for arm in sorted(final_selection.arms_state, key=lambda a: -a.sampled_value):
        mean = arm.alpha / (arm.alpha + arm.beta)
        print(f"  {arm.arm_id:10s}: mean={mean:.3f} (alpha={arm.alpha:.1f}, beta={arm.beta:.1f})")

    print("\nThe agent has learned that GPT-4 performs best!")
    print("Observability metrics help you verify this learning is correct.")


if __name__ == "__main__":
    asyncio.run(main())
