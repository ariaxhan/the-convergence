"""
Cache Analytics Dashboard

What this demonstrates:
- Concept 1: Tracking cache hit/miss metrics over time
- Concept 2: Estimating cost savings from semantic caching

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Increase the repeat ratio to see higher hit rates"
- "Lower threshold to 0.7 and watch hit rate climb"
"""

# --- Configuration ---
import asyncio
import hashlib
import random

from convergence.cache.semantic import SemanticCache

COST_PER_TOKEN = 0.00003
UNIQUE_QUERIES = [
    "What is machine learning?", "Explain neural networks",
    "How does backpropagation work?", "What are transformers?",
    "Explain attention mechanism", "What is gradient descent?",
    "How does dropout regularize?", "What are embeddings?",
    "Explain batch normalization", "What is transfer learning?",
]
RESPONSES = {
    q: {"content": f"Answer for: {q}", "tokens": random.randint(50, 200)}
    for q in UNIQUE_QUERIES
}


def hash_embedding(text):
    h = hashlib.sha256(text.lower().encode()).digest()
    return [float(b) / 255.0 for b in h[:32]]


# --- Setup ---
async def run_analytics():
    cache = SemanticCache(
        embedding_fn=hash_embedding, backend="memory", threshold=0.88,
    )
    hits, misses, tokens_saved = 0, 0, 0
    similarities = []
    hit_rate_history = []

    random.seed(42)
    queries = [random.choice(UNIQUE_QUERIES) for _ in range(50)]

    print("=== Cache Analytics Dashboard ===\n")
    for i, query in enumerate(queries, 1):
        result = await cache.get(query)
        if result is not None:
            hits += 1
            tokens_saved += RESPONSES[query]["tokens"]
            similarities.append(result.get("similarity", 1.0))
        else:
            misses += 1
            await cache.set(query, RESPONSES[query])
        if i % 10 == 0:
            rate = hits / i * 100
            hit_rate_history.append(rate)
            print(f"  Query {i:2d}: hit_rate={rate:5.1f}%  hits={hits}  misses={misses}")

    print("\n--- Final Analytics ---")
    print(f"  Total queries:     {hits + misses}")
    print(f"  Cache hits:        {hits}")
    print(f"  Cache misses:      {misses}")
    print(f"  Hit rate:          {hits / (hits + misses) * 100:.1f}%")
    if similarities:
        avg_sim = sum(similarities) / len(similarities)
        print(f"  Avg similarity:    {avg_sim:.3f}")
    print(f"  Tokens saved:      {tokens_saved}")
    print(f"  Est. cost saved:   ${tokens_saved * COST_PER_TOKEN:.4f}")
    print(f"\n  Hit rate trend:    {' -> '.join(f'{r:.0f}%' for r in hit_rate_history)}")


# --- Execution ---
if __name__ == "__main__":
    asyncio.run(run_analytics())
