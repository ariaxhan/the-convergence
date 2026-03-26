"""Pre-built LLM clients with armature runtime integration."""

# Optional Claude client (requires anthropic package)
try:
    from .claude import ClaudeClient
    _CLAUDE_AVAILABLE = True
except ImportError:
    _CLAUDE_AVAILABLE = False
    ClaudeClient = None  # type: ignore[misc, assignment]

__all__ = ["ClaudeClient"]
