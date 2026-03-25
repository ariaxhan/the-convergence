"""
SQLite Persistent Cache

What this demonstrates:
- Concept 1: SQLite backend for cache persistence across restarts
- Concept 2: Cache data survives process termination and reload

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Change threshold to 0.95 and see fewer cache hits"
- "Add more query variations to test similarity matching"
"""

# --- Configuration ---
import asyncio
import hashlib
import os

from convergence.cache.semantic import SemanticCache

DB_PATH = "./cache_demo.db"


def hash_embedding(text):
    h = hashlib.sha256(text.lower().encode()).digest()
    return [float(b) / 255.0 for b in h[:32]]


QUERIES = [
    ("What is Python?", {"content": "A programming language.", "tokens": 12}),
    ("Explain recursion", {"content": "A function calling itself.", "tokens": 15}),
    ("What are decorators?", {"content": "Functions wrapping functions.", "tokens": 14}),
    ("How do generators work?", {"content": "Lazy iteration with yield.", "tokens": 18}),
    ("What is a closure?", {"content": "Function capturing outer scope.", "tokens": 16}),
    ("Explain list comprehension", {"content": "Inline list creation syntax.", "tokens": 13}),
    ("What are type hints?", {"content": "Optional static type annotations.", "tokens": 17}),
    ("How does GIL work?", {"content": "Global interpreter lock for threads.", "tokens": 20}),
    ("What is asyncio?", {"content": "Async I/O event loop library.", "tokens": 19}),
    ("Explain context managers", {"content": "Resource management with with.", "tokens": 14}),
]


# --- Setup ---
async def populate_cache(path):
    cache = SemanticCache(
        embedding_fn=hash_embedding, backend="sqlite",
        sqlite_path=path, threshold=0.88,
    )
    for query, response in QUERIES:
        await cache.set(query, response)
    print(f"Stored {len(QUERIES)} entries in {path}")
    return cache


async def verify_persistence(path):
    cache = SemanticCache(
        embedding_fn=hash_embedding, backend="sqlite",
        sqlite_path=path, threshold=0.88,
    )
    print("\n--- After simulated restart ---")
    hits = 0
    for query, _ in QUERIES:
        result = await cache.get(query)
        if result is not None:
            hits += 1
            print(f"  HIT: '{query}' -> {result['content']}")
    print(f"\nPersistence confirmed: {hits}/{len(QUERIES)} entries survived restart")
    return cache


# --- Execution ---
async def main():
    print("=== SQLite Persistent Cache Demo ===\n")
    cache = await populate_cache(DB_PATH)
    del cache  # simulate process exit
    await verify_persistence(DB_PATH)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"\nCleaned up {DB_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
