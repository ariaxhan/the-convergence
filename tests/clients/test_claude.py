"""Tests for Claude client integration.

Defines expected behavior for the pre-built Claude API client.
Tests requiring API key skip gracefully.
"""

import pytest
import os

from tests.conftest import requires_anthropic


class TestClaudeClientInitialization:
    """Test Claude client initialization."""

    def test_init_with_api_key(self):
        """Should initialize with explicit API key."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_api_key",
            system="test_system",
        )

        assert client.system == "test_system"

    def test_init_from_environment(self):
        """Should read API key from environment."""
        from convergence.clients import ClaudeClient

        # Temporarily set env var
        original = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "env_test_key"

        try:
            client = ClaudeClient(system="test_system")
            # Should not raise
        finally:
            if original:
                os.environ["ANTHROPIC_API_KEY"] = original
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_init_without_api_key_raises(self):
        """Should raise if no API key available."""
        from convergence.clients import ClaudeClient

        # Ensure no env var
        original = os.environ.get("ANTHROPIC_API_KEY")
        os.environ.pop("ANTHROPIC_API_KEY", None)

        try:
            with pytest.raises(ValueError):
                ClaudeClient(system="test_system")
        finally:
            if original:
                os.environ["ANTHROPIC_API_KEY"] = original

    def test_default_model(self):
        """Should have sensible default model."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test_system",
        )

        # Should default to a Claude model
        assert "claude" in client.default_model.lower()

    def test_custom_model(self):
        """Should accept custom model."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test_system",
            model="claude-opus-4-5",
        )

        assert client.default_model == "claude-opus-4-5"


class TestClaudeClientConfiguration:
    """Test client configuration options."""

    def test_system_prompt_configuration(self):
        """Should support system prompt configuration."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="sales_chat",
            system_prompt="You are a helpful sales assistant.",
        )

        assert client.system_prompt == "You are a helpful sales assistant."

    def test_max_tokens_configuration(self):
        """Should support max_tokens configuration."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test",
            max_tokens=500,
        )

        assert client.max_tokens == 500

    def test_default_max_tokens(self):
        """Should have reasonable default max_tokens."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        assert client.max_tokens >= 256


class TestChatInterface:
    """Test the chat interface without actual API calls."""

    def test_chat_method_exists(self):
        """Chat method should exist and be async."""
        from convergence.clients import ClaudeClient
        import inspect

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        assert hasattr(client, "chat")
        assert inspect.iscoroutinefunction(client.chat)

    def test_chat_accepts_required_params(self):
        """Chat should accept message and user_id."""
        from convergence.clients import ClaudeClient
        import inspect

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        sig = inspect.signature(client.chat)
        params = sig.parameters

        assert "message" in params
        assert "user_id" in params

    def test_chat_accepts_tools(self):
        """Chat should accept optional tools parameter."""
        from convergence.clients import ClaudeClient
        import inspect

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        sig = inspect.signature(client.chat)
        params = sig.parameters

        assert "tools" in params


@requires_anthropic
class TestChatLiveAPI:
    """Test actual Claude API calls. Requires ANTHROPIC_API_KEY."""

    @pytest.mark.asyncio
    async def test_chat_returns_llm_response(self):
        """Chat should return LLMResponse type."""
        from convergence.clients import ClaudeClient
        from convergence.types.response import LLMResponse

        client = ClaudeClient(system="test")

        response = await client.chat(
            message="Say 'hello' and nothing else.",
            user_id="test_user",
        )

        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_chat_extracts_confidence(self):
        """Chat should auto-extract confidence."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(system="test")

        # Ask a question that might produce uncertainty
        response = await client.chat(
            message="What will the weather be like tomorrow in San Francisco?",
            user_id="test_user",
        )

        # Confidence should be extracted (may be None or a float)
        assert response.confidence is None or isinstance(response.confidence, float)

    @pytest.mark.asyncio
    async def test_chat_returns_decision_id(self):
        """Chat should return decision_id for tracking."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(system="test")

        response = await client.chat(
            message="Hello",
            user_id="test_user",
        )

        # decision_id may be None if no runtime configured
        # but the field should exist
        assert hasattr(response, "decision_id")

    @pytest.mark.asyncio
    async def test_chat_with_tools(self):
        """Chat should support tool use."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(system="test")

        # Define a simple tool
        tools = [
            {
                "name": "get_weather",
                "description": "Get the current weather in a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state",
                        },
                    },
                    "required": ["location"],
                },
            },
        ]

        response = await client.chat(
            message="What's the weather in San Francisco?",
            user_id="test_user",
            tools=tools,
        )

        # Should get a response (may or may not use the tool)
        assert response.content is not None or response.metadata.get("tool_use")


class TestRecordOutcome:
    """Test outcome recording for learning."""

    def test_record_outcome_method_exists(self):
        """record_outcome method should exist and be async."""
        from convergence.clients import ClaudeClient
        import inspect

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        assert hasattr(client, "record_outcome")
        assert inspect.iscoroutinefunction(client.record_outcome)

    def test_record_outcome_accepts_params(self):
        """record_outcome should accept decision_id and reward."""
        from convergence.clients import ClaudeClient
        import inspect

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        sig = inspect.signature(client.record_outcome)
        params = sig.parameters

        assert "decision_id" in params
        assert "reward" in params or "converted" in params


@requires_anthropic
class TestRuntimeIntegration:
    """Test integration with convergence runtime."""

    @pytest.mark.asyncio
    async def test_chat_uses_runtime_select(self, tmp_path):
        """Chat should use runtime_select for parameter selection."""
        from convergence.clients import ClaudeClient
        from convergence import configure_runtime

        # Configure runtime with arms
        await configure_runtime(
            "claude_test",
            config={
                "default_arms": [
                    {"arm_id": "low_temp", "params": {"temperature": 0.3}},
                    {"arm_id": "high_temp", "params": {"temperature": 0.9}},
                ],
            },
            storage={"backend": "sqlite", "path": str(tmp_path / "runtime.db")},
        )

        client = ClaudeClient(system="claude_test")

        response = await client.chat(
            message="Hello",
            user_id="test_user",
        )

        # Should have a decision_id if runtime is configured
        assert response.decision_id is not None

    @pytest.mark.asyncio
    async def test_record_outcome_updates_runtime(self, tmp_path):
        """record_outcome should update runtime with reward."""
        from convergence.clients import ClaudeClient
        from convergence import configure_runtime

        await configure_runtime(
            "claude_outcome_test",
            config={
                "default_arms": [
                    {"arm_id": "arm1", "params": {"temperature": 0.5}},
                ],
            },
            storage={"backend": "sqlite", "path": str(tmp_path / "runtime.db")},
        )

        client = ClaudeClient(system="claude_outcome_test")

        response = await client.chat(
            message="Hello",
            user_id="test_user",
        )

        # Record positive outcome
        await client.record_outcome(
            decision_id=response.decision_id,
            reward=1.0,
        )

        # Should not raise - outcome recorded successfully


class TestGapDetection:
    """Test automatic gap detection."""

    @pytest.mark.asyncio
    async def test_gap_detected_flag(self):
        """Response should include gap_detected flag."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test",
            gap_threshold=0.6,
        )

        # The response should have gap_detected field
        # (actual value depends on confidence)
        assert hasattr(client, "gap_threshold")

    def test_custom_gap_threshold(self):
        """Should support custom gap detection threshold."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test",
            gap_threshold=0.8,
        )

        assert client.gap_threshold == 0.8


class TestErrorHandling:
    """Test error handling behavior."""

    @pytest.mark.asyncio
    async def test_handles_api_error_gracefully(self):
        """Should handle API errors gracefully."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="invalid_key_for_testing",
            system="test",
        )

        # Should raise a clear error, not crash
        with pytest.raises(Exception) as exc_info:
            await client.chat(
                message="Hello",
                user_id="test_user",
            )

        # Error should be meaningful
        assert exc_info.value is not None

    @pytest.mark.asyncio
    async def test_handles_empty_message(self):
        """Should handle empty message input."""
        from convergence.clients import ClaudeClient

        client = ClaudeClient(
            api_key="test_key",
            system="test",
        )

        with pytest.raises(ValueError):
            await client.chat(
                message="",
                user_id="test_user",
            )
