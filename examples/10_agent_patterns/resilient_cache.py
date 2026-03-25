"""
Multi-Tier Cache with Fallback Chain and Circuit Breakers.

What this demonstrates:
- Tiered caching: SQLite primary -> memory fallback -> no-cache passthrough
- Per-tier circuit breakers that skip failing tiers automatically
- Embedding validation (dimensions, NaN/Inf, unit normalization)
- Cache warming from known Q&A pairs
- Stale-while-revalidate on backend failure
- Structured metrics per tier

Prerequisites:
- pip install the-convergence

Suggested prompts / test inputs:
- "Warm cache then query similar phrases"
- "Simulate primary failure to see fallback"
- "Check metrics dashboard after mixed workload"
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from convergence.cache.semantic import SemanticCache

logger = logging.getLogger(__name__)

# --- Constants ---
CIRCUIT_BREAKER_THRESHOLD: int = 3
CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = 30.0
DEFAULT_SIMILARITY_THRESHOLD: float = 0.88
DEFAULT_TTL_SECONDS: int = 3600
EMBEDDING_DIMENSIONS: int = 64


@dataclass
class TierCircuitBreaker:
    """Circuit breaker scoped to a single cache tier."""

    tier_name: str
    threshold: int = CIRCUIT_BREAKER_THRESHOLD
    cooldown_seconds: float = CIRCUIT_BREAKER_COOLDOWN_SECONDS
    consecutive_failures: int = 0
    is_open: bool = False
    opened_at: float = 0.0

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold and not self.is_open:
            self.is_open = True
            self.opened_at = time.monotonic()
            logger.warning({"event": "tier_circuit_opened", "tier": self.tier_name})

    def record_success(self) -> None:
        self.consecutive_failures = 0
        if self.is_open:
            self.is_open = False
            logger.info({"event": "tier_circuit_closed", "tier": self.tier_name})

    def should_skip(self) -> bool:
        if not self.is_open:
            return False
        elapsed = time.monotonic() - self.opened_at
        if elapsed >= self.cooldown_seconds:
            self.is_open = False
            self.consecutive_failures = 0
            return False
        return True


@dataclass
class TierMetrics:
    """Metrics for a single cache tier."""

    tier_name: str
    hit_count: int = 0
    miss_count: int = 0
    error_count: int = 0
    circuit_open_count: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier_name,
            "hits": self.hit_count,
            "misses": self.miss_count,
            "errors": self.error_count,
            "circuit_opens": self.circuit_open_count,
            "hit_rate": round(self.hit_rate, 3),
        }


def _hash_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> List[float]:
    """
    Deterministic hash-based embedding for demo purposes.

    Produces a normalized unit vector so cosine similarity works correctly.
    In production, replace with a real embedding model.
    """
    raw: List[float] = []
    for i in range(dimensions):
        h = hashlib.sha256(f"{text}:{i}".encode()).hexdigest()
        raw.append((int(h[:8], 16) / (2**32)) * 2 - 1)
    # Normalize to unit vector
    magnitude = math.sqrt(sum(x * x for x in raw))
    if magnitude < 1e-10:
        return [0.0] * dimensions
    return [x / magnitude for x in raw]


def validate_embedding(embedding: List[float], expected_dim: int = EMBEDDING_DIMENSIONS) -> bool:
    """
    Validate an embedding vector: check dimensions, reject NaN/Inf.

    Args:
        embedding: Vector to validate.
        expected_dim: Expected dimensionality.

    Returns:
        True if valid, False otherwise.
    """
    if len(embedding) != expected_dim:
        logger.warning({"event": "bad_embedding_dim", "expected": expected_dim, "got": len(embedding)})
        return False
    for val in embedding:
        if math.isnan(val) or math.isinf(val):
            logger.warning({"event": "bad_embedding_value", "value": val})
            return False
    return True


class ResilientCache:
    """
    Multi-tier semantic cache with automatic failover.

    Chains a primary cache (SQLite) and a fallback cache (memory).
    Each tier has its own circuit breaker. If both fail, operations
    are no-ops (the application never crashes due to cache failure).

    Args:
        primary_sqlite_path: Path for SQLite cache file.
        similarity_threshold: Cosine similarity threshold for hits.
        ttl_seconds: Time-to-live for cache entries.

    Raises:
        ValueError: If similarity_threshold is out of [0.0, 1.0].
    """

    def __init__(
        self,
        *,
        primary_sqlite_path: Optional[str] = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(f"similarity_threshold must be in [0.0, 1.0], got {similarity_threshold}")

        self._threshold = similarity_threshold
        self._ttl = ttl_seconds

        # Stale response store for stale-while-revalidate
        self._stale_store: Dict[str, Dict[str, Any]] = {}

        sqlite_path = primary_sqlite_path or os.path.join(tempfile.gettempdir(), "resilient_cache.db")

        self._primary = SemanticCache(
            embedding_fn=_hash_embedding,
            backend="sqlite",
            threshold=similarity_threshold,
            ttl_seconds=ttl_seconds,
            sqlite_path=sqlite_path,
        )
        self._fallback = SemanticCache(
            embedding_fn=_hash_embedding,
            backend="memory",
            threshold=similarity_threshold,
            ttl_seconds=ttl_seconds,
        )

        self._primary_cb = TierCircuitBreaker(tier_name="primary_sqlite")
        self._fallback_cb = TierCircuitBreaker(tier_name="fallback_memory")
        self._primary_metrics = TierMetrics(tier_name="primary_sqlite")
        self._fallback_metrics = TierMetrics(tier_name="fallback_memory")

    async def get(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Look up a query across tiers. Falls back through the chain.

        Args:
            query: The query string.

        Returns:
            Cache hit dict with content and similarity, or None on miss.
        """
        if not query or not query.strip():
            return None

        # Try primary
        if not self._primary_cb.should_skip():
            try:
                result = await self._primary.get(query)
                if result is not None:
                    self._primary_metrics.hit_count += 1
                    self._primary_cb.record_success()
                    self._stale_store[query] = result
                    return result
                self._primary_metrics.miss_count += 1
                self._primary_cb.record_success()
            except Exception as exc:
                self._primary_metrics.error_count += 1
                self._primary_cb.record_failure()
                if self._primary_cb.is_open:
                    self._primary_metrics.circuit_open_count += 1
                logger.warning({"event": "primary_cache_error", "error": str(exc)})
        else:
            self._primary_metrics.circuit_open_count += 1

        # Try fallback
        if not self._fallback_cb.should_skip():
            try:
                result = await self._fallback.get(query)
                if result is not None:
                    self._fallback_metrics.hit_count += 1
                    self._fallback_cb.record_success()
                    return result
                self._fallback_metrics.miss_count += 1
                self._fallback_cb.record_success()
            except Exception as exc:
                self._fallback_metrics.error_count += 1
                self._fallback_cb.record_failure()
                if self._fallback_cb.is_open:
                    self._fallback_metrics.circuit_open_count += 1
                logger.warning({"event": "fallback_cache_error", "error": str(exc)})

        # Stale-while-revalidate: serve stale if all tiers failed
        stale = self._stale_store.get(query)
        if stale is not None:
            logger.info({"event": "serving_stale", "query": query[:50]})
            stale_copy = dict(stale)
            stale_copy["stale"] = True
            return stale_copy

        return None

    async def set(self, query: str, response: Dict[str, Any]) -> None:
        """
        Store a query-response pair in all available tiers.

        Args:
            query: The query string.
            response: Response dict to cache.
        """
        if not query or not query.strip():
            return

        # Validate embedding before caching
        embedding = _hash_embedding(query)
        if not validate_embedding(embedding):
            logger.warning({"event": "skip_cache_bad_embedding", "query": query[:50]})
            return

        # Write to primary
        if not self._primary_cb.should_skip():
            try:
                await self._primary.set(query, response)
                self._primary_cb.record_success()
            except Exception as exc:
                self._primary_cb.record_failure()
                logger.warning({"event": "primary_set_error", "error": str(exc)})

        # Write to fallback (always attempt, for redundancy)
        if not self._fallback_cb.should_skip():
            try:
                await self._fallback.set(query, response)
                self._fallback_cb.record_success()
            except Exception as exc:
                self._fallback_cb.record_failure()
                logger.warning({"event": "fallback_set_error", "error": str(exc)})

        # Update stale store
        self._stale_store[query] = response

    async def warm(self, pairs: Dict[str, Dict[str, Any]]) -> int:
        """
        Pre-populate cache from known Q&A pairs.

        Args:
            pairs: Dict mapping query strings to response dicts.

        Returns:
            Number of entries successfully cached.
        """
        count = 0
        for query, response in pairs.items():
            try:
                await self.set(query, response)
                count += 1
            except Exception as exc:
                logger.warning({"event": "warm_entry_failed", "query": query[:50], "error": str(exc)})
        logger.info({"event": "cache_warmed", "entries": count, "total": len(pairs)})
        return count

    async def clear(self) -> None:
        """Clear all tiers."""
        for cache in [self._primary, self._fallback]:
            try:
                await cache.clear()
            except Exception as exc:
                logger.warning({"event": "clear_error", "error": str(exc)})
        self._stale_store.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Return per-tier metrics dashboard."""
        return {
            "primary": self._primary_metrics.to_dict(),
            "fallback": self._fallback_metrics.to_dict(),
            "stale_entries": len(self._stale_store),
        }


# --- Execution ---
async def main() -> None:
    cache = ResilientCache(similarity_threshold=0.85)

    # Warm with 10 known pairs
    warm_data = {
        f"What is topic {i}?": {"content": f"Topic {i} is about concept {i}.", "topic_id": i}
        for i in range(10)
    }
    warmed = await cache.warm(warm_data)
    print(f"Warmed cache with {warmed} entries")

    # Run 40 queries: mix of hits and misses
    hits, misses, stale_served = 0, 0, 0
    for i in range(40):
        if i < 10:
            # Exact match queries
            query = f"What is topic {i}?"
        elif i < 20:
            # Novel queries (cache miss)
            query = f"Explain advanced concept {i} in detail"
        elif i < 30:
            # Repeat some warm queries
            query = f"What is topic {i % 10}?"
        else:
            # More novel queries
            query = f"How does system {i} work?"

        result = await cache.get(query)
        if result is not None:
            if result.get("stale"):
                stale_served += 1
            else:
                hits += 1
        else:
            misses += 1
            # Simulate caching the response for misses
            await cache.set(query, {"content": f"Response for: {query[:40]}"})

    print(f"\nResults: {hits} hits, {misses} misses, {stale_served} stale")

    # Simulate primary failure by forcing circuit breaker open
    print("\n--- Simulating Primary Failure ---")
    cache._primary_cb.is_open = True
    cache._primary_cb.opened_at = time.monotonic()
    cache._primary_metrics.circuit_open_count += 1

    for i in range(5):
        query = f"What is topic {i}?"
        result = await cache.get(query)
        tier = "fallback" if result else "miss"
        print(f"  Query '{query}' -> {tier}")

    # Metrics dashboard
    print("\n--- Metrics Dashboard ---")
    metrics = cache.get_metrics()
    for tier_name, tier_data in metrics.items():
        if isinstance(tier_data, dict):
            print(f"  {tier_name}:")
            for key, val in tier_data.items():
                print(f"    {key}: {val}")
        else:
            print(f"  {tier_name}: {tier_data}")


if __name__ == "__main__":
    asyncio.run(main())
