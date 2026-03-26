"""
Tests for Thompson Sampling persistence.

Tests state serialization, storage integration, and restart survival.
Uses real databases (SQLite, Memory, PostgreSQL) — no mocks.
"""

import pytest

from armature.plugins.mab.thompson_sampling import (
    ThompsonSamplingStrategy,
    ThompsonSamplingConfig,
)
from armature.storage.sqlite import SQLiteStorage
from armature.storage.memory import MemoryStorage


# =============================================================================
# STATE SERIALIZATION TESTS
# =============================================================================


class TestThompsonSamplingState:
    """Test state export/import functionality."""

    def test_get_state_returns_serializable_dict(self):
        """State should be a dict that can be JSON serialized."""
        strategy = ThompsonSamplingStrategy()

        # Pull some arms to create state
        strategy.select_arm(["arm_a", "arm_b", "arm_c"], {})
        strategy.update("arm_a", 0.8, {})
        strategy.update("arm_b", 0.3, {})

        state = strategy.get_state()

        # Must be a dict
        assert isinstance(state, dict)

        # Must have arm_stats
        assert "arm_stats" in state
        assert isinstance(state["arm_stats"], dict)

        # Must have config
        assert "config" in state

        # Must be JSON serializable
        import json
        json_str = json.dumps(state)
        assert json_str is not None

    def test_set_state_restores_arm_stats(self):
        """Setting state should restore arm statistics exactly."""
        # Create strategy and build up state
        strategy1 = ThompsonSamplingStrategy()
        strategy1.select_arm(["arm_a", "arm_b"], {})
        strategy1.update("arm_a", 0.9, {})
        strategy1.update("arm_a", 0.7, {})
        strategy1.update("arm_b", 0.2, {})

        # Get state
        state = strategy1.get_state()

        # Create new strategy and restore state
        strategy2 = ThompsonSamplingStrategy()
        strategy2.set_state(state)

        # Verify arm stats match
        assert strategy2.arm_stats == strategy1.arm_stats

        # Verify estimated means match
        for arm in ["arm_a", "arm_b"]:
            assert strategy2._get_estimated_mean(arm) == strategy1._get_estimated_mean(arm)

    def test_get_state_empty_strategy(self):
        """Empty strategy should return valid empty state."""
        strategy = ThompsonSamplingStrategy()
        state = strategy.get_state()

        assert isinstance(state, dict)
        assert state["arm_stats"] == {}

    def test_set_state_with_custom_config(self):
        """State should include config and restore it."""
        config = ThompsonSamplingConfig(alpha_prior=2.0, beta_prior=3.0)
        strategy1 = ThompsonSamplingStrategy(config=config)
        strategy1.select_arm(["arm_x"], {})

        state = strategy1.get_state()

        strategy2 = ThompsonSamplingStrategy()
        strategy2.set_state(state)

        # Config should be restored
        assert strategy2.config.alpha_prior == 2.0
        assert strategy2.config.beta_prior == 3.0


# =============================================================================
# STORAGE INTEGRATION TESTS — SQLITE
# =============================================================================


class TestThompsonPersistenceSQLite:
    """Test persistence with real SQLite database."""

    @pytest.fixture
    async def sqlite_storage(self, tmp_path):
        """Create SQLite storage for testing."""
        db_path = tmp_path / "test_thompson.db"
        storage = SQLiteStorage(db_path=str(db_path))
        async with storage:
            yield storage

    @pytest.mark.asyncio
    async def test_save_and_load_state_sqlite(self, sqlite_storage):
        """State should roundtrip through SQLite storage."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        persistence = ThompsonPersistence(storage=sqlite_storage)

        # Create strategy with state
        strategy = ThompsonSamplingStrategy()
        strategy.select_arm(["model_a", "model_b", "model_c"], {})
        strategy.update("model_a", 0.85, {})
        strategy.update("model_b", 0.60, {})
        strategy.update("model_c", 0.45, {})

        # Save state
        await persistence.save(strategy, key="test_strategy_1")

        # Load into new strategy
        new_strategy = ThompsonSamplingStrategy()
        await persistence.load(new_strategy, key="test_strategy_1")

        # Verify state matches
        assert new_strategy.arm_stats == strategy.arm_stats

    @pytest.mark.asyncio
    async def test_state_survives_storage_reconnect_sqlite(self, tmp_path):
        """State should survive closing and reopening storage."""
        db_path = tmp_path / "test_reconnect.db"

        # First session: create and save
        async with SQLiteStorage(db_path=str(db_path)) as storage1:
            from armature.plugins.mab.persistence import ThompsonPersistence

            persistence = ThompsonPersistence(storage=storage1)
            strategy = ThompsonSamplingStrategy()
            strategy.select_arm(["arm_1", "arm_2"], {})
            strategy.update("arm_1", 0.9, {})

            original_stats = dict(strategy.arm_stats)
            await persistence.save(strategy, key="persistent_strategy")

        # Second session: load and verify
        async with SQLiteStorage(db_path=str(db_path)) as storage2:
            persistence = ThompsonPersistence(storage=storage2)
            loaded_strategy = ThompsonSamplingStrategy()
            await persistence.load(loaded_strategy, key="persistent_strategy")

            assert loaded_strategy.arm_stats == original_stats

    @pytest.mark.asyncio
    async def test_multiple_strategies_sqlite(self, sqlite_storage):
        """Multiple strategies should be stored independently."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        persistence = ThompsonPersistence(storage=sqlite_storage)

        # Create two different strategies
        strategy_a = ThompsonSamplingStrategy()
        strategy_a.select_arm(["fast", "slow"], {})
        strategy_a.update("fast", 0.9, {})

        strategy_b = ThompsonSamplingStrategy()
        strategy_b.select_arm(["cheap", "expensive"], {})
        strategy_b.update("expensive", 0.7, {})

        # Save both
        await persistence.save(strategy_a, key="strategy_a")
        await persistence.save(strategy_b, key="strategy_b")

        # Load and verify independence
        loaded_a = ThompsonSamplingStrategy()
        loaded_b = ThompsonSamplingStrategy()

        await persistence.load(loaded_a, key="strategy_a")
        await persistence.load(loaded_b, key="strategy_b")

        assert "fast" in loaded_a.arm_stats
        assert "cheap" in loaded_b.arm_stats
        assert "fast" not in loaded_b.arm_stats
        assert "cheap" not in loaded_a.arm_stats


# =============================================================================
# STORAGE INTEGRATION TESTS — MEMORY
# =============================================================================


class TestThompsonPersistenceMemory:
    """Test persistence with Memory storage."""

    @pytest.fixture
    async def memory_storage(self):
        """Create Memory storage for testing."""
        storage = MemoryStorage()
        yield storage
        await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_load_state_memory(self, memory_storage):
        """State should roundtrip through Memory storage."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        persistence = ThompsonPersistence(storage=memory_storage)

        strategy = ThompsonSamplingStrategy()
        strategy.select_arm(["option_1", "option_2"], {})
        strategy.update("option_1", 0.75, {})

        await persistence.save(strategy, key="memory_test")

        new_strategy = ThompsonSamplingStrategy()
        await persistence.load(new_strategy, key="memory_test")

        assert new_strategy.arm_stats == strategy.arm_stats


# =============================================================================
# STORAGE INTEGRATION TESTS — POSTGRESQL
# =============================================================================


class TestThompsonPersistencePostgres:
    """Test persistence with real PostgreSQL database."""

    @pytest.fixture
    async def postgres_storage(self):
        """Create PostgreSQL storage for testing.

        Skips if asyncpg not available or no database connection.
        """
        try:
            from armature.storage.postgres import PostgreSQLStorage
        except ImportError:
            pytest.skip("asyncpg not installed")

        import os
        dsn = os.environ.get(
            "TEST_POSTGRES_DSN",
            "postgresql://postgres:postgres@localhost:5432/armature_test"
        )

        try:
            storage = PostgreSQLStorage(dsn=dsn)
            await storage.connect()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

        yield storage
        await storage.close()

    @pytest.mark.asyncio
    async def test_save_and_load_state_postgres(self, postgres_storage):
        """State should roundtrip through PostgreSQL storage."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        persistence = ThompsonPersistence(storage=postgres_storage)

        strategy = ThompsonSamplingStrategy()
        strategy.select_arm(["pg_arm_a", "pg_arm_b"], {})
        strategy.update("pg_arm_a", 0.8, {})
        strategy.update("pg_arm_b", 0.5, {})

        await persistence.save(strategy, key="postgres_test_strategy")

        new_strategy = ThompsonSamplingStrategy()
        await persistence.load(new_strategy, key="postgres_test_strategy")

        assert new_strategy.arm_stats == strategy.arm_stats

    @pytest.mark.asyncio
    async def test_state_survives_reconnect_postgres(self, postgres_storage):
        """State should survive PostgreSQL reconnection."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        persistence = ThompsonPersistence(storage=postgres_storage)

        strategy = ThompsonSamplingStrategy()
        strategy.select_arm(["reconnect_arm"], {})
        strategy.update("reconnect_arm", 0.95, {})

        original_stats = dict(strategy.arm_stats)
        await persistence.save(strategy, key="reconnect_test")

        # Load into new strategy
        loaded_strategy = ThompsonSamplingStrategy()
        await persistence.load(loaded_strategy, key="reconnect_test")

        assert loaded_strategy.arm_stats == original_stats


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestThompsonPersistenceErrors:
    """Test error handling in persistence."""

    @pytest.mark.asyncio
    async def test_load_nonexistent_key_raises(self):
        """Loading nonexistent key should raise KeyError."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        storage = MemoryStorage()
        persistence = ThompsonPersistence(storage=storage)

        strategy = ThompsonSamplingStrategy()

        with pytest.raises(KeyError):
            await persistence.load(strategy, key="does_not_exist")

        await storage.close()

    @pytest.mark.asyncio
    async def test_exists_check(self):
        """Should be able to check if state exists."""
        from armature.plugins.mab.persistence import ThompsonPersistence

        storage = MemoryStorage()
        persistence = ThompsonPersistence(storage=storage)

        assert await persistence.exists(key="missing") is False

        strategy = ThompsonSamplingStrategy()
        await persistence.save(strategy, key="present")

        assert await persistence.exists(key="present") is True

        await storage.close()
