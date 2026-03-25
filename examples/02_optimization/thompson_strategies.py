"""
Thompson Sampling Selection Strategies

What this demonstrates:
- SelectionStrategyConfig with exploration_bonus and stability settings
- Comparing default, exploration-bonus, and stability-focused strategies
- How strategy configuration affects arm selection behavior

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Set exploration_bonus to 0.5 and watch under-explored arms get more pulls
- Set stability_improvement_threshold to 0.01 to see aggressive switching
"""

# --- Configuration ---
import random

from convergence.types.runtime import SelectionStrategyConfig

TRUE_PROBS = [0.6, 0.55, 0.3]
EPISODES = 80

STRATEGIES = {
    "default": None,
    "exploration_bonus": SelectionStrategyConfig(
        exploration_bonus=0.3,
        exploration_min_pulls=10,
        use_stability=False,
    ),
    "stability_focused": SelectionStrategyConfig(
        exploration_bonus=0.0,
        use_stability=True,
        stability_min_pulls=8,
        stability_confidence_threshold=0.3,
        stability_improvement_threshold=0.15,
    ),
}

# --- Setup ---


def run_strategy(name: str, strategy: SelectionStrategyConfig | None) -> dict:
    """Run Thompson Sampling with a given strategy configuration."""
    alphas = [1.0] * len(TRUE_PROBS)
    betas = [1.0] * len(TRUE_PROBS)
    pulls = [0] * len(TRUE_PROBS)
    total_reward = 0.0

    for _ in range(EPISODES):
        # Sample from each arm's posterior
        samples = []
        for i in range(len(TRUE_PROBS)):
            s = random.betavariate(max(alphas[i], 1e-6), max(betas[i], 1e-6))
            # Apply exploration bonus for under-explored arms
            if strategy and strategy.exploration_bonus > 0:
                if pulls[i] < strategy.exploration_min_pulls:
                    s += strategy.exploration_bonus
                    s = min(1.0, s)
            samples.append(s)

        # Stability check: stick with current best if confident enough
        selected = samples.index(max(samples))
        if strategy and strategy.use_stability:
            best_arm = max(range(len(TRUE_PROBS)),
                          key=lambda i: alphas[i] / (alphas[i] + betas[i]) if pulls[i] >= strategy.stability_min_pulls else -1)
            if pulls[best_arm] >= strategy.stability_min_pulls:
                best_mean = alphas[best_arm] / (alphas[best_arm] + betas[best_arm])
                candidate_mean = alphas[selected] / (alphas[selected] + betas[selected])
                if candidate_mean - best_mean < strategy.stability_improvement_threshold:
                    selected = best_arm

        reward = 1.0 if random.random() < TRUE_PROBS[selected] else 0.0
        total_reward += reward
        pulls[selected] += 1
        if reward > 0.5:
            alphas[selected] += 1.0
        else:
            betas[selected] += 1.0

    return {
        "name": name,
        "pulls": pulls,
        "avg_reward": total_reward / EPISODES,
        "means": [alphas[i] / (alphas[i] + betas[i]) for i in range(len(TRUE_PROBS))],
    }


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)
    print(f"True probabilities: {TRUE_PROBS}")
    print(f"Episodes per strategy: {EPISODES}\n")

    header = f"{'Strategy':<22} | {'Pulls (A/B/C)':>14} | {'Avg Reward':>10} | {'Estimates':>20}"
    print(header)
    print("-" * len(header))

    for name, strategy in STRATEGIES.items():
        result = run_strategy(name, strategy)
        pulls_str = "/".join(str(p) for p in result["pulls"])
        means_str = "/".join(f"{m:.2f}" for m in result["means"])
        print(f"{result['name']:<22} | {pulls_str:>14} | {result['avg_reward']:>10.3f} | {means_str:>20}")

    print("\nKey insight: exploration_bonus spreads pulls more evenly early on,")
    print("while stability_focused avoids unnecessary switching once confident.")
