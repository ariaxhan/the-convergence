# Dashboard & HITL Quick Start (One-Pager)

**Use this to:** Pick a framework, implement Phase 1 HITL, integrate with Convergence RL loop.

---

## Step 1: Pick Your Framework (2 options)

### Option A: Plotly Dash (Recommended for Simplicity)
**When:** Building approval dashboard for 20-200 concurrent users; want built-in callbacks.

```python
# pip install plotly dash
import dash
from dash import callback, dcc, html, Input, Output, State

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Approval Dashboard"),
    html.Div(id="pending-list"),
    html.Button("Approve", id="approve-btn"),
    html.Textarea(id="reason"),
])

@callback(
    Output("pending-list", "children"),
    Input("approve-btn", "n_clicks"),
    State("reason", "value"),
)
async def on_approve(n_clicks, reason):
    if n_clicks == 0:
        return "No decisions pending"
    
    # Log approval to audit table
    await log_approval_event(
        decision_id=current_decision_id,
        user_id=current_user.id,
        reason=reason,
    )
    
    # Update RL reward
    await update_mab_reward(arm=policy_variant, reward=1.0)
    
    return "Approved!"
```

**Setup:** 2 hours | **Scaling:** Up to 200 concurrent | **Real-time:** Polling only

---

### Option B: FastAPI + React (Recommended for Real-Time)
**When:** Need WebSocket live updates; embedding in existing admin panel; high concurrency (1000+).

```python
# pip install fastapi[websockets] sqlalchemy
from fastapi import FastAPI, WebSocket
import asyncio

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)
    
    async def broadcast(self, data: dict):
        for ws in self.active:
            try:
                await ws.send_json(data)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/decisions")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send initial state
    await websocket.send_json({
        "type": "state",
        "pending_decisions": await get_pending_decisions(),
    })
    
    # Listen for user actions
    while True:
        try:
            action = await websocket.receive_json()
            
            if action["type"] == "approve":
                # Log to audit table
                await log_approval_event(
                    decision_id=action["decision_id"],
                    user_id=current_user.id,
                    reason=action.get("reason"),
                )
                
                # Update RL reward
                await update_mab_reward(
                    arm=action.get("policy_variant"),
                    reward=1.0,
                )
                
                # Broadcast update to all clients
                await manager.broadcast({
                    "type": "decision_updated",
                    "decision_id": action["decision_id"],
                    "status": "approved",
                })
        except:
            break
```

**Setup:** 4 hours | **Scaling:** 1000+ concurrent | **Real-time:** < 100ms WebSocket

---

## Step 2: Add Audit Logging (Required for Compliance)

```python
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from datetime import datetime
import uuid

Base = declarative_base()

class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id = Column(String, nullable=False)
    policy_variant = Column(String, nullable=False)
    confidence = Column(float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    action = Column(String, nullable=False)  # "approved", "rejected", "auto_approved"
    reason = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    # Prevent updates (immutable)

# Auto-log all approvals
@event.listens_for(ApprovalDecision, 'after_insert')
def log_approval(mapper, connection, target):
    audit = AuditLog(
        decision_id=target.decision_id,
        user_id=target.approved_by,
        action="approved",
        reason=target.reason,
    )
    connection.execute(AuditLog.__table__.insert(), audit.__dict__)
```

---

## Step 3: Implement Risk-Based Routing (Auto-Approve 80%)

```python
async def should_require_approval(decision: dict) -> bool:
    """
    Return True if human approval needed.
    Auto-approve high-confidence, low-risk decisions.
    """
    confidence = decision.get("confidence", 0.0)
    false_positive_rate = await compute_fpr(decision["pattern_id"])
    
    # High confidence + low FPR = auto-approve
    if confidence >= 0.95 and false_positive_rate <= 0.05:
        return False
    
    # Uncertain or risky = human review
    return True

async def process_decision(decision: dict):
    if await should_require_approval(decision):
        # Queue for human review
        await queue_for_approval(decision)
        return {"status": "pending_approval", "url": "/dashboard/approve"}
    else:
        # Auto-approve
        await execute_decision(decision)
        await log_audit_event(
            decision_id=decision["id"],
            user_id="system",
            action="auto_approved",
            reason="high_confidence_low_risk",
        )
        # Positive reward signal
        await update_mab_reward(arm=decision["policy_variant"], reward=1.0)
        return {"status": "approved"}
```

---

## Step 4: Connect to Convergence RL Loop

```python
# In your thompson_sampling.py or reward_computation.py

async def compute_arm_reward(
    arm: str,
    decision_outcome: str,  # "approved", "rejected", "auto_approved"
    metrics: dict,  # {"confidence": 0.92, "fpr": 0.05}
) -> float:
    """
    Compute reward from approval outcome + metrics.
    
    - If approved: +1.0 (human validated the policy)
    - If rejected: -1.0 (policy was wrong)
    - If auto-approved: +0.8 (high confidence but not human-reviewed)
    """
    base_reward = {
        "approved": 1.0,
        "rejected": -1.0,
        "auto_approved": 0.8,
    }[decision_outcome]
    
    # Bonus for low FPR
    fpr_bonus = max(0.0, (0.1 - metrics.get("fpr", 0.0)) * 10)
    
    # Penalty for low confidence
    confidence_penalty = max(0.0, (0.9 - metrics.get("confidence", 0.9)) * 5)
    
    return base_reward + fpr_bonus - confidence_penalty

# Wire into MAB update
async def update_from_approval_outcome(
    decision_id: str,
    outcome: str,
    reason: str,
):
    decision = await db.get_decision(decision_id)
    metrics = await fetch_decision_metrics(decision)
    
    reward = await compute_arm_reward(
        arm=decision["policy_variant"],
        decision_outcome=outcome,
        metrics=metrics,
    )
    
    # Update Thompson Sampling state
    await update_thompson_sampling(
        arm=decision["policy_variant"],
        reward=reward,
        context={"reason": reason, "metrics": metrics},
    )
    
    # If rejected: trigger SAO (Self-Adaptive Optimization)
    if outcome == "rejected":
        await trigger_policy_evolution(
            failed_decision=decision,
            human_feedback=reason,
        )
```

---

## Step 5: Expose Metrics (Prometheus)

```python
# pip install prometheus-client

from prometheus_client import Counter, Gauge, Histogram

# Dashboard metrics
pending_approvals = Gauge(
    'hitl_pending_approvals',
    'Number of pending approvals',
)

approvals_total = Counter(
    'hitl_approvals_total',
    'Total approvals',
    ['outcome'],  # outcome: approved, rejected, auto_approved
)

approval_time = Histogram(
    'hitl_approval_time_seconds',
    'Time from decision to approval',
    buckets=(30, 60, 300, 900, 3600),
)

# RL metrics
mab_reward = Gauge(
    'mab_reward_total',
    'Total reward per arm',
    ['arm'],
)

# In your approval handler:
async def record_approval(outcome: str, decision_time_seconds: float):
    approvals_total.labels(outcome=outcome).inc()
    approval_time.observe(decision_time_seconds)
    pending_approvals.dec()
```

---

## Step 6: Visualize in Grafana (Optional, Phase 2)

```
# Prometheus queries:

# Queue depth
hitl_pending_approvals

# Approval rate (last 24h)
increase(hitl_approvals_total{outcome="approved"}[24h])
/
(increase(hitl_approvals_total[24h]))

# Avg approval time
histogram_quantile(0.5, hitl_approval_time_seconds_bucket)

# Auto-approve rate
increase(hitl_approvals_total{outcome="auto_approved"}[24h])
/
(increase(hitl_approvals_total[24h]))
```

---

## Checklist for Phase 1

- [ ] Pick Dash OR FastAPI+React
- [ ] Create approval form UI
- [ ] Add SQLAlchemy audit table
- [ ] Wire up SQLAlchemy event listener
- [ ] Implement `should_require_approval()` logic
- [ ] Add approval/rejection handlers
- [ ] Test with 5-10 manual decisions
- [ ] Document approval reason field requirements
- [ ] Set up logging (structlog for JSON-friendly format)
- [ ] Deploy to staging; test with team

**Expected time: 16 hours**  
**Expected output: Functional approval workflow with audit trail**

---

## Testing the Approval Flow

```python
# tests/test_hitl_approval.py

async def test_auto_approve_high_confidence():
    """Low-risk, high-confidence decisions bypass approval."""
    decision = {
        "id": "test-1",
        "pattern_id": "email",
        "confidence": 0.98,
        "policy_variant": "regex_v2",
    }
    
    result = await process_decision(decision)
    assert result["status"] == "approved"
    
    # Check audit log
    audit = await db.get_audit_log("test-1")
    assert audit.action == "auto_approved"
    assert audit.reason == "high_confidence_low_risk"

async def test_human_review_uncertain():
    """Low-confidence decisions require approval."""
    decision = {
        "id": "test-2",
        "pattern_id": "email",
        "confidence": 0.65,
        "policy_variant": "classifier_v1",
    }
    
    result = await process_decision(decision)
    assert result["status"] == "pending_approval"
    
    # Check it's in approval queue
    pending = await db.get_pending_approvals()
    assert any(d["id"] == "test-2" for d in pending)

async def test_approval_logs_audit():
    """Approvals are immutably logged."""
    await approve_decision(
        decision_id="test-3",
        user_id="alice@example.com",
        reason="Pattern matches test cases correctly",
    )
    
    audit = await db.get_audit_log("test-3")
    assert audit.user_id == "alice@example.com"
    assert audit.action == "approved"
    assert audit.timestamp is not None
```

---

## One-Line Summary

**Auto-approve high-confidence, low-risk decisions; human-review uncertain cases; log every decision to immutable audit table; feed rejections back to RL loop as negative rewards.**

---

## Resources

- [Full Dashboard Research](dashboard-hitl-research.md) - 984 lines with anti-patterns, all frameworks, HITL patterns
- [Research Summary](DASHBOARD-HITL-SUMMARY.md) - Executive summary with scorecard
- [Dash Docs](https://dash.plotly.com/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Events](https://docs.sqlalchemy.org/en/21/orm/events.html)
- [Prometheus Metrics](https://prometheus.io/docs/instrumenting/writing_clientlibs/)

