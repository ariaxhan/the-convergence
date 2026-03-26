"""
PostgreSQL runtime storage backend for The Armature framework.

Provides persistent storage for runtime decisions and arm state using PostgreSQL.
Implements RuntimeStorageProtocol for multi-armed bandit optimization.

Requires asyncpg for async PostgreSQL operations.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

try:
    import asyncpg
    ASYNCPG_AVAILABLE = True
except ImportError:
    asyncpg = None
    ASYNCPG_AVAILABLE = False


# SQL schema for runtime storage
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS runtime_arms (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    arm_id TEXT NOT NULL,
    params JSONB NOT NULL,
    alpha FLOAT DEFAULT 1.0,
    beta FLOAT DEFAULT 1.0,
    total_pulls INTEGER DEFAULT 0,
    total_reward FLOAT DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, agent_type, arm_id)
);

CREATE TABLE IF NOT EXISTS runtime_decisions (
    id SERIAL PRIMARY KEY,
    decision_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    arm_pulled TEXT NOT NULL,
    strategy_params JSONB,
    arms_snapshot JSONB,
    metadata JSONB,
    reward FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


class PostgreSQLRuntimeStorage:
    """
    PostgreSQL-based runtime storage for multi-armed bandit decisions.

    Implements RuntimeStorageProtocol for:
    - Storing and retrieving arm configurations per user/agent
    - Recording decisions with full context snapshots
    - Updating arm statistics with Bayesian updates

    Features:
    - Connection pooling via asyncpg
    - Automatic schema creation
    - JSONB for flexible parameter storage
    - Idempotent operations (safe to retry)

    Usage:
        async with PostgreSQLRuntimeStorage(dsn="postgresql://...") as storage:
            await storage.initialize_arms(user_id="u1", agent_type="support", arms=[...])
            decision_id = await storage.create_decision(...)
            await storage.update_performance(decision_id=decision_id, reward=1.0, ...)
    """

    def __init__(self, dsn: str):
        """
        Initialize PostgreSQL runtime storage.

        Args:
            dsn: PostgreSQL connection string (e.g., "postgresql://user:pass@host:5432/db")
        """
        if not ASYNCPG_AVAILABLE:
            raise ImportError(
                "asyncpg is required for PostgreSQL storage. "
                "Install with: pip install asyncpg"
            )

        self.dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    @property
    def is_connected(self) -> bool:
        """Check if connection pool is active."""
        return self._pool is not None

    async def connect(self) -> None:
        """
        Establish connection pool and create schema if needed.

        Raises:
            Exception: If connection fails (asyncpg connection errors)
        """
        if self._pool is not None:
            return  # Already connected

        # Create connection pool
        self._pool = await asyncpg.create_pool(self.dsn)

        # Create tables if not exist
        async with self._pool.acquire() as conn:
            await conn.execute(_SCHEMA_SQL)

    async def close(self) -> None:
        """
        Close the connection pool.

        Idempotent - safe to call multiple times.
        """
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception:
                pass  # Ignore errors during close
            finally:
                self._pool = None

    async def __aenter__(self) -> "PostgreSQLRuntimeStorage":
        """Async context manager entry - establishes connection."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit - closes connection."""
        await self.close()

    async def _ensure_connected(self) -> asyncpg.Pool:
        """Ensure connection is established and return pool."""
        if self._pool is None:
            await self.connect()
        assert self._pool is not None
        return self._pool

    # =========================================================================
    # RuntimeStorageProtocol Implementation
    # =========================================================================

    async def get_arms(
        self,
        *,
        user_id: str,
        agent_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Return all arms for the user/agent pair.

        Args:
            user_id: Unique user identifier
            agent_type: Type of agent (e.g., "support", "sales")

        Returns:
            List of arm dictionaries with: arm_id, params, alpha, beta,
            total_pulls, total_reward. Empty list for new users.
        """
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT arm_id, params, alpha, beta, total_pulls, total_reward
                FROM runtime_arms
                WHERE user_id = $1 AND agent_type = $2
                ORDER BY arm_id
                """,
                user_id,
                agent_type,
            )

        return [
            {
                "arm_id": row["arm_id"],
                "params": json.loads(row["params"]) if isinstance(row["params"], str) else row["params"],
                "alpha": row["alpha"],
                "beta": row["beta"],
                "total_pulls": row["total_pulls"],
                "total_reward": row["total_reward"],
            }
            for row in rows
        ]

    async def initialize_arms(
        self,
        *,
        user_id: str,
        agent_type: str,
        arms: List[Dict[str, Any]],
    ) -> int:
        """
        Seed arms for cold-start users (idempotent).

        Args:
            user_id: Unique user identifier
            agent_type: Type of agent
            arms: List of arm configurations with arm_id, params, and optional
                  alpha/beta priors

        Returns:
            Number of arms created (0 if all already exist)
        """
        pool = await self._ensure_connected()
        created_count = 0

        async with pool.acquire() as conn:
            for arm in arms:
                arm_id = arm["arm_id"]
                params = json.dumps(arm.get("params", {}))
                alpha = arm.get("alpha", 1.0)
                beta = arm.get("beta", 1.0)

                # Use ON CONFLICT DO NOTHING for idempotency
                result = await conn.execute(
                    """
                    INSERT INTO runtime_arms (user_id, agent_type, arm_id, params, alpha, beta, total_pulls, total_reward)
                    VALUES ($1, $2, $3, $4, $5, $6, 0, 0.0)
                    ON CONFLICT (user_id, agent_type, arm_id) DO NOTHING
                    """,
                    user_id,
                    agent_type,
                    arm_id,
                    params,
                    alpha,
                    beta,
                )

                # Check if row was inserted
                if result == "INSERT 0 1":
                    created_count += 1

        return created_count

    async def create_decision(
        self,
        *,
        user_id: str,
        agent_type: str,
        arm_pulled: str,
        strategy_params: Dict[str, Any],
        arms_snapshot: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Persist a decision event and return its identifier.

        Args:
            user_id: Unique user identifier
            agent_type: Type of agent
            arm_pulled: ID of the arm that was selected
            strategy_params: Parameters used for this decision
            arms_snapshot: Snapshot of all arm states at decision time
            metadata: Optional additional metadata

        Returns:
            Unique decision_id (UUID string)
        """
        pool = await self._ensure_connected()

        decision_id = str(uuid.uuid4())

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO runtime_decisions
                (decision_id, user_id, agent_type, arm_pulled, strategy_params, arms_snapshot, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                decision_id,
                user_id,
                agent_type,
                arm_pulled,
                json.dumps(strategy_params),
                json.dumps(arms_snapshot),
                json.dumps(metadata) if metadata else None,
            )

        return decision_id

    async def get_decision(
        self,
        *,
        user_id: str,
        decision_id: str,
    ) -> Dict[str, Any]:
        """
        Fetch a recorded decision for auditing or reward calculation.

        Args:
            user_id: Unique user identifier
            decision_id: Decision identifier from create_decision

        Returns:
            Decision details dict with arm_pulled, strategy_params, created_at,
            reward (if recorded), metadata. Empty dict if not found.
        """
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT arm_pulled, strategy_params, arms_snapshot, metadata, reward, created_at
                FROM runtime_decisions
                WHERE decision_id = $1 AND user_id = $2
                """,
                decision_id,
                user_id,
            )

        if row is None:
            return {}

        def parse_json(val: Any) -> Any:
            if val is None:
                return None
            if isinstance(val, str):
                return json.loads(val)
            return val

        return {
            "arm_pulled": row["arm_pulled"],
            "strategy_params": parse_json(row["strategy_params"]),
            "arms_snapshot": parse_json(row["arms_snapshot"]),
            "metadata": parse_json(row["metadata"]),
            "reward": row["reward"],
            "created_at": row["created_at"],
        }

    async def update_performance(
        self,
        *,
        user_id: str,
        agent_type: str,
        decision_id: str,
        reward: float,
        engagement: Optional[float] = None,
        grading: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        computed_update: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Apply a reward update to the selected arm.

        If computed_update is provided, use those pre-computed values instead of
        computing them. This allows the SDK to centralize all Bayesian update
        computation logic.

        Args:
            user_id: Unique user identifier
            agent_type: Type of agent
            decision_id: Decision identifier to update
            reward: Reward value (typically 0.0 to 1.0)
            engagement: Optional engagement signal
            grading: Optional quality grading
            metadata: Optional additional metadata
            computed_update: Optional pre-computed Bayesian update values.
                If provided, should contain: alpha, beta, total_pulls, total_reward.

        Returns:
            True if update was applied successfully
        """
        pool = await self._ensure_connected()

        async with pool.acquire() as conn:
            # Get the decision to find which arm was pulled
            decision = await conn.fetchrow(
                """
                SELECT arm_pulled FROM runtime_decisions
                WHERE decision_id = $1 AND user_id = $2
                """,
                decision_id,
                user_id,
            )

            if decision is None:
                return False

            arm_pulled = decision["arm_pulled"]

            # Update the decision record with reward
            await conn.execute(
                """
                UPDATE runtime_decisions
                SET reward = $1
                WHERE decision_id = $2 AND user_id = $3
                """,
                reward,
                decision_id,
                user_id,
            )

            # Update arm statistics
            if computed_update is not None:
                # Use pre-computed values directly
                await conn.execute(
                    """
                    UPDATE runtime_arms
                    SET alpha = $1,
                        beta = $2,
                        total_pulls = $3,
                        total_reward = $4,
                        updated_at = NOW()
                    WHERE user_id = $5 AND agent_type = $6 AND arm_id = $7
                    """,
                    computed_update.get("alpha", 1.0),
                    computed_update.get("beta", 1.0),
                    computed_update.get("total_pulls", 0),
                    computed_update.get("total_reward", 0.0),
                    user_id,
                    agent_type,
                    arm_pulled,
                )
            else:
                # Simple increment: total_pulls += 1, total_reward += reward
                await conn.execute(
                    """
                    UPDATE runtime_arms
                    SET total_pulls = total_pulls + 1,
                        total_reward = total_reward + $1,
                        updated_at = NOW()
                    WHERE user_id = $2 AND agent_type = $3 AND arm_id = $4
                    """,
                    reward,
                    user_id,
                    agent_type,
                    arm_pulled,
                )

        return True
