"""Semantic cache layer for The Armature framework.

Provides intelligent caching of LLM responses based on semantic similarity,
reducing redundant API calls for semantically equivalent queries.
"""

from .semantic import SemanticCache

__all__ = ["SemanticCache"]
