# Dashboard & HITL Research - Executive Summary

**Research Date:** 2026-03-12  
**Full Document:** `dashboard-hitl-research.md` (984 lines)

---

## TL;DR: Recommended Stack for Convergence

### Dashboard Framework
- **Primary:** Plotly Dash (enterprise-grade; 250K/week downloads)
- **Alternative:** FastAPI + React (if need WebSocket real-time + embeddable)
- **NOT:** Streamlit (doesn't scale beyond ~10 concurrent users)

### Real-Time Backend
- **FastAPI with WebSocket + Postgres LISTEN/NOTIFY**
- ConnectionManager for broadcast
- Heartbeat/ping every 30s (detect dead connections)
- < 100ms latency for metrics updates

### Audit & Approval
- **SQLAlchemy event listeners** (auto-log all state changes)
- **Immutable append-only audit table** (no edits, only appends)
- **Risk-based routing**: auto-approve high-confidence decisions; human-review uncertain ones
- Structured approval context (why? what are risks? alternatives?)

### Observability
- **Prometheus + Grafana** for metrics dashboard
- **OpenTelemetry** for spans (when you scale to multi-service)
- Expose: `pending_approvals`, `approval_rate`, `approval_time`, `auto_approve_rate`

### RBAC/Multi-Persona
- **Django/Permit.io** for role definitions
- **Row-level security (RLS)** at query layer (not UI layer)
- Separate dashboards for: approvers, auditors, engineers, product managers

---

## 5 Critical Anti-Patterns (What Breaks)

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| **Streamlit for production** | Sessions crash under load; state resets | Switch to Dash/FastAPI; add Redis persistence |
| **No audit trail** | Compliance failure; can't defend decisions | SQLAlchemy events + immutable log table |
| **WebSocket without heartbeat** | Zombie connections; stale UI | Send ping every 30s; reconnect on missed pong |
| **View-level auth only** | Data leakage; Team A sees Team B's data | Add row-level security at DB query layer |
| **Log everything** | PII exposure (credit cards, emails in logs) | Scrub fields; hash text; use structlog processors |

---

## Framework Scorecard

| Framework | Multi-User Scale | Real-Time | Auth/RBAC | Embeddable | HITL-Ready | Recommendation |
|-----------|-----------------|-----------|-----------|-----------|-----------|-----------------|
| **Dash** | ✅ 100+ users | ⚠️ polling | ✅ good | ⚠️ via iFrame | ✅ yes | **DEFAULT** |
| **FastAPI + React** | ✅ 1000+ users | ✅ WebSocket | ✅ custom | ✅ yes | ✅ yes | **For real-time** |
| **Panel** | ✅ 100+ users | ✅ Bokeh | ⚠️ basic | ✅ yes | ⚠️ limited | **For scientific** |
| **Streamlit** | ❌ <10 users | ❌ no | ❌ addon | ❌ no | ❌ no | **Avoid** |
| **Gradio** | ✅ demos | ⚠️ polling | ❌ no | ⚠️ web component | ❌ no | **Demos only** |

---

## HITL Decision Flow

```
Decision from model/agent
    ↓
Is confidence >= 95% AND risk <= 10%?
    ├─ YES → AUTO-APPROVE (80% of decisions)
    │        ↓
    │        Log to audit table
    │        Execute immediately
    │        Emit metrics (auto_approvals_total++)
    │
    └─ NO → QUEUE FOR HUMAN REVIEW (20% edge cases)
            ↓
            Send structured approval context to dashboard
            (Why? Risks? Alternatives? Metrics?)
            ↓
            Approver reviews (async or real-time)
            ↓
            Approve / Reject + reason
            ↓
            Log to audit table (immutable)
            ↓
            If rejected: feed back to RL loop (negative reward)
            If approved: execute; feed positive reward
```

---

## Implementation Priority

### Phase 1 (Sprint 1): Core HITL
- Add Dash skeleton with basic approval form
- SQLAlchemy event listener for audit logging
- Risk scoring function (confidence + false positive rate)
- Basic auto-approve logic

**Effort:** 16 hours | **Output:** Approve/reject decisions with audit trail

### Phase 2 (Sprint 2): Real-Time + Metrics
- FastAPI WebSocket endpoint for live updates
- Prometheus metrics: `pending_approvals`, `approval_rate`, `approval_time`
- Postgres LISTEN/NOTIFY for real-time state sync
- Heartbeat/ping mechanism

**Effort:** 20 hours | **Output:** Real-time dashboard showing live queue, metrics

### Phase 3 (Sprint 3): Integration with RL Loop
- Rejection = negative reward signal
- Feed approval metrics into MAB reward function
- Spawn policy evolution on failed decisions
- Connect to existing RLP/SAO

**Effort:** 24 hours | **Output:** Closed feedback loop (human decisions → policy improvement)

### Phase 4 (Future): Multi-Tenant + Enterprise
- RBAC via Permit.io or custom
- Row-level security at query layer
- SSO/OAuth integration
- Embedding in existing admin panel

**Effort:** 32 hours | **Output:** Enterprise-ready; multiple orgs/teams

---

## Key Code Patterns

### Risk-Based Routing (50 lines)
```python
async def should_require_approval(decision: Dict) -> bool:
    confidence = decision.get("confidence", 0.0)
    risk_level = compute_risk_level(decision)
    
    if confidence >= 0.95 and risk_level <= 0.1:
        return False  # Auto-approve
    return True  # Human review
```

### Audit Logging with SQLAlchemy (30 lines)
```python
@event.listens_for(ApprovalDecision, 'after_insert')
def log_approval(mapper, connection, target):
    audit_log = AuditLog(
        user_id=target.approved_by,
        action="approval",
        context=target.to_dict(),
        timestamp=datetime.utcnow(),
    )
    connection.execute(insert(AuditLog), audit_log.to_dict())
```

### WebSocket Broadcast (40 lines)
```python
class ConnectionManager:
    def __init__(self):
        self.active = []
    
    async def broadcast(self, data: dict):
        for ws in self.active:
            await ws.send_json(data)

@app.websocket("/ws/dashboard")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(data)
    except:
        pass
```

### Row-Level Security (20 lines)
```python
@require_role("approver")
async def get_pending_decisions(user: User):
    return await db.query(ApprovalDecision).filter(
        ApprovalDecision.team_id == user.team_id,  # Always filter
        ApprovalDecision.status == "pending",
    ).all()
```

---

## Tools & Libraries (Minimal Dependencies)

| Purpose | Library | Downloads | Why |
|---------|---------|-----------|-----|
| Dashboard | plotly-dash | 250K/week | Enterprise-ready; no state management headaches |
| Real-time API | fastapi | 2M+/week | Async-native; WebSocket built-in |
| Async DB | sqlalchemy | 2M+/week | Already in codebase; event listeners |
| Metrics | prometheus-client | 500K/week | Standard; Grafana integration |
| Auth | authlib | 150K/week | OAuth 2.0; SSO support |
| Audit logs | python-audit-log | 10K/week | Lightweight; append-only |

**Total new deps for Phase 1:** 2 (plotly-dash, prometheus-client)

---

## Metrics to Track (Dashboard)

```
HITL Queue:
- pending_approvals (gauge)
- approvals_total (counter, by outcome)
- approval_time_seconds (histogram)
- auto_approve_rate (%)

Decision Quality:
- approval_rate (% approved vs rejected)
- false_approval_rate (approved but later wrong)
- confidence_trend (7-day rolling avg)

Policy Learning:
- rejections_by_reason (category)
- policy_evolution_triggered (counter)
- reward_signal_from_approvals (gauge)
```

---

## Red Flags to Avoid

1. **Don't use Streamlit for multi-user HITL** (state reset on re-run breaks approval flows)
2. **Don't log full text** (PII exposure; use hashes instead)
3. **Don't check auth at view layer only** (implement RLS at database)
4. **Don't approve everything manually** (implement risk-based routing; target 80% auto-approve)
5. **Don't skip audit trails** (compliance failure; regulatory requirement)
6. **Don't use in-memory metrics** (persistent storage required)
7. **Don't embed with iFrame without CORS/CSRF hardening** (security risk)

---

## Sources

- [Dashboard Anti-Patterns & Trends 2026](https://www.truefoundry.com/blog/best-ai-observability-platforms-for-llms-in-2026)
- [Streamlit Scalability Limits](https://discuss.streamlit.io/t/scalability-concerns-with-large-user-base/69494)
- [Dash vs Streamlit vs Gradio](https://docs.kanaries.net/topics/Streamlit/streamlit-vs-dash)
- [FastAPI WebSocket Real-Time Patterns](https://testdriven.io/blog/fastapi-postgres-websockets/)
- [HITL Best Practices](https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo)
- [Audit Trail & Compliance](https://testrigor.com/blog/building-audit-ready-automation/)
- [SQLAlchemy Audit Events](https://medium.com/@singh.surbhicse/creating-audit-table-to-log-insert-update-and-delete-changes-in-flask-sqlalchemy-f2ca53f7b02f)
- [Panel Production Deployment](https://panel.holoviz.org/how_to/deployment/index.html)

