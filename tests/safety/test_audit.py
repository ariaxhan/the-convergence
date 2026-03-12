"""
Tests for audit logging.

Every decision must be logged. No silent failures.
"""

import pytest
import json
from datetime import datetime

from convergence.safety.audit import (
    AuditLogger,
    AuditEvent,
    AuditLevel,
    AuditCategory,
)


# =============================================================================
# BASIC AUDIT LOGGING
# =============================================================================


class TestBasicAuditLogging:
    """Test basic audit logging operations."""

    @pytest.fixture
    def audit_logger(self, tmp_path):
        """Create audit logger with file backend."""
        log_path = tmp_path / "audit.jsonl"
        return AuditLogger(log_path=str(log_path))

    def test_log_event(self, audit_logger):
        """Should log events."""
        audit_logger.log(
            level=AuditLevel.INFO,
            category=AuditCategory.DECISION,
            message="Selected arm A",
            data={"arm": "A", "confidence": 0.85},
        )

        events = audit_logger.get_recent(count=1)

        assert len(events) == 1
        assert events[0].message == "Selected arm A"

    def test_log_with_session_context(self, audit_logger):
        """Should track session context."""
        audit_logger.set_session("session-123")

        audit_logger.log(
            level=AuditLevel.INFO,
            category=AuditCategory.REQUEST,
            message="Request received",
        )

        events = audit_logger.get_recent(count=1)

        assert events[0].session_id == "session-123"

    def test_log_timestamps(self, audit_logger):
        """Should include timestamps."""
        audit_logger.log(
            level=AuditLevel.INFO,
            category=AuditCategory.DECISION,
            message="Test event",
        )

        events = audit_logger.get_recent(count=1)

        assert events[0].timestamp is not None
        # Timestamp should be recent
        now = datetime.utcnow()
        event_time = datetime.fromisoformat(events[0].timestamp)
        assert (now - event_time).total_seconds() < 5


# =============================================================================
# AUDIT LEVELS
# =============================================================================


class TestAuditLevels:
    """Test audit level filtering."""

    @pytest.fixture
    def audit_logger(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        return AuditLogger(log_path=str(log_path))

    def test_filter_by_level(self, audit_logger):
        """Should filter events by level."""
        audit_logger.log(AuditLevel.DEBUG, AuditCategory.DECISION, "Debug msg")
        audit_logger.log(AuditLevel.INFO, AuditCategory.DECISION, "Info msg")
        audit_logger.log(AuditLevel.WARNING, AuditCategory.DECISION, "Warning msg")
        audit_logger.log(AuditLevel.ERROR, AuditCategory.DECISION, "Error msg")

        warnings_and_above = audit_logger.get_recent(
            count=100,
            min_level=AuditLevel.WARNING,
        )

        assert len(warnings_and_above) == 2
        assert all(e.level in ["warning", "error"] for e in warnings_and_above)

    def test_security_level_always_logged(self, audit_logger):
        """Security events should always be logged."""
        # Even with high threshold, security should log
        audit_logger.set_min_level(AuditLevel.ERROR)

        audit_logger.log(
            level=AuditLevel.SECURITY,
            category=AuditCategory.INJECTION,
            message="Injection attempt blocked",
        )

        events = audit_logger.get_recent(count=1)

        assert len(events) == 1
        assert events[0].level == "security"


# =============================================================================
# AUDIT CATEGORIES
# =============================================================================


class TestAuditCategories:
    """Test audit event categories."""

    @pytest.fixture
    def audit_logger(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        return AuditLogger(log_path=str(log_path))

    def test_filter_by_category(self, audit_logger):
        """Should filter events by category."""
        audit_logger.log(AuditLevel.INFO, AuditCategory.DECISION, "Decision made")
        audit_logger.log(AuditLevel.INFO, AuditCategory.BUDGET, "Cost recorded")
        audit_logger.log(AuditLevel.INFO, AuditCategory.INJECTION, "Input checked")

        budget_events = audit_logger.get_recent(
            count=100,
            category=AuditCategory.BUDGET,
        )

        assert len(budget_events) == 1
        assert budget_events[0].category == "budget"

    def test_all_categories_supported(self, audit_logger):
        """All categories should be loggable."""
        categories = [
            AuditCategory.REQUEST,
            AuditCategory.RESPONSE,
            AuditCategory.DECISION,
            AuditCategory.BUDGET,
            AuditCategory.INJECTION,
            AuditCategory.VALIDATION,
            AuditCategory.ERROR,
            AuditCategory.SYSTEM,
        ]

        for cat in categories:
            audit_logger.log(AuditLevel.INFO, cat, f"Test {cat}")

        events = audit_logger.get_recent(count=100)

        assert len(events) == len(categories)


# =============================================================================
# SECURITY AUDIT
# =============================================================================


class TestSecurityAudit:
    """Test security-specific audit logging."""

    @pytest.fixture
    def audit_logger(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        return AuditLogger(log_path=str(log_path))

    def test_log_injection_attempt(self, audit_logger):
        """Should log injection attempts with full context."""
        audit_logger.log_injection_attempt(
            input_text="ignore previous instructions",
            severity="high",
            detection_method="rule_based",
            action_taken="blocked",
        )

        events = audit_logger.get_security_events()

        assert len(events) == 1
        assert events[0].category == "injection"
        assert "ignore previous" in events[0].data.get("input_text", "")

    def test_log_budget_violation(self, audit_logger):
        """Should log budget violations."""
        audit_logger.log_budget_violation(
            limit_type="per_session",
            limit_value=10.0,
            attempted_value=15.0,
            session_id="s123",
        )

        events = audit_logger.get_security_events()

        assert len(events) == 1
        assert events[0].data["limit_type"] == "per_session"

    def test_log_pii_detected(self, audit_logger):
        """Should log PII detection (without logging actual PII)."""
        audit_logger.log_pii_detected(
            pii_types=["email", "phone"],
            action_taken="redacted",
            output_hash="abc123",  # Hash, not actual content
        )

        events = audit_logger.get_security_events()

        assert len(events) == 1
        # Should not contain actual PII
        assert "email" in str(events[0].data.get("pii_types", []))


# =============================================================================
# PERSISTENCE
# =============================================================================


class TestAuditPersistence:
    """Test audit log persistence."""

    def test_logs_persist_to_file(self, tmp_path):
        """Logs should persist to file."""
        log_path = tmp_path / "audit.jsonl"

        # First logger
        logger1 = AuditLogger(log_path=str(log_path))
        logger1.log(AuditLevel.INFO, AuditCategory.DECISION, "First event")
        logger1.close()

        # Second logger (simulating restart)
        logger2 = AuditLogger(log_path=str(log_path))
        logger2.log(AuditLevel.INFO, AuditCategory.DECISION, "Second event")

        events = logger2.get_recent(count=100)

        assert len(events) == 2

    def test_log_format_jsonl(self, tmp_path):
        """Logs should be in JSONL format."""
        log_path = tmp_path / "audit.jsonl"

        logger = AuditLogger(log_path=str(log_path))
        logger.log(AuditLevel.INFO, AuditCategory.DECISION, "Event 1")
        logger.log(AuditLevel.INFO, AuditCategory.DECISION, "Event 2")
        logger.flush()

        # Read raw file
        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 2

        # Each line should be valid JSON
        for line in lines:
            data = json.loads(line)
            assert "message" in data
            assert "timestamp" in data

    def test_log_rotation(self, tmp_path):
        """Should support log rotation."""
        log_path = tmp_path / "audit.jsonl"

        logger = AuditLogger(
            log_path=str(log_path),
            max_size_mb=0.001,  # Very small for testing
            max_files=3,
        )

        # Write enough to trigger rotation
        for i in range(1000):
            logger.log(AuditLevel.INFO, AuditCategory.DECISION, f"Event {i}")

        logger.flush()

        # Should have rotated files
        log_files = list(tmp_path.glob("audit*.jsonl*"))
        assert len(log_files) >= 1


# =============================================================================
# QUERYING
# =============================================================================


class TestAuditQuerying:
    """Test audit log querying."""

    @pytest.fixture
    def populated_logger(self, tmp_path):
        """Create logger with test data."""
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=str(log_path))

        # Various events
        logger.set_session("s1")
        logger.log(AuditLevel.INFO, AuditCategory.REQUEST, "Request 1")
        logger.log(AuditLevel.INFO, AuditCategory.DECISION, "Decision 1")

        logger.set_session("s2")
        logger.log(AuditLevel.WARNING, AuditCategory.BUDGET, "Budget warning")
        logger.log(AuditLevel.ERROR, AuditCategory.ERROR, "Error occurred")

        return logger

    def test_query_by_session(self, populated_logger):
        """Should query events by session."""
        events = populated_logger.get_by_session("s1")

        assert len(events) == 2
        assert all(e.session_id == "s1" for e in events)

    def test_query_by_time_range(self, populated_logger):
        """Should query events by time range."""
        from datetime import timedelta

        now = datetime.utcnow()
        events = populated_logger.get_by_time_range(
            start=now - timedelta(minutes=1),
            end=now + timedelta(minutes=1),
        )

        assert len(events) == 4

    def test_count_by_category(self, populated_logger):
        """Should count events by category."""
        counts = populated_logger.get_category_counts()

        assert counts.get("request", 0) == 1
        assert counts.get("decision", 0) == 1
        assert counts.get("budget", 0) == 1


# =============================================================================
# AUDIT EVENT STRUCTURE
# =============================================================================


class TestAuditEventStructure:
    """Test AuditEvent structure."""

    def test_event_has_required_fields(self):
        """AuditEvent should have required fields."""
        event = AuditEvent(
            level=AuditLevel.INFO,
            category=AuditCategory.DECISION,
            message="Test",
        )

        assert event.level is not None
        assert event.category is not None
        assert event.message is not None
        assert event.timestamp is not None
        assert event.id is not None

    def test_event_serializable(self):
        """AuditEvent should be JSON serializable."""
        event = AuditEvent(
            level=AuditLevel.INFO,
            category=AuditCategory.DECISION,
            message="Test",
            data={"key": "value"},
        )

        data = event.model_dump()
        json.dumps(data)  # Should not raise

    def test_event_id_unique(self):
        """Each event should have unique ID."""
        events = [
            AuditEvent(AuditLevel.INFO, AuditCategory.DECISION, f"Event {i}")
            for i in range(100)
        ]

        ids = [e.id for e in events]

        assert len(ids) == len(set(ids))  # All unique


# =============================================================================
# EDGE CASES
# =============================================================================


class TestAuditEdgeCases:
    """Test edge cases."""

    def test_concurrent_logging(self, tmp_path):
        """Should handle concurrent logging."""
        import asyncio

        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=str(log_path))

        async def log_event(i):
            logger.log(AuditLevel.INFO, AuditCategory.DECISION, f"Event {i}")

        async def run():
            await asyncio.gather(*[log_event(i) for i in range(100)])

        asyncio.run(run())
        logger.flush()

        events = logger.get_recent(count=200)
        assert len(events) == 100

    def test_large_data_payload(self, tmp_path):
        """Should handle large data payloads."""
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=str(log_path))

        large_data = {"items": list(range(10000))}

        logger.log(
            AuditLevel.INFO,
            AuditCategory.DECISION,
            "Large payload",
            data=large_data,
        )

        events = logger.get_recent(count=1)
        assert len(events[0].data["items"]) == 10000

    def test_special_characters_in_message(self, tmp_path):
        """Should handle special characters."""
        log_path = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_path=str(log_path))

        messages = [
            "Message with 'quotes' and \"double quotes\"",
            "Message with\nnewlines\tand\ttabs",
            "Unicode: 日本語 🎉 مرحبا",
        ]

        for msg in messages:
            logger.log(AuditLevel.INFO, AuditCategory.DECISION, msg)

        logger.flush()

        events = logger.get_recent(count=10)
        assert len(events) == 3

    def test_missing_log_directory(self, tmp_path):
        """Should create missing directories."""
        log_path = tmp_path / "subdir" / "nested" / "audit.jsonl"

        # Directory doesn't exist
        assert not log_path.parent.exists()

        logger = AuditLogger(log_path=str(log_path))
        logger.log(AuditLevel.INFO, AuditCategory.DECISION, "Test")
        logger.flush()

        # Should have created directory
        assert log_path.exists()
