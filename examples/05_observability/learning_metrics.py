"""
Learning Metrics

What this demonstrates:
- Tracking agent improvement over 100 episodes
- Measuring: average reward, selection entropy, exploration ratio
- ASCII learning curve visualization
- How Thompson Sampling shifts from exploration to exploitation

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Increase to 500 episodes to see entropy drop further
- Make arms very similar (0.5, 0.48, 0.52) to see slower entropy decline
"""

# --- Configuration ---
import math
import random

TRUE_PROBS = [0.75, 0.5, 0.35]
ARM_NAMES = ["best", "medium", "worst"]
EPISODES = 100
WINDOW = 10  # rolling window for metrics

# --- Setup ---


def selection_entropy(pull_counts: list, total: int) -> float:
    """Shannon entropy of arm selection distribution."""
    if total == 0:
        return math.log(len(pull_counts))  # max entropy
    entropy = 0.0
    for count in pull_counts:
        if count > 0:
            p = count / total
            entropy -= p * math.log(p + 1e-10)
    return entropy


def run_with_metrics() -> dict:
    """Run Thompson Sampling and collect metrics per window."""
    alphas = [1.0] * len(TRUE_PROBS)
    betas = [1.0] * len(TRUE_PROBS)
    window_rewards: list[float] = []
    window_selections: list[int] = []
    metrics_log: list[dict] = []

    for ep in range(1, EPISODES + 1):
        samples = [random.betavariate(max(a, 1e-6), max(b, 1e-6))
                   for a, b in zip(alphas, betas)]
        selected = samples.index(max(samples))
        reward = 1.0 if random.random() < TRUE_PROBS[selected] else 0.0

        if reward > 0.5:
            alphas[selected] += 1.0
        else:
            betas[selected] += 1.0

        window_rewards.append(reward)
        window_selections.append(selected)

        # Emit metrics every WINDOW episodes
        if ep % WINDOW == 0:
            avg_reward = sum(window_rewards[-WINDOW:]) / WINDOW
            pulls_in_window = [window_selections[-WINDOW:].count(i) for i in range(len(TRUE_PROBS))]
            entropy = selection_entropy(pulls_in_window, WINDOW)
            exploration_ratio = 1.0 - (max(pulls_in_window) / WINDOW)
            best_arm_pct = pulls_in_window[0] / WINDOW  # arm 0 is best

            metrics_log.append({
                "episode": ep, "avg_reward": avg_reward,
                "entropy": entropy, "exploration_ratio": exploration_ratio,
                "best_arm_pct": best_arm_pct,
            })
            window_rewards.clear()
            window_selections.clear()

    return {"metrics": metrics_log, "alphas": alphas, "betas": betas}


def ascii_learning_curve(metrics: list) -> str:
    """Render ASCII learning curve from metrics."""
    width = len(metrics)
    height = 10
    lines = []
    for row in range(height, 0, -1):
        threshold = row / height
        line = ""
        for m in metrics:
            line += "*" if m["avg_reward"] >= threshold else " "
        lines.append(f" {threshold:.1f} |{line}")
    lines.append(f"     +{'=' * width}")
    labels = "".join(str(m["episode"] // 10 % 10) for m in metrics)
    lines.append(f"      {labels} (x10 episodes)")
    return "\n".join(lines)


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)
    result = run_with_metrics()

    print(f"Thompson Sampling: {len(TRUE_PROBS)} arms, {EPISODES} episodes")
    print(f"True probabilities: {dict(zip(ARM_NAMES, TRUE_PROBS))}\n")

    print("Learning Curve (average reward per window):")
    print(ascii_learning_curve(result["metrics"]))

    print(f"\n{'Episode':>7} | {'Avg Reward':>10} | {'Entropy':>7} | {'Explore%':>8} | {'Best Arm%':>9}")
    print("-" * 55)
    for m in result["metrics"]:
        print(f"{m['episode']:>7} | {m['avg_reward']:>10.2f} | {m['entropy']:>7.3f} | "
              f"{m['exploration_ratio']:>7.0%} | {m['best_arm_pct']:>8.0%}")

    print("\nKey: entropy decreases = converging. Best arm % increases = exploiting.")
