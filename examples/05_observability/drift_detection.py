"""
Concept Drift Detection

What this demonstrates:
- Simulating concept drift: arm rewards change after episode 80
- Thompson Sampling detecting the shift and re-exploring
- Comparing pre-drift, transition, and post-drift performance
- How Beta parameters adapt when the world changes

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Make the drift more subtle (0.7->0.6) to see slower detection
- Add a second drift at episode 160 to see repeated adaptation
"""

# --- Configuration ---
import random

EPISODES = 200
DRIFT_AT = 80
PRE_DRIFT_PROBS = [0.7, 0.4]  # Arm A is best
POST_DRIFT_PROBS = [0.3, 0.8]  # Arm B becomes best
ARM_NAMES = ["Arm A", "Arm B"]

# --- Setup ---


def get_reward(arm: int, episode: int) -> float:
    """Get reward based on current regime."""
    probs = PRE_DRIFT_PROBS if episode < DRIFT_AT else POST_DRIFT_PROBS
    return 1.0 if random.random() < probs[arm] else 0.0


def run_drift_experiment() -> dict:
    """Run Thompson Sampling through a drift event."""
    alphas = [1.0, 1.0]
    betas = [1.0, 1.0]
    history: list[dict] = []

    for ep in range(EPISODES):
        samples = [random.betavariate(max(a, 1e-6), max(b, 1e-6))
                   for a, b in zip(alphas, betas)]
        selected = samples.index(max(samples))
        reward = get_reward(selected, ep)

        if reward > 0.5:
            alphas[selected] += 1.0
        else:
            betas[selected] += 1.0

        history.append({
            "episode": ep, "selected": selected, "reward": reward,
            "alphas": list(alphas), "betas": list(betas),
            "means": [a / (a + b) for a, b in zip(alphas, betas)],
        })

    return {"history": history}


def summarize_phase(history: list, start: int, end: int, label: str) -> dict:
    """Summarize metrics for a phase."""
    phase = [h for h in history if start <= h["episode"] < end]
    if not phase:
        return {"label": label, "avg_reward": 0, "arm_a_pct": 0, "arm_b_pct": 0}
    avg_reward = sum(h["reward"] for h in phase) / len(phase)
    arm_a = sum(1 for h in phase if h["selected"] == 0) / len(phase)
    return {
        "label": label, "avg_reward": avg_reward,
        "arm_a_pct": arm_a, "arm_b_pct": 1 - arm_a,
        "final_means": phase[-1]["means"],
    }


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)
    result = run_drift_experiment()
    history = result["history"]

    print(f"Drift Detection: {EPISODES} episodes, drift at episode {DRIFT_AT}")
    print(f"Pre-drift:  Arm A={PRE_DRIFT_PROBS[0]}, Arm B={PRE_DRIFT_PROBS[1]}")
    print(f"Post-drift: Arm A={POST_DRIFT_PROBS[0]}, Arm B={POST_DRIFT_PROBS[1]}\n")

    # Phase analysis
    phases = [
        summarize_phase(history, 0, DRIFT_AT, f"Pre-drift (0-{DRIFT_AT})"),
        summarize_phase(history, DRIFT_AT, DRIFT_AT + 40, f"Transition ({DRIFT_AT}-{DRIFT_AT + 40})"),
        summarize_phase(history, DRIFT_AT + 40, EPISODES, f"Adapted ({DRIFT_AT + 40}-{EPISODES})"),
    ]

    header = f"{'Phase':<25} | {'Avg Reward':>10} | {'Arm A %':>7} | {'Arm B %':>7}"
    print(header)
    print("-" * 55)
    for p in phases:
        print(f"{p['label']:<25} | {p['avg_reward']:>10.3f} | {p['arm_a_pct']:>6.0%} | {p['arm_b_pct']:>6.0%}")

    # Show key moments
    print("\nBeta parameter evolution at key episodes:")
    print(f"{'Episode':>7} | {'A mean':>7} | {'B mean':>7} | {'Selected':>8} | {'Note'}")
    print("-" * 55)
    key_episodes = [0, DRIFT_AT - 1, DRIFT_AT, DRIFT_AT + 10, DRIFT_AT + 30, EPISODES - 1]
    for ep in key_episodes:
        h = history[ep]
        note = ""
        if ep == DRIFT_AT - 1:
            note = "pre-drift"
        elif ep == DRIFT_AT:
            note = "DRIFT"
        elif ep == DRIFT_AT + 10:
            note = "detecting..."
        elif ep == DRIFT_AT + 30:
            note = "adapting"
        arm = ARM_NAMES[h["selected"]]
        print(f"{ep:>7} | {h['means'][0]:>7.3f} | {h['means'][1]:>7.3f} | {arm:>8} | {note}")

    print("\nNote: Thompson Sampling adapts to drift naturally through Bayesian updating,")
    print("though accumulated priors slow re-convergence. Consider prior decay for faster adaptation.")
