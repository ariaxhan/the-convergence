"""
Cost Tracking with Cache Savings

What this demonstrates:
- Tracking API costs per interaction
- Simulating semantic cache hit rates
- Calculating cost savings from caching
- Cost dashboard with per-query and aggregate metrics

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- Change CACHE_HIT_RATE to 0.8 to see higher savings
- Add different pricing tiers for different query types
"""

# --- Configuration ---
import hashlib
import random

COST_PER_1K_TOKENS = 0.03  # $0.03 per 1K tokens
CACHE_HIT_RATE = 0.4       # 40% of queries are semantically similar
NUM_QUERIES = 30


def simple_embedding(text: str) -> list[float]:
    """Hash-based embedding for demo purposes."""
    h = hashlib.sha256(text.lower().encode()).digest()
    return [float(b) / 255.0 for b in h[:32]]


# --- Setup ---

QUERIES = [
    ("What is Thompson Sampling?", 450),
    ("Explain Thompson Sampling", 420),
    ("How does multi-armed bandit work?", 380),
    ("What is a multi-armed bandit?", 350),
    ("How to configure reward evaluator?", 300),
    ("Reward evaluator configuration", 280),
    ("What is concept drift?", 400),
    ("Explain concept drift in ML", 380),
    ("How to set up semantic cache?", 320),
    ("Semantic cache configuration", 290),
]


class CostTracker:
    """Track API costs and cache savings."""

    def __init__(self, cost_per_1k: float):
        self.cost_per_1k = cost_per_1k
        self.total_tokens = 0
        self.total_cost = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.saved_tokens = 0
        self.entries: list[dict] = []

    def record_query(self, query: str, tokens: int, cache_hit: bool) -> dict:
        """Record a query and its cost."""
        cost = 0.0 if cache_hit else (tokens / 1000) * self.cost_per_1k
        saved = (tokens / 1000) * self.cost_per_1k if cache_hit else 0.0

        self.total_tokens += 0 if cache_hit else tokens
        self.total_cost += cost
        self.saved_tokens += tokens if cache_hit else 0
        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

        entry = {
            "query": query[:35], "tokens": tokens,
            "cache_hit": cache_hit, "cost": cost, "saved": saved,
        }
        self.entries.append(entry)
        return entry

    def total_saved(self) -> float:
        return (self.saved_tokens / 1000) * self.cost_per_1k

    def hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0


# --- Execution ---
if __name__ == "__main__":
    random.seed(42)
    tracker = CostTracker(COST_PER_1K_TOKENS)

    print(f"Cost Tracking: {NUM_QUERIES} queries, ${COST_PER_1K_TOKENS}/1K tokens")
    print(f"Expected cache hit rate: ~{CACHE_HIT_RATE:.0%}\n")

    header = f"{'Query':<37} | {'Tokens':>6} | {'Cache':>5} | {'Cost':>7} | {'Saved':>7}"
    print(header)
    print("-" * 70)

    for i in range(NUM_QUERIES):
        query, tokens = random.choice(QUERIES)
        tokens += random.randint(-50, 50)  # add noise
        # Simulate cache: higher hit rate for repeated-ish queries
        cache_hit = i > 3 and random.random() < CACHE_HIT_RATE

        entry = tracker.record_query(query, tokens, cache_hit)
        hit_str = "HIT" if cache_hit else "miss"
        print(f"{entry['query']:<37} | {tokens:>6} | {hit_str:>5} | "
              f"${entry['cost']:>6.4f} | ${entry['saved']:>6.4f}")

    # Dashboard
    total_possible = sum(e["tokens"] for e in tracker.entries) / 1000 * COST_PER_1K_TOKENS
    print(f"\n{'=' * 40}")
    print("COST DASHBOARD")
    print(f"{'=' * 40}")
    print(f"Total queries:     {len(tracker.entries)}")
    print(f"Cache hits:        {tracker.cache_hits} ({tracker.hit_rate():.0%})")
    print(f"Cache misses:      {tracker.cache_misses}")
    print(f"Tokens consumed:   {tracker.total_tokens:,}")
    print(f"Tokens saved:      {tracker.saved_tokens:,}")
    print(f"Total cost:        ${tracker.total_cost:.4f}")
    print(f"Total saved:       ${tracker.total_saved():.4f}")
    print(f"Without cache:     ${total_possible:.4f}")
    savings_pct = tracker.total_saved() / total_possible if total_possible > 0 else 0
    print(f"Savings:           {savings_pct:.0%}")
