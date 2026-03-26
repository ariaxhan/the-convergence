"""
Cache Quality Monitor — Effectiveness Metrics & Recommendations

What this demonstrates:
- Rolling hit rate tracking with configurable window
- False positive detection via simulated user feedback
- Staleness scoring for cache entries
- Cost savings calculation from cache hits
- Composite quality score with actionable recommendations
- Decay detection (alerts on dropping hit rate)

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- "Adjust AVG_API_COST to match your LLM pricing"
- "Change FEEDBACK_POSITIVE_RATE to simulate worse cache quality"
- "Try different ROLLING_WINDOW sizes for smoother/noisier metrics"
"""

# --- Configuration ---
import asyncio
import hashlib
import math
import random
import re
import time
from typing import Dict, List, Optional, Tuple

from armature.cache.semantic import SemanticCache

EMBEDDING_DIM: int = 64
ROLLING_WINDOW: int = 100
AVG_API_COST: float = 0.003  # Dollars per LLM call avoided
CACHE_THRESHOLD: float = 0.65
FEEDBACK_POSITIVE_RATE: float = 0.90  # Simulated user satisfaction rate
STALENESS_WARN_SECONDS: float = 3600.0  # 1 hour


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


# --- Cache Quality Monitor ---

class CacheQualityMonitor:
    """Tracks and reports cache effectiveness metrics.

    Args:
        cache: SemanticCache instance to monitor.
        rolling_window: Number of recent queries for rolling metrics.
        avg_api_cost: Average cost per LLM API call (for savings calculation).
        staleness_warn_seconds: Age threshold for staleness warnings.
    """

    def __init__(
        self,
        cache: SemanticCache,
        rolling_window: int = ROLLING_WINDOW,
        avg_api_cost: float = AVG_API_COST,
        staleness_warn_seconds: float = STALENESS_WARN_SECONDS,
    ) -> None:
        if rolling_window < 1:
            raise ValueError(f"rolling_window must be >= 1, got {rolling_window}")
        if avg_api_cost < 0:
            raise ValueError(f"avg_api_cost must be >= 0, got {avg_api_cost}")
        self._cache = cache
        self._window = rolling_window
        self._api_cost = avg_api_cost
        self._staleness_warn = staleness_warn_seconds

        # Tracking state
        self._query_log: List[Dict] = []  # {timestamp, query, hit, similarity, feedback}
        self._total_queries: int = 0
        self._total_hits: int = 0
        self._total_misses: int = 0
        self._false_positives: int = 0
        self._hit_similarities: List[float] = []

    async def query(self, text: str) -> Optional[Dict]:
        """Query the cache and record metrics.

        Args:
            text: Query string.

        Returns:
            Cache result or None on miss.
        """
        if not text.strip():
            raise ValueError("Query cannot be empty")
        self._total_queries += 1
        result = await self._cache.get(text)
        is_hit = result is not None
        similarity = result["similarity"] if result else 0.0

        entry = {
            "timestamp": time.time(),
            "query": text,
            "hit": is_hit,
            "similarity": similarity,
            "feedback": None,
        }

        if is_hit:
            self._total_hits += 1
            self._hit_similarities.append(similarity)
        else:
            self._total_misses += 1

        self._query_log.append(entry)
        # Trim to bounded size (5x window to keep enough history for decay detection)
        if len(self._query_log) > self._window * 5:
            self._query_log = self._query_log[-self._window * 5:]

        return result

    def record_feedback(self, positive: bool) -> None:
        """Record user feedback on the most recent cache hit.

        Args:
            positive: Whether the user found the cached response helpful.
        """
        # Find the last hit in the log
        for entry in reversed(self._query_log):
            if entry["hit"] and entry["feedback"] is None:
                entry["feedback"] = positive
                if not positive:
                    self._false_positives += 1
                return
        # No unfeedback'd hit found — ignore silently

    @property
    def hit_rate(self) -> float:
        """Rolling hit rate over the last N queries."""
        recent = self._query_log[-self._window:]
        if not recent:
            return 0.0
        return sum(1 for e in recent if e["hit"]) / len(recent)

    @property
    def false_positive_rate(self) -> float:
        """Rate of cache hits with negative feedback."""
        hits_with_feedback = [
            e for e in self._query_log if e["hit"] and e["feedback"] is not None
        ]
        if not hits_with_feedback:
            return 0.0
        negatives = sum(1 for e in hits_with_feedback if not e["feedback"])
        return negatives / len(hits_with_feedback)

    @property
    def avg_hit_similarity(self) -> float:
        """Average cosine similarity of cache hits."""
        if not self._hit_similarities:
            return 0.0
        return sum(self._hit_similarities) / len(self._hit_similarities)

    @property
    def cost_savings(self) -> float:
        """Estimated dollar savings from cache hits."""
        return self._total_hits * self._api_cost

    @property
    def quality_score(self) -> float:
        """Composite quality score (0-1). Weighted blend of metrics."""
        hr = self.hit_rate
        fpr = self.false_positive_rate
        avg_sim = self.avg_hit_similarity
        # Quality = high hit rate + low false positives + high similarity on hits
        score = 0.4 * hr + 0.3 * (1.0 - fpr) + 0.3 * avg_sim
        return max(0.0, min(1.0, score))

    def detect_decay(self) -> Optional[str]:
        """Alert if recent hit rate is significantly below overall average."""
        if len(self._query_log) < self._window * 2:
            return None  # Not enough data
        overall = self._total_hits / self._total_queries if self._total_queries > 0 else 0
        recent = self.hit_rate
        if recent < overall - 0.10:
            return (
                f"DECAY ALERT: Recent hit rate ({recent:.2%}) is significantly below "
                f"overall ({overall:.2%}). Consider cache warming or threshold adjustment."
            )
        return None

    def recommendations(self) -> List[str]:
        """Generate actionable recommendations based on current metrics."""
        recs: List[str] = []
        if self.hit_rate < 0.3:
            recs.append("Hit rate is low (<30%). Consider: lower threshold, pre-warm cache, "
                         "or improve embedding quality.")
        if self.false_positive_rate > 0.15:
            recs.append(f"False positive rate is high ({self.false_positive_rate:.1%}). "
                         "Raise similarity threshold or add negative keyword filters.")
        if self.avg_hit_similarity < 0.80 and self._hit_similarities:
            recs.append(f"Average hit similarity is low ({self.avg_hit_similarity:.3f}). "
                         "Consider switching to a higher-quality embedding strategy.")
        decay = self.detect_decay()
        if decay:
            recs.append(decay)
        if not recs:
            recs.append("Cache is performing well. No changes recommended.")
        return recs

    def effectiveness_report(self) -> Dict:
        """Comprehensive effectiveness report as a dict."""
        return {
            "total_queries": self._total_queries,
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "rolling_hit_rate": round(self.hit_rate, 4),
            "false_positive_rate": round(self.false_positive_rate, 4),
            "avg_hit_similarity": round(self.avg_hit_similarity, 4),
            "cost_savings_usd": round(self.cost_savings, 4),
            "quality_score": round(self.quality_score, 4),
            "recommendations": self.recommendations(),
        }


# --- Execution ---

async def main() -> None:
    cache = SemanticCache(
        embedding_fn=sentence_embedding,
        backend="memory",
        threshold=CACHE_THRESHOLD,
    )
    monitor = CacheQualityMonitor(cache)

    rng = random.Random(42)

    # Seed cache with 20 entries
    seed_entries: List[Tuple[str, str]] = [
        ("How to reset password?", "Go to Settings > Security > Reset."),
        ("Return policy", "30-day returns on all items."),
        ("Track my order", "Check Orders page for tracking."),
        ("Cancel subscription", "Billing > Cancel."),
        ("Contact support", "Email support@example.com."),
        ("Export data", "Settings > Privacy > Export."),
        ("Change email", "Settings > Profile > Email."),
        ("Payment methods", "We accept Visa, MC, PayPal."),
        ("Refund request", "Contact support within 30 days."),
        ("API documentation", "Visit docs.example.com."),
        ("Upgrade plan", "Billing > Plans > Upgrade."),
        ("Two-factor auth", "Security > Enable 2FA."),
        ("Notification settings", "Settings > Notifications."),
        ("Delete account", "Settings > Delete Account."),
        ("Shipping times", "Standard: 5-7 days. Express: 1-2 days."),
        ("Bulk pricing", "Contact sales for bulk orders."),
        ("Integration guide", "See docs.example.com/integrations."),
        ("Webhooks setup", "Developer > Webhooks > Add."),
        ("User permissions", "Admin > Roles > Permissions."),
        ("Audit log", "Admin > Security > Audit Log."),
    ]
    for q, a in seed_entries:
        await cache.set(q, {"content": a})

    # Cacheable queries — paraphrases of seeded entries
    cacheable_queries: List[str] = [
        "how do I change my password",
        "what is your return policy",
        "where is my package",
        "I want to cancel my plan",
        "how to reach customer service",
        "download my account data",
        "update my email address",
        "what payment options available",
        "I need a refund",
        "where are the API docs",
        "how to upgrade my account",
        "set up 2FA",
        "change notification preferences",
        "remove my account",
        "how long does shipping take",
    ]

    # Novel queries — unlikely to match
    novel_queries: List[str] = [
        "quantum computing applications",
        "best hiking trails in Colorado",
        "machine learning model training",
        "cryptocurrency market analysis",
        "interior design color theory",
        "sourdough bread baking tips",
        "satellite orbit mechanics",
    ]

    # Run 100 queries: ~60% cacheable, ~40% novel
    print("=" * 70)
    print("CACHE QUALITY SIMULATION — 100 Queries")
    print("=" * 70)
    print()

    for i in range(100):
        if rng.random() < 0.60:
            query = rng.choice(cacheable_queries)
        else:
            query = rng.choice(novel_queries)

        result = await monitor.query(query)

        # Simulate feedback on hits
        if result is not None:
            positive = rng.random() < FEEDBACK_POSITIVE_RATE
            monitor.record_feedback(positive)

    # Print dashboard
    report = monitor.effectiveness_report()

    print("CACHE QUALITY DASHBOARD")
    print("-" * 50)
    print(f"  Total queries:       {report['total_queries']}")
    print(f"  Cache hits:          {report['total_hits']}")
    print(f"  Cache misses:        {report['total_misses']}")
    print(f"  Rolling hit rate:    {report['rolling_hit_rate']:.2%}")
    print(f"  False positive rate: {report['false_positive_rate']:.2%}")
    print(f"  Avg hit similarity:  {report['avg_hit_similarity']:.4f}")
    print(f"  Cost savings:        ${report['cost_savings_usd']:.4f}")
    print(f"  Quality score:       {report['quality_score']:.4f}")
    print()
    print("RECOMMENDATIONS")
    print("-" * 50)
    for rec in report["recommendations"]:
        print(f"  - {rec}")


if __name__ == "__main__":
    asyncio.run(main())
