"""
Type definitions for Armature SDK.
"""

from .config import (
    AdaptersConfig,
    AgentConfig,
    ApiConfig,
    ArmatureConfig,
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
    from armature.runtime.reward_evaluator import RewardEvaluatorConfig  # noqa: F401
    RuntimeConfig.model_rebuild()
except ImportError:
    pass  # Will be rebuilt when RewardEvaluatorConfig is imported

__all__ = [
    "ArmatureConfig",
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

