"""
Similarity Threshold Tuning — Production Calibration

What this demonstrates:
- Grid search over thresholds to find F1-optimal similarity cutoff
- Precision/recall tradeoff visualization (ASCII)
- Adaptive threshold that responds to recent match quality
- Bootstrap confidence intervals for threshold selection
- Per-domain threshold support for multi-category systems

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Change GRID_STEP to 0.005 for finer resolution"
- "Add domain-specific pairs for your use case"
- "Try BOOTSTRAP_SAMPLES=500 for tighter confidence intervals"
"""

# --- Configuration ---
import hashlib
import math
import random
import re
from typing import Dict, List, Optional, Tuple

EMBEDDING_DIM: int = 64
GRID_START: float = 0.50
GRID_END: float = 0.99
GRID_STEP: float = 0.01
DEFAULT_THRESHOLD: float = 0.88
BOOTSTRAP_SAMPLES: int = 200
ADAPTIVE_WINDOW: int = 20


# --- Utilities ---

def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-10:
        return [0.0] * len(vec)
    return [x / norm for x in vec]


def hash_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """SHA-256 hash to fixed-dim float vector."""
    h = hashlib.sha256(text.lower().strip().encode()).digest()
    raw = [float(b) / 255.0 for b in h]
    while len(raw) < dim:
        h = hashlib.sha256(h).digest()
        raw.extend(float(b) / 255.0 for b in h)
    return _l2_normalize(raw[:dim])


def sentence_embedding(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Word-average embedding with positional weighting."""
    words = re.findall(r'\w+', text.lower())
    if not words:
        return _l2_normalize([0.0] * dim)
    vec = [0.0] * dim
    total_w = 0.0
    for pos, word in enumerate(words):
        w = 1.0 / (1.0 + 0.1 * pos)
        total_w += w
        wv = hash_embedding(word, dim)
        for i in range(dim):
            vec[i] += wv[i] * w
    if total_w > 0:
        vec = [v / total_w for v in vec]
    return _l2_normalize(vec)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, dot))


# --- Threshold Calibrator ---

class ThresholdCalibrator:
    """Finds optimal similarity thresholds using labeled pairs.

    Args:
        embed_fn: Function mapping text to embedding vector.
        grid_start: Lowest threshold to test.
        grid_end: Highest threshold to test.
        grid_step: Step size for grid search.
    """

    def __init__(
        self,
        embed_fn=sentence_embedding,
        grid_start: float = GRID_START,
        grid_end: float = GRID_END,
        grid_step: float = GRID_STEP,
    ) -> None:
        self._embed = embed_fn
        self._grid_start = grid_start
        self._grid_end = grid_end
        self._grid_step = grid_step
        self._domain_thresholds: Dict[str, float] = {}
        self._adaptive_history: List[float] = []

    def _compute_similarities(
        self, pairs: List[Tuple[str, str]]
    ) -> List[float]:
        """Compute cosine similarity for each pair."""
        return [
            cosine_similarity(self._embed(a), self._embed(b))
            for a, b in pairs
        ]

    def _metrics_at_threshold(
        self,
        similar_sims: List[float],
        different_sims: List[float],
        threshold: float,
    ) -> Dict[str, float]:
        """Compute precision, recall, F1 at a given threshold."""
        tp = sum(1 for s in similar_sims if s >= threshold)
        fn = sum(1 for s in similar_sims if s < threshold)
        fp = sum(1 for s in different_sims if s >= threshold)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        return {"precision": precision, "recall": recall, "f1": f1}

    def grid_search(
        self,
        similar_pairs: List[Tuple[str, str]],
        different_pairs: List[Tuple[str, str]],
    ) -> List[Dict]:
        """Test all thresholds in grid. Returns list of {threshold, precision, recall, f1}."""
        if not similar_pairs:
            raise ValueError("Need at least one similar pair")
        if not different_pairs:
            raise ValueError("Need at least one different pair")

        sim_sims = self._compute_similarities(similar_pairs)
        diff_sims = self._compute_similarities(different_pairs)

        results: List[Dict] = []
        t = self._grid_start
        while t <= self._grid_end + 1e-9:
            metrics = self._metrics_at_threshold(sim_sims, diff_sims, t)
            results.append({"threshold": round(t, 4), **metrics})
            t += self._grid_step
        return results

    def find_optimal_threshold(
        self,
        similar_pairs: List[Tuple[str, str]],
        different_pairs: List[Tuple[str, str]],
    ) -> Dict[str, float]:
        """Find threshold that maximizes F1 score."""
        grid = self.grid_search(similar_pairs, different_pairs)
        best = max(grid, key=lambda x: x["f1"])
        return best

    def bootstrap_confidence_interval(
        self,
        similar_pairs: List[Tuple[str, str]],
        different_pairs: List[Tuple[str, str]],
        n_samples: int = BOOTSTRAP_SAMPLES,
        confidence: float = 0.95,
    ) -> Dict[str, float]:
        """Bootstrap CI for optimal threshold. Resamples pairs with replacement."""
        if not similar_pairs or not different_pairs:
            raise ValueError("Need both similar and different pairs for bootstrap")
        rng = random.Random(42)  # Reproducible
        optimal_thresholds: List[float] = []

        for _ in range(n_samples):
            sim_sample = [rng.choice(similar_pairs) for _ in range(len(similar_pairs))]
            diff_sample = [rng.choice(different_pairs) for _ in range(len(different_pairs))]
            best = self.find_optimal_threshold(sim_sample, diff_sample)
            optimal_thresholds.append(best["threshold"])

        optimal_thresholds.sort()
        alpha = 1.0 - confidence
        lo_idx = int(math.floor(alpha / 2 * n_samples))
        hi_idx = int(math.ceil((1 - alpha / 2) * n_samples)) - 1
        lo_idx = max(0, min(lo_idx, n_samples - 1))
        hi_idx = max(0, min(hi_idx, n_samples - 1))
        mean_t = sum(optimal_thresholds) / len(optimal_thresholds)

        return {
            "mean_threshold": round(mean_t, 4),
            "ci_lower": round(optimal_thresholds[lo_idx], 4),
            "ci_upper": round(optimal_thresholds[hi_idx], 4),
            "confidence": confidence,
        }

    def set_domain_threshold(self, domain: str, threshold: float) -> None:
        """Set a per-domain threshold override."""
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(f"Threshold must be in [0, 1], got {threshold}")
        self._domain_thresholds[domain] = threshold

    def get_threshold(self, domain: Optional[str] = None) -> float:
        """Get threshold for a domain, falling back to adaptive or default."""
        if domain and domain in self._domain_thresholds:
            return self._domain_thresholds[domain]
        if self._adaptive_history:
            return self._adaptive_threshold()
        return DEFAULT_THRESHOLD

    def record_hit_quality(self, similarity: float) -> None:
        """Record a hit similarity for adaptive threshold tuning."""
        self._adaptive_history.append(similarity)
        # Keep window bounded
        if len(self._adaptive_history) > ADAPTIVE_WINDOW * 5:
            self._adaptive_history = self._adaptive_history[-ADAPTIVE_WINDOW * 5:]

    def _adaptive_threshold(self) -> float:
        """Adjust threshold based on recent hit quality distribution."""
        recent = self._adaptive_history[-ADAPTIVE_WINDOW:]
        if not recent:
            return DEFAULT_THRESHOLD
        avg = sum(recent) / len(recent)
        # If recent hits are low-quality, raise threshold; if high-quality, lower slightly
        if avg < 0.85:
            return min(0.99, DEFAULT_THRESHOLD + 0.05)
        elif avg > 0.95:
            return max(0.50, DEFAULT_THRESHOLD - 0.03)
        return DEFAULT_THRESHOLD


def _ascii_precision_recall_curve(grid: List[Dict], width: int = 50) -> str:
    """Render a simple ASCII precision/recall curve."""
    lines: List[str] = []
    lines.append("Threshold  Precision  Recall  F1      |  PR Curve")
    lines.append("-" * 70)
    # Sample ~20 points for display
    step = max(1, len(grid) // 20)
    for i in range(0, len(grid), step):
        g = grid[i]
        bar_p = int(g["precision"] * width / 2)
        bar_r = int(g["recall"] * width / 2)
        lines.append(
            f"  {g['threshold']:.2f}     {g['precision']:.3f}     {g['recall']:.3f}  "
            f"{g['f1']:.3f}   |  P{'#' * bar_p:<{width // 2}} R{'=' * bar_r}"
        )
    return "\n".join(lines)


# --- Execution ---

if __name__ == "__main__":
    similar_pairs: List[Tuple[str, str]] = [
        ("How do I reset my password?", "I need to change my password"),
        ("What is the return policy?", "How can I return an item?"),
        ("Track my order status", "Where is my package?"),
        ("Cancel my subscription", "I want to stop my subscription"),
        ("Contact customer support", "How do I reach support?"),
        ("Set up two-factor authentication", "Enable 2FA on my account"),
        ("Update my billing information", "Change my credit card details"),
        ("How to export my data?", "Download my account data"),
        ("Delete my account permanently", "I want to close my account"),
        ("What payment methods do you accept?", "Can I pay with PayPal?"),
    ]
    different_pairs: List[Tuple[str, str]] = [
        ("How do I reset my password?", "What is the return policy?"),
        ("Track my order status", "Delete my account permanently"),
        ("Contact customer support", "Update my billing information"),
        ("Cancel my subscription", "Set up two-factor authentication"),
        ("How to export my data?", "What payment methods do you accept?"),
        ("Enable 2FA on my account", "Where is my package?"),
        ("Change my credit card details", "How do I reach support?"),
        ("Download my account data", "I want to stop my subscription"),
        ("I want to close my account", "Can I pay with PayPal?"),
        ("I need to change my password", "How can I return an item?"),
    ]

    calibrator = ThresholdCalibrator()

    print("=" * 70)
    print("THRESHOLD CALIBRATION — GRID SEARCH")
    print("=" * 70)

    grid = calibrator.grid_search(similar_pairs, different_pairs)
    print(_ascii_precision_recall_curve(grid))

    print()
    optimal = calibrator.find_optimal_threshold(similar_pairs, different_pairs)
    print(f"F1-optimal threshold: {optimal['threshold']:.4f}")
    print(f"  Precision: {optimal['precision']:.4f}")
    print(f"  Recall:    {optimal['recall']:.4f}")
    print(f"  F1:        {optimal['f1']:.4f}")

    print()
    print(f"Default threshold comparison: {DEFAULT_THRESHOLD}")
    default_metrics = None
    for g in grid:
        if abs(g["threshold"] - DEFAULT_THRESHOLD) < GRID_STEP / 2:
            default_metrics = g
            break
    if default_metrics:
        delta_f1 = optimal["f1"] - default_metrics["f1"]
        print(f"  Default F1: {default_metrics['f1']:.4f}  (delta: {delta_f1:+.4f})")

    print()
    print("BOOTSTRAP CONFIDENCE INTERVAL")
    print("-" * 40)
    ci = calibrator.bootstrap_confidence_interval(similar_pairs, different_pairs)
    print(f"  Mean optimal threshold: {ci['mean_threshold']:.4f}")
    print(f"  {ci['confidence']*100:.0f}% CI: [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}]")

    # Domain-specific thresholds
    calibrator.set_domain_threshold("billing", 0.92)
    calibrator.set_domain_threshold("auth", 0.85)
    print()
    print("PER-DOMAIN THRESHOLDS")
    print(f"  billing: {calibrator.get_threshold('billing'):.2f}")
    print(f"  auth:    {calibrator.get_threshold('auth'):.2f}")
    print(f"  general: {calibrator.get_threshold():.2f}")
