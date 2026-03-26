"""
Cache Invalidation Patterns

What this demonstrates:
- Concept 1: TTL-based automatic cache expiry
- Concept 2: Manual invalidation via cache.clear()

Prerequisites:
- pip install armature-ai

Suggested prompts / test inputs:
- "Change ttl_seconds to 5 and observe longer cache life"
- "Add more entries and clear selectively"
"""

# --- Configuration ---
import asyncio
import hashlib

from armature.cache.semantic import SemanticCache

TTL_SECONDS = 2


def hash_embedding(text):
    h = hashlib.sha256(text.lower().encode()).digest()
    return [float(b) / 255.0 for b in h[:32]]


ENTRIES = [
    ("current weather in SF", {"content": "72F sunny", "tokens": 10}),
    ("stock price of AAPL", {"content": "$185.50", "tokens": 8}),
    ("latest news headlines", {"content": "Markets rally today", "tokens": 12}),
]


# --- Setup ---
async def demo_ttl_expiry():
    cache = SemanticCache(
        embedding_fn=hash_embedding, backend="memory",
        threshold=0.88, ttl_seconds=TTL_SECONDS,
    )
    print(f"--- TTL Expiry (ttl={TTL_SECONDS}s) ---\n")

    for query, response in ENTRIES:
        await cache.set(query, response)
    print(f"Stored {len(ENTRIES)} entries")

    print("\nImmediate lookup:")
    for query, _ in ENTRIES:
        result = await cache.get(query)
        status = "HIT" if result else "MISS"
        print(f"  {status}: '{query}'")

    wait = TTL_SECONDS + 1
    print(f"\nWaiting {wait}s for TTL expiry...")
    await asyncio.sleep(wait)

    print("\nPost-expiry lookup:")
    expired = 0
    for query, _ in ENTRIES:
        result = await cache.get(query)
        status = "HIT" if result else "EXPIRED"
        if result is None:
            expired += 1
        print(f"  {status}: '{query}'")
    print(f"\n{expired}/{len(ENTRIES)} entries expired as expected")


async def demo_manual_clear():
    cache = SemanticCache(
        embedding_fn=hash_embedding, backend="memory", threshold=0.88,
    )
    print("\n--- Manual Invalidation ---\n")

    for query, response in ENTRIES:
        await cache.set(query, response)

    result = await cache.get(ENTRIES[0][0])
    print(f"Before clear: {'HIT' if result else 'MISS'} on '{ENTRIES[0][0]}'")

    await cache.clear()
    print("Called cache.clear()")

    result = await cache.get(ENTRIES[0][0])
    print(f"After clear:  {'HIT' if result else 'MISS'} on '{ENTRIES[0][0]}'")
    print("\nAll entries removed successfully")


# --- Execution ---
async def main():
    print("=== Cache Invalidation Demo ===\n")
    await demo_ttl_expiry()
    await demo_manual_clear()


if __name__ == "__main__":
    asyncio.run(main())
