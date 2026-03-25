"""
The Convergence: API Optimization Framework.

Finds optimal API configurations through evolutionary optimization powered by
an agent society using RLP (reasoning), SAO (self-improvement), MAB (exploration),
and hierarchical learning.

Usage:
    CLI: convergence optimize config.yaml
    SDK: from convergence import run_optimization
"""

__version__ = "1.0.0"

from convergence.core.config import ConvergenceConfig
from convergence.core.protocols import (
    Agent,
    LLMProvider,
    MABStrategy,
    MemorySystem,
    Plugin,
)
from convergence.core.registry import PluginRegistry

# Optimization components
from convergence.optimization.config_loader import ConfigLoader
from convergence.optimization.runner import OptimizationRunner
from convergence.runtime.evolution import evolve_arms as runtime_evolve_arms

# Runtime interface
from convergence.runtime.online import (
    configure as configure_runtime,
)
from convergence.runtime.online import (
    get_decision as runtime_get_decision,
)
from convergence.runtime.online import (
    select as runtime_select,
)
from convergence.runtime.online import (
    update as runtime_update,
)
from convergence.runtime.reward_evaluator import (
    RewardEvaluatorConfig,
    RewardMetricConfig,
    RuntimeRewardEvaluator,
)

# SDK interface (for programmatic use)
from convergence.sdk import run_optimization

# Type definitions
from convergence.types import (
    ConvergenceConfig as ConvergenceConfigSDK,
)

# Rebuild RuntimeConfig to resolve RewardEvaluatorConfig forward reference (Pydantic v2)
# This ensures RuntimeConfig can be instantiated after RewardEvaluatorConfig is imported
from convergence.types import (
    RuntimeArmTemplate,
    RuntimeConfig,
    RuntimeDecision,
    RuntimeSelection,
    SelectionStrategyConfig,
)
from convergence.types import (
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
    "ConvergenceConfig",  # From core.config
    "ConvergenceConfigSDK",  # From types (programmatic SDK config)
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
