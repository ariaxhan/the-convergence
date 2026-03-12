"""
Claude API client with convergence runtime integration.

Provides a pre-built client for Claude that automatically:
- Extracts confidence from responses
- Integrates with runtime MAB selection
- Records outcomes for learning
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    _ANTHROPIC_AVAILABLE = False

from convergence.types.response import LLMResponse, detect_gap


def _load_extract_confidence() -> Callable[[str], Optional[float]]:
    """
    Load extract_confidence without triggering evaluators/__init__.py.

    This avoids import errors from missing gemini_evaluator.py and openai_responses.py
    which are referenced in evaluators/__init__.py but don't exist.
    """
    # Find the confidence module path
    module_name = "convergence.evaluators.confidence"

    # Try to find it in sys.modules first (in case already imported)
    if module_name in sys.modules:
        fn: Callable[[str], Optional[float]] = sys.modules[module_name].extract_confidence
        return fn

    # Locate the file relative to this module
    this_dir = Path(__file__).parent
    confidence_path = this_dir.parent / "evaluators" / "confidence.py"

    if not confidence_path.exists():
        raise ImportError(f"Cannot find confidence module at {confidence_path}")

    # Load the module directly from file
    spec = importlib.util.spec_from_file_location(module_name, confidence_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {confidence_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    loaded_fn: Callable[[str], Optional[float]] = module.extract_confidence
    return loaded_fn


# Load the function at module import time
extract_confidence = _load_extract_confidence()


class ClaudeClient:
    """
    Claude API client with convergence runtime integration.

    Automatically extracts confidence, integrates with MAB selection,
    and supports outcome recording for continuous learning.

    Example:
        client = ClaudeClient(
            system="sales_chat",
            system_prompt="You are a helpful sales assistant.",
        )

        response = await client.chat(
            message="What's your return policy?",
            user_id="user_123",
        )

        # Later, record outcome
        if response.decision_id:
            await client.record_outcome(
                decision_id=response.decision_id,
                user_id="user_123",
                reward=1.0,  # User converted
            )
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        system: str,
        system_prompt: Optional[str] = None,
        model: str = "claude-sonnet-4-5",
        max_tokens: int = 1024,
        gap_threshold: float = 0.6,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            system: System identifier for runtime tracking.
            system_prompt: Optional system prompt for Claude.
            model: Claude model to use (default: claude-sonnet-4-5).
            max_tokens: Maximum tokens in response (default: 1024).
            gap_threshold: Confidence threshold for gap detection (default: 0.6).

        Raises:
            ValueError: If no API key is provided and ANTHROPIC_API_KEY is not set.
        """
        if not _ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required for ClaudeClient. "
                "Install it with: pip install anthropic"
            )

        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise ValueError(
                "No API key provided. Either pass api_key or set ANTHROPIC_API_KEY environment variable."
            )

        self._api_key = resolved_key
        self._system = system
        self._system_prompt = system_prompt
        self._model = model
        self._max_tokens = max_tokens
        self._gap_threshold = gap_threshold

        # Initialize Anthropic client
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key)

    @property
    def system(self) -> str:
        """System identifier for runtime tracking."""
        return self._system

    @property
    def system_prompt(self) -> Optional[str]:
        """System prompt for Claude."""
        return self._system_prompt

    @property
    def default_model(self) -> str:
        """Default model name."""
        return self._model

    @property
    def max_tokens(self) -> int:
        """Maximum tokens in response."""
        return self._max_tokens

    @property
    def gap_threshold(self) -> float:
        """Confidence threshold for gap detection."""
        return self._gap_threshold

    async def chat(
        self,
        *,
        message: str,
        user_id: str,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """
        Send a message to Claude and get a response.

        Automatically:
        - Uses runtime MAB selection for parameters (if configured)
        - Extracts confidence from response
        - Detects knowledge gaps

        Args:
            message: User message to send.
            user_id: User identifier for tracking.
            tools: Optional list of tools for Claude to use.

        Returns:
            LLMResponse with content, confidence, decision_id, etc.

        Raises:
            ValueError: If message is empty.
            anthropic.APIError: If API call fails.
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")

        # Try to get runtime selection for parameters
        decision_id: Optional[str] = None
        params: Dict[str, Any] = {}

        try:
            from convergence import runtime_select

            selection = await runtime_select(
                self._system,
                user_id=user_id,
            )
            decision_id = selection.decision_id
            params = selection.params or {}
        except Exception:
            # Runtime not configured or selection failed - use defaults
            pass

        # Build messages
        messages: List[Dict[str, str]] = [{"role": "user", "content": message}]

        # Build API call parameters
        model = params.get("model", self._model)
        max_tokens = params.get("max_tokens", self._max_tokens)
        temperature = params.get("temperature")

        api_kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if self._system_prompt:
            api_kwargs["system"] = self._system_prompt

        if temperature is not None:
            api_kwargs["temperature"] = temperature

        if tools:
            api_kwargs["tools"] = tools

        # Make API call
        response = await self._client.messages.create(**api_kwargs)

        # Extract content and tool use
        content = ""
        tool_use_data: Optional[List[Dict[str, Any]]] = None

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                if tool_use_data is None:
                    tool_use_data = []
                tool_use_data.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        # Extract confidence from content
        confidence = extract_confidence(content)

        # Build metadata
        metadata: Dict[str, Any] = {
            "stop_reason": response.stop_reason,
        }
        if tool_use_data:
            metadata["tool_use"] = tool_use_data

        # Calculate tokens used
        tokens_used = None
        if response.usage:
            tokens_used = response.usage.input_tokens + response.usage.output_tokens

        # Build response
        llm_response = LLMResponse(
            content=content,
            confidence=confidence,
            decision_id=decision_id,
            model=model,
            tokens_used=tokens_used,
            params=params if params else None,
            metadata=metadata,
        )

        # Apply gap detection
        llm_response = detect_gap(llm_response, self._gap_threshold)

        return llm_response

    async def record_outcome(
        self,
        *,
        decision_id: str,
        user_id: str,
        reward: float,
    ) -> None:
        """
        Record outcome for a previous decision.

        Updates the runtime with reward signal for learning.

        Args:
            decision_id: Decision ID from a previous chat response.
            user_id: User ID that was used for the original chat call.
            reward: Reward signal (0.0 to 1.0).
        """
        try:
            from convergence import runtime_update

            await runtime_update(
                self._system,
                user_id=user_id,
                decision_id=decision_id,
                reward=reward,
            )
        except Exception:
            # Runtime not configured or update failed - silently ignore
            pass
