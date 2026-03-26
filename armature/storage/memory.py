"""
In-memory storage backend for The Armature framework.

Provides fast, non-persistent storage using Python dict.
Perfect for testing and development scenarios.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from armature.storage.base import (
    StorageError,
)


class MemoryStorage:
    """
    In-memory storage implementation.

    Features:
    - Fast dict-based storage
    - Optional TTL (time-to-live) support
    - Thread-safe with asyncio.Lock
    - Non-persistent (data lost on restart)

    Good for:
    - Unit testing
    - Integration testing
    - Development
    - Temporary data
    - High-performance caching

    Not recommended for:
    - Production data (not persistent)
    - Large datasets (limited by RAM)
    - Multi-process scenarios (not shared)

    Usage:
        storage = MemoryStorage(ttl_seconds=300)  # 5 min TTL
        await storage.save("agent:1", agent_data)
        data = await storage.load("agent:1")
    """

    def __init__(
        self,
        ttl_seconds: Optional[int] = None,
        max_size: Optional[int] = None
    ):
        """
        Initialize in-memory storage.

        Args:
            ttl_seconds: Optional time-to-live for entries (seconds)
                        None means entries never expire
            max_size: Optional maximum number of entries
                     None means unlimited size
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size

        # Storage: key -> (value, expiry_time)
        self._storage: Dict[str, tuple[Any, Optional[datetime]]] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._cleanup_started = False

    def _ensure_cleanup_started(self) -> None:
        """Ensure cleanup task is started (lazy initialization)."""
        if self.ttl_seconds is not None and not self._cleanup_started:
            try:
                # Only start if we have an event loop
                loop = asyncio.get_running_loop()
                if loop is not None and self._cleanup_task is None:
                    self._cleanup_task = asyncio.create_task(self._cleanup_expired())
                    self._cleanup_started = True
            except RuntimeError:
                # No event loop running yet - will start on first async operation
                pass

    async def _cleanup_expired(self) -> None:
        """Background task to periodically remove expired entries."""
        try:
            while True:
                # Run cleanup every minute or half of TTL, whichever is smaller
                cleanup_interval = min(60, (self.ttl_seconds or 60) / 2)
                await asyncio.sleep(cleanup_interval)

                async with self._lock:
                    now = datetime.utcnow()
                    expired_keys = [
                        key for key, (_, expiry) in self._storage.items()
                        if expiry is not None and expiry <= now
                    ]

                    for key in expired_keys:
                        del self._storage[key]

        except asyncio.CancelledError:
            pass  # Task was cancelled during shutdown

    def _calculate_expiry(self) -> Optional[datetime]:
        """Calculate expiry time for new entries."""
        if self.ttl_seconds is None:
            return None
        return datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

    def _is_expired(self, expiry: Optional[datetime]) -> bool:
        """Check if entry is expired."""
        if expiry is None:
            return False
        return expiry <= datetime.utcnow()

    async def save(self, key: str, value: Any) -> None:
        """
        Save a value with a key.

        Args:
            key: Unique identifier
            value: Python object to store (kept in memory as-is)

        Raises:
            StorageError: If max_size exceeded
        """
        self._ensure_cleanup_started()
        async with self._lock:
            # Check size limit
            if self.max_size is not None and len(self._storage) >= self.max_size:
                if key not in self._storage:  # Only error on new keys
                    raise StorageError(
                        f"Storage full: max size {self.max_size} reached"
                    )

            # Calculate expiry
            expiry = self._calculate_expiry()

            # Store value with expiry
            self._storage[key] = (value, expiry)

    async def load(self, key: str) -> Any:
        """
        Load a value by key.

        Args:
            key: Unique identifier

        Returns:
            Stored Python object

        Raises:
            KeyError: If key doesn't exist or has expired
        """
        self._ensure_cleanup_started()
        async with self._lock:
            if key not in self._storage:
                raise KeyError(f"Key not found: {key}")

            value, expiry = self._storage[key]

            # Check expiry
            if self._is_expired(expiry):
                # Remove expired entry
                del self._storage[key]
                raise KeyError(f"Key expired: {key}")

            return value

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists and is not expired.

        Args:
            key: Unique identifier

        Returns:
            True if key exists and not expired, False otherwise
        """
        self._ensure_cleanup_started()
        async with self._lock:
            if key not in self._storage:
                return False

            _, expiry = self._storage[key]

            # Check expiry
            if self._is_expired(expiry):
                # Remove expired entry
                del self._storage[key]
                return False

            return True

    async def delete(self, key: str) -> None:
        """
        Delete a key.

        Args:
            key: Unique identifier

        Note:
            Silently succeeds if key doesn't exist (idempotent).
        """
        async with self._lock:
            if key in self._storage:
                del self._storage[key]

    async def list_keys(self, prefix: str = "") -> List[str]:
        """
        List all keys, optionally filtered by prefix.

        Expired keys are automatically excluded.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of matching keys
        """
        self._ensure_cleanup_started()
        async with self._lock:
            now = datetime.utcnow()
            keys = []

            for key, (_, expiry) in self._storage.items():
                # Skip expired entries
                if expiry is not None and expiry <= now:
                    continue

                # Filter by prefix
                if not prefix or key.startswith(prefix):
                    keys.append(key)

            return sorted(keys)

    async def close(self) -> None:
        """
        Clean up resources.

        Cancels background cleanup task and clears storage.
        Idempotent - safe to call multiple times.
        """
        # Cancel cleanup task
        if self._cleanup_task is not None:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # Clear storage
        async with self._lock:
            self._storage.clear()

    # Additional utility methods

    async def count_keys(self, prefix: str = "") -> int:
        """
        Count keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            Number of matching keys
        """
        keys = await self.list_keys(prefix)
        return len(keys)

    async def clear(self, prefix: str = "") -> int:
        """
        Delete all keys, optionally filtered by prefix.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            Number of keys deleted
        """
        keys = await self.list_keys(prefix)

        for key in keys:
            await self.delete(key)

        return len(keys)

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dict with stats (total_keys, expired_keys, memory_usage_estimate)
        """
        now = datetime.utcnow()

        total_keys = len(self._storage)
        expired_keys = sum(
            1 for _, (_, expiry) in self._storage.items()
            if expiry is not None and expiry <= now
        )

        return {
            "total_keys": total_keys,
            "active_keys": total_keys - expired_keys,
            "expired_keys": expired_keys,
            "ttl_seconds": self.ttl_seconds,
            "max_size": self.max_size,
        }


class MemoryRuntimeStorage:
    """
    In-memory implementation of RuntimeStorageProtocol.

    Stores arms, decisions, and performance updates in Python dicts.
    Ideal for examples, testing, and development -- no external dependencies.

    Usage:
        storage = MemoryRuntimeStorage()
        await configure_runtime("my_system", config=config, storage=storage)
    """

    def __init__(self) -> None:
        # arms[(user_id, agent_type)] -> list of arm dicts
        self._arms: Dict[tuple, List[Dict[str, Any]]] = {}
        # decisions[decision_id] -> decision dict
        self._decisions: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    async def get_arms(self, *, user_id: str, agent_type: str) -> List[Any]:
        return list(self._arms.get((user_id, agent_type), []))

    async def initialize_arms(
        self,
        *,
        user_id: str,
        agent_type: str,
        arms: List[Dict[str, Any]],
    ) -> Any:
        key = (user_id, agent_type)
        if key not in self._arms:
            self._arms[key] = [
                {
                    "arm_id": a["arm_id"],
                    "name": a.get("name"),
                    "params": a.get("params", {}),
                    "alpha": 1.0,
                    "beta": 1.0,
                    "total_pulls": 0,
                    "total_reward": 0.0,
                    "mean_estimate": None,
                    "avg_reward": None,
                    "metadata": a.get("metadata", {}),
                }
                for a in arms
            ]

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
        self._counter += 1
        decision_id = f"dec_{self._counter}"
        self._decisions[decision_id] = {
            "decision_id": decision_id,
            "user_id": user_id,
            "agent_type": agent_type,
            "arm_id": arm_pulled,
            "params": strategy_params,
            "arms_snapshot": arms_snapshot,
            "metadata": metadata or {},
        }
        return decision_id

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
    ) -> Any:
        decision = self._decisions.get(decision_id)
        if not decision:
            return {"success": False}
        arm_id = decision["arm_id"]
        key = (user_id, agent_type)
        arms = self._arms.get(key, [])
        for arm in arms:
            if arm["arm_id"] == arm_id:
                if computed_update:
                    arm["alpha"] = computed_update.get("alpha", arm["alpha"])
                    arm["beta"] = computed_update.get("beta", arm["beta"])
                    arm["total_pulls"] = computed_update.get(
                        "total_pulls", arm["total_pulls"]
                    )
                    arm["total_reward"] = computed_update.get(
                        "total_reward", arm["total_reward"]
                    )
                    arm["mean_estimate"] = computed_update.get("mean_estimate")
                    arm["avg_reward"] = computed_update.get("avg_reward")
                else:
                    arm["alpha"] += reward
                    arm["beta"] += 1.0 - reward
                    arm["total_pulls"] += 1
                    arm["total_reward"] += reward
                    pulls = arm["total_pulls"]
                    arm["avg_reward"] = arm["total_reward"] / pulls if pulls else 0
                    arm["mean_estimate"] = arm["alpha"] / (
                        arm["alpha"] + arm["beta"]
                    )
                break
        return {"success": True}

    async def get_decision(
        self, *, user_id: str, decision_id: str
    ) -> Dict[str, Any]:
        return self._decisions.get(decision_id, {})


# Note: Protocol verification is done via type checking at runtime
# MemoryStorage implements StorageProtocol via structural subtyping

