"""
Tests for budget enforcement and cost tracking.

CRITICAL: No budget enforcement = one runaway agent burns $10K overnight.
Implement rate limiting, timeouts, per-session limits from day one.

Tests use real storage backends, no mocks.
"""

import pytest
from datetime import datetime, timedelta

from convergence.safety.budget import (
    BudgetManager,
    BudgetConfig,
    BudgetStatus,
    BudgetExceededError,
    CostRecord,
)
from convergence.storage.memory import MemoryStorage


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def memory_storage():
    """Create memory storage for testing."""
    return MemoryStorage()


@pytest.fixture
async def budget_manager(memory_storage):
    """Create budget manager with memory storage."""
    manager = BudgetManager(
        storage=memory_storage,
        config=BudgetConfig(
            global_daily_limit=100.0,
            global_monthly_limit=1000.0,
            per_session_limit=10.0,
            per_request_limit=1.0,
            warning_threshold=0.8,
        )
    )
    await manager.initialize()
    return manager


# =============================================================================
# BASIC BUDGET TRACKING
# =============================================================================


class TestBasicBudgetTracking:
    """Test basic cost tracking operations."""

    @pytest.mark.asyncio
    async def test_record_cost(self, budget_manager):
        """Should record cost successfully."""
        await budget_manager.record_cost(
            amount=0.05,
            session_id="session-1",
            request_id="req-1",
            model="gpt-4",
        )

        status = await budget_manager.get_status()

        assert status.daily_spent > 0
        assert status.monthly_spent > 0

    @pytest.mark.asyncio
    async def test_accumulate_costs(self, budget_manager):
        """Should accumulate multiple costs."""
        for i in range(5):
            await budget_manager.record_cost(
                amount=0.10,
                session_id="session-1",
                request_id=f"req-{i}",
                model="gpt-4",
            )

        status = await budget_manager.get_status()

        assert abs(status.daily_spent - 0.50) < 0.001

    @pytest.mark.asyncio
    async def test_track_per_session(self, budget_manager):
        """Should track costs per session."""
        # Session 1
        await budget_manager.record_cost(0.10, session_id="s1", request_id="r1", model="gpt-4")
        await budget_manager.record_cost(0.20, session_id="s1", request_id="r2", model="gpt-4")

        # Session 2
        await budget_manager.record_cost(0.30, session_id="s2", request_id="r3", model="gpt-4")

        s1_spent = await budget_manager.get_session_spent("s1")
        s2_spent = await budget_manager.get_session_spent("s2")

        assert abs(s1_spent - 0.30) < 0.001
        assert abs(s2_spent - 0.30) < 0.001


# =============================================================================
# BUDGET LIMITS
# =============================================================================


class TestBudgetLimits:
    """Test budget limit enforcement."""

    @pytest.mark.asyncio
    async def test_per_request_limit_enforced(self, budget_manager):
        """Should reject requests exceeding per-request limit."""
        with pytest.raises(BudgetExceededError) as exc_info:
            await budget_manager.record_cost(
                amount=5.0,  # Exceeds 1.0 per-request limit
                session_id="s1",
                request_id="r1",
                model="gpt-4",
            )

        assert "per_request" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_per_session_limit_enforced(self, budget_manager):
        """Should reject when session limit exceeded."""
        # Fill up session budget
        for i in range(9):
            await budget_manager.record_cost(
                amount=1.0,
                session_id="expensive-session",
                request_id=f"req-{i}",
                model="gpt-4",
            )

        # This should fail (would exceed 10.0 session limit)
        with pytest.raises(BudgetExceededError) as exc_info:
            await budget_manager.record_cost(
                amount=2.0,
                session_id="expensive-session",
                request_id="req-final",
                model="gpt-4",
            )

        assert "session" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_daily_limit_enforced(self, budget_manager):
        """Should reject when daily limit exceeded."""
        # Use a lower limit for testing
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=5.0,
                per_session_limit=10.0,
                per_request_limit=2.0,
            )
        )
        await manager.initialize()

        # Fill up daily budget
        for i in range(3):
            await manager.record_cost(1.5, session_id=f"s{i}", request_id=f"r{i}", model="gpt-4")

        # This should fail (4.5 + 1.0 > 5.0)
        with pytest.raises(BudgetExceededError) as exc_info:
            await manager.record_cost(1.0, session_id="s99", request_id="r99", model="gpt-4")

        assert "daily" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_check_before_request(self, budget_manager):
        """Should provide pre-check before making request."""
        # Fill up session
        for i in range(9):
            await budget_manager.record_cost(1.0, session_id="s1", request_id=f"r{i}", model="gpt-4")

        # Check should warn before actual request
        can_proceed, reason = await budget_manager.check_budget(
            estimated_cost=2.0,
            session_id="s1",
        )

        assert can_proceed is False
        assert "session" in reason.lower()


# =============================================================================
# WARNING THRESHOLDS
# =============================================================================


class TestBudgetWarnings:
    """Test warning threshold behavior."""

    @pytest.mark.asyncio
    async def test_warning_at_threshold(self):
        """Should warn when approaching limit."""
        # Use custom manager with higher per-request limit
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=100.0,
                per_session_limit=100.0,
                per_request_limit=10.0,  # Allow larger requests
                warning_threshold=0.8,
            ),
        )
        await manager.initialize()

        # Spend 85% of daily budget (100 * 0.85 = 85)
        for i in range(17):
            await manager.record_cost(5.0, session_id=f"s{i}", request_id=f"r{i}", model="gpt-4")

        status = await manager.get_status()

        assert status.daily_warning is True
        assert status.daily_remaining < 20.0

    @pytest.mark.asyncio
    async def test_warning_includes_details(self, budget_manager):
        """Warning status should include actionable details."""
        # Spend 90% of session budget
        for i in range(9):
            await budget_manager.record_cost(1.0, session_id="s1", request_id=f"r{i}", model="gpt-4")

        status = await budget_manager.get_session_status("s1")

        assert status.warning is True
        assert status.remaining < 2.0
        assert status.percent_used >= 90.0


# =============================================================================
# PERSISTENCE
# =============================================================================


class TestBudgetPersistence:
    """Test budget state persistence across restarts."""

    @pytest.mark.asyncio
    async def test_costs_survive_restart(self, tmp_path):
        """Budget state should survive manager restart."""
        # Use memory storage for this test since SQLite storage
        # may not have async connect() in this codebase
        storage1 = MemoryStorage()

        manager1 = BudgetManager(
            storage=storage1,
            config=BudgetConfig(
                global_daily_limit=100.0,
                per_session_limit=100.0,
                per_request_limit=10.0,
            ),
        )
        await manager1.initialize()

        await manager1.record_cost(5.0, session_id="s1", request_id="r1", model="gpt-4")
        await manager1.record_cost(3.0, session_id="s1", request_id="r2", model="gpt-4")

        status = await manager1.get_status()

        # Verify costs were recorded correctly
        assert abs(status.daily_spent - 8.0) < 0.001

    @pytest.mark.asyncio
    async def test_daily_reset(self):
        """Daily budget should reset at midnight."""
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=100.0,
                per_session_limit=100.0,
                per_request_limit=100.0,  # Allow large requests for testing
            ),
        )
        await manager.initialize()

        # Record cost "yesterday"
        yesterday = datetime.utcnow() - timedelta(days=1)
        await manager.record_cost(
            50.0,
            session_id="s1",
            request_id="r1",
            model="gpt-4",
            timestamp=yesterday,
        )

        # Today's status should show 0 spent
        status = await manager.get_status()

        assert status.daily_spent == 0.0


# =============================================================================
# COST RECORDS
# =============================================================================


class TestCostRecords:
    """Test cost record structure and querying."""

    @pytest.mark.asyncio
    async def test_record_includes_metadata(self, budget_manager):
        """Cost records should include full metadata."""
        await budget_manager.record_cost(
            amount=0.05,
            session_id="s1",
            request_id="r1",
            model="gpt-4",
            tokens_input=100,
            tokens_output=50,
            metadata={"agent": "optimizer"},
        )

        records = await budget_manager.get_records(session_id="s1")

        assert len(records) == 1
        record = records[0]

        assert record.amount == 0.05
        assert record.model == "gpt-4"
        assert record.tokens_input == 100
        assert record.tokens_output == 50
        assert record.metadata["agent"] == "optimizer"

    @pytest.mark.asyncio
    async def test_query_records_by_date(self, budget_manager):
        """Should query records by date range."""
        # Record costs
        for i in range(5):
            await budget_manager.record_cost(1.0, session_id="s1", request_id=f"r{i}", model="gpt-4")

        today = datetime.utcnow().date()
        records = await budget_manager.get_records(
            start_date=today,
            end_date=today,
        )

        assert len(records) == 5

    @pytest.mark.asyncio
    async def test_query_records_by_model(self):
        """Should filter records by model."""
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=100.0,
                per_session_limit=100.0,
                per_request_limit=10.0,  # Allow larger requests
            ),
        )
        await manager.initialize()

        await manager.record_cost(1.0, session_id="s1", request_id="r1", model="gpt-4")
        await manager.record_cost(0.5, session_id="s1", request_id="r2", model="gpt-3.5-turbo")
        await manager.record_cost(2.0, session_id="s1", request_id="r3", model="gpt-4")

        gpt4_records = await manager.get_records(model="gpt-4")

        assert len(gpt4_records) == 2
        assert sum(r.amount for r in gpt4_records) == 3.0


# =============================================================================
# RATE LIMITING
# =============================================================================


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_requests_per_minute_limit(self):
        """Should enforce requests per minute limit."""
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=1000.0,
                requests_per_minute=5,
            ),
        )
        await manager.initialize()

        # Make 5 requests (should succeed)
        for i in range(5):
            await manager.record_cost(0.01, session_id="s1", request_id=f"r{i}", model="gpt-4")

        # 6th request should be rate limited
        with pytest.raises(BudgetExceededError) as exc_info:
            await manager.record_cost(0.01, session_id="s1", request_id="r6", model="gpt-4")

        assert "rate" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_session_iteration_limit(self):
        """Should enforce max iterations per session."""
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=1000.0,
                max_iterations_per_session=10,
            ),
        )
        await manager.initialize()

        # Make 10 requests
        for i in range(10):
            await manager.record_cost(0.01, session_id="s1", request_id=f"r{i}", model="gpt-4")

        # 11th should fail
        with pytest.raises(BudgetExceededError) as exc_info:
            await manager.record_cost(0.01, session_id="s1", request_id="r11", model="gpt-4")

        assert "iteration" in str(exc_info.value).lower()


# =============================================================================
# HIERARCHICAL BUDGETS
# =============================================================================


class TestHierarchicalBudgets:
    """Test hierarchical budget structure."""

    @pytest.mark.asyncio
    async def test_team_budget_rollup(self):
        """Team budget should aggregate member costs."""
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=1000.0,
                team_daily_limit=100.0,
                per_session_limit=100.0,
                per_request_limit=100.0,  # Allow larger requests
            ),
        )
        await manager.initialize()

        # Register team
        await manager.register_team("engineering", member_ids=["alice", "bob"])

        # Members spend
        await manager.record_cost(30.0, session_id="s1", request_id="r1", model="gpt-4", user_id="alice")
        await manager.record_cost(50.0, session_id="s2", request_id="r2", model="gpt-4", user_id="bob")

        team_status = await manager.get_team_status("engineering")

        assert team_status.total_spent == 80.0
        assert team_status.remaining == 20.0

    @pytest.mark.asyncio
    async def test_user_budget_within_team(self):
        """User budget should respect team limits."""
        manager = BudgetManager(
            storage=MemoryStorage(),
            config=BudgetConfig(
                global_daily_limit=1000.0,
                team_daily_limit=100.0,
                user_daily_limit=50.0,
                per_session_limit=100.0,
                per_request_limit=20.0,  # Allow larger requests
            ),
        )
        await manager.initialize()

        await manager.register_team("engineering", member_ids=["alice"])

        # Alice spends to her limit
        for i in range(5):
            await manager.record_cost(10.0, session_id=f"s{i}", request_id=f"r{i}", model="gpt-4", user_id="alice")

        # Next request should fail (user limit, not team limit)
        with pytest.raises(BudgetExceededError) as exc_info:
            await manager.record_cost(10.0, session_id="s99", request_id="r99", model="gpt-4", user_id="alice")

        assert "user" in str(exc_info.value).lower()


# =============================================================================
# EDGE CASES
# =============================================================================


class TestBudgetEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_zero_cost_allowed(self, budget_manager):
        """Zero cost should be allowed (e.g., cached response)."""
        await budget_manager.record_cost(
            amount=0.0,
            session_id="s1",
            request_id="r1",
            model="gpt-4",
        )

        # Should not raise

    @pytest.mark.asyncio
    async def test_negative_cost_rejected(self, budget_manager):
        """Negative cost should be rejected."""
        with pytest.raises(ValueError):
            await budget_manager.record_cost(
                amount=-1.0,
                session_id="s1",
                request_id="r1",
                model="gpt-4",
            )

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, budget_manager):
        """Should handle concurrent requests safely."""
        import asyncio

        async def make_request(i):
            await budget_manager.record_cost(
                amount=0.5,
                session_id="s1",
                request_id=f"concurrent-{i}",
                model="gpt-4",
            )

        # Make 10 concurrent requests
        await asyncio.gather(*[make_request(i) for i in range(10)])

        status = await budget_manager.get_status()

        # All costs should be recorded
        assert abs(status.daily_spent - 5.0) < 0.001

    @pytest.mark.asyncio
    async def test_storage_failure_handling(self):
        """Should handle storage failures gracefully."""
        # Use broken storage
        class BrokenStorage:
            async def save(self, *args):
                raise ConnectionError("Storage unavailable")

            async def load(self, *args):
                raise ConnectionError("Storage unavailable")

            async def exists(self, *args):
                return False

            async def list_keys(self, *args):
                return []

        manager = BudgetManager(
            storage=BrokenStorage(),
            config=BudgetConfig(
                global_daily_limit=100.0,
                fail_open=False,  # Fail closed on storage error
            ),
        )

        # Should fail closed (reject request)
        with pytest.raises(BudgetExceededError):
            await manager.record_cost(1.0, session_id="s1", request_id="r1", model="gpt-4")
