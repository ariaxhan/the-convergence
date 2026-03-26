"""
Storage abstraction for The Armature framework.

Provides pluggable storage backends via Protocol-based design.
Users can bring their own storage by implementing StorageProtocol.

LEGACY SYSTEM:
The multi-backend storage and legacy manager ensure data is NEVER lost.
Every episode, every insight, every best method is preserved forever.
This is how knowledge passes between generations.
"""

from armature.storage.base import (
    StorageConfig,
    StorageConnectionError,
    StorageError,
    StorageNotFoundError,
    StorageProtocol,
)
from armature.storage.file import FileStorage
from armature.storage.legacy_manager import (
    LegacyManager,
    create_agent_from_legacy,
)
from armature.storage.memory import MemoryStorage
from armature.storage.multi_backend import (
    MultiBackendStorage,
    get_legacy_storage,
)
from armature.storage.registry import (
    StorageRegistry,
    get_storage_registry,
    reset_storage_registry,
)
from armature.storage.rl_models import (
    AgentLegacy,
    CivilizationLegacy,
    RLAction,
    RLEpisode,
    RLState,
    RLTrainingRun,
    RLTrajectory,
)
from armature.storage.sqlite import SQLiteStorage

# Optional Convex storage (requires backend environment)
try:
    from armature.storage.convex import ConvexStorage
    _CONVEX_AVAILABLE = True
except ImportError:
    _CONVEX_AVAILABLE = False
    ConvexStorage = None  # type: ignore[misc, assignment]

# Optional PostgreSQL runtime storage (requires asyncpg)
try:
    from armature.storage.postgresql import PostgreSQLRuntimeStorage
    _POSTGRESQL_AVAILABLE = True
except ImportError:
    _POSTGRESQL_AVAILABLE = False
    PostgreSQLRuntimeStorage = None  # type: ignore[misc, assignment]

# Optional generic PostgreSQL storage (requires asyncpg)
try:
    from armature.storage.postgres import PostgreSQLStorage
    _POSTGRES_STORAGE_AVAILABLE = True
except ImportError:
    _POSTGRES_STORAGE_AVAILABLE = False
    PostgreSQLStorage = None  # type: ignore[misc, assignment]

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

    # Generic PostgreSQL storage (optional, requires asyncpg)
    "PostgreSQLStorage",

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

