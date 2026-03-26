"""
Persistence layer for Thompson Sampling MAB strategy.

Provides storage-agnostic persistence for Thompson Sampling state.
Works with any storage backend implementing StorageProtocol.
"""

from typing import Any

from armature.storage.base import StorageProtocol


class ThompsonPersistence:
    """
    Storage-agnostic persistence for Thompson Sampling strategies.

    Handles saving and loading Thompson Sampling state to any storage
    backend implementing StorageProtocol.

    Usage:
        from armature.storage.sqlite import SQLiteStorage
        from armature.plugins.mab.thompson_sampling import ThompsonSamplingStrategy

        async with SQLiteStorage("./data/mab.db") as storage:
            persistence = ThompsonPersistence(storage=storage)

            # Save state
            strategy = ThompsonSamplingStrategy()
            strategy.select_arm(["arm_a", "arm_b"], {})
            strategy.update("arm_a", 0.8, {})
            await persistence.save(strategy, key="my_strategy")

            # Load state
            new_strategy = ThompsonSamplingStrategy()
            await persistence.load(new_strategy, key="my_strategy")
    """

    KEY_PREFIX = "mab:thompson:"

    def __init__(self, storage: StorageProtocol):
        """
        Initialize Thompson persistence.

        Args:
            storage: Any storage backend implementing StorageProtocol
        """
        self.storage = storage

    def _make_key(self, key: str) -> str:
        """Create full storage key with prefix."""
        return f"{self.KEY_PREFIX}{key}"

    async def save(self, strategy: Any, key: str) -> None:
        """
        Save Thompson Sampling strategy state to storage.

        Args:
            strategy: ThompsonSamplingStrategy instance
            key: Unique identifier for this strategy

        Raises:
            StorageError: If save operation fails
        """
        state = strategy.get_state()
        await self.storage.save(self._make_key(key), state)

    async def load(self, strategy: Any, key: str) -> None:
        """
        Load Thompson Sampling strategy state from storage.

        Args:
            strategy: ThompsonSamplingStrategy instance to restore into
            key: Unique identifier for the strategy

        Raises:
            KeyError: If key doesn't exist
            StorageError: If load operation fails
        """
        state = await self.storage.load(self._make_key(key))
        strategy.set_state(state)

    async def exists(self, key: str) -> bool:
        """
        Check if strategy state exists in storage.

        Args:
            key: Unique identifier for the strategy

        Returns:
            True if state exists, False otherwise
        """
        return await self.storage.exists(self._make_key(key))

    async def delete(self, key: str) -> None:
        """
        Delete strategy state from storage.

        Args:
            key: Unique identifier for the strategy

        Note:
            Silently succeeds if key doesn't exist.
        """
        await self.storage.delete(self._make_key(key))

    async def list_strategies(self) -> list[str]:
        """
        List all saved strategy keys.

        Returns:
            List of strategy keys (without prefix)
        """
        full_keys = await self.storage.list_keys(self.KEY_PREFIX)
        prefix_len = len(self.KEY_PREFIX)
        return [key[prefix_len:] for key in full_keys]


__all__ = ['ThompsonPersistence']
