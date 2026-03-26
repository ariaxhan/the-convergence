"""
The Armature: API Optimization Framework.

Finds optimal API configurations through evolutionary optimization powered by
an agent society using RLP (reasoning), SAO (self-improvement), MAB (exploration),
and hierarchical learning.

Usage:
    CLI: armature optimize config.yaml
    SDK: from armature import run_optimization
"""

__version__ = "1.0.0"

from armature.core.config import ArmatureConfig
from armature.core.protocols import (
    Agent,
    LLMProvider,
    MABStrategy,
    MemorySystem,
    Plugin,
)
from armature.core.registry import PluginRegistry

# Optimization components
from armature.optimization.config_loader import ConfigLoader
from armature.optimization.runner import OptimizationRunner
from armature.runtime.evolution import evolve_arms as runtime_evolve_arms

# Runtime interface
from armature.runtime.online import (
    configure as configure_runtime,
)
from armature.runtime.online import (
    get_decision as runtime_get_decision,
)
from armature.runtime.online import (
    select as runtime_select,
)
from armature.runtime.online import (
    update as runtime_update,
)
from armature.runtime.reward_evaluator import (
    RewardEvaluatorConfig,
    RewardMetricConfig,
    RuntimeRewardEvaluator,
)

# SDK interface (for programmatic use)
from armature.sdk import run_optimization

# Type definitions
from armature.types import (
    ArmatureConfig as ArmatureConfigSDK,
)

# Rebuild RuntimeConfig to resolve RewardEvaluatorConfig forward reference (Pydantic v2)
# This ensures RuntimeConfig can be instantiated after RewardEvaluatorConfig is imported
from armature.types import (
    RuntimeArmTemplate,
    RuntimeConfig,
    RuntimeDecision,
    RuntimeSelection,
    SelectionStrategyConfig,
)
from armature.types import (
    RuntimeConfig as RuntimeConfigSDK,
)

RuntimeConfig.model_rebuild()

__all__ = [
    # Core protocols
    "LLMProvider",
    "MABStrategy",
    "MemorySystem",
    "Agent",
    "Plugin",
    "ArmatureConfig",  # From core.config
    "ArmatureConfigSDK",  # From types (programmatic SDK config)
    "PluginRegistry",
    # Optimization
    "ConfigLoader",
    "OptimizationRunner",
    # SDK
    "run_optimization",
    # Runtime
    "configure_runtime",
    "runtime_select",
    "runtime_update",
    "runtime_get_decision",
    "runtime_evolve_arms",
    "RuntimeConfigSDK",
    "RuntimeSelection",
    "RuntimeDecision",
    "SelectionStrategyConfig",
    "RuntimeRewardEvaluator",
    "RewardEvaluatorConfig",
    "RewardMetricConfig",
    "RuntimeArmTemplate",
]
