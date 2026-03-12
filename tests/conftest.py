"""Shared test fixtures and configuration.

Design principle: No mocks. Integration tests with graceful skip on missing deps.
"""

import os
import pytest
import asyncio
from typing import List, Callable, Awaitable


# ============================================================================
# Environment Detection
# ============================================================================

def has_postgresql() -> bool:
    """Check if PostgreSQL is available for testing."""
    try:
        import asyncpg
        # Check for test database URL
        return bool(os.environ.get("TEST_POSTGRESQL_DSN"))
    except ImportError:
        return False


def has_redis() -> bool:
    """Check if Redis is available for testing."""
    try:
        import redis
        # Check for test redis URL
        url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379")
        client = redis.from_url(url)
        client.ping()
        return True
    except Exception:
        return False


def has_anthropic_key() -> bool:
    """Check if Anthropic API key is available."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def has_openai_key() -> bool:
    """Check if OpenAI API key is available (for embeddings)."""
    return bool(os.environ.get("OPENAI_API_KEY"))


# ============================================================================
# Skip Markers
# ============================================================================

requires_postgresql = pytest.mark.skipif(
    not has_postgresql(),
    reason="PostgreSQL not available (set TEST_POSTGRESQL_DSN)"
)

requires_redis = pytest.mark.skipif(
    not has_redis(),
    reason="Redis not available"
)

requires_anthropic = pytest.mark.skipif(
    not has_anthropic_key(),
    reason="ANTHROPIC_API_KEY not set"
)

requires_openai = pytest.mark.skipif(
    not has_openai_key(),
    reason="OPENAI_API_KEY not set"
)


# ============================================================================
# Test Embedding Functions (for cache tests without external APIs)
# ============================================================================

def simple_embedding_fn(text: str) -> List[float]:
    """
    Simple deterministic embedding for testing.

    Creates a 64-dimensional vector based on character frequencies.
    Not semantically meaningful, but deterministic and fast.
    """
    # Initialize 64-dim vector
    vec = [0.0] * 64

    # Fill based on character codes
    for i, char in enumerate(text.lower()):
        idx = ord(char) % 64
        vec[idx] += 1.0

    # Normalize
    magnitude = sum(v * v for v in vec) ** 0.5
    if magnitude > 0:
        vec = [v / magnitude for v in vec]

    return vec


async def async_simple_embedding_fn(text: str) -> List[float]:
    """Async version of simple embedding."""
    return simple_embedding_fn(text)


def semantic_embedding_fn(text: str) -> List[float]:
    """
    Slightly more semantic embedding for testing similarity.

    Groups similar concepts together. Still deterministic.
    """
    vec = [0.0] * 64

    # Word-based features
    words = text.lower().split()

    # Question words → dim 0-7
    question_words = {"how", "what", "why", "when", "where", "who", "which", "can"}
    for i, w in enumerate(question_words):
        if w in words:
            vec[i] = 1.0

    # Action words → dim 8-15
    action_words = {"reset", "change", "update", "delete", "create", "add", "remove", "set"}
    for i, w in enumerate(action_words):
        if w in words:
            vec[8 + i] = 1.0

    # Object words → dim 16-23
    object_words = {"password", "email", "account", "profile", "settings", "name", "user", "data"}
    for i, w in enumerate(object_words):
        if w in words:
            vec[16 + i] = 1.0

    # Fill rest with character-based features
    for char in text.lower():
        idx = 24 + (ord(char) % 40)
        vec[idx] += 0.1

    # Normalize
    magnitude = sum(v * v for v in vec) ** 0.5
    if magnitude > 0:
        vec = [v / magnitude for v in vec]

    return vec


async def async_semantic_embedding_fn(text: str) -> List[float]:
    """Async version of semantic embedding."""
    return semantic_embedding_fn(text)


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def temp_sqlite_path(tmp_path):
    """Provide a temporary SQLite database path."""
    return str(tmp_path / "test_cache.db")


@pytest.fixture
async def postgresql_dsn():
    """Provide PostgreSQL DSN if available."""
    dsn = os.environ.get("TEST_POSTGRESQL_DSN")
    if not dsn:
        pytest.skip("TEST_POSTGRESQL_DSN not set")
    return dsn


@pytest.fixture
def redis_url():
    """Provide Redis URL if available."""
    url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379")
    if not has_redis():
        pytest.skip("Redis not available")
    return url


# ============================================================================
# Sample Data
# ============================================================================

@pytest.fixture
def sample_queries():
    """Sample queries for cache testing."""
    return {
        "password_reset": [
            "How do I reset my password?",
            "How can I change my password?",
            "I forgot my password, how to reset?",
            "Reset password please",
        ],
        "account_deletion": [
            "How do I delete my account?",
            "Can I remove my account?",
            "I want to delete my profile",
        ],
        "pricing": [
            "How much does it cost?",
            "What are your prices?",
            "Pricing information please",
        ],
    }


@pytest.fixture
def sample_responses():
    """Sample LLM responses for testing."""
    return {
        "confident": "The password reset link has been sent to your email. "
                    "Click the link within 24 hours to reset your password.",
        "uncertain": "I think you might be able to reset your password through "
                    "the settings page, but I'm not entirely sure about the exact steps.",
        "hedging": "Maybe you could try the forgot password link? I believe it "
                  "should be on the login page, possibly in the bottom right corner.",
        "explicit_confidence": "Based on our documentation, the answer is X. "
                              "Confidence: 92%",
        "very_certain": "Definitely use the reset link. It will always work "
                       "and is guaranteed to send within seconds.",
    }


@pytest.fixture
def sample_arms():
    """Sample arms for runtime storage testing."""
    return [
        {
            "arm_id": "arm_conservative",
            "name": "Conservative",
            "params": {"temperature": 0.3, "model": "claude-haiku-4-5"},
        },
        {
            "arm_id": "arm_balanced",
            "name": "Balanced",
            "params": {"temperature": 0.7, "model": "claude-sonnet-4-5"},
        },
        {
            "arm_id": "arm_creative",
            "name": "Creative",
            "params": {"temperature": 1.0, "model": "claude-sonnet-4-5"},
        },
    ]
