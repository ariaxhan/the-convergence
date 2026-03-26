"""
Confidence Calibration

What this demonstrates:
- Comparing predicted confidence to actual outcomes
- Building calibration data over 50 simulated interactions
- Calculating Expected Calibration Error (ECE)
- Calibration table: confidence bucket vs actual accuracy

Prerequisites:
- pip install -e .

Suggested prompts / test inputs:
- Change the bias in simulate_outcome to see miscalibration
- Add more buckets (e.g., 20 instead of 10) for finer granularity
"""

# --- Configuration ---
import random

from armature.evaluators.confidence import extract_confidence

NUM_INTERACTIONS = 50
NUM_BUCKETS = 5

# --- Setup ---

RESPONSE_TEMPLATES = [
    ("The answer is definitely {a}. Confidence: {c}%", True),
    ("I think the answer might be {a}.", False),
    ("I'm fairly sure it's {a}. Confidence: {c}%", True),
    ("Perhaps it could be {a}, but I'm uncertain.", False),
    ("The answer is {a}. Absolutely certain.", True),
    ("Maybe {a}? I'm not entirely sure.", False),
    ("I believe the answer is {a}. Confidence: {c}%", True),
    ("{a} is clearly the right answer.", True),
]


def simulate_interaction(idx: int) -> dict:
    """Simulate an interaction with predicted confidence and actual outcome."""
    template, has_explicit = random.choice(RESPONSE_TEMPLATES)
    answer = f"option_{random.choice(['A', 'B', 'C'])}"
    conf_pct = random.randint(30, 99)
    text = template.format(a=answer, c=conf_pct)

    predicted = extract_confidence(text)
    if predicted is None:
        predicted = 0.5

    # Simulate: higher confidence = slightly higher chance of being correct
    # but add noise to create realistic miscalibration
    noise = random.gauss(0, 0.15)
    is_correct = (predicted + noise) > 0.5

    return {"text": text[:60], "predicted": predicted, "actual": float(is_correct)}


def compute_ece(interactions: list, num_buckets: int) -> tuple:
    """Compute Expected Calibration Error and bucket stats."""
    buckets: dict[int, list] = {i: [] for i in range(num_buckets)}

    for interaction in interactions:
        bucket_idx = min(int(interaction["predicted"] * num_buckets), num_buckets - 1)
        buckets[bucket_idx].append(interaction)

    ece = 0.0
    bucket_stats = []
    total = len(interactions)

    for i in range(num_buckets):
        items = buckets[i]
        if not items:
            bucket_stats.append({"range": f"{i / num_buckets:.1f}-{(i + 1) / num_buckets:.1f}",
                                "count": 0, "avg_conf": 0, "accuracy": 0, "gap": 0})
            continue

        avg_conf = sum(it["predicted"] for it in items) / len(items)
        accuracy = sum(it["actual"] for it in items) / len(items)
        gap = abs(accuracy - avg_conf)
        ece += (len(items) / total) * gap

        bucket_stats.append({
            "range": f"{i / num_buckets:.1f}-{(i + 1) / num_buckets:.1f}",
            "count": len(items), "avg_conf": avg_conf,
            "accuracy": accuracy, "gap": gap,
        })

    return ece, bucket_stats


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)

    interactions = [simulate_interaction(i) for i in range(NUM_INTERACTIONS)]
    ece, stats = compute_ece(interactions, NUM_BUCKETS)

    print(f"Confidence Calibration ({NUM_INTERACTIONS} interactions, {NUM_BUCKETS} buckets)\n")

    header = f"{'Bucket':<10} | {'Count':>5} | {'Avg Conf':>8} | {'Accuracy':>8} | {'Gap':>5} | {'Visual'}"
    print(header)
    print("-" * 65)

    for s in stats:
        bar_conf = "#" * int(s["avg_conf"] * 20) if s["count"] > 0 else ""
        bar_acc = "." * int(s["accuracy"] * 20) if s["count"] > 0 else ""
        visual = f"C:{bar_conf:<20} A:{bar_acc}"
        print(f"{s['range']:<10} | {s['count']:>5} | {s['avg_conf']:>8.3f} | "
              f"{s['accuracy']:>8.3f} | {s['gap']:>5.3f} | {visual}")

    print(f"\nExpected Calibration Error (ECE): {ece:.4f}")
    if ece < 0.1:
        print("Calibration: GOOD (ECE < 0.1)")
    elif ece < 0.2:
        print("Calibration: FAIR (0.1 <= ECE < 0.2)")
    else:
        print("Calibration: POOR (ECE >= 0.2) -- consider recalibrating")
