"""
04 - Semantic Cache

What this demonstrates:
- SemanticCache with in-memory backend
- Hash-based embedding function (no external API needed)
- Cache miss on first query, cache hit on similar query
- Similarity threshold controlling hit/miss boundary

Suggested prompts to explore after running:
- Lower the threshold to 0.8 and see more cache hits
- Raise it to 0.99 and see only exact matches hit
- Replace the hash embedding with a real embedding API for production use

No API keys required. Uses a simple hash-based embedding for demonstration.
"""

import asyncio
import hashlib
import math
from typing import List

from convergence.cache.semantic import SemanticCache


# ---------------------------------------------------------------------------
# Simple deterministic embedding function (hash-based)
# In production, replace with OpenAI/Cohere/local embeddings.
# ---------------------------------------------------------------------------
EMBEDDING_DIM = 64


def hash_embedding(text: str) -> List[float]:
    """Create a deterministic embedding from text using SHA-256.

    This produces consistent vectors where similar inputs (same words)
    get similar-ish vectors. Good enough for demonstrating cache mechanics.
    """
    # Normalize
    words = text.lower().strip().split()

    # Build vector by hashing each word and accumulating
    vector = [0.0] * EMBEDDING_DIM
    for word in words:
        digest = hashlib.sha256(word.encode()).digest()
        for i in range(EMBEDDING_DIM):
            vector[i] += digest[i % len(digest)] / 255.0

    # Normalize to unit vector
    magnitude = math.sqrt(sum(v * v for v in vector))
    if magnitude > 0:
        vector = [v / magnitude for v in vector]

    return vector


# --- Configuration ---
cache = SemanticCache(
    embedding_fn=hash_embedding,
    backend="memory",
    threshold=0.97,
)


# --- Execution ---
async def main() -> None:
    print("Semantic Cache Demo")
    print("=" * 50)
    print()

    # First query: cache miss
    query1 = "How do I reset my password?"
    result = await cache.get(query1)
    print(f"Query:  \"{query1}\"")
    print(f"Result: {result}  (cache miss)")
    print()

    # Store a response
    await cache.set(query1, {"content": "Go to Settings > Security > Reset Password."})
    print("Stored response for first query.")
    print()

    # Same query: cache hit
    result = await cache.get(query1)
    print(f"Query:  \"{query1}\"")
    print(f"Hit:    similarity={result['similarity']:.4f}")
    print(f"        content={result['content']}")
    print()

    # Similar query: may hit depending on embedding similarity
    query2 = "How can I change my password?"
    result = await cache.get(query2)
    print(f"Query:  \"{query2}\"")
    if result:
        print(f"Hit:    similarity={result['similarity']:.4f}")
        print(f"        content={result['content']}")
    else:
        print(f"Result: None  (below threshold {cache.threshold})")
    print()

    # Unrelated query: cache miss
    query3 = "What is the weather forecast for tomorrow?"
    result = await cache.get(query3)
    print(f"Query:  \"{query3}\"")
    print(f"Result: {result}  (unrelated, cache miss)")


if __name__ == "__main__":
    asyncio.run(main())
