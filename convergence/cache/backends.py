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

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[CacheEntry]:
        """Get a cache entry by its ID (query hash)."""
        ...

    @abstractmethod
    def get_index(self) -> "ANNIndex":
        """Get the ANN index for fast similarity search."""
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
# ANN Index
# ============================================================================


class ANNIndex:
    """
    Approximate Nearest Neighbor index for O(log n) similarity search.

    Uses numpy-accelerated similarity computation with heap-based top-k.
    Falls back to pure Python if numpy unavailable.

    Thread-safe for concurrent access.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension
        self._vectors: Dict[str, List[float]] = {}
        self._sync_lock = __import__("threading").Lock()
        # Cache numpy arrays for batch operations
        self._ids_cache: Optional[List[str]] = None
        self._matrix_cache: Optional[Any] = None
        self._cache_valid = False
        # Check numpy availability
        try:
            import numpy as np
            self._np: Any = np
            self._has_numpy = True
        except ImportError:
            self._np = None
            self._has_numpy = False

    @property
    def size(self) -> int:
        """Number of vectors in the index."""
        return len(self._vectors)

    def _invalidate_cache(self) -> None:
        """Invalidate numpy cache."""
        self._cache_valid = False
        self._ids_cache = None
        self._matrix_cache = None

    def _build_cache(self) -> None:
        """Build numpy matrix cache for fast batch similarity."""
        if not self._has_numpy or not self._vectors:
            return

        self._ids_cache = list(self._vectors.keys())
        # Build normalized matrix (N x D)
        vectors = [self._vectors[id] for id in self._ids_cache]
        matrix = self._np.array(vectors, dtype=self._np.float32)
        # Normalize rows
        norms = self._np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = self._np.where(norms == 0, 1, norms)  # Avoid division by zero
        self._matrix_cache = matrix / norms
        self._cache_valid = True

    def add(self, id: str, vector: List[float]) -> None:
        """Add or update vector in index."""
        with self._sync_lock:
            self._vectors[id] = vector
            self._invalidate_cache()

    def remove(self, id: str) -> None:
        """Remove vector from index."""
        with self._sync_lock:
            if id in self._vectors:
                del self._vectors[id]
                self._invalidate_cache()

    def search(self, query: List[float], k: int = 10) -> List[tuple[str, float]]:
        """
        Search for k nearest neighbors.

        Returns: List of (id, similarity) tuples, sorted by similarity descending.
        """
        with self._sync_lock:
            if not self._vectors:
                return []

            if self._has_numpy:
                return self._search_numpy(query, k)
            else:
                return self._search_pure_python(query, k)

    def _search_numpy(self, query: List[float], k: int) -> List[tuple[str, float]]:
        """Numpy-accelerated search using matrix multiplication."""
        if not self._cache_valid:
            self._build_cache()

        if self._matrix_cache is None or self._ids_cache is None:
            return self._search_pure_python(query, k)

        # Normalize query
        q = self._np.array(query, dtype=self._np.float32)
        q_norm = self._np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        # Compute all similarities in one matrix-vector multiply
        # Result is (N,) array of cosine similarities
        similarities = self._matrix_cache @ q

        # Get top k indices using argpartition (O(n) instead of O(n log n))
        if k >= len(similarities):
            top_k_idx = self._np.argsort(similarities)[::-1]
        else:
            # argpartition gives us the k largest (unsorted)
            partition_idx = self._np.argpartition(similarities, -k)[-k:]
            # Sort just the top k
            top_k_idx = partition_idx[self._np.argsort(similarities[partition_idx])[::-1]]

        results = []
        for idx in top_k_idx:
            results.append((self._ids_cache[idx], float(similarities[idx])))

        return results

    def _search_pure_python(self, query: List[float], k: int) -> List[tuple[str, float]]:
        """Pure Python fallback with heap-based top-k."""
        import heapq

        # Use min-heap of size k for efficient top-k
        heap: List[tuple[float, str]] = []

        for id, vec in self._vectors.items():
            sim = cosine_similarity(query, vec)
            if len(heap) < k:
                heapq.heappush(heap, (sim, id))
            elif sim > heap[0][0]:
                heapq.heapreplace(heap, (sim, id))

        # Sort by similarity descending
        results = [(id, sim) for sim, id in sorted(heap, reverse=True)]
        return results

    def clear(self) -> None:
        """Clear all vectors from index."""
        with self._sync_lock:
            self._vectors.clear()
            self._invalidate_cache()


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
        self._index = ANNIndex()

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
            # Add to ANN index
            self._index.add(key, embedding)

    async def get_by_id(self, id: str) -> Optional[CacheEntry]:
        """Get a cache entry by its ID (query hash)."""
        async with self._lock:
            entry = self._entries.get(id)
            if entry and not self._is_expired(entry.created_at):
                return entry
            return None

    async def clear(self) -> None:
        """Remove all cache entries."""
        async with self._lock:
            self._entries.clear()
            self._index.clear()

    def get_index(self) -> ANNIndex:
        """Get the ANN index for fast similarity search."""
        return self._index


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
        self._index = ANNIndex()
        self._index_loaded = False

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

    async def _ensure_index_loaded(self) -> None:
        """Load embeddings into ANN index from database."""
        if self._index_loaded:
            return

        import aiosqlite

        await self._ensure_initialized()

        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT query_hash, embedding, created_at FROM cache_entries"
            ) as cursor:
                rows = await cursor.fetchall()

            for row in rows:
                if not self._is_expired(row["created_at"]):
                    self._index.add(row["query_hash"], json.loads(row["embedding"]))

        self._index_loaded = True

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
                # Add to ANN index
                self._index.add(query_hash, embedding)
                # Mark index as current (we're building it incrementally)
                self._index_loaded = True

    async def clear(self) -> None:
        """Remove all cache entries."""
        import aiosqlite

        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.sqlite_path) as db:
                await db.execute("DELETE FROM cache_entries")
                await db.commit()
            self._index.clear()
            # Index is empty but valid - no need to reload
            self._index_loaded = True

    async def get_by_id(self, id: str) -> Optional[CacheEntry]:
        """Get a cache entry by its ID (query hash)."""
        import aiosqlite

        await self._ensure_initialized()

        async with self._lock:
            async with aiosqlite.connect(self.sqlite_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT query, embedding, response, created_at FROM cache_entries WHERE query_hash = ?",
                    (id,),
                ) as cursor:
                    row = await cursor.fetchone()

                if row is None:
                    return None

                entry = CacheEntry(
                    query=row["query"],
                    embedding=json.loads(row["embedding"]),
                    response=json.loads(row["response"]),
                    created_at=row["created_at"],
                )

                if self._is_expired(entry.created_at):
                    return None

                return entry

    def get_index(self) -> ANNIndex:
        """Get the ANN index for fast similarity search."""
        return self._index


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
        namespace: str = "convergence_cache",
        ttl_seconds: Optional[int] = None,
    ) -> None:
        super().__init__(ttl_seconds)
        self.redis_url = redis_url
        self.namespace = namespace
        self._client: Optional[Any] = None
        self._lock = asyncio.Lock()
        self._index = ANNIndex()

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
            # Add to ANN index
            self._index.add(query_hash, embedding)

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
            self._index.clear()

    async def get_by_id(self, id: str) -> Optional[CacheEntry]:
        """Get a cache entry by its ID (query hash)."""
        client = await self._get_client()
        key = self._make_key(id)

        async with self._lock:
            data = await client.get(key)
            if data is None:
                return None

            entry_data = json.loads(data)
            entry = CacheEntry(
                query=entry_data["query"],
                embedding=entry_data["embedding"],
                response=entry_data["response"],
                created_at=entry_data["created_at"],
            )

            if self._is_expired(entry.created_at):
                return None

            return entry

    def get_index(self) -> ANNIndex:
        """Get the ANN index for fast similarity search."""
        return self._index
