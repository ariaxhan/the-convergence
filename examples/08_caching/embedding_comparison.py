"""
Embedding Strategy Comparison

What this demonstrates:
- Concept 1: Different embedding functions produce different cache behavior
- Concept 2: Embedding quality directly controls cache effectiveness

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Add your own embedding function and compare"
- "Try threshold=0.7 vs 0.95 to see sensitivity per strategy"
"""

# --- Configuration ---
import asyncio
import hashlib
import string

from convergence.cache.semantic import SemanticCache

QUERY_PAIRS = [
    ("What is Python?", {"content": "A programming language", "tokens": 10}),
    ("Tell me about Python", None),  # should match above
    ("Explain recursion", {"content": "Self-referential functions", "tokens": 12}),
    ("What is recursion?", None),  # should match above
    ("How do lists work?", {"content": "Ordered mutable sequences", "tokens": 11}),
    ("Explain Python lists", None),  # should match above
    ("What are decorators?", {"content": "Function wrappers", "tokens": 9}),
    ("Describe decorators in Python", None),  # should match above
    ("What is a lambda?", {"content": "Anonymous function", "tokens": 8}),
    ("Explain lambda functions", None),  # should match above
]


# --- Setup ---
def hash_embedding(text):
    """SHA-256 hash -> 32-dim float vector."""
    h = hashlib.sha256(text.lower().encode()).digest()
    return [float(b) / 255.0 for b in h[:32]]


def char_freq_embedding(text):
    """Character frequency -> 26-dim vector."""
    text = text.lower()
    total = max(len(text), 1)
    return [text.count(c) / total for c in string.ascii_lowercase]


def word_overlap_embedding(text):
    """Word presence -> 50-dim boolean vector (common word vocabulary)."""
    vocab = [
        "what", "is", "how", "explain", "python", "function", "list",
        "class", "method", "variable", "type", "return", "loop", "for",
        "while", "if", "else", "import", "module", "string", "dict",
        "set", "tuple", "lambda", "decorator", "generator", "async",
        "await", "error", "exception", "file", "read", "write", "data",
        "array", "sort", "search", "tree", "graph", "recursion", "stack",
        "queue", "memory", "thread", "process", "api", "http", "json",
        "database", "query",
    ]
    words = set(text.lower().split())
    return [1.0 if v in words else 0.0 for v in vocab]


STRATEGIES = [
    ("Hash (SHA-256)", hash_embedding),
    ("Char Frequency", char_freq_embedding),
    ("Word Overlap", word_overlap_embedding),
]


async def test_strategy(name, embed_fn):
    cache = SemanticCache(
        embedding_fn=embed_fn, backend="memory", threshold=0.88,
    )
    hits, misses = 0, 0
    for query, response in QUERY_PAIRS:
        if response is not None:
            await cache.set(query, response)
            misses += 1
        else:
            result = await cache.get(query)
            if result is not None:
                hits += 1
            else:
                misses += 1
    return name, hits, misses


# --- Execution ---
async def main():
    print("=== Embedding Strategy Comparison ===\n")
    print(f"{'Strategy':<20} {'Hits':>5} {'Misses':>7} {'Hit Rate':>9}")
    print("-" * 44)

    for name, embed_fn in STRATEGIES:
        name, hits, misses = await test_strategy(name, embed_fn)
        total = hits + misses
        rate = hits / total * 100 if total else 0
        print(f"{name:<20} {hits:>5} {misses:>7} {rate:>8.1f}%")

    print("\nKey insight: embedding quality directly controls cache effectiveness.")
    print("Hash-based rarely matches similar queries (exact match only).")
    print("Semantic embeddings (char freq, word overlap) catch paraphrases.")


if __name__ == "__main__":
    asyncio.run(main())
