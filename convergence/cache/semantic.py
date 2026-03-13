"""Semantic cache for LLM responses.

Caches responses based on semantic similarity of queries,
reducing redundant API calls for similar questions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .backends import (
    CacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
    SQLiteCacheBackend,
)

# Protocol for observer to avoid circular imports
try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol


class CacheObserver(Protocol):
    """Protocol for cache observation."""

    def track_cache_access(self, hit: bool) -> None:
        """Track cache hit/miss."""
        ...

# Type alias for embedding functions
EmbeddingFn = Union[
    Callable[[str], List[float]],
    Callable[[str], Awaitable[List[float]]],
]


class SemanticCache:
    """Semantic cache for LLM responses.

    Caches responses keyed by semantic similarity of queries.
    When a new query comes in, finds the most similar cached query
    above the threshold and returns its response.

    Args:
        embedding_fn: Function that converts text to embedding vector.
            Can be sync or async.
        backend: Storage backend ("memory", "sqlite", or "redis").
        threshold: Minimum cosine similarity for cache hit (0.0-1.0).
        ttl_seconds: Optional time-to-live for cache entries.
        sqlite_path: Path to SQLite database (required for sqlite backend).
        redis_url: Redis connection URL (required for redis backend).
        namespace: Namespace for Redis keys.

    Example:
        ```python
        async def get_embedding(text: str) -> List[float]:
            # Your embedding function
            return await openai.embeddings.create(input=text, model="text-embedding-3-small")

        cache = SemanticCache(
            embedding_fn=get_embedding,
            backend="memory",
            threshold=0.88,
        )

        # Check cache first
        result = await cache.get("How do I reset my password?")
        if result is None:
            # Cache miss - call LLM
            response = await call_llm("How do I reset my password?")
            await cache.set("How do I reset my password?", {"content": response})
        ```
    """

    VALID_BACKENDS = {"memory", "sqlite", "redis"}

    def __init__(
        self,
        embedding_fn: EmbeddingFn,
        backend: str = "memory",
        threshold: float = 0.88,
        ttl_seconds: Optional[int] = None,
        sqlite_path: Optional[str] = None,
        redis_url: Optional[str] = None,
        namespace: str = "convergence_cache",
        observer: Optional[CacheObserver] = None,
    ) -> None:
        # Validate threshold
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"threshold must be between 0.0 and 1.0, got {threshold}"
            )

        # Validate backend
        if backend not in self.VALID_BACKENDS:
            raise ValueError(
                f"backend must be one of {self.VALID_BACKENDS}, got '{backend}'"
            )

        self.threshold = threshold
        self._embedding_fn = embedding_fn
        self._is_async_embedding = asyncio.iscoroutinefunction(embedding_fn)
        self._observer = observer
        self._false_positives: List[Dict[str, Any]] = []
        self._stats = {"hits": 0, "misses": 0, "false_positives": 0}

        # Initialize backend
        self._backend: CacheBackend
        if backend == "memory":
            self._backend = MemoryCacheBackend(ttl_seconds=ttl_seconds)
        elif backend == "sqlite":
            if sqlite_path is None:
                raise ValueError("sqlite_path is required for sqlite backend")
            self._backend = SQLiteCacheBackend(
                sqlite_path=sqlite_path, ttl_seconds=ttl_seconds
            )
        elif backend == "redis":
            if redis_url is None:
                raise ValueError("redis_url is required for redis backend")
            self._backend = RedisCacheBackend(
                redis_url=redis_url, namespace=namespace, ttl_seconds=ttl_seconds
            )

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text, handling sync or async functions."""
        if self._is_async_embedding:
            return await self._embedding_fn(text)  # type: ignore
        else:
            # Run sync function in executor to avoid blocking
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self._embedding_fn, text)  # type: ignore

    async def get(self, query: str) -> Optional[Dict[str, Any]]:
        """Look up a query in the cache.

        Args:
            query: The query string to look up.

        Returns:
            On cache hit: dict with keys:
                - content: The cached response content
                - similarity: Cosine similarity score (0.0-1.0)
                - original_query: The original query that was cached
                - created_at: Timestamp when entry was created
                - (plus any other fields from the cached response)
            On cache miss: None
        """
        # Get embedding for query
        query_embedding = await self._get_embedding(query)

        # Ensure index is loaded (for SQLite backend)
        if hasattr(self._backend, "_ensure_index_loaded"):
            await self._backend._ensure_index_loaded()

        # Use ANN index for fast lookup
        index = self._backend.get_index()
        candidates = index.search(query_embedding, k=10)

        if not candidates:
            self._stats["misses"] += 1
            if self._observer:
                self._observer.track_cache_access(hit=False)
            return None

        # Find best match above threshold
        for entry_id, similarity in candidates:
            if similarity >= self.threshold:
                entry = await self._backend.get_by_id(entry_id)
                if entry:
                    # Track hit
                    self._stats["hits"] += 1
                    if self._observer:
                        self._observer.track_cache_access(hit=True)

                    # Build result
                    result = dict(entry.response)
                    result["similarity"] = similarity
                    result["original_query"] = entry.query
                    result["created_at"] = entry.created_at
                    return result

        # No match above threshold
        self._stats["misses"] += 1
        if self._observer:
            self._observer.track_cache_access(hit=False)
        return None

    async def set(self, query: str, response: Dict[str, Any]) -> None:
        """Store a query-response pair in the cache.

        Args:
            query: The query string.
            response: The response to cache (must be a dict).
        """
        # Get embedding for query
        query_embedding = await self._get_embedding(query)

        # Store in backend
        await self._backend.set(query, query_embedding, response)

    async def clear(self) -> None:
        """Remove all entries from the cache."""
        await self._backend.clear()
        self._stats = {"hits": 0, "misses": 0, "false_positives": 0}
        self._false_positives = []

    async def validate_threshold(
        self, test_cases: List[tuple[str, bool]]
    ) -> Dict[str, Any]:
        """Validate threshold accuracy with test cases.

        Args:
            test_cases: List of (query, expected_hit) tuples.
                expected_hit=True means we expect a cache hit.

        Returns:
            Dict with keys:
                - accuracy: Overall accuracy (0.0-1.0)
                - false_positives: Number of false positives
                - false_negatives: Number of false negatives
                - details: List of individual test results
        """
        results = []
        false_positives = 0
        false_negatives = 0
        correct = 0

        for query, expected_hit in test_cases:
            result = await self.get(query)
            actual_hit = result is not None

            if actual_hit == expected_hit:
                correct += 1
            elif actual_hit and not expected_hit:
                false_positives += 1
            else:
                false_negatives += 1

            results.append({
                "query": query,
                "expected_hit": expected_hit,
                "actual_hit": actual_hit,
                "similarity": result["similarity"] if result else None,
            })

        total = len(test_cases)
        return {
            "accuracy": correct / total if total > 0 else 0.0,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "details": results,
        }

    async def recommend_threshold(
        self, test_cases: List[tuple[str, bool]]
    ) -> Dict[str, Any]:
        """Recommend optimal threshold based on test cases.

        Args:
            test_cases: List of (query, expected_hit) tuples.

        Returns:
            Dict with keys:
                - recommended_threshold: Optimal threshold value
                - analysis: Details about the analysis
        """
        # Collect all similarities
        similarities: List[Dict[str, Any]] = []

        for query, expected_hit in test_cases:
            query_embedding = await self._get_embedding(query)

            # Ensure index is loaded
            if hasattr(self._backend, "_ensure_index_loaded"):
                await self._backend._ensure_index_loaded()

            index = self._backend.get_index()
            candidates = index.search(query_embedding, k=1)

            if candidates:
                entry_id, similarity = candidates[0]
                similarities.append({
                    "query": query,
                    "expected_hit": expected_hit,
                    "best_similarity": similarity,
                })

        if not similarities:
            return {
                "recommended_threshold": 0.85,
                "analysis": "No data available for analysis",
            }

        # Find threshold that maximizes accuracy
        best_threshold = 0.85
        best_accuracy = 0.0

        for threshold_candidate in [i / 100 for i in range(50, 100)]:
            correct = 0
            for s in similarities:
                actual_hit = s["best_similarity"] >= threshold_candidate
                if actual_hit == s["expected_hit"]:
                    correct += 1

            accuracy = correct / len(similarities)
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold_candidate

        return {
            "recommended_threshold": best_threshold,
            "analysis": {
                "test_cases_analyzed": len(similarities),
                "best_accuracy": best_accuracy,
            },
        }

    async def report_false_positive(
        self, query: str, matched_query: str
    ) -> None:
        """Report a false positive match.

        Args:
            query: The query that was made.
            matched_query: The query it incorrectly matched to.
        """
        self._false_positives.append({
            "query": query,
            "matched_query": matched_query,
        })
        self._stats["false_positives"] += 1

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with keys:
                - hits: Number of cache hits
                - misses: Number of cache misses
                - hit_rate: Hit rate (0.0-1.0)
                - false_positives: Number of reported false positives
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0.0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "false_positives": self._stats["false_positives"],
        }
