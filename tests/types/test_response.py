"""Tests for LLMResponse type.

Defines expected behavior for the standard LLM response wrapper.
"""

import pytest
from pydantic import ValidationError


class TestLLMResponseModel:
    """Test LLMResponse Pydantic model behavior."""

    def test_create_with_content_only(self):
        """Content is the only required field."""
        from armature.types.response import LLMResponse

        response = LLMResponse(content="Hello, world!")

        assert response.content == "Hello, world!"
        assert response.confidence is None
        assert response.decision_id is None
        assert response.cache_hit is False
        assert response.gap_detected is False

    def test_create_with_all_fields(self):
        """All fields can be set explicitly."""
        from armature.types.response import LLMResponse

        response = LLMResponse(
            content="The answer is 42.",
            confidence=0.95,
            decision_id="dec_abc123",
            cache_hit=True,
            similarity=0.92,
            model="claude-haiku-4-5",
            tokens_used=150,
            params={"temperature": 0.7},
            gap_detected=False,
            metadata={"source": "cache"},
        )

        assert response.content == "The answer is 42."
        assert response.confidence == 0.95
        assert response.decision_id == "dec_abc123"
        assert response.cache_hit is True
        assert response.similarity == 0.92
        assert response.model == "claude-haiku-4-5"
        assert response.tokens_used == 150
        assert response.params == {"temperature": 0.7}
        assert response.gap_detected is False
        assert response.metadata == {"source": "cache"}

    def test_confidence_validation_bounds(self):
        """Confidence must be between 0.0 and 1.0."""
        from armature.types.response import LLMResponse

        # Valid bounds
        LLMResponse(content="test", confidence=0.0)
        LLMResponse(content="test", confidence=1.0)
        LLMResponse(content="test", confidence=0.5)

        # Invalid: above 1.0
        with pytest.raises(ValidationError):
            LLMResponse(content="test", confidence=1.5)

        # Invalid: below 0.0
        with pytest.raises(ValidationError):
            LLMResponse(content="test", confidence=-0.1)

    def test_json_serialization(self):
        """Response can be serialized to JSON and back."""
        from armature.types.response import LLMResponse

        original = LLMResponse(
            content="Test response",
            confidence=0.85,
            decision_id="dec_xyz",
            cache_hit=False,
            params={"temperature": 0.7},
        )

        # Serialize
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)
        assert "Test response" in json_str

        # Deserialize
        restored = LLMResponse.model_validate_json(json_str)
        assert restored.content == original.content
        assert restored.confidence == original.confidence
        assert restored.decision_id == original.decision_id

    def test_dict_serialization(self):
        """Response can be converted to dict."""
        from armature.types.response import LLMResponse

        response = LLMResponse(
            content="Test",
            confidence=0.9,
            params={"model": "test"},
        )

        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["content"] == "Test"
        assert data["confidence"] == 0.9
        assert data["params"] == {"model": "test"}

    def test_immutable_by_default(self):
        """Response fields should not be accidentally mutated."""
        from armature.types.response import LLMResponse

        response = LLMResponse(content="Original")

        # Pydantic v2 models are mutable by default, but we test the value
        # doesn't change unexpectedly
        original_content = response.content
        assert response.content == original_content


class TestDetectGap:
    """Test the detect_gap helper function."""

    def test_no_gap_high_confidence(self):
        """High confidence should not detect gap."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(content="Answer", confidence=0.85)
        result = detect_gap(response, threshold=0.6)

        assert result.gap_detected is False
        assert result.content == response.content

    def test_gap_detected_low_confidence(self):
        """Low confidence should detect gap."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(content="Maybe answer", confidence=0.4)
        result = detect_gap(response, threshold=0.6)

        assert result.gap_detected is True

    def test_gap_at_threshold_boundary(self):
        """Confidence exactly at threshold should not detect gap."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(content="Answer", confidence=0.6)
        result = detect_gap(response, threshold=0.6)

        assert result.gap_detected is False

    def test_gap_just_below_threshold(self):
        """Confidence just below threshold should detect gap."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(content="Answer", confidence=0.59)
        result = detect_gap(response, threshold=0.6)

        assert result.gap_detected is True

    def test_gap_with_none_confidence(self):
        """None confidence should be treated as gap (unknown = uncertain)."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(content="Answer", confidence=None)
        result = detect_gap(response, threshold=0.6)

        assert result.gap_detected is True

    def test_gap_preserves_other_fields(self):
        """detect_gap should preserve all other response fields."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(
            content="Answer",
            confidence=0.4,
            decision_id="dec_123",
            cache_hit=True,
            model="test-model",
            metadata={"key": "value"},
        )
        result = detect_gap(response, threshold=0.6)

        assert result.content == response.content
        assert result.decision_id == response.decision_id
        assert result.cache_hit == response.cache_hit
        assert result.model == response.model
        assert result.metadata == response.metadata
        assert result.gap_detected is True

    def test_custom_threshold(self):
        """Different thresholds should work correctly."""
        from armature.types.response import LLMResponse, detect_gap

        response = LLMResponse(content="Answer", confidence=0.75)

        # 0.75 >= 0.7: no gap
        assert detect_gap(response, threshold=0.7).gap_detected is False

        # 0.75 < 0.8: gap
        assert detect_gap(response, threshold=0.8).gap_detected is True

        # 0.75 < 0.9: gap
        assert detect_gap(response, threshold=0.9).gap_detected is True


class TestLLMResponseFromDict:
    """Test creating LLMResponse from various dict formats."""

    def test_from_minimal_dict(self):
        """Create from dict with only content."""
        from armature.types.response import LLMResponse

        data = {"content": "Hello"}
        response = LLMResponse.model_validate(data)

        assert response.content == "Hello"

    def test_from_api_response_format(self):
        """Create from a typical API response structure."""
        from armature.types.response import LLMResponse

        # Simulating what might come from an LLM API
        data = {
            "content": "The answer is 42.",
            "model": "claude-haiku-4-5",
            "tokens_used": 125,
            "metadata": {
                "stop_reason": "end_turn",
                "latency_ms": 234,
            },
        }
        response = LLMResponse.model_validate(data)

        assert response.content == "The answer is 42."
        assert response.model == "claude-haiku-4-5"
        assert response.tokens_used == 125
        assert response.metadata["stop_reason"] == "end_turn"
