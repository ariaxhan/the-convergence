"""
Type definitions for Convergence SDK.
"""

from .config import (
    AdaptersConfig,
    AgentConfig,
    ApiConfig,
    ConvergenceConfig,
    EvaluationConfig,
    RunnerConfig,
    SearchSpaceConfig,
    StorageConfig,
)
from .evaluator import Evaluator
from .response import LLMResponse, detect_gap
from .results import OptimizationRunResult
from .runtime import (
    RuntimeArm,
    RuntimeArmState,
    RuntimeArmTemplate,
    RuntimeConfig,
    RuntimeDecision,
    RuntimeSelection,
    SelectionStrategyConfig,
)

# Rebuild RuntimeConfig to resolve RewardEvaluatorConfig forward reference (Pydantic v2)
try:
    from convergence.runtime.reward_evaluator import RewardEvaluatorConfig
    RuntimeConfig.model_rebuild()
except ImportError:
    pass  # Will be rebuilt when RewardEvaluatorConfig is imported

__all__ = [
    "ConvergenceConfig",
    "ApiConfig",
    "SearchSpaceConfig",
    "RunnerConfig",
    "EvaluationConfig",
    "StorageConfig",
    "AdaptersConfig",
    "AgentConfig",
    "OptimizationRunResult",
    "Evaluator",
    "RuntimeArm",
    "RuntimeArmState",
    "RuntimeArmTemplate",
    "RuntimeConfig",
    "RuntimeDecision",
    "RuntimeSelection",
    "SelectionStrategyConfig",
    # Response types
    "LLMResponse",
    "detect_gap",
]

