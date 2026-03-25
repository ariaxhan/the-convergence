"""
Thompson Sampling Basics

What this demonstrates:
- Two-arm Thompson Sampling with known reward distributions
- Beta distribution parameter evolution over 100 episodes
- How the algorithm learns which arm is better

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Change TRUE_PROBS to (0.5, 0.51) to see how the algorithm handles near-identical arms
- Increase EPISODES to 500 to see tighter convergence
"""

# --- Configuration ---
import random

TRUE_PROBS = (0.7, 0.4)  # Arm A is better
EPISODES = 100

# --- Setup ---


def beta_sample(alpha: float, beta: float) -> float:
    """Sample from Beta(alpha, beta) distribution."""
    return random.betavariate(max(alpha, 1e-6), max(beta, 1e-6))


def simulate_reward(arm_index: int) -> float:
    """Simulate binary reward based on true probability."""
    return 1.0 if random.random() < TRUE_PROBS[arm_index] else 0.0


def run_thompson_sampling() -> None:
    """Run Thompson Sampling for two arms and print evolution."""
    alphas = [1.0, 1.0]  # Success priors
    betas = [1.0, 1.0]   # Failure priors
    pulls = [0, 0]

    print(f"True reward probabilities: Arm A={TRUE_PROBS[0]}, Arm B={TRUE_PROBS[1]}")
    print(f"Running {EPISODES} episodes of Thompson Sampling\n")
    print(f"{'Episode':>7} | {'Selected':>8} | {'Reward':>6} | {'A alpha/beta':>14} | {'B alpha/beta':>14}")
    print("-" * 65)

    for episode in range(1, EPISODES + 1):
        # Thompson Sampling: sample from each arm's posterior
        samples = [beta_sample(alphas[i], betas[i]) for i in range(2)]
        selected = 0 if samples[0] > samples[1] else 1

        # Observe reward from selected arm
        reward = simulate_reward(selected)
        pulls[selected] += 1

        # Bayesian update: success -> alpha+1, failure -> beta+1
        if reward > 0.5:
            alphas[selected] += 1.0
        else:
            betas[selected] += 1.0

        # Print every 10th episode + first and last
        if episode <= 3 or episode % 10 == 0 or episode == EPISODES:
            arm_label = "A" if selected == 0 else "B"
            a_params = f"{alphas[0]:.0f}/{betas[0]:.0f}"
            b_params = f"{alphas[1]:.0f}/{betas[1]:.0f}"
            print(f"{episode:>7} | {arm_label:>8} | {reward:>6.1f} | {a_params:>14} | {b_params:>14}")

    print("\nFinal statistics:")
    for i, label in enumerate(["A", "B"]):
        mean = alphas[i] / (alphas[i] + betas[i])
        print(f"  Arm {label}: pulls={pulls[i]}, mean_estimate={mean:.3f}, "
              f"alpha={alphas[i]:.0f}, beta={betas[i]:.0f}")

    better = "A" if pulls[0] > pulls[1] else "B"
    print(f"\nAlgorithm preferred Arm {better} ({max(pulls)}/{EPISODES} pulls)")


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)
    run_thompson_sampling()
