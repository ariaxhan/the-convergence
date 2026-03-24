"""
08 - Reward Evaluation

What this demonstrates:
- RuntimeRewardEvaluator with weighted multi-signal aggregation
- Computing composite rewards from multiple metric signals
- Custom evaluator functions for complex reward logic
- How different weight configurations affect final reward

Suggested prompts to explore after running:
- Change the weights to prioritize different metrics
- Add your own custom evaluator function
- Feed in real metric signals from your application

No API keys required. Pure local.
"""

from convergence import RewardEvaluatorConfig, RewardMetricConfig, RuntimeRewardEvaluator


# --- Configuration: Weighted Metrics ---
config = RewardEvaluatorConfig(
    metrics={
        "user_rating": RewardMetricConfig(
            name="user_rating",
            weight=0.5,
            normalize=True,
        ),
        "response_time": RewardMetricConfig(
            name="response_time",
            weight=0.3,
            normalize=True,
        ),
        "task_completion": RewardMetricConfig(
            name="task_completion",
            weight=0.2,
            normalize=True,
        ),
    }
)


# --- Execution ---
def main() -> None:
    print("Reward Evaluation Demo")
    print("=" * 55)
    print()

    # --- Weighted aggregation ---
    evaluator = RuntimeRewardEvaluator(config)

    scenarios = [
        ("Great response", {"user_rating": 0.9, "response_time": 0.8, "task_completion": 1.0}),
        ("Slow but accurate", {"user_rating": 0.7, "response_time": 0.3, "task_completion": 1.0}),
        ("Fast but wrong", {"user_rating": 0.2, "response_time": 1.0, "task_completion": 0.0}),
        ("Average", {"user_rating": 0.5, "response_time": 0.5, "task_completion": 0.5}),
        ("Partial signals", {"user_rating": 0.8}),  # Missing metrics
    ]

    print("Metric weights: user_rating=0.5, response_time=0.3, task_completion=0.2")
    print()

    for label, signals in scenarios:
        reward = evaluator.evaluate(signals)
        print(f"  {label:20s} | reward={reward:.3f} | signals={signals}")

    print()

    # --- Custom evaluator ---
    print("--- Custom Evaluator (bonus for high completion) ---")
    print()

    def custom_reward(signals: dict) -> float:
        """Custom evaluator: bonus when task_completion is perfect."""
        base = sum(signals.values()) / max(len(signals), 1)
        bonus = 0.1 if signals.get("task_completion", 0) >= 1.0 else 0.0
        return min(1.0, base + bonus)

    custom_config = RewardEvaluatorConfig(
        metrics={
            "user_rating": RewardMetricConfig(name="user_rating", weight=0.5),
            "task_completion": RewardMetricConfig(name="task_completion", weight=0.5),
        }
    )

    custom_evaluator = RuntimeRewardEvaluator(
        custom_config, custom_evaluator_callable=custom_reward
    )

    for label, signals in scenarios[:3]:
        reward = custom_evaluator.evaluate(signals)
        print(f"  {label:20s} | reward={reward:.3f}")


if __name__ == "__main__":
    main()
