"""Tests for PostgreSQL runtime storage.

Defines expected behavior for PostgreSQL as a RuntimeStorageProtocol backend.
Tests require PostgreSQL - skip gracefully if unavailable.
"""

import pytest
import uuid

from tests.conftest import requires_postgresql


@requires_postgresql
class TestPostgreSQLConnection:
    """Test PostgreSQL connection and setup."""

    @pytest.mark.asyncio
    async def test_connect_creates_schema(self, postgresql_dsn):
        """Connection should auto-create required tables."""
        from armature.storage import PostgreSQLRuntimeStorage

        storage = PostgreSQLRuntimeStorage(dsn=postgresql_dsn)

        try:
            await storage.connect()

            # Tables should exist - verify by querying
            # (implementation will use asyncpg, this tests the interface)
            assert storage.is_connected
        finally:
            await storage.close()

    @pytest.mark.asyncio
    async def test_context_manager(self, postgresql_dsn):
        """Should work as async context manager."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            assert storage.is_connected

        # After context, should be disconnected
        assert not storage.is_connected

    @pytest.mark.asyncio
    async def test_invalid_dsn_raises(self):
        """Invalid DSN should raise connection error."""
        from armature.storage import PostgreSQLRuntimeStorage

        storage = PostgreSQLRuntimeStorage(dsn="postgresql://invalid:5432/nonexistent")

        with pytest.raises(Exception):  # Connection error
            await storage.connect()


@requires_postgresql
class TestRuntimeStorageProtocol:
    """Test implementation of RuntimeStorageProtocol."""

    @pytest.mark.asyncio
    async def test_implements_protocol(self, postgresql_dsn):
        """Should implement RuntimeStorageProtocol."""
        from armature.storage import PostgreSQLRuntimeStorage
        from armature.storage.runtime_protocol import RuntimeStorageProtocol

        storage = PostgreSQLRuntimeStorage(dsn=postgresql_dsn)

        # Check protocol methods exist
        assert hasattr(storage, "get_arms")
        assert hasattr(storage, "initialize_arms")
        assert hasattr(storage, "create_decision")
        assert hasattr(storage, "update_performance")
        assert hasattr(storage, "get_decision")

        # Verify callable
        assert callable(storage.get_arms)
        assert callable(storage.initialize_arms)
        assert callable(storage.create_decision)
        assert callable(storage.update_performance)
        assert callable(storage.get_decision)


@requires_postgresql
class TestGetArms:
    """Test get_arms method."""

    @pytest.mark.asyncio
    async def test_get_arms_empty_for_new_user(self, postgresql_dsn):
        """New user should have no arms."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            arms = await storage.get_arms(user_id=user_id, agent_type="test_agent")

            assert arms == []

    @pytest.mark.asyncio
    async def test_get_arms_returns_initialized(self, postgresql_dsn, sample_arms):
        """Should return arms after initialization."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            arms = await storage.get_arms(user_id=user_id, agent_type=agent_type)

            assert len(arms) == len(sample_arms)
            arm_ids = [a["arm_id"] for a in arms]
            assert "arm_conservative" in arm_ids
            assert "arm_balanced" in arm_ids
            assert "arm_creative" in arm_ids

    @pytest.mark.asyncio
    async def test_get_arms_user_isolation(self, postgresql_dsn, sample_arms):
        """Arms should be isolated per user."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user1 = f"user1_{uuid.uuid4()}"
            user2 = f"user2_{uuid.uuid4()}"
            agent_type = "test_agent"

            # Initialize arms for user1 only
            await storage.initialize_arms(
                user_id=user1,
                agent_type=agent_type,
                arms=sample_arms,
            )

            # User1 should have arms
            arms1 = await storage.get_arms(user_id=user1, agent_type=agent_type)
            assert len(arms1) == len(sample_arms)

            # User2 should have no arms
            arms2 = await storage.get_arms(user_id=user2, agent_type=agent_type)
            assert arms2 == []


@requires_postgresql
class TestInitializeArms:
    """Test initialize_arms method."""

    @pytest.mark.asyncio
    async def test_initialize_arms_creates_arms(self, postgresql_dsn, sample_arms):
        """Should create arms for user."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            result = await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            # Should return some confirmation
            assert result is not None

            # Arms should be retrievable
            arms = await storage.get_arms(user_id=user_id, agent_type=agent_type)
            assert len(arms) == len(sample_arms)

    @pytest.mark.asyncio
    async def test_initialize_arms_idempotent(self, postgresql_dsn, sample_arms):
        """Calling initialize_arms twice should be safe (idempotent)."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            # Initialize twice
            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )
            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            # Should still have correct number of arms (not doubled)
            arms = await storage.get_arms(user_id=user_id, agent_type=agent_type)
            assert len(arms) == len(sample_arms)

    @pytest.mark.asyncio
    async def test_initialize_arms_with_priors(self, postgresql_dsn):
        """Should respect initial alpha/beta priors."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            arms_with_priors = [
                {
                    "arm_id": "arm_1",
                    "params": {"temperature": 0.5},
                    "alpha": 10.0,
                    "beta": 2.0,
                },
            ]

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=arms_with_priors,
            )

            arms = await storage.get_arms(user_id=user_id, agent_type=agent_type)
            assert len(arms) == 1
            assert arms[0]["alpha"] == 10.0
            assert arms[0]["beta"] == 2.0


@requires_postgresql
class TestCreateDecision:
    """Test create_decision method."""

    @pytest.mark.asyncio
    async def test_create_decision_returns_id(self, postgresql_dsn, sample_arms):
        """Should return decision ID."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            decision_id = await storage.create_decision(
                user_id=user_id,
                agent_type=agent_type,
                arm_pulled="arm_balanced",
                strategy_params={"temperature": 0.7},
                arms_snapshot=sample_arms,
            )

            assert decision_id is not None
            assert isinstance(decision_id, str)
            assert len(decision_id) > 0

    @pytest.mark.asyncio
    async def test_create_decision_with_metadata(self, postgresql_dsn, sample_arms):
        """Should store optional metadata."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            metadata = {"context": "test", "request_id": "req_123"}

            decision_id = await storage.create_decision(
                user_id=user_id,
                agent_type=agent_type,
                arm_pulled="arm_balanced",
                strategy_params={"temperature": 0.7},
                arms_snapshot=sample_arms,
                metadata=metadata,
            )

            # Retrieve and verify metadata
            decision = await storage.get_decision(
                user_id=user_id,
                decision_id=decision_id,
            )

            assert decision["metadata"] == metadata


@requires_postgresql
class TestGetDecision:
    """Test get_decision method."""

    @pytest.mark.asyncio
    async def test_get_decision_returns_details(self, postgresql_dsn, sample_arms):
        """Should return full decision details."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            decision_id = await storage.create_decision(
                user_id=user_id,
                agent_type=agent_type,
                arm_pulled="arm_creative",
                strategy_params={"temperature": 1.0},
                arms_snapshot=sample_arms,
            )

            decision = await storage.get_decision(
                user_id=user_id,
                decision_id=decision_id,
            )

            assert decision["arm_pulled"] == "arm_creative"
            assert decision["strategy_params"]["temperature"] == 1.0
            assert "created_at" in decision

    @pytest.mark.asyncio
    async def test_get_decision_not_found(self, postgresql_dsn):
        """Should handle non-existent decision gracefully."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"

            decision = await storage.get_decision(
                user_id=user_id,
                decision_id="nonexistent_decision_id",
            )

            # Should return empty dict or raise KeyError
            assert decision == {} or decision is None


@requires_postgresql
class TestUpdatePerformance:
    """Test update_performance method."""

    @pytest.mark.asyncio
    async def test_update_performance_applies_reward(self, postgresql_dsn, sample_arms):
        """Should update arm stats with reward."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            # Create decision
            decision_id = await storage.create_decision(
                user_id=user_id,
                agent_type=agent_type,
                arm_pulled="arm_balanced",
                strategy_params={"temperature": 0.7},
                arms_snapshot=sample_arms,
            )

            # Update with reward
            await storage.update_performance(
                user_id=user_id,
                agent_type=agent_type,
                decision_id=decision_id,
                reward=1.0,
            )

            # Verify arm was updated
            arms = await storage.get_arms(user_id=user_id, agent_type=agent_type)
            balanced_arm = next(a for a in arms if a["arm_id"] == "arm_balanced")

            assert balanced_arm["total_pulls"] >= 1

    @pytest.mark.asyncio
    async def test_update_performance_with_computed_update(
        self, postgresql_dsn, sample_arms
    ):
        """Should use pre-computed Bayesian updates when provided."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            decision_id = await storage.create_decision(
                user_id=user_id,
                agent_type=agent_type,
                arm_pulled="arm_balanced",
                strategy_params={"temperature": 0.7},
                arms_snapshot=sample_arms,
            )

            # Pre-computed update values
            computed_update = {
                "alpha": 5.0,
                "beta": 2.0,
                "total_pulls": 6,
                "total_reward": 4.5,
                "avg_reward": 0.75,
                "mean_estimate": 0.714,
                "confidence_interval": 0.15,
            }

            await storage.update_performance(
                user_id=user_id,
                agent_type=agent_type,
                decision_id=decision_id,
                reward=1.0,
                computed_update=computed_update,
            )

            # Verify computed values were applied
            arms = await storage.get_arms(user_id=user_id, agent_type=agent_type)
            balanced_arm = next(a for a in arms if a["arm_id"] == "arm_balanced")

            assert balanced_arm["alpha"] == 5.0
            assert balanced_arm["beta"] == 2.0
            assert balanced_arm["total_pulls"] == 6

    @pytest.mark.asyncio
    async def test_update_performance_records_reward(
        self, postgresql_dsn, sample_arms
    ):
        """Reward should be recorded in decision."""
        from armature.storage import PostgreSQLRuntimeStorage

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            decision_id = await storage.create_decision(
                user_id=user_id,
                agent_type=agent_type,
                arm_pulled="arm_balanced",
                strategy_params={"temperature": 0.7},
                arms_snapshot=sample_arms,
            )

            await storage.update_performance(
                user_id=user_id,
                agent_type=agent_type,
                decision_id=decision_id,
                reward=0.8,
            )

            decision = await storage.get_decision(
                user_id=user_id,
                decision_id=decision_id,
            )

            assert decision["reward"] == 0.8


@requires_postgresql
class TestConcurrency:
    """Test concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_decisions(self, postgresql_dsn, sample_arms):
        """Concurrent decision creation should work."""
        from armature.storage import PostgreSQLRuntimeStorage
        import asyncio

        async with PostgreSQLRuntimeStorage(dsn=postgresql_dsn) as storage:
            user_id = f"test_user_{uuid.uuid4()}"
            agent_type = "test_agent"

            await storage.initialize_arms(
                user_id=user_id,
                agent_type=agent_type,
                arms=sample_arms,
            )

            async def create_decision(i: int):
                return await storage.create_decision(
                    user_id=user_id,
                    agent_type=agent_type,
                    arm_pulled=sample_arms[i % len(sample_arms)]["arm_id"],
                    strategy_params={"i": i},
                    arms_snapshot=sample_arms,
                )

            # Create 20 concurrent decisions
            decision_ids = await asyncio.gather(
                *[create_decision(i) for i in range(20)]
            )

            # All should succeed with unique IDs
            assert len(decision_ids) == 20
            assert len(set(decision_ids)) == 20  # All unique
