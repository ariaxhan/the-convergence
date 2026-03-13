# Enterprise Integration

Deploy The Convergence in production environments.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Your Application                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Safety    │  │  Runtime    │  │   Observability    │  │
│  │  Injection  │  │  select()   │  │   NativeObserver   │  │
│  │  Budget     │  │  update()   │  │   WeaveObserver    │  │
│  │  Audit      │  │             │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                     Storage Layer                            │
│     SQLite (dev) │ PostgreSQL (prod) │ Custom Backend        │
└─────────────────────────────────────────────────────────────┘
```

## Storage Backends

### SQLite (Development)

```python
from convergence.storage.sqlite import SQLiteStorage

storage = SQLiteStorage(db_path="./convergence.db")
await storage.initialize()
```

### PostgreSQL (Production)

```python
from convergence.storage.postgres import PostgresStorage

storage = PostgresStorage(
    connection_string="postgresql://user:pass@host:5432/dbname",
)
await storage.initialize()
```

### Custom Backend

Implement the storage protocol:

```python
from convergence.storage.runtime_protocol import RuntimeStorageProtocol
from typing import List, Dict, Optional

class CustomStorage(RuntimeStorageProtocol):
    async def get_arms(
        self,
        *,
        user_id: str,
        agent_type: str,
    ) -> List[Dict[str, object]]:
        # Return list of arm dicts
        ...

    async def initialize_arms(
        self,
        *,
        user_id: str,
        agent_type: str,
        arms: List[Dict[str, object]],
    ) -> None:
        # Initialize arms for user
        ...

    async def create_decision(
        self,
        *,
        user_id: str,
        agent_type: str,
        arm_pulled: str,
        strategy_params: Dict[str, object],
        arms_snapshot: List[Dict[str, object]],
        metadata: Dict[str, object],
    ) -> Optional[str]:
        # Create decision record, return decision_id
        ...

    async def get_decision(
        self,
        *,
        user_id: str,
        decision_id: str,
    ) -> Dict[str, object]:
        # Return decision record
        ...

    async def update_performance(
        self,
        *,
        user_id: str,
        agent_type: str,
        decision_id: str,
        reward: float,
        engagement: float,
        grading: Optional[float],
        metadata: Optional[Dict[str, object]],
        computed_update: Optional[Dict[str, object]],
    ) -> Dict[str, object]:
        # Update arm with reward, return status
        ...
```

## Multi-System Deployment

Run multiple systems with different configurations:

```python
from convergence.runtime.online import configure, select, update
from convergence.types import RuntimeConfig, RuntimeArmTemplate

# System 1: Code generation
await configure(
    "code-agent",
    config=RuntimeConfig(
        system="code-agent",
        default_arms=[
            RuntimeArmTemplate(arm_id="gpt-4", name="GPT-4", params={"model": "gpt-4"}),
            RuntimeArmTemplate(arm_id="claude-3", name="Claude 3", params={"model": "claude-3-sonnet"}),
        ],
    ),
    storage=storage,
)

# System 2: Customer support
await configure(
    "support-agent",
    config=RuntimeConfig(
        system="support-agent",
        default_arms=[
            RuntimeArmTemplate(arm_id="gpt-3.5", name="GPT-3.5", params={"model": "gpt-3.5-turbo"}),
            RuntimeArmTemplate(arm_id="gpt-4", name="GPT-4", params={"model": "gpt-4"}),
        ],
    ),
    storage=storage,
)

# Select from appropriate system
code_selection = await select("code-agent", user_id="user-123")
support_selection = await select("support-agent", user_id="user-123")
```

## User Isolation

Arms are tracked per-user by default:

```python
# User A gets their own arm statistics
selection_a = await select("my-agent", user_id="user-a")
await update("my-agent", user_id="user-a", decision_id=selection_a.decision_id, reward=0.9)

# User B gets their own arm statistics
selection_b = await select("my-agent", user_id="user-b")
await update("my-agent", user_id="user-b", decision_id=selection_b.decision_id, reward=0.7)
```

For shared learning across users, use a common user_id:

```python
# All users share the same arm statistics
selection = await select("my-agent", user_id="global")
```

## Agent Types

Segment learning by agent type within a system:

```python
config = RuntimeConfig(
    system="my-app",
    agent_type="summarizer",  # Default agent type
    default_arms=[...],
)

# Override per-request
selection = await select(
    "my-app",
    user_id="user-123",
    agent_type="translator",  # Different agent type
)
```

## Production Checklist

### Before Deployment

- [ ] Choose production storage backend (PostgreSQL recommended)
- [ ] Configure budget limits
- [ ] Enable audit logging
- [ ] Set up injection detection
- [ ] Configure observability export

### Safety Configuration

```python
from convergence.safety import (
    InjectionDetector,
    OutputValidator,
    BudgetManager,
    BudgetConfig,
    AuditLogger,
)

# Required for production
detector = InjectionDetector(sensitivity="high", mode="block")
validator = OutputValidator(detect_pii=True, detect_secrets=True, mode="redact")
budget = BudgetManager(
    storage=storage,
    config=BudgetConfig(
        global_daily_limit=1000.0,
        per_session_limit=50.0,
        per_request_limit=5.0,
        warning_threshold=0.8,
    ),
)
audit = AuditLogger(log_path="/var/log/convergence/audit.jsonl")
```

### Monitoring

```python
from convergence.observability import NativeObserver

observer = NativeObserver()

# Track all decisions
selection = await select("my-agent", user_id="user-123")
observer.track_arm_selection(selection.arm_id)

# After getting reward
observer.track_regret(optimal_reward=1.0, actual_reward=reward)
observer.track_cost(actual_cost, model=selection.arm_id)

# Export metrics periodically
metrics_json = observer.export_json()
# Send to your monitoring system
```

## Error Handling

### Storage Failures

```python
from convergence.runtime.online import select

try:
    selection = await select("my-agent", user_id="user-123")
except Exception as e:
    # Fall back to default arm
    selection = fallback_selection
    logger.error(f"Selection failed: {e}")
```

### Budget Exceeded

```python
from convergence.safety import BudgetExceededError

try:
    can_proceed, reason = await budget.check_budget(
        estimated_cost=0.05,
        session_id="session-123",
    )
    if not can_proceed:
        raise BudgetExceededError(reason)
except BudgetExceededError as e:
    # Return cached response or simplified fallback
    return cached_response
```

## Scaling Considerations

### Cache TTL

Reduce database load with appropriate cache TTL:

```python
config = RuntimeConfig(
    system="my-agent",
    cache_ttl_seconds=60,  # Cache arm state for 60s
    default_arms=[...],
)
```

### Connection Pooling

For PostgreSQL, use connection pooling:

```python
storage = PostgresStorage(
    connection_string="postgresql://...",
    pool_size=20,
    max_overflow=10,
)
```

### Read Replicas

For high-read workloads, use read replicas:

```python
storage = PostgresStorage(
    connection_string="postgresql://primary:5432/db",
    read_replica="postgresql://replica:5432/db",
)
```

## Migrations

### Schema Updates

The storage backends auto-create tables on `initialize()`. For schema changes:

```python
# Run migrations before starting app
await storage.migrate()
```

### Data Export

Export arm statistics for backup:

```python
# Export all arms for a system
arms_data = await storage.export_arms(system="my-agent")

# Import on new system
await storage.import_arms(system="my-agent", data=arms_data)
```

## Testing

### Integration Tests

```python
import pytest
from convergence.runtime.online import configure, select, update
from convergence.storage.sqlite import SQLiteStorage

@pytest.fixture
async def test_storage():
    storage = SQLiteStorage(db_path=":memory:")
    await storage.initialize()
    return storage

async def test_learning_loop(test_storage):
    config = RuntimeConfig(
        system="test",
        default_arms=[
            RuntimeArmTemplate(arm_id="a", name="A", params={}),
            RuntimeArmTemplate(arm_id="b", name="B", params={}),
        ],
    )
    await configure("test", config=config, storage=test_storage)

    # Simulate 100 decisions
    for _ in range(100):
        selection = await select("test", user_id="test-user")
        reward = 0.9 if selection.arm_id == "a" else 0.5
        await update("test", user_id="test-user", decision_id=selection.decision_id, reward=reward)

    # After learning, arm "a" should be selected more often
    selections = [await select("test", user_id="test-user") for _ in range(10)]
    a_count = sum(1 for s in selections if s.arm_id == "a")
    assert a_count >= 7  # At least 70% should be "a"
```

## Deployment Examples

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV CONVERGENCE_DB_URL=postgresql://...
ENV CONVERGENCE_AUDIT_PATH=/var/log/convergence/audit.jsonl

CMD ["python", "-m", "your_app"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convergence-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: your-app:latest
        env:
        - name: CONVERGENCE_DB_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        volumeMounts:
        - name: audit-logs
          mountPath: /var/log/convergence
      volumes:
      - name: audit-logs
        persistentVolumeClaim:
          claimName: audit-logs-pvc
```
