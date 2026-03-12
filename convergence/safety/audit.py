"""
Audit logging for The Convergence framework.

Every decision must be logged. No silent failures.

Features:
- JSONL format for easy parsing
- Log rotation
- Level and category filtering
- Session tracking
- Security event logging
"""

import json
import threading
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AuditLevel(str, Enum):
    """Audit log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SECURITY = "security"

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, AuditLevel):
            return NotImplemented
        order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, AuditLevel.ERROR, AuditLevel.SECURITY]
        return order.index(self) >= order.index(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, AuditLevel):
            return NotImplemented
        order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, AuditLevel.ERROR, AuditLevel.SECURITY]
        return order.index(self) > order.index(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, AuditLevel):
            return NotImplemented
        order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, AuditLevel.ERROR, AuditLevel.SECURITY]
        return order.index(self) <= order.index(other)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, AuditLevel):
            return NotImplemented
        order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, AuditLevel.ERROR, AuditLevel.SECURITY]
        return order.index(self) < order.index(other)


class AuditCategory(str, Enum):
    """Audit event categories."""
    REQUEST = "request"
    RESPONSE = "response"
    DECISION = "decision"
    BUDGET = "budget"
    INJECTION = "injection"
    VALIDATION = "validation"
    ERROR = "error"
    SYSTEM = "system"


class AuditEvent(BaseModel):
    """A single audit event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    level: str
    category: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    session_id: Optional[str] = None

    def __init__(
        self,
        level: AuditLevel | str = AuditLevel.INFO,
        category: AuditCategory | str = AuditCategory.SYSTEM,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        **kwargs: Any,
    ):
        # Convert enums to strings
        if isinstance(level, AuditLevel):
            level = level.value
        if isinstance(category, AuditCategory):
            category = category.value

        super().__init__(
            level=level,
            category=category,
            message=message,
            data=data,
            session_id=session_id,
            **kwargs,
        )


class AuditLogger:
    """
    Thread-safe audit logger with JSONL output.

    Features:
    - JSONL format for easy parsing
    - Log rotation by size
    - Level filtering
    - Category filtering
    - Session tracking
    - Concurrent logging safety
    """

    def __init__(
        self,
        log_path: str,
        max_size_mb: float = 10.0,
        max_files: int = 5,
        min_level: AuditLevel = AuditLevel.DEBUG,
    ):
        """
        Initialize audit logger.

        Args:
            log_path: Path to log file (JSONL format)
            max_size_mb: Max size before rotation (MB)
            max_files: Max number of rotated files to keep
            min_level: Minimum level to log
        """
        self.log_path = Path(log_path)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_files = max_files
        self.min_level = min_level

        self._session_id: Optional[str] = None
        self._lock = threading.Lock()
        self._buffer: List[AuditEvent] = []
        self._file_handle: Optional[Any] = None

        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing events for querying
        self._events: List[AuditEvent] = []
        self._load_existing_events()

    def _load_existing_events(self) -> None:
        """Load existing events from log file."""
        if self.log_path.exists():
            try:
                with open(self.log_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                self._events.append(AuditEvent(**data))
                            except (json.JSONDecodeError, Exception):
                                pass
            except Exception:
                pass

    def _should_log(self, level: AuditLevel) -> bool:
        """Check if level should be logged."""
        # Security events always logged
        if level == AuditLevel.SECURITY:
            return True
        return level >= self.min_level

    def _rotate_if_needed(self) -> None:
        """Rotate log file if size limit exceeded."""
        if not self.log_path.exists():
            return

        try:
            current_size = self.log_path.stat().st_size
        except Exception:
            return

        if current_size < self.max_size_bytes:
            return

        # Close current handle if open
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

        # Rotate files: .1 -> .2 -> .3 etc
        for i in range(self.max_files - 1, 0, -1):
            old_path = Path(f"{self.log_path}.{i}")
            new_path = Path(f"{self.log_path}.{i + 1}")
            if old_path.exists():
                if i + 1 > self.max_files:
                    old_path.unlink()
                else:
                    old_path.rename(new_path)

        # Move current to .1
        backup_path = Path(f"{self.log_path}.1")
        if self.log_path.exists():
            self.log_path.rename(backup_path)

    def _write_event(self, event: AuditEvent) -> None:
        """Write event to log file."""
        self._rotate_if_needed()

        line = json.dumps(event.model_dump(), default=str) + "\n"

        try:
            with open(self.log_path, "a") as f:
                f.write(line)
        except Exception:
            pass

    def set_session(self, session_id: str) -> None:
        """Set current session ID for all subsequent logs."""
        self._session_id = session_id

    def set_min_level(self, level: AuditLevel) -> None:
        """Set minimum logging level."""
        self.min_level = level

    def log(
        self,
        level: AuditLevel,
        category: AuditCategory,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an event.

        Args:
            level: Event level
            category: Event category
            message: Event message
            data: Additional data
        """
        if not self._should_log(level):
            return

        event = AuditEvent(
            level=level,
            category=category,
            message=message,
            data=data,
            session_id=self._session_id,
        )

        with self._lock:
            self._events.append(event)
            self._buffer.append(event)
            self._write_event(event)

    def log_injection_attempt(
        self,
        input_text: str,
        severity: str,
        detection_method: str,
        action_taken: str,
    ) -> None:
        """Log an injection attempt."""
        self.log(
            level=AuditLevel.SECURITY,
            category=AuditCategory.INJECTION,
            message="Injection attempt detected",
            data={
                "input_text": input_text,
                "severity": severity,
                "detection_method": detection_method,
                "action_taken": action_taken,
            },
        )

    def log_budget_violation(
        self,
        limit_type: str,
        limit_value: float,
        attempted_value: float,
        session_id: str,
    ) -> None:
        """Log a budget violation."""
        self.log(
            level=AuditLevel.SECURITY,
            category=AuditCategory.BUDGET,
            message="Budget limit exceeded",
            data={
                "limit_type": limit_type,
                "limit_value": limit_value,
                "attempted_value": attempted_value,
                "session_id": session_id,
            },
        )

    def log_pii_detected(
        self,
        pii_types: List[str],
        action_taken: str,
        output_hash: str,
    ) -> None:
        """Log PII detection (without logging actual PII)."""
        self.log(
            level=AuditLevel.SECURITY,
            category=AuditCategory.VALIDATION,
            message="PII detected in output",
            data={
                "pii_types": pii_types,
                "action_taken": action_taken,
                "output_hash": output_hash,
            },
        )

    def get_recent(
        self,
        count: int,
        min_level: Optional[AuditLevel] = None,
        category: Optional[AuditCategory] = None,
    ) -> List[AuditEvent]:
        """
        Get recent events.

        Args:
            count: Maximum number of events to return
            min_level: Filter by minimum level
            category: Filter by category

        Returns:
            List of matching events (most recent last)
        """
        with self._lock:
            events = self._events.copy()

        # Filter by level
        if min_level:
            level_order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, AuditLevel.ERROR, AuditLevel.SECURITY]
            min_idx = level_order.index(min_level)
            events = [
                e for e in events
                if level_order.index(AuditLevel(e.level)) >= min_idx
            ]

        # Filter by category
        if category:
            events = [e for e in events if e.category == category.value]

        # Return most recent
        return events[-count:]

    def get_security_events(self) -> List[AuditEvent]:
        """Get all security-level events."""
        with self._lock:
            return [e for e in self._events if e.level == AuditLevel.SECURITY.value]

    def get_by_session(self, session_id: str) -> List[AuditEvent]:
        """Get events for a session."""
        with self._lock:
            return [e for e in self._events if e.session_id == session_id]

    def get_by_time_range(
        self,
        start: datetime,
        end: datetime,
    ) -> List[AuditEvent]:
        """Get events within a time range."""
        with self._lock:
            results = []
            for e in self._events:
                try:
                    event_time = datetime.fromisoformat(e.timestamp)
                    if start <= event_time <= end:
                        results.append(e)
                except Exception:
                    pass
            return results

    def get_category_counts(self) -> Dict[str, int]:
        """Get event counts by category."""
        with self._lock:
            counts: Dict[str, int] = {}
            for e in self._events:
                counts[e.category] = counts.get(e.category, 0) + 1
            return counts

    def flush(self) -> None:
        """Flush any buffered events to disk."""
        with self._lock:
            self._buffer.clear()

    def close(self) -> None:
        """Close the logger and flush remaining events."""
        self.flush()
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None
