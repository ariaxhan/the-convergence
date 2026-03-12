"""
Tests for generic PostgreSQL storage implementing StorageProtocol.

Uses real PostgreSQL database — skips if not available.
"""

import os
import pytest

# Skip entire module if asyncpg not available
asyncpg = pytest.importorskip("asyncpg")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def postgres_dsn():
    """Get PostgreSQL DSN from environment or use default."""
    return os.environ.get(
        "TEST_POSTGRES_DSN",
        "postgresql://postgres:postgres@localhost:5432/convergence_test"
    )


@pytest.fixture
async def postgres_storage(postgres_dsn):
    """Create PostgreSQL storage for testing.

    Skips if database not available.
    """
    from convergence.storage.postgres import PostgreSQLStorage

    try:
        storage = PostgreSQLStorage(dsn=postgres_dsn)
        await storage.connect()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")

    yield storage

    # Cleanup: delete test keys
    try:
        test_keys = await storage.list_keys(prefix="test_")
        for key in test_keys:
            await storage.delete(key)
    except Exception:
        pass

    await storage.close()


# =============================================================================
# BASIC STORAGE PROTOCOL TESTS
# =============================================================================


class TestPostgreSQLStorageProtocol:
    """Test PostgreSQLStorage implements StorageProtocol correctly."""

    @pytest.mark.asyncio
    async def test_save_and_load_string(self, postgres_storage):
        """Should save and load string values."""
        await postgres_storage.save("test_string", "hello world")

        result = await postgres_storage.load("test_string")

        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_save_and_load_dict(self, postgres_storage):
        """Should save and load dict values."""
        data = {"name": "test", "values": [1, 2, 3], "nested": {"a": 1}}

        await postgres_storage.save("test_dict", data)

        result = await postgres_storage.load("test_dict")

        assert result == data

    @pytest.mark.asyncio
    async def test_save_and_load_list(self, postgres_storage):
        """Should save and load list values."""
        data = [1, "two", {"three": 3}]

        await postgres_storage.save("test_list", data)

        result = await postgres_storage.load("test_list")

        assert result == data

    @pytest.mark.asyncio
    async def test_save_overwrites(self, postgres_storage):
        """Saving to same key should overwrite."""
        await postgres_storage.save("test_overwrite", "first")
        await postgres_storage.save("test_overwrite", "second")

        result = await postgres_storage.load("test_overwrite")

        assert result == "second"

    @pytest.mark.asyncio
    async def test_load_nonexistent_raises_keyerror(self, postgres_storage):
        """Loading nonexistent key should raise KeyError."""
        with pytest.raises(KeyError):
            await postgres_storage.load("test_nonexistent_key_12345")

    @pytest.mark.asyncio
    async def test_exists_true(self, postgres_storage):
        """Exists should return True for existing key."""
        await postgres_storage.save("test_exists", "value")

        assert await postgres_storage.exists("test_exists") is True

    @pytest.mark.asyncio
    async def test_exists_false(self, postgres_storage):
        """Exists should return False for missing key."""
        assert await postgres_storage.exists("test_not_exists_xyz") is False

    @pytest.mark.asyncio
    async def test_delete(self, postgres_storage):
        """Delete should remove key."""
        await postgres_storage.save("test_delete", "to be deleted")
        assert await postgres_storage.exists("test_delete") is True

        await postgres_storage.delete("test_delete")

        assert await postgres_storage.exists("test_delete") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_silent(self, postgres_storage):
        """Delete nonexistent key should not raise."""
        # Should not raise
        await postgres_storage.delete("test_never_existed_abc")

    @pytest.mark.asyncio
    async def test_list_keys(self, postgres_storage):
        """List keys should return all keys."""
        await postgres_storage.save("test_list_a", "a")
        await postgres_storage.save("test_list_b", "b")
        await postgres_storage.save("test_list_c", "c")

        keys = await postgres_storage.list_keys(prefix="test_list_")

        assert "test_list_a" in keys
        assert "test_list_b" in keys
        assert "test_list_c" in keys

    @pytest.mark.asyncio
    async def test_list_keys_prefix_filter(self, postgres_storage):
        """List keys should filter by prefix."""
        await postgres_storage.save("test_prefix_a", "a")
        await postgres_storage.save("test_prefix_b", "b")
        await postgres_storage.save("test_other_c", "c")

        keys = await postgres_storage.list_keys(prefix="test_prefix_")

        assert "test_prefix_a" in keys
        assert "test_prefix_b" in keys
        assert "test_other_c" not in keys


# =============================================================================
# CONNECTION HANDLING TESTS
# =============================================================================


class TestPostgreSQLConnectionHandling:
    """Test connection management."""

    @pytest.mark.asyncio
    async def test_context_manager(self, postgres_dsn):
        """Should work as async context manager."""
        from convergence.storage.postgres import PostgreSQLStorage

        try:
            async with PostgreSQLStorage(dsn=postgres_dsn) as storage:
                await storage.save("test_context", "value")
                result = await storage.load("test_context")
                assert result == "value"

                await storage.delete("test_context")
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    @pytest.mark.asyncio
    async def test_close_idempotent(self, postgres_storage):
        """Close should be safe to call multiple times."""
        await postgres_storage.close()
        await postgres_storage.close()  # Should not raise


# =============================================================================
# DATA TYPES TESTS
# =============================================================================


class TestPostgreSQLDataTypes:
    """Test various data types are handled correctly."""

    @pytest.mark.asyncio
    async def test_save_none(self, postgres_storage):
        """Should handle None values."""
        await postgres_storage.save("test_none", None)

        result = await postgres_storage.load("test_none")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_bool(self, postgres_storage):
        """Should handle boolean values."""
        await postgres_storage.save("test_true", True)
        await postgres_storage.save("test_false", False)

        assert await postgres_storage.load("test_true") is True
        assert await postgres_storage.load("test_false") is False

    @pytest.mark.asyncio
    async def test_save_float(self, postgres_storage):
        """Should handle float values."""
        await postgres_storage.save("test_float", 3.14159)

        result = await postgres_storage.load("test_float")

        assert abs(result - 3.14159) < 0.0001

    @pytest.mark.asyncio
    async def test_save_large_dict(self, postgres_storage):
        """Should handle large nested structures."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "values": list(range(100)),
                        "strings": [f"item_{i}" for i in range(50)],
                    }
                }
            }
        }

        await postgres_storage.save("test_large", data)

        result = await postgres_storage.load("test_large")

        assert result == data


# =============================================================================
# REGISTRY INTEGRATION TEST
# =============================================================================


class TestPostgreSQLRegistryIntegration:
    """Test PostgreSQL storage integrates with StorageRegistry."""

    @pytest.mark.asyncio
    async def test_registered_in_registry(self):
        """PostgreSQLStorage should be registered in StorageRegistry."""
        from convergence.storage.registry import StorageRegistry

        # Import to trigger registration
        try:
            from convergence.storage.postgres import PostgreSQLStorage  # noqa: F401

            # Check if registered (may fail if asyncpg not available)
            assert StorageRegistry.is_registered("postgres")
        except ImportError:
            pytest.skip("PostgreSQL storage not available")
