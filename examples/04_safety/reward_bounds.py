"""
Reward Bounds and Safe Updates

What this demonstrates:
- Reward clamping to [0.0, 1.0] range
- Handling edge cases: None, negative, overflow values
- Safe Bayesian update patterns with bounded rewards
- How the RuntimeRewardEvaluator auto-clamps outputs

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Feed rewards of exactly 0.0 and 1.0 to verify boundary behavior
- Try very large negative values to confirm clamping
"""

# --- Configuration ---
from convergence.runtime.reward_evaluator import (
    RewardEvaluatorConfig,
    RewardMetricConfig,
    RuntimeRewardEvaluator,
)

# --- Setup ---


def clamp_reward(value: object) -> float:
    """Safely clamp any value to [0.0, 1.0]."""
    if value is None:
        return 0.0
    try:
        f = float(value)
    except (TypeError, ValueError):
        return 0.0
    if f != f:  # NaN check
        return 0.0
    return max(0.0, min(1.0, f))


def safe_bayesian_update(alpha: float, beta: float, reward: float) -> dict:
    """Apply Bayesian update with clamped reward."""
    clamped = clamp_reward(reward)
    new_alpha = alpha + clamped
    new_beta = beta + (1.0 - clamped)
    mean = new_alpha / (new_alpha + new_beta)
    return {"alpha": new_alpha, "beta": new_beta, "mean": mean, "clamped": clamped}


EDGE_CASES = [
    ("Normal (0.7)", 0.7),
    ("Zero", 0.0),
    ("One", 1.0),
    ("Negative (-0.5)", -0.5),
    ("Overflow (1.5)", 1.5),
    ("Large negative (-100)", -100),
    ("Large positive (999)", 999),
    ("None", None),
    ("String '0.8'", "0.8"),
    ("Invalid string", "abc"),
    ("Boolean True", True),
    ("NaN", float("nan")),
]

# --- Execution ---
if __name__ == "__main__":
    print("Reward Clamping: edge case handling\n")

    header = f"{'Input':<22} | {'Clamped':>7} | {'After Update (a=5, b=3)':>30}"
    print(header)
    print("-" * 65)

    for label, value in EDGE_CASES:
        clamped = clamp_reward(value)
        update = safe_bayesian_update(5.0, 3.0, value)
        update_str = f"a={update['alpha']:.1f} b={update['beta']:.1f} mean={update['mean']:.3f}"
        print(f"{label:<22} | {clamped:>7.3f} | {update_str:>30}")

    # Show evaluator auto-clamping
    print("\nRewardEvaluator auto-clamping:")
    config = RewardEvaluatorConfig(metrics={
        "score": RewardMetricConfig(name="score", weight=1.0, normalize=True),
    })
    evaluator = RuntimeRewardEvaluator(config)

    test_signals = [
        {"score": 0.5},
        {"score": -0.3},
        {"score": 1.5},
        {"score": 0.0},
        {"score": 1.0},
    ]
    for signals in test_signals:
        result = evaluator.evaluate(signals)
        raw = signals["score"]
        print(f"  signal={raw:>5.1f} -> reward={result:.3f}")

    print("\nAll rewards safely bounded to [0.0, 1.0]")
