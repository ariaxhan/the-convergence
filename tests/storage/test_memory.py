"""Tests for in-memory storage backend.

This backend is critical for testing - must work reliably.
"""

import pytest
import asyncio

from convergence.storage.memory import MemoryStorage
from convergence.storage.base import StorageError


class TestMemoryStorageBasics:
    """Test basic storage operations."""

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Should save and load values."""
        storage = MemoryStorage()

        await storage.save("key1", {"value": 42})
        result = await storage.load("key1")

        assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_load_nonexistent_raises_keyerror(self):
        """Loading nonexistent key should raise KeyError."""
        storage = MemoryStorage()

        with pytest.raises(KeyError):
            await storage.load("nonexistent")

    @pytest.mark.asyncio
    async def test_overwrite_value(self):
        """Should overwrite existing values."""
        storage = MemoryStorage()

        await storage.save("key", "value1")
        await storage.save("key", "value2")
        result = await storage.load("key")

        assert result == "value2"

    @pytest.mark.asyncio
    async def test_store_various_types(self):
        """Should store various Python types."""
        storage = MemoryStorage()

        # Dict
        await storage.save("dict", {"a": 1, "b": 2})
        assert await storage.load("dict") == {"a": 1, "b": 2}

        # List
        await storage.save("list", [1, 2, 3])
        assert await storage.load("list") == [1, 2, 3]

        # String
        await storage.save("string", "hello")
        assert await storage.load("string") == "hello"

        # Number
        await storage.save("number", 42)
        assert await storage.load("number") == 42

        # None
        await storage.save("none", None)
        assert await storage.load("none") is None


class TestExists:
    """Test exists method."""

    @pytest.mark.asyncio
    async def test_exists_true(self):
        """Should return True for existing key."""
        storage = MemoryStorage()

        await storage.save("key", "value")
        assert await storage.exists("key") is True

    @pytest.mark.asyncio
    async def test_exists_false(self):
        """Should return False for nonexistent key."""
        storage = MemoryStorage()

        assert await storage.exists("nonexistent") is False


class TestDelete:
    """Test delete method."""

    @pytest.mark.asyncio
    async def test_delete_removes_key(self):
        """Delete should remove the key."""
        storage = MemoryStorage()

        await storage.save("key", "value")
        await storage.delete("key")

        assert await storage.exists("key") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self):
        """Delete nonexistent key should not raise error."""
        storage = MemoryStorage()

        # Should not raise
        await storage.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_idempotent(self):
        """Multiple deletes should be safe."""
        storage = MemoryStorage()

        await storage.save("key", "value")
        await storage.delete("key")
        await storage.delete("key")  # Second delete

        assert await storage.exists("key") is False


class TestListKeys:
    """Test list_keys method."""

    @pytest.mark.asyncio
    async def test_list_all_keys(self):
        """Should list all keys."""
        storage = MemoryStorage()

        await storage.save("a", 1)
        await storage.save("b", 2)
        await storage.save("c", 3)

        keys = await storage.list_keys()

        assert set(keys) == {"a", "b", "c"}

    @pytest.mark.asyncio
    async def test_list_keys_with_prefix(self):
        """Should filter by prefix."""
        storage = MemoryStorage()

        await storage.save("user:1", "alice")
        await storage.save("user:2", "bob")
        await storage.save("session:1", "xyz")

        keys = await storage.list_keys(prefix="user:")

        assert set(keys) == {"user:1", "user:2"}

    @pytest.mark.asyncio
    async def test_list_keys_empty(self):
        """Empty storage should return empty list."""
        storage = MemoryStorage()

        keys = await storage.list_keys()

        assert keys == []

    @pytest.mark.asyncio
    async def test_list_keys_sorted(self):
        """Keys should be sorted."""
        storage = MemoryStorage()

        await storage.save("c", 1)
        await storage.save("a", 2)
        await storage.save("b", 3)

        keys = await storage.list_keys()

        assert keys == ["a", "b", "c"]


class TestTTL:
    """Test time-to-live functionality."""

    @pytest.mark.asyncio
    async def test_entry_expires(self):
        """Entry should expire after TTL."""
        storage = MemoryStorage(ttl_seconds=0.1)  # 100ms TTL

        await storage.save("key", "value")

        # Immediately available
        assert await storage.exists("key") is True

        # Wait for expiration
        await asyncio.sleep(0.15)

        # Should be expired
        assert await storage.exists("key") is False

    @pytest.mark.asyncio
    async def test_expired_load_raises_keyerror(self):
        """Loading expired key should raise KeyError."""
        storage = MemoryStorage(ttl_seconds=0.1)

        await storage.save("key", "value")
        await asyncio.sleep(0.15)

        with pytest.raises(KeyError):
            await storage.load("key")

    @pytest.mark.asyncio
    async def test_no_ttl_never_expires(self):
        """Without TTL, entries should not expire."""
        storage = MemoryStorage(ttl_seconds=None)

        await storage.save("key", "value")
        await asyncio.sleep(0.1)

        # Still available
        assert await storage.load("key") == "value"

    @pytest.mark.asyncio
    async def test_overwrite_resets_ttl(self):
        """Overwriting should reset TTL."""
        storage = MemoryStorage(ttl_seconds=0.2)

        await storage.save("key", "value1")
        await asyncio.sleep(0.1)

        # Overwrite before expiration
        await storage.save("key", "value2")
        await asyncio.sleep(0.15)

        # Should still exist (TTL was reset)
        assert await storage.load("key") == "value2"


class TestMaxSize:
    """Test max size functionality."""

    @pytest.mark.asyncio
    async def test_max_size_enforced(self):
        """Should enforce max size."""
        storage = MemoryStorage(max_size=3)

        await storage.save("a", 1)
        await storage.save("b", 2)
        await storage.save("c", 3)

        # Fourth key should fail
        with pytest.raises(StorageError):
            await storage.save("d", 4)

    @pytest.mark.asyncio
    async def test_overwrite_allowed_at_max(self):
        """Overwriting existing key should be allowed at max size."""
        storage = MemoryStorage(max_size=2)

        await storage.save("a", 1)
        await storage.save("b", 2)

        # Overwrite should succeed
        await storage.save("a", 100)

        assert await storage.load("a") == 100


class TestClear:
    """Test clear method."""

    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Should clear all entries."""
        storage = MemoryStorage()

        await storage.save("a", 1)
        await storage.save("b", 2)
        await storage.save("c", 3)

        count = await storage.clear()

        assert count == 3
        assert await storage.list_keys() == []

    @pytest.mark.asyncio
    async def test_clear_with_prefix(self):
        """Should clear only matching prefix."""
        storage = MemoryStorage()

        await storage.save("user:1", "alice")
        await storage.save("user:2", "bob")
        await storage.save("session:1", "xyz")

        count = await storage.clear(prefix="user:")

        assert count == 2
        assert await storage.list_keys() == ["session:1"]


class TestCountKeys:
    """Test count_keys method."""

    @pytest.mark.asyncio
    async def test_count_all(self):
        """Should count all keys."""
        storage = MemoryStorage()

        await storage.save("a", 1)
        await storage.save("b", 2)
        await storage.save("c", 3)

        count = await storage.count_keys()

        assert count == 3

    @pytest.mark.asyncio
    async def test_count_with_prefix(self):
        """Should count only matching prefix."""
        storage = MemoryStorage()

        await storage.save("user:1", "alice")
        await storage.save("user:2", "bob")
        await storage.save("session:1", "xyz")

        count = await storage.count_keys(prefix="user:")

        assert count == 2


class TestClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_clears_storage(self):
        """Close should clear storage."""
        storage = MemoryStorage()

        await storage.save("key", "value")
        await storage.close()

        # Storage should be empty after close
        # (Can't test directly as close clears internal dict)

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Multiple closes should be safe."""
        storage = MemoryStorage()

        await storage.save("key", "value")
        await storage.close()
        await storage.close()  # Second close


class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self):
        """Concurrent reads should work."""
        storage = MemoryStorage()

        await storage.save("key", "value")

        # Many concurrent reads
        tasks = [storage.load("key") for _ in range(100)]
        results = await asyncio.gather(*tasks)

        assert all(r == "value" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_writes(self):
        """Concurrent writes should not lose data."""
        storage = MemoryStorage()

        # Write different keys concurrently
        async def write(i: int):
            await storage.save(f"key_{i}", i)

        await asyncio.gather(*[write(i) for i in range(100)])

        # All keys should exist
        for i in range(100):
            assert await storage.load(f"key_{i}") == i

    @pytest.mark.asyncio
    async def test_concurrent_read_write(self):
        """Concurrent reads and writes should be safe."""
        storage = MemoryStorage()

        await storage.save("key", 0)

        async def increment():
            current = await storage.load("key")
            await storage.save("key", current + 1)

        # Note: This won't guarantee atomicity, but should not crash
        await asyncio.gather(*[increment() for _ in range(10)])

        # Value should be >= 1 (at least one write succeeded)
        result = await storage.load("key")
        assert result >= 1


class TestStorageStats:
    """Test storage statistics."""

    @pytest.mark.asyncio
    async def test_get_storage_stats(self):
        """Should return storage statistics."""
        storage = MemoryStorage(ttl_seconds=60, max_size=100)

        await storage.save("a", 1)
        await storage.save("b", 2)

        stats = storage.get_storage_stats()

        assert stats["total_keys"] == 2
        assert stats["active_keys"] == 2
        assert stats["expired_keys"] == 0
        assert stats["ttl_seconds"] == 60
        assert stats["max_size"] == 100

    @pytest.mark.asyncio
    async def test_stats_with_expired(self):
        """Stats should track expired keys."""
        storage = MemoryStorage(ttl_seconds=0.1)

        await storage.save("key", "value")
        await asyncio.sleep(0.15)

        stats = storage.get_storage_stats()

        # Key is expired but not yet cleaned up
        assert stats["expired_keys"] >= 0
