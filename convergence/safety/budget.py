"""
Budget enforcement for The Convergence framework.

Implements hierarchical budget limits:
- Global daily/monthly limits
- Per-session limits
- Per-request limits
- Team and user limits
- Rate limiting

Prevents runaway agents from burning through API credits.
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field


class StorageProtocol(Protocol):
    """Protocol for storage backends."""
    async def save(self, key: str, value: Any) -> None: ...
    async def load(self, key: str) -> Any: ...
    async def exists(self, key: str) -> bool: ...
    async def list_keys(self, prefix: str) -> List[str]: ...


class BudgetConfig(BaseModel):
    """Configuration for budget manager."""
    global_daily_limit: float = 100.0
    global_monthly_limit: float = 1000.0
    per_session_limit: float = 10.0
    per_request_limit: float = 1.0
    warning_threshold: float = 0.8
    requests_per_minute: Optional[int] = None
    max_iterations_per_session: Optional[int] = None
    team_daily_limit: Optional[float] = None
    user_daily_limit: Optional[float] = None
    fail_open: bool = True  # If True, allow requests on storage failure


class BudgetStatus(BaseModel):
    """Status of budget usage."""
    daily_spent: float = 0.0
    monthly_spent: float = 0.0
    daily_remaining: float = 0.0
    monthly_remaining: float = 0.0
    daily_warning: bool = False
    percent_used: float = 0.0
    # For session/team status
    warning: bool = False
    remaining: float = 0.0
    total_spent: float = 0.0


class CostRecord(BaseModel):
    """Record of a single cost event."""
    amount: float
    session_id: str
    request_id: str
    model: str
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None


class BudgetExceededError(Exception):
    """Raised when a budget limit is exceeded."""
    pass


class BudgetManager:
    """
    Manage and enforce budget limits.

    Features:
    - Hierarchical limits (global > team > user > session > request)
    - Rate limiting (requests per minute)
    - Iteration limits per session
    - Persistent storage
    - Concurrent request safety
    """

    def __init__(
        self,
        storage: Any,
        config: Optional[BudgetConfig] = None,
    ):
        """
        Initialize budget manager.

        Args:
            storage: Storage backend implementing StorageProtocol
            config: Budget configuration
        """
        self.storage = storage
        self.config = config or BudgetConfig()
        self._lock = asyncio.Lock()
        self._initialized = False

        # In-memory caches for rate limiting
        self._request_timestamps: List[datetime] = []
        self._session_iterations: Dict[str, int] = {}

        # Team registry
        self._teams: Dict[str, List[str]] = {}

    async def initialize(self) -> None:
        """Initialize the budget manager."""
        self._initialized = True
        # Load team registrations from storage if available
        try:
            if await self.storage.exists("budget:teams"):
                self._teams = await self.storage.load("budget:teams")
        except Exception:
            pass

    async def _ensure_initialized(self) -> None:
        """Ensure manager is initialized."""
        if not self._initialized:
            await self.initialize()

    def _get_date_key(self, dt: datetime) -> str:
        """Get storage key for a date."""
        return dt.strftime("%Y-%m-%d")

    def _get_month_key(self, dt: datetime) -> str:
        """Get storage key for a month."""
        return dt.strftime("%Y-%m")

    async def _get_daily_records(self, target_date: Optional[date] = None) -> List[CostRecord]:
        """Get all cost records for a date."""
        if target_date is None:
            target_date = datetime.utcnow().date()

        date_key = target_date.strftime("%Y-%m-%d")
        key = f"budget:daily:{date_key}"

        try:
            if await self.storage.exists(key):
                records_data = await self.storage.load(key)
                return [CostRecord.model_validate(r) for r in records_data]
        except Exception:
            pass

        return []

    async def _save_daily_records(self, records: List[CostRecord], target_date: Optional[date] = None) -> None:
        """Save cost records for a date."""
        if target_date is None:
            target_date = datetime.utcnow().date()

        date_key = target_date.strftime("%Y-%m-%d")
        key = f"budget:daily:{date_key}"

        records_data = [r.model_dump(mode="json") for r in records]
        await self.storage.save(key, records_data)

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limit."""
        if self.config.requests_per_minute is None:
            return

        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > minute_ago
        ]

        if len(self._request_timestamps) >= self.config.requests_per_minute:
            raise BudgetExceededError(
                f"Rate limit exceeded: {self.config.requests_per_minute} requests per minute"
            )

        self._request_timestamps.append(now)

    async def _check_iteration_limit(self, session_id: str) -> None:
        """Check and enforce iteration limit."""
        if self.config.max_iterations_per_session is None:
            return

        current = self._session_iterations.get(session_id, 0)

        if current >= self.config.max_iterations_per_session:
            raise BudgetExceededError(
                f"Iteration limit exceeded: {self.config.max_iterations_per_session} iterations per session"
            )

    async def _get_user_for_team(self, user_id: str) -> Optional[str]:
        """Get team ID for a user."""
        for team_id, members in self._teams.items():
            if user_id in members:
                return team_id
        return None

    async def record_cost(
        self,
        amount: float,
        session_id: str,
        request_id: str,
        model: str,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Record a cost and check limits.

        Args:
            amount: Cost amount in dollars
            session_id: Session identifier
            request_id: Request identifier
            model: Model used
            tokens_input: Input token count
            tokens_output: Output token count
            metadata: Additional metadata
            timestamp: Override timestamp (default: now)
            user_id: User identifier for hierarchical limits

        Raises:
            BudgetExceededError: If any limit would be exceeded
            ValueError: If amount is negative
        """
        await self._ensure_initialized()

        if amount < 0:
            raise ValueError("Cost amount cannot be negative")

        # Create record
        record = CostRecord(
            amount=amount,
            session_id=session_id,
            request_id=request_id,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            metadata=metadata,
            timestamp=timestamp or datetime.utcnow(),
            user_id=user_id,
        )

        async with self._lock:
            try:
                # Check rate limit first
                await self._check_rate_limit()

                # Check iteration limit
                await self._check_iteration_limit(session_id)

                # Get current daily records
                today = record.timestamp.date()
                records = await self._get_daily_records(today)

                # Check accumulated limits first (more relevant to user)
                # Check session limit
                session_spent = sum(r.amount for r in records if r.session_id == session_id)
                if session_spent + amount > self.config.per_session_limit:
                    raise BudgetExceededError(
                        f"Session limit exceeded: ${session_spent + amount:.2f} > ${self.config.per_session_limit:.2f}"
                    )

                # Check user limit (if configured and user_id provided)
                if self.config.user_daily_limit and user_id:
                    user_spent = sum(r.amount for r in records if r.user_id == user_id)
                    if user_spent + amount > self.config.user_daily_limit:
                        raise BudgetExceededError(
                            f"User daily limit exceeded: ${user_spent + amount:.2f} > ${self.config.user_daily_limit:.2f}"
                        )

                # Check daily limit (only for today's date)
                if today == datetime.utcnow().date():
                    daily_spent = sum(r.amount for r in records)
                    if daily_spent + amount > self.config.global_daily_limit:
                        raise BudgetExceededError(
                            f"Daily limit exceeded: ${daily_spent + amount:.2f} > ${self.config.global_daily_limit:.2f}"
                        )

                # Check per-request limit last
                if amount > self.config.per_request_limit:
                    raise BudgetExceededError(
                        f"Per_request limit exceeded: ${amount:.2f} > ${self.config.per_request_limit:.2f}"
                    )

                # Record the cost
                records.append(record)
                await self._save_daily_records(records, today)

                # Update iteration count
                self._session_iterations[session_id] = self._session_iterations.get(session_id, 0) + 1

            except BudgetExceededError:
                raise
            except Exception as e:
                if not self.config.fail_open:
                    raise BudgetExceededError(f"Storage error (fail closed): {e}")
                # fail_open: allow the request but log the error
                # In production, you'd want to log this

    async def check_budget(
        self,
        estimated_cost: float,
        session_id: str,
    ) -> tuple[bool, str]:
        """
        Check if a request can proceed without recording.

        Args:
            estimated_cost: Estimated cost of the request
            session_id: Session identifier

        Returns:
            Tuple of (can_proceed, reason)
        """
        await self._ensure_initialized()

        async with self._lock:
            records = await self._get_daily_records()

            # Check session limit
            session_spent = sum(r.amount for r in records if r.session_id == session_id)
            if session_spent + estimated_cost > self.config.per_session_limit:
                return False, f"Would exceed session limit (${session_spent + estimated_cost:.2f} > ${self.config.per_session_limit:.2f})"

            # Check daily limit
            daily_spent = sum(r.amount for r in records)
            if daily_spent + estimated_cost > self.config.global_daily_limit:
                return False, f"Would exceed daily limit (${daily_spent + estimated_cost:.2f} > ${self.config.global_daily_limit:.2f})"

            return True, "OK"

    async def get_status(self) -> BudgetStatus:
        """Get current budget status."""
        await self._ensure_initialized()

        async with self._lock:
            records = await self._get_daily_records()
            daily_spent = sum(r.amount for r in records)

            # Calculate monthly spent (sum all days in current month)
            monthly_spent = daily_spent  # Start with today

            # Get all daily keys for this month
            now = datetime.utcnow()
            month_prefix = f"budget:daily:{now.strftime('%Y-%m')}"

            try:
                keys = await self.storage.list_keys(month_prefix)
                for key in keys:
                    date_str = key.replace("budget:daily:", "")
                    if date_str != now.strftime("%Y-%m-%d"):  # Don't double count today
                        try:
                            day_records = await self.storage.load(key)
                            for r in day_records:
                                monthly_spent += r.get("amount", 0)
                        except Exception:
                            pass
            except Exception:
                pass

            daily_remaining = max(0, self.config.global_daily_limit - daily_spent)
            monthly_remaining = max(0, self.config.global_monthly_limit - monthly_spent)

            warning_threshold = self.config.warning_threshold
            daily_warning = daily_spent >= self.config.global_daily_limit * warning_threshold

            percent_used = (daily_spent / self.config.global_daily_limit * 100) if self.config.global_daily_limit > 0 else 0

            return BudgetStatus(
                daily_spent=daily_spent,
                monthly_spent=monthly_spent,
                daily_remaining=daily_remaining,
                monthly_remaining=monthly_remaining,
                daily_warning=daily_warning,
                percent_used=percent_used,
            )

    async def get_session_spent(self, session_id: str) -> float:
        """Get total spent for a session."""
        await self._ensure_initialized()

        async with self._lock:
            records = await self._get_daily_records()
            return sum(r.amount for r in records if r.session_id == session_id)

    async def get_session_status(self, session_id: str) -> BudgetStatus:
        """Get budget status for a session."""
        await self._ensure_initialized()

        async with self._lock:
            records = await self._get_daily_records()
            session_spent = sum(r.amount for r in records if r.session_id == session_id)

            remaining = max(0, self.config.per_session_limit - session_spent)
            warning = session_spent >= self.config.per_session_limit * self.config.warning_threshold
            percent_used = (session_spent / self.config.per_session_limit * 100) if self.config.per_session_limit > 0 else 0

            return BudgetStatus(
                daily_spent=session_spent,
                total_spent=session_spent,
                remaining=remaining,
                warning=warning,
                percent_used=percent_used,
            )

    async def get_records(
        self,
        session_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        model: Optional[str] = None,
    ) -> List[CostRecord]:
        """
        Query cost records.

        Args:
            session_id: Filter by session
            start_date: Filter by start date
            end_date: Filter by end date
            model: Filter by model

        Returns:
            List of matching cost records
        """
        await self._ensure_initialized()

        # Default to today if no date range
        if start_date is None and end_date is None:
            start_date = datetime.utcnow().date()
            end_date = start_date

        if start_date is None:
            start_date = end_date
        if end_date is None:
            end_date = start_date

        results: List[CostRecord] = []

        # Iterate through date range (ensure both dates are set)
        if start_date is None or end_date is None:
            return results

        current: date = start_date
        while current <= end_date:
            day_records = await self._get_daily_records(current)
            results.extend(day_records)
            current = current + timedelta(days=1)

        # Apply filters
        if session_id:
            results = [r for r in results if r.session_id == session_id]
        if model:
            results = [r for r in results if r.model == model]

        return results

    async def register_team(self, team_id: str, member_ids: List[str]) -> None:
        """Register a team with member IDs."""
        await self._ensure_initialized()

        async with self._lock:
            self._teams[team_id] = member_ids
            await self.storage.save("budget:teams", self._teams)

    async def get_team_status(self, team_id: str) -> BudgetStatus:
        """Get budget status for a team."""
        await self._ensure_initialized()

        if team_id not in self._teams:
            return BudgetStatus()

        member_ids = self._teams[team_id]

        async with self._lock:
            records = await self._get_daily_records()
            team_spent = sum(r.amount for r in records if r.user_id in member_ids)

            team_limit = self.config.team_daily_limit or self.config.global_daily_limit
            remaining = max(0, team_limit - team_spent)

            return BudgetStatus(
                total_spent=team_spent,
                remaining=remaining,
                daily_spent=team_spent,
            )
