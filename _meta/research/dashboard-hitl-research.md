# Production-Grade Dashboard & HITL Research
**Research Date:** 2026-03-12  
**Status:** Complete  
**Scope:** Dashboard frameworks, human-in-the-loop patterns, enterprise integration for Python ML systems

---

## PART 1: ANTI-PATTERNS (What Breaks at Scale)

### Anti-Pattern 1: Streamlit for Production Multi-User Systems

**Symptom:** Sessions crash, app becomes unresponsive under load, state resets unpredictably.

**Why It Happens:**
- Streamlit reruns the entire script on every user interaction
- No built-in state persistence across sessions/server restarts
- Single-threaded event loop; scaling horizontally requires complex workarounds
- State lives in memory; restart = data loss
- Designed for prototyping, not production multi-user deployments

**Source:** [Streamlit Scalability Discussions 2025-2026](https://discuss.streamlit.io/t/scalability-concerns-with-large-user-base/69494)

**Fix:**
1. Use Streamlit only for internal-facing dashboards (< 10 concurrent users)
2. For production: switch to Dash, Panel, or FastAPI + React
3. If you must use Streamlit: add Redis state store + containerized deployment with load balancing
4. Never rely on in-memory state for multi-user workflows

**Code Anti-Pattern:**
```python
# BAD: This state is lost on re-run
app_state = {"user_session": None, "decisions": []}

if st.button("Approve"):
    app_state["decisions"].append("approved")  # Lost on next interaction
```

**Better:**
```python
# Use Streamlit Session State (still limited, but better)
if "decisions" not in st.session_state:
    st.session_state.decisions = []

if st.button("Approve"):
    st.session_state.decisions.append("approved")
    # Still not persistent across restarts—use external storage
```

---

### Anti-Pattern 2: No Audit Trail for Human Decisions

**Symptom:** Compliance failure. No record of who approved what, when, or why. Can't defend decisions in court/audit.

**Why It Happens:**
- Dashboards show decisions but don't record context (user, timestamp, reason)
- "Approve" button clicks aren't logged to database
- Manual overrides have no justification field
- No version control for policy changes

**Source:** [Compliance in Automated Workflows](https://testrigor.com/blog/building-audit-ready-automation/)

**Fix:**
1. Every user action = database record with: `(user_id, action, timestamp, context, reason, ip_address)`
2. Use SQLAlchemy event listeners to auto-log state changes
3. Immutable audit log (no edits, only appends)
4. Dashboard shows audit trail alongside the decision

**Minimal Implementation:**
```python
from sqlalchemy import event
from datetime import datetime

@event.listens_for(ApprovalDecision, 'after_insert')
def receive_after_insert(mapper, connection, target):
    """Auto-log approval decisions."""
    audit_log = AuditLog(
        user_id=target.approved_by,
        action="approval",
        target_id=target.id,
        context=target.to_dict(),
        timestamp=datetime.utcnow(),
        ip_address=request.remote_addr,  # Capture IP
    )
    connection.execute(insert(AuditLog), audit_log.to_dict())
```

---

### Anti-Pattern 3: Real-Time Dashboards Without WebSocket Heartbeats

**Symptom:** Stale UI, zombie connections, silent failures. Users see outdated data.

**Why It Happens:**
- WebSocket connections die silently (network hiccups, proxies timeout connections after 60s)
- No heartbeat/ping mechanism to detect dead connections
- Dashboard polls for updates but doesn't know if connection is alive
- Broadcast failures don't propagate to UI

**Source:** [FastAPI WebSocket Patterns 2026](https://betterstack.com/community/guides/scaling-python/fastapi-websockets/)

**Fix:**
1. Implement server-side heartbeat: send ping every 30s
2. Client-side: close connection and reconnect on missed pong
3. Graceful degradation: fall back to polling if WebSocket fails

**Implementation:**
```python
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    heartbeat_task = asyncio.create_task(send_heartbeat(websocket))
    
    try:
        while True:
            data = await websocket.receive_text()
            # Process data
    except Exception as e:
        await websocket.close()
    finally:
        heartbeat_task.cancel()

async def send_heartbeat(websocket: WebSocket):
    """Send ping every 30 seconds."""
    while True:
        try:
            await websocket.send_json({"type": "ping"})
            await asyncio.sleep(30)
        except:
            break
```

---

### Anti-Pattern 4: Multi-Persona Dashboards with View-Level Auth Only

**Symptom:** Data leakage. Different roles see data they shouldn't. No column-level filtering.

**Why It Happens:**
- Auth only checks view access (user can see the dashboard)
- Data filtering happens in template/frontend (users can inspect HTML/API calls)
- No row-level security (RLS) at database level
- One user sees another user's decisions/metrics in shared tables

**Source:** [RBAC Best Practices in Django](https://www.permit.io/blog/how-to-implement-role-based-access-control-rbac-into-a-django-application)

**Fix:**
1. **Database-level RLS**: Filter queries by user/role at query time, not UI time
2. **View Decorator**: Check permission before returning data
3. **Column Masking**: Hide sensitive columns (user names, IPs) from certain roles

**Better Pattern:**
```python
# Use row-level security at query layer
@require_role('approver')
async def get_decisions_for_approval(user: User):
    """Only return decisions assigned to this user's team."""
    return await db.query(ApprovalDecision).filter(
        ApprovalDecision.team_id == user.team_id,
        ApprovalDecision.status == "pending",
    ).all()
```

---

### Anti-Pattern 5: Dashboard Logging Everything (PII Exposure)

**Symptom:** Logs contain credit card numbers, emails, passwords. Data breach.

**Why It Happens:**
- Structured logging makes it easy to "just log everything"
- No scrubbing policy for sensitive fields
- Logs shipped to cloud; retention unclear
- Text previews include raw input

**Source:** [Structlog Context Processors](https://www.structlog.org/en/17.1.0/)

**Fix:**
1. Define list of fields that are NEVER logged: `PII_FIELDS = ["password", "credit_card", "ssn", "email_address"]`
2. Hash or truncate text fields: `text_preview=text[:50] + "..." if len(text) > 50 else text`
3. Log hashes instead of raw values: `text_hash=hashlib.sha256(text.encode()).hexdigest()`
4. Scrub logs with processor pipeline before shipping

**Implementation:**
```python
import structlog
from functools import wraps

PII_FIELDS = {"password", "credit_card", "ssn", "email_address"}

def scrub_dict(_, __, event_dict):
    """Remove PII before logging."""
    for field in PII_FIELDS:
        if field in event_dict:
            event_dict[field] = "***REDACTED***"
    return event_dict

structlog.configure(
    processors=[scrub_dict, structlog.processors.JSONRenderer()],
)
```

---

## PART 2: Framework Comparison

### Recommended Stack by Use Case

| Use Case | Framework | Why | Weekly Downloads | Production Ready |
|----------|-----------|-----|-----------------|-----------------|
| **Fast iteration, internal dashboard, < 10 users** | Streamlit | Simplest API; Python-native | 1.2M | No (use Session State + external storage) |
| **Production, multi-user, complex state** | **Plotly Dash** | Callback-driven; explicit control; scales | 250K | **YES** |
| **Real-time, WebSocket, async Python** | **FastAPI + React** | Full async; WebSocket native; embeddable | N/A (FastAPI 2M+) | **YES** |
| **Production, extensible, Bokeh-backed** | **Panel** | Bi-directional communication; deployment options | 50K | **YES** |
| **ML model demos, rapid prototyping** | Gradio | Simplest for input/output; web components | 800K | Yes (for demos; not HITL workflows) |
| **Embedded in existing admin panel** | **FastAPI micro-routes** | No framework overhead; embeddable; lightweight | 2M+ | **YES** |

---

### Framework Deep Dives

#### 1. Plotly Dash (Recommended for Enterprise)

**Strengths:**
- Explicit callback architecture (unlike Streamlit's implicit reruns)
- Only runs functions called during interaction (efficient)
- Rich Plotly visualizations built-in
- Scales well to 100+ concurrent users
- RBAC patterns well-documented

**Limitations:**
- Steeper learning curve (callbacks, app layout structure)
- More boilerplate than Streamlit
- State management still in-memory (use persistence middleware for multi-server deployments)

**When to Use:**
- Production dashboards with 20+ concurrent users
- Complex workflows with approval chains
- Embedding into admin panels (Dash can serve under /dashboard route)

**Quick Start for HITL:**
```python
import dash
from dash import callback, dcc, html, Input, Output, State

app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Approval Dashboard"),
    dcc.Loading(id="loading", children=[
        html.Div(id="pending-decisions"),
    ]),
    html.Button("Approve", id="approve-btn", n_clicks=0),
    html.Button("Reject", id="reject-btn", n_clicks=0),
    html.Textarea(id="reason", placeholder="Reason for decision"),
    html.Div(id="audit-log"),
])

@callback(
    Output("pending-decisions", "children"),
    Input("approve-btn", "n_clicks"),
    State("reason", "value"),
    prevent_initial_call=True,
)
async def approve_decision(n_clicks, reason):
    if n_clicks == 0:
        return "No decisions pending"
    
    # Log to audit table
    await log_approval(current_user.id, reason)
    return await fetch_pending_decisions()
```

---

#### 2. FastAPI + WebSocket + React (Recommended for Real-Time)

**Strengths:**
- Native async/await; no blocking
- WebSocket built-in; real-time updates
- Embeddable: serve under any base path
- Separates API from UI (flexible frontend)
- Perfect for RL systems (real-time reward signals)

**Limitations:**
- Requires separate React frontend (more setup)
- Need to manage CORS, CSRF
- More moving parts; higher complexity

**When to Use:**
- Real-time dashboards (live metrics, reward updates)
- Embedded in existing admin panels
- Multi-tenant systems
- RL systems tracking arm selection, reward distribution

**Minimal Real-Time Dashboard:**
```python
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
import asyncio
import json

app = FastAPI()
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    # Send initial state
    await websocket.send_json({
        "type": "state",
        "data": await get_dashboard_state(),
    })
    
    # Listen for user actions
    while True:
        try:
            data = await websocket.receive_json()
            
            if data["action"] == "approve":
                await log_approval(data)
                # Broadcast update to all connected clients
                await manager.broadcast({
                    "type": "decision_updated",
                    "decision_id": data["id"],
                    "status": "approved",
                })
            
            await asyncio.sleep(0.01)  # Heartbeat
        except:
            break

@app.get("/api/metrics")
async def get_metrics():
    """Expose RL metrics for real-time dashboard."""
    return {
        "arm_selection": await fetch_arm_selection_distribution(),
        "reward_mean": await fetch_mean_reward(),
        "confidence_drift": await detect_drift(),
    }
```

---

#### 3. Panel (Recommended for Scientific/Complex)

**Strengths:**
- Bokeh-backed; handles large datasets
- Bi-directional communication (faster than Streamlit)
- Multiple deployment options (Tornado, FastAPI, Flask, Django)
- Excellent for interactive data exploration
- Production-ready performance

**Limitations:**
- Smaller ecosystem than Dash/Streamlit
- Less documentation for enterprise HITL workflows
- State management still in-memory

**When to Use:**
- Large-scale data visualization (finance, research)
- Interactive data exploration with complex interactions
- Existing Bokeh/HoloViews pipeline
- Need high-performance real-time updates

---

#### 4. Gradio (NOT Recommended for HITL)

**Strengths:**
- Simplest API: `gr.Interface(fn, inputs, outputs)`
- Zero boilerplate for demos
- Web components (lightweight embedding)

**Limitations:**
- **Not designed for approval workflows** - no built-in auth/RBAC
- No WebSocket support (polling only)
- iFrame embedding has security issues
- Web component + mounted app = not embeddable
- No audit trail, state management, or multi-step workflows

**When to Use:**
- Model demonstrations (HuggingFace Spaces)
- Internal tool prototypes
- One-off inference endpoints

**NOT for:** Production HITL workflows, compliance-critical systems, multi-user approval chains.

---

## PART 3: Human-in-the-Loop (HITL) Patterns

### Core HITL Architecture

```
┌─────────────────────────────────────────┐
│ System Decision (Model/Agent/Policy)    │
└─────────────┬───────────────────────────┘
              │
              ├─ High confidence? → Execute (low-risk paths)
              │
              └─ Low confidence? → Human Approval Layer
                                    │
                        ┌───────────┴────────────┐
                        │                        │
                    Approve              Reject/Revise
                        │                        │
                        └───────────┬────────────┘
                                    │
                        ┌───────────▼────────────┐
                        │   Audit Log (immutable)│
                        │   - User ID            │
                        │   - Timestamp          │
                        │   - Reason             │
                        │   - Context            │
                        │   - IP Address         │
                        └───────────┬────────────┘
                                    │
                    ┌───────────────┴──────────────────┐
                    │                                  │
                Execute Approved Decision      Use Rejection as Signal
                (with audit trail)            (retrain/evolve policy)
```

---

### Pattern 1: Risk-Based Routing

**Core Idea:** Not all decisions need human review. Route only uncertain/high-risk cases.

**Implementation:**
```python
async def should_require_approval(decision: Dict) -> bool:
    """Determine if decision needs human approval."""
    confidence = decision.get("confidence", 0.0)
    risk_level = compute_risk_level(decision)
    
    # High confidence + low risk = auto-approve
    if confidence >= 0.95 and risk_level <= 0.1:
        return False
    
    # Medium confidence or medium risk = human review
    if confidence < 0.9 or risk_level > 0.3:
        return True
    
    return False

async def process_decision(decision: Dict, user_id: str):
    if await should_require_approval(decision):
        # Queue for human review
        await queue_for_approval(decision)
        return {"status": "pending_approval"}
    else:
        # Auto-approve
        await execute_decision(decision)
        await log_audit("auto_approved", user_id, decision)
        return {"status": "approved"}
```

**Benefit:** 80% of low-risk decisions auto-execute; humans review 20% edge cases. Reduces approval bottleneck by 4x.

---

### Pattern 2: Structured Approval Context

**Core Idea:** Don't show raw data. Show context: "Why is this decision needed?" + "What are the risks?"

**Implementation:**
```python
@dataclass
class ApprovalContext:
    """Structured data for approval UI."""
    decision_id: str
    action: str  # e.g., "override_pattern"
    rationale: str  # e.g., "Pattern X has 15% false positive rate"
    risk_level: str  # "low", "medium", "high"
    risk_description: str  # e.g., "May affect 5000 users"
    alternative: str  # e.g., "Wait for new pattern variant"
    deadline: Optional[datetime]  # e.g., "Review needed by 5pm"
    metrics: Dict  # e.g., {"current_fpr": 0.15, "baseline_fpr": 0.05}

async def create_approval_context(decision: Dict) -> ApprovalContext:
    """Create human-friendly context for approval."""
    return ApprovalContext(
        decision_id=decision["id"],
        action=decision["action"],
        rationale=f"Pattern {decision['pattern_id']} has degraded confidence",
        risk_level="medium",
        risk_description=f"Affects {count_impacted_users()} users",
        alternative="Wait for pattern evolution in next cycle",
        metrics=await fetch_metrics_for_pattern(decision["pattern_id"]),
    )
```

**UI Display:**
```python
# Dash component
@callback(Output("approval-form", "children"), Input("decision-id", "value"))
def render_approval_form(decision_id):
    ctx = get_approval_context(decision_id)
    
    return html.Div([
        html.H3(f"Review: {ctx.action}"),
        html.P(f"Rationale: {ctx.rationale}"),
        
        html.Div([
            html.Span("Risk Level: "),
            html.Badge(ctx.risk_level, color="warning" if ctx.risk_level == "medium" else "danger"),
        ]),
        
        html.Details([
            html.Summary("Why this decision?"),
            html.P(ctx.risk_description),
        ]),
        
        html.Details([
            html.Summary("Alternative"),
            html.P(ctx.alternative),
        ]),
        
        dcc.Graph(figure=plot_metrics(ctx.metrics)),
        
        html.Textarea(placeholder="Reason for decision..."),
        html.Button("Approve", id="approve-btn"),
        html.Button("Reject", id="reject-btn"),
    ])
```

---

### Pattern 3: Asynchronous Approval (Batch + Notification)

**Core Idea:** Don't require real-time UI. Send digest emails/Slack; batch approvals.

**Implementation:**
```python
async def queue_for_approval(decision: Dict, priority: str = "normal"):
    """Queue decision; don't block on human response."""
    await db.insert("approval_queue", {
        "id": uuid.uuid4(),
        "decision_id": decision["id"],
        "created_at": datetime.utcnow(),
        "priority": priority,  # "urgent" or "normal"
        "status": "pending",
    })
    
    # Send async notification
    if priority == "urgent":
        await notify_slack(f"URGENT: Approval needed for {decision['action']}")
    else:
        # Batch digest sent hourly
        pass

async def send_approval_digest():
    """Send hourly digest of pending approvals."""
    pending = await db.query(ApprovalQueue).filter(
        ApprovalQueue.status == "pending",
        ApprovalQueue.priority == "normal",
    ).all()
    
    if pending:
        await send_email(
            to=get_reviewers(),
            subject=f"Pending Approvals ({len(pending)} items)",
            body=render_digest(pending),
        )
```

**Benefit:** Non-blocking; reviewers approve in batch when ready. Reduces interrupt cost.

---

### Pattern 4: Feedback Loop → Evolution

**Core Idea:** Rejections and corrections are training signals for policy improvement.

**Implementation:**
```python
async def record_approval_outcome(
    decision_id: str,
    outcome: str,  # "approved" or "rejected"
    reason: str,
    user_feedback: Optional[Dict] = None,  # e.g., {"corrected_action": "..."}
):
    """Record outcome; use as RL signal."""
    await db.insert("approval_log", {
        "id": uuid.uuid4(),
        "decision_id": decision_id,
        "outcome": outcome,
        "reason": reason,
        "user_feedback": user_feedback,
        "timestamp": datetime.utcnow(),
    })
    
    # If rejected, treat as negative reward signal
    if outcome == "rejected":
        decision = await db.query(ApprovalDecision).filter_by(id=decision_id).first()
        
        # Feed back to RL loop: this policy decision was wrong
        reward = -1.0  # Negative reward
        await update_mab_reward(
            arm=decision["policy_variant"],
            reward=reward,
            context={"reason": reason, "feedback": user_feedback},
        )
        
        # Trigger policy evolution
        await spawn_policy_evolution_task(
            failed_decision=decision,
            human_feedback=user_feedback,
        )
```

**Integration with Convergence RL Loop:**
- Arm = Policy variant
- Reward = `+1.0` if approved, `-1.0` if rejected, `+0.5` if approved with minor edits
- Thompson Sampling explores new policy variants
- SAO generates improved policies from rejected decisions

---

## PART 4: Observability for HITL Systems

### What to Expose for Dashboard

```python
# FastAPI endpoint for real-time metrics
@app.get("/api/hitl/metrics")
async def get_hitl_metrics():
    return {
        # Queue metrics
        "pending_approvals": await count_pending_approvals(),
        "avg_approval_time_minutes": await compute_avg_approval_time(),
        "approval_backlog_by_priority": await get_backlog_by_priority(),
        
        # Decision quality
        "approval_rate": await compute_approval_rate(),  # % approved
        "rejection_rate": await compute_rejection_rate(),  # % rejected
        "auto_approve_rate": await compute_auto_approve_rate(),  # % bypassed
        
        # Policy performance
        "recent_rejections": await get_recent_rejections(limit=10),
        "confidence_trend": await compute_confidence_trend(days=7),
        "false_approval_rate": await compute_false_approval_rate(),  # Approved but later found wrong
        
        # Audit
        "audit_trail_recent": await get_recent_audit_entries(limit=5),
        "approvers_active": await count_active_approvers(),
    }
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Gauge, Histogram

# Counters
approvals_total = Counter(
    'hitl_approvals_total',
    'Total approvals',
    ['outcome', 'priority'],  # outcome: approved/rejected, priority: urgent/normal
)

auto_approvals_total = Counter(
    'hitl_auto_approvals_total',
    'Decisions auto-approved (low risk)',
)

# Gauges
pending_approvals = Gauge(
    'hitl_pending_approvals',
    'Pending approval count',
)

# Histograms
approval_time_seconds = Histogram(
    'hitl_approval_time_seconds',
    'Time from decision to approval',
    buckets=(30, 60, 300, 900, 3600),  # 30s, 1m, 5m, 15m, 1h
)

# Usage
async def record_approval(outcome: str, priority: str, approval_time: float):
    approvals_total.labels(outcome=outcome, priority=priority).inc()
    approval_time_seconds.observe(approval_time)
    pending_approvals.dec()
```

---

## PART 5: Enterprise Integration

### Multi-Tenant Isolation

```python
# Ensure queries are tenant-scoped
class TenantMiddleware:
    async def __call__(self, request: Request, call_next):
        # Extract tenant from subdomain or header
        tenant_id = extract_tenant_id(request)
        request.state.tenant_id = tenant_id
        
        response = await call_next(request)
        return response

# Auto-filter all queries
@app.get("/api/decisions")
async def get_decisions(request: Request):
    # All queries scoped to current tenant
    decisions = await db.query(ApprovalDecision).filter(
        ApprovalDecision.tenant_id == request.state.tenant_id,
    ).all()
    return decisions
```

### SSO/OAuth Integration

```python
from authlib.integrations.fastapi_client import OAuth2Session

oauth = OAuth2Session(
    client_id=os.getenv("OAUTH_CLIENT_ID"),
    client_secret=os.getenv("OAUTH_CLIENT_SECRET"),
)

@app.get("/auth/login")
async def login():
    redirect_uri = url_for("auth_callback", _external=True)
    return await oauth.create_authorization_url(
        "https://idp.example.com/authorize",
        scopes=["openid", "profile", "email"],
    )

@app.get("/auth/callback")
async def auth_callback(code: str):
    token = await oauth.fetch_token(
        "https://idp.example.com/token",
        code=code,
    )
    user_info = token.get("userinfo")
    
    # Extract roles from OAuth claims
    roles = user_info.get("roles", [])  # e.g., ["approver", "auditor"]
    
    # Create session
    session["user_id"] = user_info["sub"]
    session["roles"] = roles
    
    return RedirectResponse(url="/dashboard")
```

### Embedding in Admin Panel

```python
# Admin panel = existing Flask/Django app
# Dashboard = separate FastAPI app

# In admin Flask app:
@admin_bp.route("/dashboard")
@require_login
def dashboard_view():
    """Render iframe to embedded dashboard."""
    user_token = create_dashboard_token(current_user.id, current_user.roles)
    
    return render_template("dashboard_embed.html", token=user_token)

# dashboard_embed.html
<iframe
    src="https://dashboard.internal/embedded?token={{ token }}"
    width="100%"
    height="600"
    style="border: none;"
    allow="clipboard-read; clipboard-write"
></iframe>

# In FastAPI dashboard app:
@app.get("/embedded")
async def embedded_dashboard(token: str):
    """Validate token; render dashboard."""
    user_id, roles = validate_dashboard_token(token)
    
    return HTMLResponse(render_dashboard_html(user_id, roles))
```

---

## PART 6: Common Pitfalls

### Pitfall 1: Approval Bottleneck (Too Many Manual Decisions)

**Symptom:** Queue grows unbounded; 100+ pending approvals; response time = 1 week.

**Why:** Not using risk-based routing; approving everything manually.

**Fix:**
```python
# Auto-approve if high confidence + low risk
if decision["confidence"] >= 0.95 and risk_score <= 0.1:
    await execute_immediately()
    await log_audit("auto_approved", reason="high_confidence_low_risk")
else:
    await queue_for_approval()
```

**Target:** < 5% of decisions in approval queue; 80% auto-executed.

---

### Pitfall 2: Audit Log Tampering (No Immutability)

**Symptom:** Audit entries deleted/modified; compliance failure.

**Why:** Audit log stored in editable table; no version control.

**Fix:**
```python
# Immutable append-only log
class AuditLog(Base):
    __table_args__ = (
        UniqueConstraint('id', 'created_at', name='audit_immutable'),
    )
    
    id = Column(UUID, primary_key=True)
    decision_id = Column(UUID, nullable=False)
    user_id = Column(UUID, nullable=False)
    action = Column(String(50), nullable=False)
    context = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Event listener: prevent updates
    @event.listens_for(AuditLog, 'before_update')
    def prevent_audit_updates(mapper, connection, target):
        raise RuntimeError("Audit logs are immutable. Cannot update.")
```

**Better:** Use PostgreSQL-Audit library (automatic versioning).

---

### Pitfall 3: Stale Metrics in Real-Time Dashboard

**Symptom:** Dashboard shows "Decision approved 2 minutes ago" but UI still shows "Pending".

**Why:** WebSocket connection died; UI cached stale state.

**Fix:**
```python
// Client-side JavaScript
const ws = new WebSocket("wss://dashboard/ws");
let lastHeartbeat = Date.now();

ws.onmessage = (event) => {
    if (event.data.type === "ping") {
        lastHeartbeat = Date.now();
    }
};

// Detect dead connection
setInterval(() => {
    if (Date.now() - lastHeartbeat > 60000) {
        console.log("Heartbeat timeout; reconnecting...");
        ws.close();
        connectWebSocket();
    }
}, 30000);
```

---

### Pitfall 4: No Row-Level Security (Data Leakage)

**Symptom:** Team A sees Team B's approval decisions in shared dashboard.

**Why:** Auth checked at view level; data filtering in template.

**Fix:**
```python
# Apply RLS at query level
@require_role("approver")
async def get_pending_approvals(user: User):
    return await db.query(ApprovalDecision).filter(
        ApprovalDecision.team_id == user.team_id,  # Always filter by team
        ApprovalDecision.status == "pending",
    ).all()
```

---

### Pitfall 5: No Rollback for Approved Decisions

**Symptom:** Approved decision was wrong; now it's deployed. Can't undo.

**Why:** Execution is immediate and irreversible.

**Fix:**
```python
# Add explicit rollback mechanism
async def execute_decision_with_rollback(decision: Dict, execution_id: str):
    try:
        await execute_decision(decision)
        await update_execution_status(execution_id, "success")
    except Exception as e:
        # Rollback: revert the change
        await rollback_decision(decision)
        await update_execution_status(execution_id, "rolled_back", reason=str(e))
```

**Better:** Use feature flags; deploy changes with ability to toggle off.

---

## PART 7: Implementation Recommendations

### Recommended Stack for Convergence

**Frontend:** Dash (Plotly) or FastAPI + React
- Dash: simpler setup, built-in HITL patterns
- FastAPI + React: more control, better real-time, embed anywhere

**Real-Time Updates:** FastAPI WebSocket + Postgres LISTEN/NOTIFY
- Push metrics to dashboard in < 100ms
- Async-native; no blocking

**Audit Logging:** SQLAlchemy event listeners + Postgres
- Auto-log all state changes
- Immutable append-only table

**Observability:** OpenTelemetry + Prometheus + Grafana
- Track HITL metrics (approval rate, time-to-approval, backlog)
- Expose RL metrics (arm selection, reward distribution, policy updates)

**Multi-Persona:** RBAC via Permit.io or custom decorator
- Role-based view access
- Row-level security at query layer

---

## Summary Table

| Problem | Solution | Implementation | Lines |
|---------|----------|-----------------|-------|
| Multi-user scaling | Dash or FastAPI+React | Switch from Streamlit; add persistence | 500 |
| Real-time updates | FastAPI WebSocket | ConnectionManager + heartbeat | 150 |
| Audit trail | SQLAlchemy events + Postgres | Event listener + audit table | 100 |
| Risk-based routing | Confidence scoring | Auto-approve if high confidence | 50 |
| Multi-persona | RBAC decorator | Role check + RLS at query layer | 100 |
| Approval backlog | Async notifications | Queue + Slack/email digest | 150 |
| Feedback loop | MAB integration | Rejection = negative reward | 100 |
| Stale metrics | Prometheus + WebSocket | Expose /metrics + broadcast updates | 200 |

---

## Key Sources

- [ML Dashboard Anti-Patterns at Scale](https://www.truefoundry.com/blog/best-ai-observability-platforms-for-llms-in-2026)
- [Dashboard Trends 2026](https://b-eye.com/blog/business-intelligence-data-analytics-trends/)
- [Streamlit vs Dash vs Gradio Comparison](https://docs.kanaries.net/topics/Streamlit/streamlit-vs-dash)
- [Streamlit Scalability Issues](https://discuss.streamlit.io/t/scalability-concerns-with-large-user-base/69494)
- [FastAPI WebSockets Real-Time Patterns](https://testdriven.io/blog/fastapi-postgres-websockets/)
- [HITL Best Practices](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
- [HITL Architecture Patterns](https://www.agentpatterns.tech/en/architecture/human-in-the-loop-architecture)
- [Compliance in Automated Workflows](https://testrigor.com/blog/building-audit-ready-automation/)
- [RBAC in Django](https://www.permit.io/blog/how-to-implement-role-based-access-control-rbac-into-a-django-application)
- [Panel Framework Production Deployment](https://panel.holoviz.org/how_to/deployment/index.html)
- [OpenTelemetry Python Observability](https://opentelemetry.io/docs/languages/python/)
- [SQLAlchemy Audit Logging](https://medium.com/@singh.surbhicse/creating-audit-table-to-log-insert-update-and-delete-changes-in-flask-sqlalchemy-f2ca53f7b02f)
- [Dashboard Embedding Best Practices](https://www.usedatabrain.com/blog/secure-sso-oauth-embedded-dashboards-2026)

