"""Cache backend implementations for semantic caching.

Provides pluggable storage backends: memory, SQLite, and Redis.
All backends implement async interface for consistency.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CacheEntry:
    """A single cache entry with embedding and metadata."""

    query: str
    embedding: List[float]
    response: Dict[str, Any]
    created_at: float


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        self.ttl_seconds = ttl_seconds

    def _is_expired(self, created_at: float) -> bool:
        """Check if an entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        return time.time() - created_at > self.ttl_seconds

    @abstractmethod
    async def get_all_entries(self) -> List[CacheEntry]:
        """Retrieve all non-expired cache entries."""
        ...

    @abstractmethod
    async def set(self, query: str, embedding: List[float], response: Dict[str, Any]) -> None:
        """Store a cache entry."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Remove all cache entries."""
        ...


def _compute_hash(text: str) -> str:
    """Compute a hash for a text string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(x * x for x in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# ============================================================================
# Memory Backend
# ============================================================================


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend using a dictionary.

    Fast but not persistent. Each instance maintains its own cache.
    """

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        super().__init__(ttl_seconds)
        self._entries: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get_all_entries(self) -> List[CacheEntry]:
        """Retrieve all non-expired cache entries."""
        async with self._lock:
            entries = []
            expired_keys = []

            for key, entry in self._entries.items():
                if self._is_expired(entry.created_at):
                    expired_keys.append(key)
                else:
                    entries.append(entry)

            # Clean up expired entries
            for key in expired_keys:
                del self._entries[key]

            return entries

    async def set(self, query: str, embedding: List[float], response: Dict[str, Any]) -> None:
        """Store a cache entry."""
        async with self._lock:
            key = _compute_hash(query)
            self._entries[key] = CacheEntry(
                query=query,
                embedding=embedding,
                response=response,
                created_at=time.time(),
            )

    async def clear(self) -> None:
        """Remove all cache entries."""
        async with self._lock:
            self._entries.clear()


# ============================================================================
# SQLite Backend
# ============================================================================


class SQLiteCacheBackend(CacheBackend):
    """SQLite-based cache backend.

    Persistent storage using aiosqlite for async operations.
    Embeddings stored as JSON-serialized lists.
    """

    def __init__(
        self, sqlite_path: str, ttl_seconds: Optional[int] = None
    ) -> None:
        super().__init__(ttl_seconds)
        self.sqlite_path = sqlite_path
        self._initialized = False
        self._lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        """Ensure the database table exists."""
        if self._initialized:
            return

        import aiosqlite

        async with aiosqlite.connect(self.sqlite_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT UNIQUE NOT NULL,
                    query TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_query_hash ON cache_entries(query_hash)"
            )
            await db.commit()

        self._initialized = True

    async def get_all_entries(self) -> List[CacheEntry]:
        """Retrieve all non-expired cache entries."""
        import aiosqlite

        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row

                if self.ttl_seconds is not None:
                    # Delete expired entries
                    cutoff = time.time() - self.ttl_seconds
                    await db.execute(
                        "DELETE FROM cache_entries WHERE created_at < ?", (cutoff,)
                    )
                    await db.commit()

                async with db.execute(
                    "SELECT query, embedding, response, created_at FROM cache_entries"
                ) as cursor:
                    rows = await cursor.fetchall()

                entries = []
                for row in rows:
                    entry = CacheEntry(
                        query=row["query"],
                        embedding=json.loads(row["embedding"]),
                        response=json.loads(row["response"]),
                        created_at=row["created_at"],
                    )
                    if not self._is_expired(entry.created_at):
                        entries.append(entry)

                return entries

    async def set(self, query: str, embedding: List[float], response: Dict[str, Any]) -> None:
        """Store a cache entry."""
        import aiosqlite

        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.sqlite_path) as db:
                query_hash = _compute_hash(query)
                await db.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (query_hash, query, embedding, response, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        query_hash,
                        query,
                        json.dumps(embedding),
                        json.dumps(response),
                        time.time(),
                    ),
                )
                await db.commit()

    async def clear(self) -> None:
        """Remove all cache entries."""
        import aiosqlite

        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM cache_entries")
                await db.commit()


# ============================================================================
# Redis Backend
# ============================================================================


class RedisCacheBackend(CacheBackend):
    """Redis-based cache backend.

    Distributed cache using redis.asyncio for async operations.
    Supports namespacing for multi-tenant scenarios.
    """

    def __init__(
        self,
        redis_url: str,
        namespace: str = "armature_cache",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        super().__init__(ttl_seconds)
        self.redis_url = redis_url
        self.namespace = namespace
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Any:
        """Get or create Redis client."""
        if self._client is None:
            import redis.asyncio as redis

            self._client = redis.from_url(self.redis_url)
        return self._client

    def _make_key(self, query_hash: str) -> str:
        """Create a namespaced Redis key."""
        return f"{self.namespace}:embedding:{query_hash}"

    async def get_all_entries(self) -> List[CacheEntry]:
        """Retrieve all non-expired cache entries."""
        client = await self._get_client()
        pattern = f"{self.namespace}:embedding:*"

        entries = []
        async with self._lock:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            for key in keys:
                data = await client.get(key)
                if data is None:
                    continue

                entry_data = json.loads(data)
                entry = CacheEntry(
                    query=entry_data["query"],
                    embedding=entry_data["embedding"],
                    response=entry_data["response"],
                    created_at=entry_data["created_at"],
                )

                if not self._is_expired(entry.created_at):
                    entries.append(entry)
                elif self.ttl_seconds is not None:
                    # Clean up expired entry
                    await client.delete(key)

        return entries

    async def set(self, query: str, embedding: List[float], response: Dict[str, Any]) -> None:
        """Store a cache entry."""
        client = await self._get_client()
        query_hash = _compute_hash(query)
        key = self._make_key(query_hash)

        entry_data = {
            "query": query,
            "embedding": embedding,
            "response": response,
            "created_at": time.time(),
        }

        async with self._lock:
            if self.ttl_seconds is not None:
                await client.setex(key, self.ttl_seconds, json.dumps(entry_data))
            else:
                await client.set(key, json.dumps(entry_data))

    async def clear(self) -> None:
        """Remove all cache entries in this namespace."""
        client = await self._get_client()
        pattern = f"{self.namespace}:embedding:*"

        async with self._lock:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await client.delete(*keys)
