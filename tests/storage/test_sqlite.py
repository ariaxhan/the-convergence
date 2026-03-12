"""Tests for SQLite storage backend.

This is the default persistent storage - must be reliable.
"""

import pytest
import asyncio
from pathlib import Path

from convergence.storage.sqlite import SQLiteStorage
from convergence.storage.base import StorageError, StorageConnectionError


class TestSQLiteStorageBasics:
    """Test basic storage operations."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, tmp_path):
        """Should save and load values."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key1", {"value": 42})
            result = await storage.load("key1")

            assert result == {"value": 42}

    @pytest.mark.asyncio
    async def test_load_nonexistent_raises_keyerror(self, tmp_path):
        """Loading nonexistent key should raise KeyError."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            with pytest.raises(KeyError):
                await storage.load("nonexistent")

    @pytest.mark.asyncio
    async def test_overwrite_value(self, tmp_path):
        """Should overwrite existing values."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value1")
            await storage.save("key", "value2")
            result = await storage.load("key")

            assert result == "value2"

    @pytest.mark.asyncio
    async def test_store_various_types(self, tmp_path):
        """Should store various Python types."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
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


class TestPersistence:
    """Test data persistence across sessions."""

    @pytest.mark.asyncio
    async def test_data_persists_after_close(self, tmp_path):
        """Data should persist after closing and reopening."""
        db_path = tmp_path / "test.db"

        # First session - write data
        async with SQLiteStorage(db_path) as storage:
            await storage.save("persistent", "I survive!")

        # Second session - read data
        async with SQLiteStorage(db_path) as storage:
            result = await storage.load("persistent")
            assert result == "I survive!"

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, tmp_path):
        """Multiple sessions should work correctly."""
        db_path = tmp_path / "test.db"

        # Session 1
        async with SQLiteStorage(db_path) as storage:
            await storage.save("key1", "value1")

        # Session 2
        async with SQLiteStorage(db_path) as storage:
            await storage.save("key2", "value2")
            assert await storage.load("key1") == "value1"

        # Session 3
        async with SQLiteStorage(db_path) as storage:
            assert await storage.load("key1") == "value1"
            assert await storage.load("key2") == "value2"


class TestContextManager:
    """Test async context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_connects(self, tmp_path):
        """Context manager should establish connection."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            # Connection should be established
            assert storage._conn is not None

    @pytest.mark.asyncio
    async def test_context_manager_closes(self, tmp_path):
        """Context manager should close connection on exit."""
        db_path = tmp_path / "test.db"

        storage = SQLiteStorage(db_path)
        async with storage:
            pass

        # Connection should be closed
        assert storage._conn is None

    @pytest.mark.asyncio
    async def test_context_manager_closes_on_error(self, tmp_path):
        """Context manager should close connection even on error."""
        db_path = tmp_path / "test.db"

        storage = SQLiteStorage(db_path)

        with pytest.raises(ValueError):
            async with storage:
                raise ValueError("Test error")

        # Connection should be closed
        assert storage._conn is None


class TestExists:
    """Test exists method."""

    @pytest.mark.asyncio
    async def test_exists_true(self, tmp_path):
        """Should return True for existing key."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value")
            assert await storage.exists("key") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, tmp_path):
        """Should return False for nonexistent key."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            assert await storage.exists("nonexistent") is False


class TestDelete:
    """Test delete method."""

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, tmp_path):
        """Delete should remove the key."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value")
            await storage.delete("key")

            assert await storage.exists("key") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_no_error(self, tmp_path):
        """Delete nonexistent key should not raise error."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            # Should not raise
            await storage.delete("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_persists(self, tmp_path):
        """Deletion should persist across sessions."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value")
            await storage.delete("key")

        async with SQLiteStorage(db_path) as storage:
            assert await storage.exists("key") is False


class TestListKeys:
    """Test list_keys method."""

    @pytest.mark.asyncio
    async def test_list_all_keys(self, tmp_path):
        """Should list all keys."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("a", 1)
            await storage.save("b", 2)
            await storage.save("c", 3)

            keys = await storage.list_keys()

            assert set(keys) == {"a", "b", "c"}

    @pytest.mark.asyncio
    async def test_list_keys_with_prefix(self, tmp_path):
        """Should filter by prefix."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("user:1", "alice")
            await storage.save("user:2", "bob")
            await storage.save("session:1", "xyz")

            keys = await storage.list_keys(prefix="user:")

            assert set(keys) == {"user:1", "user:2"}

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, tmp_path):
        """Empty storage should return empty list."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            keys = await storage.list_keys()
            assert keys == []

    @pytest.mark.asyncio
    async def test_list_keys_sorted(self, tmp_path):
        """Keys should be sorted."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("c", 1)
            await storage.save("a", 2)
            await storage.save("b", 3)

            keys = await storage.list_keys()

            assert keys == ["a", "b", "c"]


class TestCountKeys:
    """Test count_keys method."""

    @pytest.mark.asyncio
    async def test_count_all(self, tmp_path):
        """Should count all keys."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("a", 1)
            await storage.save("b", 2)
            await storage.save("c", 3)

            count = await storage.count_keys()

            assert count == 3

    @pytest.mark.asyncio
    async def test_count_with_prefix(self, tmp_path):
        """Should count only matching prefix."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("user:1", "alice")
            await storage.save("user:2", "bob")
            await storage.save("session:1", "xyz")

            count = await storage.count_keys(prefix="user:")

            assert count == 2


class TestClear:
    """Test clear method."""

    @pytest.mark.asyncio
    async def test_clear_all(self, tmp_path):
        """Should clear all entries."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("a", 1)
            await storage.save("b", 2)
            await storage.save("c", 3)

            count = await storage.clear()

            assert count == 3
            assert await storage.list_keys() == []

    @pytest.mark.asyncio
    async def test_clear_with_prefix(self, tmp_path):
        """Should clear only matching prefix."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("user:1", "alice")
            await storage.save("user:2", "bob")
            await storage.save("session:1", "xyz")

            count = await storage.clear(prefix="user:")

            assert count == 2
            assert await storage.list_keys() == ["session:1"]


class TestSerialization:
    """Test serialization options."""

    @pytest.mark.asyncio
    async def test_pickle_serializer(self, tmp_path):
        """Pickle serializer should work."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path, serializer="pickle") as storage:
            # Pickle can handle complex objects
            data = {"nested": {"list": [1, 2, 3]}, "tuple": (1, 2)}
            await storage.save("complex", data)

            result = await storage.load("complex")
            assert result == data

    @pytest.mark.asyncio
    async def test_json_serializer(self, tmp_path):
        """JSON serializer should work."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path, serializer="json") as storage:
            data = {"key": "value", "number": 42}
            await storage.save("json_data", data)

            result = await storage.load("json_data")
            assert result == data

    @pytest.mark.asyncio
    async def test_json_serializer_limitations(self, tmp_path):
        """JSON serializer should fail on non-JSON types."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path, serializer="json") as storage:
            # Tuples become lists in JSON
            await storage.save("tuple", (1, 2, 3))
            result = await storage.load("tuple")
            assert result == [1, 2, 3]  # Tuple becomes list


class TestTableName:
    """Test custom table name support."""

    @pytest.mark.asyncio
    async def test_custom_table_name(self, tmp_path):
        """Should support custom table names."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path, table_name="custom_table") as storage:
            await storage.save("key", "value")
            result = await storage.load("key")
            assert result == "value"

    @pytest.mark.asyncio
    async def test_table_isolation(self, tmp_path):
        """Different table names should be isolated."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path, table_name="table1") as storage1:
            await storage1.save("key", "value1")

        async with SQLiteStorage(db_path, table_name="table2") as storage2:
            # table2 should not see table1's data
            assert await storage2.exists("key") is False


class TestClose:
    """Test close method."""

    @pytest.mark.asyncio
    async def test_close_idempotent(self, tmp_path):
        """Multiple closes should be safe."""
        db_path = tmp_path / "test.db"

        storage = SQLiteStorage(db_path)
        await storage._connect()
        await storage.close()
        await storage.close()  # Second close should not raise


class TestAutoConnect:
    """Test automatic connection handling."""

    @pytest.mark.asyncio
    async def test_auto_connect_on_save(self, tmp_path):
        """Should auto-connect on save."""
        db_path = tmp_path / "test.db"

        storage = SQLiteStorage(db_path)
        try:
            await storage.save("key", "value")
            assert storage._conn is not None
        finally:
            await storage.close()

    @pytest.mark.asyncio
    async def test_auto_connect_on_load(self, tmp_path):
        """Should auto-connect on load."""
        db_path = tmp_path / "test.db"

        # First, create some data
        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value")

        # Then test auto-connect
        storage = SQLiteStorage(db_path)
        try:
            result = await storage.load("key")
            assert result == "value"
            assert storage._conn is not None
        finally:
            await storage.close()


class TestDirectoryCreation:
    """Test automatic directory creation."""

    @pytest.mark.asyncio
    async def test_creates_parent_directory(self, tmp_path):
        """Should create parent directories."""
        db_path = tmp_path / "nested" / "deep" / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value")

        assert db_path.exists()


class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, tmp_path):
        """Concurrent reads should work."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            await storage.save("key", "value")

            # Many concurrent reads
            tasks = [storage.load("key") for _ in range(50)]
            results = await asyncio.gather(*tasks)

            assert all(r == "value" for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, tmp_path):
        """Concurrent writes should not lose data."""
        db_path = tmp_path / "test.db"

        async with SQLiteStorage(db_path) as storage:
            # Write different keys concurrently
            async def write(i: int):
                await storage.save(f"key_{i}", i)

            await asyncio.gather(*[write(i) for i in range(50)])

            # All keys should exist
            for i in range(50):
                assert await storage.load(f"key_{i}") == i


class TestMemoryDatabase:
    """Test in-memory database support."""

    @pytest.mark.asyncio
    async def test_memory_database(self):
        """Should support :memory: database."""
        async with SQLiteStorage(":memory:") as storage:
            await storage.save("key", "value")
            result = await storage.load("key")
            assert result == "value"
