"""
Storage abstraction for The Convergence framework.

Provides pluggable storage backends via Protocol-based design.
Users can bring their own storage by implementing StorageProtocol.

LEGACY SYSTEM:
The multi-backend storage and legacy manager ensure data is NEVER lost.
Every episode, every insight, every best method is preserved forever.
This is how knowledge passes between generations.
"""

from convergence.storage.base import (
    StorageConfig,
    StorageConnectionError,
    StorageError,
    StorageNotFoundError,
    StorageProtocol,
)
from convergence.storage.file import FileStorage
from convergence.storage.legacy_manager import (
    LegacyManager,
    create_agent_from_legacy,
)
from convergence.storage.memory import MemoryStorage
from convergence.storage.multi_backend import (
    MultiBackendStorage,
    get_legacy_storage,
)
from convergence.storage.registry import (
    StorageRegistry,
    get_storage_registry,
    reset_storage_registry,
)
from convergence.storage.rl_models import (
    AgentLegacy,
    CivilizationLegacy,
    RLAction,
    RLEpisode,
    RLState,
    RLTrainingRun,
    RLTrajectory,
)
from convergence.storage.sqlite import SQLiteStorage

# Optional Convex storage (requires backend environment)
try:
    from convergence.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None

# Optional PostgreSQL runtime storage (requires asyncpg)
try:
    from convergence.storage.postgresql import PostgreSQLRuntimeStorage
    _POSTGRESQL_AVAILABLE = True
except ImportError:
    _POSTGRESQL_AVAILABLE = False
    PostgreSQLRuntimeStorage = None  # type: ignore[misc, assignment]

__all__ = [
    # Protocol and base classes
    "StorageProtocol",
    "StorageConfig",
    "StorageError",
    "StorageConnectionError",
    "StorageNotFoundError",

    # Registry
    "StorageRegistry",
    "get_storage_registry",
    "reset_storage_registry",

    # Built-in backends
    "SQLiteStorage",
    "FileStorage",
    "MemoryStorage",

    # Multi-backend (CRITICAL for legacy)
    "MultiBackendStorage",
    "get_legacy_storage",

    # Convex backend (optional, requires backend)
    "ConvexStorage",

    # PostgreSQL runtime storage (optional, requires asyncpg)
    "PostgreSQLRuntimeStorage",

    # Legacy management
    "LegacyManager",
    "create_agent_from_legacy",

    # RL-optimized data models
    "RLEpisode",
    "RLTrajectory",
    "AgentLegacy",
    "CivilizationLegacy",
    "RLTrainingRun",
    "RLState",
    "RLAction",
]

