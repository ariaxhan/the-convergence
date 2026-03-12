"""
LLM Response type definitions.

Standard wrapper for LLM responses with metadata tracking.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMResponse(BaseModel):
    """Standard LLM response wrapper with metadata tracking."""

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
    )

    content: str = Field(..., description="The response text")
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score between 0.0 and 1.0",
    )
    decision_id: Optional[str] = Field(
        default=None,
        description="For tracking runtime decisions",
    )
    cache_hit: bool = Field(
        default=False,
        description="Whether response came from cache",
    )
    similarity: Optional[float] = Field(
        default=None,
        description="Cache hit similarity score",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model used for generation",
    )
    tokens_used: Optional[int] = Field(
        default=None,
        description="Token count",
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parameters used",
    )
    gap_detected: bool = Field(
        default=False,
        description="Whether knowledge gap detected",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata",
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """Ensure confidence is between 0.0 and 1.0."""
        if v is not None:
            if v < 0.0 or v > 1.0:
                raise ValueError("confidence must be between 0.0 and 1.0")
        return v


def detect_gap(response: LLMResponse, threshold: float) -> LLMResponse:
    """
    Detect knowledge gap based on confidence threshold.

    Args:
        response: The LLM response to evaluate
        threshold: Confidence threshold for gap detection

    Returns:
        New LLMResponse with gap_detected set based on confidence vs threshold.
        If confidence >= threshold: gap_detected = False
        If confidence < threshold or confidence is None: gap_detected = True
    """
    gap_detected = response.confidence is None or response.confidence < threshold

    return LLMResponse(
        content=response.content,
        confidence=response.confidence,
        decision_id=response.decision_id,
        cache_hit=response.cache_hit,
        similarity=response.similarity,
        model=response.model,
        tokens_used=response.tokens_used,
        params=response.params,
        gap_detected=gap_detected,
        metadata=response.metadata,
    )
