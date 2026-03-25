"""
Multi-Metric Reward Evaluation

What this demonstrates:
- RuntimeRewardEvaluator with 3 weighted metrics
- How different signal combinations produce different rewards
- Weighted aggregation: sum(signal * weight) / sum(weights)

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Change weights to see how prioritizing speed vs quality shifts rewards
- Add a 4th metric and observe the rebalancing
"""

# --- Configuration ---
from convergence.runtime.reward_evaluator import (
    RewardEvaluatorConfig,
    RewardMetricConfig,
    RuntimeRewardEvaluator,
)

METRICS = {
    "quality": RewardMetricConfig(name="quality", weight=0.5, normalize=True),
    "speed": RewardMetricConfig(name="speed", weight=0.3, normalize=True),
    "cost": RewardMetricConfig(name="cost", weight=0.2, normalize=True),
}

# --- Setup ---
evaluator_config = RewardEvaluatorConfig(metrics=METRICS)
evaluator = RuntimeRewardEvaluator(evaluator_config)

SCENARIOS = [
    ("High quality, slow, cheap", {"quality": 0.95, "speed": 0.3, "cost": 0.9}),
    ("Low quality, fast, cheap", {"quality": 0.4, "speed": 0.95, "cost": 0.85}),
    ("Balanced", {"quality": 0.7, "speed": 0.7, "cost": 0.7}),
    ("Perfect", {"quality": 1.0, "speed": 1.0, "cost": 1.0}),
    ("Worst case", {"quality": 0.1, "speed": 0.1, "cost": 0.1}),
    ("Quality only", {"quality": 0.9, "speed": 0.0, "cost": 0.0}),
    ("Missing metrics", {"quality": 0.8}),
]


def compute_expected(signals: dict) -> float:
    """Manual weighted sum for verification."""
    total_w = sum(m.weight for m in METRICS.values())
    weighted = sum(
        signals.get(name, 0.0) * cfg.weight
        for name, cfg in METRICS.items()
        if name in signals
    )
    return max(0.0, min(1.0, weighted / total_w))


# --- Execution ---
if __name__ == "__main__":
    print("Reward Evaluator Configuration:")
    for name, cfg in METRICS.items():
        print(f"  {name}: weight={cfg.weight}")
    print()

    header = f"{'Scenario':<28} | {'quality':>7} {'speed':>7} {'cost':>7} | {'Reward':>7} | {'Verify':>7}"
    print(header)
    print("-" * len(header))

    for label, signals in SCENARIOS:
        reward = evaluator.evaluate(signals)
        expected = compute_expected(signals)
        q = signals.get("quality", "-")
        s = signals.get("speed", "-")
        c = signals.get("cost", "-")
        q_str = f"{q:>7.2f}" if isinstance(q, float) else f"{q:>7}"
        s_str = f"{s:>7.2f}" if isinstance(s, float) else f"{s:>7}"
        c_str = f"{c:>7.2f}" if isinstance(c, float) else f"{c:>7}"
        print(f"{label:<28} | {q_str} {s_str} {c_str} | {reward:>7.3f} | {expected:>7.3f}")

    print("\nNote: 'Missing metrics' only uses quality (weight=0.5),")
    print("but divides by total weight (1.0), penalizing missing signals.")
