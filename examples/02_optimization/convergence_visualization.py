"""
Convergence Visualization with Cumulative Regret

What this demonstrates:
- 4-arm Thompson Sampling over 200 episodes
- Cumulative regret tracking (gap from optimal)
- ASCII chart showing convergence behavior
- Final arm statistics with posterior parameters

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Set all TRUE_PROBS close together (e.g., 0.5, 0.48, 0.52, 0.49) to see slower convergence
- Increase EPISODES to 1000 for clearer convergence
"""

# --- Configuration ---
import random

TRUE_PROBS = [0.8, 0.5, 0.3, 0.6]
ARM_NAMES = ["alpha", "bravo", "charlie", "delta"]
EPISODES = 200
CHART_WIDTH = 60
CHART_HEIGHT = 15

# --- Setup ---


def run_and_track() -> dict:
    """Run Thompson Sampling and track cumulative regret."""
    optimal_prob = max(TRUE_PROBS)
    alphas = [1.0] * len(TRUE_PROBS)
    betas = [1.0] * len(TRUE_PROBS)
    pulls = [0] * len(TRUE_PROBS)
    cumulative_regret = []
    total_regret = 0.0

    for _ in range(EPISODES):
        samples = [random.betavariate(max(a, 1e-6), max(b, 1e-6))
                   for a, b in zip(alphas, betas)]
        selected = samples.index(max(samples))

        reward = 1.0 if random.random() < TRUE_PROBS[selected] else 0.0
        pulls[selected] += 1
        total_regret += optimal_prob - TRUE_PROBS[selected]
        cumulative_regret.append(total_regret)

        if reward > 0.5:
            alphas[selected] += 1.0
        else:
            betas[selected] += 1.0

    return {
        "alphas": alphas, "betas": betas, "pulls": pulls,
        "regret": cumulative_regret,
    }


def ascii_chart(values: list, width: int, height: int) -> str:
    """Render a simple ASCII line chart."""
    if not values:
        return ""
    max_val = max(values) or 1.0
    step = max(1, len(values) // width)
    sampled = [values[i] for i in range(0, len(values), step)][:width]

    lines = []
    for row in range(height, 0, -1):
        threshold = max_val * row / height
        line = ""
        for val in sampled:
            line += "*" if val >= threshold else " "
        label = f"{threshold:>6.1f} |"
        lines.append(f"{label}{line}")
    lines.append(f"{'':>7}+{'-' * len(sampled)}")
    lines.append(f"{'':>8}0{' ' * (len(sampled) - 5)}ep {len(values)}")
    return "\n".join(lines)


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)
    result = run_and_track()

    print(f"Thompson Sampling: {len(TRUE_PROBS)} arms, {EPISODES} episodes")
    print(f"True probabilities: {dict(zip(ARM_NAMES, TRUE_PROBS))}\n")

    print("Cumulative Regret Chart:")
    print(ascii_chart(result["regret"], CHART_WIDTH, CHART_HEIGHT))

    print(f"\nFinal Arm Statistics:")
    print(f"{'Arm':<10} | {'Pulls':>5} | {'True P':>6} | {'Estimate':>8} | {'alpha':>5} | {'beta':>5}")
    print("-" * 55)
    for i, name in enumerate(ARM_NAMES):
        a, b = result["alphas"][i], result["betas"][i]
        estimate = a / (a + b)
        print(f"{name:<10} | {result['pulls'][i]:>5} | {TRUE_PROBS[i]:>6.2f} | "
              f"{estimate:>8.3f} | {a:>5.0f} | {b:>5.0f}")

    final_regret = result["regret"][-1]
    print(f"\nTotal cumulative regret: {final_regret:.1f}")
    print(f"Average regret per episode: {final_regret / EPISODES:.4f}")
