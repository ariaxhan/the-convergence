"""Semantic cache for LLM responses.

Caches responses based on semantic similarity of queries,
reducing redundant API calls for similar questions.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from .backends import (
    CacheBackend,
    CacheEntry,
    MemoryCacheBackend,
    RedisCacheBackend,
    SQLiteCacheBackend,
    cosine_similarity,
)

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
        namespace: str = "armature_cache",
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

        # Get all entries from backend
        entries = await self._backend.get_all_entries()

        if not entries:
            return None

        # Find best match
        best_match: Optional[CacheEntry] = None
        best_similarity: float = 0.0

        for entry in entries:
            similarity = cosine_similarity(query_embedding, entry.embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = entry

        # Check threshold
        if best_match is None or best_similarity < self.threshold:
            return None

        # Build result
        result = dict(best_match.response)
        result["similarity"] = best_similarity
        result["original_query"] = best_match.query
        result["created_at"] = best_match.created_at

        return result

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
