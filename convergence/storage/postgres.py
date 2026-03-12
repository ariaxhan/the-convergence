"""
Generic PostgreSQL storage backend for The Convergence framework.

Provides persistent storage using PostgreSQL database with async operations.
Implements StorageProtocol with JSONB for flexible value storage.

Requires asyncpg for async PostgreSQL operations.
"""

from __future__ import annotations

import json
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

try:
    import asyncpg as asyncpg_module
    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg_module = None  # type: ignore
    ASYNCPG_AVAILABLE = False

from convergence.storage.base import (
    StorageConnectionError,
    StorageError,
    StorageProtocol,
    StorageSerializationError,
)


class PostgreSQLStorage:
    """
    PostgreSQL-based storage implementation.

    Features:
    - Async operations via asyncpg
    - JSONB storage for flexible data types
    - Connection pooling via asyncpg pool
    - Automatic table creation
    - Timestamp tracking

    Usage:
        async with PostgreSQLStorage(dsn="postgresql://...") as storage:
            await storage.save("agent:1", agent_data)
            data = await storage.load("agent:1")

    Or with StorageRegistry:
        storage = StorageRegistry.get("postgres", dsn="postgresql://...")
    """

    def __init__(
        self,
        dsn: str,
        table_name: str = "storage",
    ):
        """
        Initialize PostgreSQL storage.

        Args:
            dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host:5432/db")
            table_name: Name of the storage table (default: "storage")
        """
        if not ASYNCPG_AVAILABLE:
            raise ImportError(
                "asyncpg is required for PostgreSQL storage. "
                "Install with: pip install asyncpg"
            )

        self.dsn = dsn
        self.table_name = table_name
        self._pool: Optional[asyncpg.Pool] = None  # type: ignore[name-defined]

    async def __aenter__(self):
        """Async context manager entry - establishes connection."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connection."""
        await self.close()

    async def connect(self) -> None:
        """
        Establish database connection pool and create table if needed.

        Raises:
            StorageConnectionError: If connection fails
        """
        if self._pool is not None:
            return  # Already connected

        try:
            self._pool = await asyncpg_module.create_pool(self.dsn)

            # Create table if not exists
            async with self._pool.acquire() as conn:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        key TEXT PRIMARY KEY,
                        value JSONB NOT NULL,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

                # Create index on key for faster lookups
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_key
                    ON {self.table_name}(key)
                """)

        except Exception as e:
            raise StorageConnectionError(
                f"Failed to connect to PostgreSQL database: {e}"
            ) from e

    async def _ensure_connected(self) -> asyncpg.Pool:  # type: ignore[name-defined]
        """Ensure connection is established and return pool."""
        if self._pool is None:
            await self.connect()
        assert self._pool is not None
        return self._pool

    def _serialize(self, value: Any) -> str:
        """
        Serialize value to JSON string.

        Args:
            value: Python object to serialize

        Returns:
            JSON string

        Raises:
            StorageSerializationError: If serialization fails
        """
        try:
            return json.dumps(value)
        except Exception as e:
            raise StorageSerializationError(
                f"Failed to serialize value: {e}"
            ) from e

    def _deserialize(self, data: str) -> Any:
        """
        Deserialize JSON string to Python object.

        Args:
            data: JSON string

        Returns:
            Deserialized Python object

        Raises:
            StorageSerializationError: If deserialization fails
        """
        try:
            return json.loads(data)
        except Exception as e:
            raise StorageSerializationError(
                f"Failed to deserialize value: {e}"
            ) from e

    async def save(self, key: str, value: Any) -> None:
        """
        Save a value with a key.

        Args:
            key: Unique identifier
            value: Python object to store (must be JSON serializable)

        Raises:
            StorageError: If save operation fails
        """
        pool = await self._ensure_connected()

        try:
            serialized = self._serialize(value)

            async with pool.acquire() as conn:
                await conn.execute(f"""
                    INSERT INTO {self.table_name} (key, value, updated_at)
                    VALUES ($1, $2::jsonb, NOW())
                    ON CONFLICT (key) DO UPDATE
                    SET value = $2::jsonb, updated_at = NOW()
                """, key, serialized)

        except StorageSerializationError:
            raise  # Re-raise serialization errors as-is
        except Exception as e:
            raise StorageError(
                f"Failed to save key '{key}': {e}"
            ) from e

    async def load(self, key: str) -> Any:
        """
        Load a value by key.

        Args:
            key: Unique identifier

        Returns:
            Stored Python object

        Raises:
            KeyError: If key doesn't exist
            StorageError: If load operation fails
        """
        pool = await self._ensure_connected()

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT value FROM {self.table_name}
                    WHERE key = $1
                """, key)

                if row is None:
                    raise KeyError(f"Key not found: {key}")

                value = row["value"]

                # asyncpg returns JSONB as dict/list directly
                if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                    return value

                # Fallback: deserialize if string
                return self._deserialize(value)

        except KeyError:
            raise  # Re-raise KeyError as-is
        except StorageSerializationError:
            raise  # Re-raise deserialization errors as-is
        except Exception as e:
            raise StorageError(
                f"Failed to load key '{key}': {e}"
            ) from e

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Unique identifier

        Returns:
            True if key exists, False otherwise
        """
        pool = await self._ensure_connected()

        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(f"""
                    SELECT 1 FROM {self.table_name}
                    WHERE key = $1
                    LIMIT 1
                """, key)

                return row is not None

        except Exception as e:
            raise StorageError(
                f"Failed to check existence of key '{key}': {e}"
            ) from e

    async def delete(self, key: str) -> None:
        """
        Delete a key.

        Args:
            key: Unique identifier

        Note:
            Silently succeeds if key doesn't exist (idempotent).
        """
        pool = await self._ensure_connected()

        try:
            async with pool.acquire() as conn:
                await conn.execute(f"""
                    DELETE FROM {self.table_name}
                    WHERE key = $1
                """, key)

        except Exception as e:
            raise StorageError(
                f"Failed to delete key '{key}': {e}"
            ) from e

    async def list_keys(self, prefix: str = "") -> List[str]:
        """
        List all keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of matching keys
        """
        pool = await self._ensure_connected()

        try:
            async with pool.acquire() as conn:
                if prefix:
                    # Use LIKE for prefix matching
                    rows = await conn.fetch(f"""
                        SELECT key FROM {self.table_name}
                        WHERE key LIKE $1
                        ORDER BY key
                    """, f"{prefix}%")
                else:
                    # Get all keys
                    rows = await conn.fetch(f"""
                        SELECT key FROM {self.table_name}
                        ORDER BY key
                    """)

            return [row["key"] for row in rows]

        except Exception as e:
            raise StorageError(
                f"Failed to list keys with prefix '{prefix}': {e}"
            ) from e

    async def close(self) -> None:
        """
        Close the database connection pool.

        Idempotent - safe to call multiple times.
        """
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception:
                pass  # Ignore errors during close
            finally:
                self._pool = None

    # Additional utility methods

    async def count_keys(self, prefix: str = "") -> int:
        """
        Count keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            Number of matching keys
        """
        pool = await self._ensure_connected()

        try:
            async with pool.acquire() as conn:
                if prefix:
                    row = await conn.fetchrow(f"""
                        SELECT COUNT(*) FROM {self.table_name}
                        WHERE key LIKE $1
                    """, f"{prefix}%")
                else:
                    row = await conn.fetchrow(f"""
                        SELECT COUNT(*) FROM {self.table_name}
                    """)

            return row[0] if row else 0

        except Exception as e:
            raise StorageError(
                f"Failed to count keys with prefix '{prefix}': {e}"
            ) from e

    async def clear(self, prefix: str = "") -> int:
        """
        Delete all keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            Number of keys deleted
        """
        pool = await self._ensure_connected()

        try:
            async with pool.acquire() as conn:
                if prefix:
                    result = await conn.execute(f"""
                        DELETE FROM {self.table_name}
                        WHERE key LIKE $1
                    """, f"{prefix}%")
                else:
                    result = await conn.execute(f"""
                        DELETE FROM {self.table_name}
                    """)

            # Parse result like "DELETE 5"
            if result:
                parts = result.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return int(parts[1])
            return 0

        except Exception as e:
            raise StorageError(
                f"Failed to clear keys with prefix '{prefix}': {e}"
            ) from e


# Verify protocol implementation at module level
# This ensures PostgreSQLStorage implements StorageProtocol correctly
def _verify_protocol() -> None:
    """Verify that PostgreSQLStorage implements StorageProtocol."""
    if not ASYNCPG_AVAILABLE:
        return  # Skip verification if asyncpg not available

    # Create a mock DSN for verification (won't actually connect)
    storage = PostgreSQLStorage(dsn="postgresql://test:test@localhost/test")
    assert isinstance(storage, StorageProtocol), \
        "PostgreSQLStorage must implement StorageProtocol"


_verify_protocol()
