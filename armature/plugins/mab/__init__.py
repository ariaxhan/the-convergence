"""MAB (Multi-Armed Bandit) plugins for The Armature framework."""

from armature.plugins.mab.persistence import ThompsonPersistence
from armature.plugins.mab.thompson_sampling import (
    ThompsonSamplingConfig,
    ThompsonSamplingPlugin,
    ThompsonSamplingStrategy,
)

__all__ = [
    'ThompsonSamplingStrategy',
    'ThompsonSamplingPlugin',
    'ThompsonSamplingConfig',
    'ThompsonPersistence',
]

