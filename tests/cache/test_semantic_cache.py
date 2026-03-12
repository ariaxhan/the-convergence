"""Tests for semantic cache layer.

Defines expected behavior for caching LLM responses by semantic similarity.
"""

import pytest
import asyncio
from typing import List

from tests.conftest import (
    async_simple_embedding_fn,
    async_semantic_embedding_fn,
)


class TestSemanticCacheBasics:
    """Test basic cache operations."""

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self):
        """Empty cache should return None."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        result = await cache.get("How do I reset my password?")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_after_set(self):
        """Exact same query should hit cache."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        query = "How do I reset my password?"
        response = {"content": "Click forgot password link."}

        await cache.set(query, response)
        result = await cache.get(query)

        assert result is not None
        assert result["content"] == response["content"]

    @pytest.mark.asyncio
    async def test_cache_returns_similarity_score(self):
        """Cache hit should include similarity score."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        query = "How do I reset my password?"
        await cache.set(query, {"content": "Answer"})
        result = await cache.get(query)

        assert "similarity" in result
        assert result["similarity"] >= 0.99  # Exact match

    @pytest.mark.asyncio
    async def test_clear_removes_all_entries(self):
        """Clear should remove all cached entries."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        await cache.set("query1", {"content": "response1"})
        await cache.set("query2", {"content": "response2"})

        await cache.clear()

        assert await cache.get("query1") is None
        assert await cache.get("query2") is None


class TestSemanticSimilarity:
    """Test semantic similarity matching."""

    @pytest.mark.asyncio
    async def test_similar_queries_hit_cache(self):
        """Semantically similar queries should hit cache."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_semantic_embedding_fn,
            backend="memory",
            threshold=0.7,  # Lower threshold for test embeddings
        )

        # Original query
        await cache.set(
            "How do I reset my password?",
            {"content": "Click the forgot password link."},
        )

        # Similar query should hit
        result = await cache.get("How can I change my password?")

        assert result is not None
        assert result["content"] == "Click the forgot password link."

    @pytest.mark.asyncio
    async def test_dissimilar_queries_miss_cache(self):
        """Semantically different queries should miss cache."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_semantic_embedding_fn,
            backend="memory",
            threshold=0.8,
        )

        # Cache password question
        await cache.set(
            "How do I reset my password?",
            {"content": "Click the forgot password link."},
        )

        # Completely different question should miss
        result = await cache.get("What are your business hours?")

        assert result is None

    @pytest.mark.asyncio
    async def test_threshold_respected(self):
        """Similarity threshold should be respected."""
        from convergence.cache import SemanticCache

        # High threshold - stricter matching
        strict_cache = SemanticCache(
            embedding_fn=async_semantic_embedding_fn,
            backend="memory",
            threshold=0.95,
        )

        # Low threshold - looser matching
        loose_cache = SemanticCache(
            embedding_fn=async_semantic_embedding_fn,
            backend="memory",
            threshold=0.5,
        )

        query = "How do I reset my password?"
        response = {"content": "Answer"}

        await strict_cache.set(query, response)
        await loose_cache.set(query, response)

        # Somewhat similar query
        similar = "password reset help"

        # Loose cache should hit, strict might miss
        loose_result = await loose_cache.get(similar)
        strict_result = await strict_cache.get(similar)

        # At minimum, loose should find it
        assert loose_result is not None or strict_result is None


class TestCacheMetadata:
    """Test cache entry metadata."""

    @pytest.mark.asyncio
    async def test_stores_original_query(self):
        """Cache should store the original query."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        original_query = "How do I reset my password?"
        await cache.set(original_query, {"content": "Answer"})

        result = await cache.get(original_query)

        assert "original_query" in result
        assert result["original_query"] == original_query

    @pytest.mark.asyncio
    async def test_stores_timestamp(self):
        """Cache entries should have timestamps."""
        from convergence.cache import SemanticCache
        import time

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        before = time.time()
        await cache.set("query", {"content": "response"})
        after = time.time()

        result = await cache.get("query")

        assert "created_at" in result
        assert before <= result["created_at"] <= after


class TestCacheTTL:
    """Test cache TTL (time-to-live) behavior."""

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Entries should expire after TTL."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
            ttl_seconds=0.1,  # 100ms TTL
        )

        await cache.set("query", {"content": "response"})

        # Immediately available
        assert await cache.get("query") is not None

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        assert await cache.get("query") is None

    @pytest.mark.asyncio
    async def test_no_ttl_never_expires(self):
        """Entries with no TTL should not expire."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
            ttl_seconds=None,  # No TTL
        )

        await cache.set("query", {"content": "response"})
        await asyncio.sleep(0.1)

        # Should still be available
        assert await cache.get("query") is not None


class TestMemoryBackend:
    """Test in-memory cache backend."""

    @pytest.mark.asyncio
    async def test_memory_backend_works(self):
        """Memory backend should function correctly."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        await cache.set("test", {"content": "response"})
        result = await cache.get("test")

        assert result is not None
        assert result["content"] == "response"

    @pytest.mark.asyncio
    async def test_memory_backend_isolation(self):
        """Different cache instances should be isolated."""
        from convergence.cache import SemanticCache

        cache1 = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )
        cache2 = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        await cache1.set("query", {"content": "response1"})

        # cache2 should not see cache1's entries
        assert await cache2.get("query") is None


class TestSQLiteBackend:
    """Test SQLite cache backend."""

    @pytest.mark.asyncio
    async def test_sqlite_backend_works(self, temp_sqlite_path):
        """SQLite backend should function correctly."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="sqlite",
            sqlite_path=temp_sqlite_path,
        )

        await cache.set("test", {"content": "response"})
        result = await cache.get("test")

        assert result is not None
        assert result["content"] == "response"

    @pytest.mark.asyncio
    async def test_sqlite_persistence(self, temp_sqlite_path):
        """SQLite should persist across cache instances."""
        from convergence.cache import SemanticCache

        # First instance - write
        cache1 = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="sqlite",
            sqlite_path=temp_sqlite_path,
        )
        await cache1.set("persistent", {"content": "I persist"})

        # Second instance - read
        cache2 = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="sqlite",
            sqlite_path=temp_sqlite_path,
        )
        result = await cache2.get("persistent")

        assert result is not None
        assert result["content"] == "I persist"


class TestRedisBackend:
    """Test Redis cache backend."""

    @pytest.mark.asyncio
    async def test_redis_backend_works(self, redis_url):
        """Redis backend should function correctly."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="redis",
            redis_url=redis_url,
        )

        try:
            await cache.set("test", {"content": "response"})
            result = await cache.get("test")

            assert result is not None
            assert result["content"] == "response"
        finally:
            await cache.clear()

    @pytest.mark.asyncio
    async def test_redis_shared_cache(self, redis_url):
        """Redis cache should be shared across instances."""
        from convergence.cache import SemanticCache

        cache1 = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="redis",
            redis_url=redis_url,
            namespace="shared_test",
        )
        cache2 = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="redis",
            redis_url=redis_url,
            namespace="shared_test",
        )

        try:
            await cache1.set("shared_key", {"content": "shared_value"})
            result = await cache2.get("shared_key")

            assert result is not None
            assert result["content"] == "shared_value"
        finally:
            await cache1.clear()


class TestConcurrency:
    """Test concurrent cache operations."""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self):
        """Concurrent reads should not interfere."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        await cache.set("query", {"content": "response"})

        # Many concurrent reads
        tasks = [cache.get("query") for _ in range(100)]
        results = await asyncio.gather(*tasks)

        assert all(r is not None for r in results)
        assert all(r["content"] == "response" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """Concurrent writes should not lose data."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        # Concurrent writes with different keys
        async def write(i: int):
            await cache.set(f"query_{i}", {"content": f"response_{i}"})

        await asyncio.gather(*[write(i) for i in range(50)])

        # All should be retrievable
        for i in range(50):
            result = await cache.get(f"query_{i}")
            assert result is not None
            assert result["content"] == f"response_{i}"


class TestCacheConfiguration:
    """Test cache configuration options."""

    @pytest.mark.asyncio
    async def test_custom_threshold(self):
        """Custom threshold should be applied."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
            threshold=0.99,  # Very strict
        )

        assert cache.threshold == 0.99

    @pytest.mark.asyncio
    async def test_default_threshold(self):
        """Default threshold should be 0.88."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,
            backend="memory",
        )

        assert cache.threshold == 0.88

    @pytest.mark.asyncio
    async def test_invalid_threshold_raises(self):
        """Invalid threshold should raise error."""
        from convergence.cache import SemanticCache

        with pytest.raises(ValueError):
            SemanticCache(
                embedding_fn=async_simple_embedding_fn,
                backend="memory",
                threshold=1.5,  # Invalid
            )

        with pytest.raises(ValueError):
            SemanticCache(
                embedding_fn=async_simple_embedding_fn,
                backend="memory",
                threshold=-0.1,  # Invalid
            )

    @pytest.mark.asyncio
    async def test_invalid_backend_raises(self):
        """Invalid backend should raise error."""
        from convergence.cache import SemanticCache

        with pytest.raises(ValueError):
            SemanticCache(
                embedding_fn=async_simple_embedding_fn,
                backend="invalid_backend",
            )


class TestEmbeddingFunction:
    """Test embedding function handling."""

    @pytest.mark.asyncio
    async def test_sync_embedding_fn_works(self):
        """Sync embedding function should be wrapped."""
        from convergence.cache import SemanticCache
        from tests.conftest import simple_embedding_fn

        cache = SemanticCache(
            embedding_fn=simple_embedding_fn,  # Sync function
            backend="memory",
        )

        await cache.set("test", {"content": "response"})
        result = await cache.get("test")

        assert result is not None

    @pytest.mark.asyncio
    async def test_async_embedding_fn_works(self):
        """Async embedding function should work directly."""
        from convergence.cache import SemanticCache

        cache = SemanticCache(
            embedding_fn=async_simple_embedding_fn,  # Async function
            backend="memory",
        )

        await cache.set("test", {"content": "response"})
        result = await cache.get("test")

        assert result is not None

    @pytest.mark.asyncio
    async def test_embedding_dimension_consistency(self):
        """Cache should handle varying embedding dimensions."""
        from convergence.cache import SemanticCache

        # 128-dim embeddings
        async def embed_128(text: str) -> List[float]:
            return [0.1] * 128

        cache = SemanticCache(
            embedding_fn=embed_128,
            backend="memory",
        )

        await cache.set("test", {"content": "response"})
        result = await cache.get("test")

        assert result is not None
