"""Core protocols, registry, and configuration for The Armature."""

from armature.core.config import ArmatureConfig
from armature.core.protocols import (
    Agent,
    LLMProvider,
    MABStrategy,
    MemorySystem,
    Plugin,
)
from armature.core.registry import PluginRegistry

__all__ = [
    "LLMProvider",
    "MABStrategy",
    "MemorySystem",
    "Agent",
    "Plugin",
    "ArmatureConfig",
    "PluginRegistry",
]

