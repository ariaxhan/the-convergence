# Dashboard & HITL Research Index

**Status:** Complete | **Date:** 2026-03-12 | **Scope:** Production dashboards for Python ML systems

This research answers 5 key questions for Convergence:

1. **What breaks in ML dashboards at scale?** → Anti-patterns
2. **Which framework should we use?** → Plotly Dash or FastAPI+React
3. **How do we implement human-in-the-loop approval?** → HITL patterns
4. **How do we integrate with the RL loop?** → Feedback signal patterns
5. **What's the enterprise integration story?** → Multi-tenant, SSO, embeddable

---

## Research Documents

### 1. **DASHBOARD-QUICK-START.md** (420 lines)
**Start here.** Pick a framework, implement Phase 1, integrate with RL loop.

**Contains:**
- Dash vs FastAPI+React comparison with complete code examples
- SQLAlchemy audit logging (copy-paste ready)
- Risk-based routing implementation (auto-approve 80% of decisions)
- RL loop integration (approval outcome → MAB reward)
- Prometheus metrics setup
- Testing checklist

**Time to implement:** 16 hours (Phase 1)

---

### 2. **DASHBOARD-HITL-SUMMARY.md** (246 lines)
**Executive summary.** Framework scorecard, anti-patterns, implementation roadmap.

**Contains:**
- 5 critical anti-patterns with fixes
- Framework comparison scorecard (Dash, FastAPI, Panel, Streamlit, Gradio)
- HITL decision flow diagram
- 4-phase implementation roadmap (0-96 hours)
- Key code patterns (risk routing, audit logging, WebSocket broadcast)
- Minimal dependency list

**Best for:** Decision-makers, technical planning, architecture review.

---

### 3. **dashboard-hitl-research.md** (984 lines)
**Comprehensive reference.** Deep dives on everything.

**Contains:**
- **Part 1: Anti-Patterns** (5 detailed patterns with symptoms, causes, fixes)
  - Streamlit scaling failures
  - No audit trails
  - WebSocket reliability
  - Multi-persona data leakage
  - PII logging exposure
  
- **Part 2: Framework Comparison** (use case matrix + deep dives)
  - Plotly Dash (recommended for enterprise)
  - FastAPI + WebSocket (for real-time)
  - Panel (scientific/complex)
  - Gradio (NOT for HITL)
  
- **Part 3: HITL Patterns**
  - Risk-based routing
  - Structured approval context
  - Asynchronous approval flows
  - Feedback loop → evolution
  
- **Part 4: Observability**
  - HITL metrics to expose
  - Prometheus setup
  - Real-time dashboard signals
  
- **Part 5: Enterprise Integration**
  - Multi-tenant isolation
  - SSO/OAuth
  - Embedding in admin panels
  - Row-level security (RLS)
  
- **Part 6: Pitfalls**
  - Approval bottlenecks
  - Audit tampering
  - Stale metrics
  - Data leakage
  - No rollback
  
- **Part 7: Implementation Roadmap**
  - Summary table with effort/complexity
  - Phase-by-phase breakdown

**Best for:** Deep understanding, troubleshooting, enterprise requirements.

---

## Quick Navigation

### By Role

**Product Manager:**
→ Read DASHBOARD-HITL-SUMMARY.md (246 lines)
- Understand approval workflow
- See implementation timeline (96 hours total)
- Know competitive positioning (why Dash > Streamlit)

**Tech Lead / Architect:**
→ Read DASHBOARD-HITL-SUMMARY.md + Parts 1-3 of dashboard-hitl-research.md
- Anti-patterns to avoid
- Framework selection criteria
- HITL architecture patterns
- Enterprise integration requirements

**Engineer (Frontend/Full-Stack):**
→ Read DASHBOARD-QUICK-START.md + Part 3 (HITL Patterns) of dashboard-hitl-research.md
- Copy-paste code for Dash/FastAPI setup
- Audit logging implementation
- Risk-based routing logic
- Testing checklist

**Engineer (Backend/ML):**
→ Read DASHBOARD-QUICK-START.md Part 4 (RL Integration) + Parts 3-4 of dashboard-hitl-research.md
- How to wire approval outcomes to MAB rewards
- Feedback signal integration
- Prometheus metrics for RL
- Rejection → SAO trigger

**DevOps/SRE:**
→ Read DASHBOARD-HITL-SUMMARY.md Part 5 + dashboard-hitl-research.md Part 5-6
- Deployment options (Dash on Tornado/FastAPI/Flask/Django)
- Multi-tenant isolation patterns
- Monitoring & alerting (Prometheus + Grafana)
- Row-level security (database-level)

---

## Implementation Roadmap

```
PHASE 1 (Sprint 1): Core HITL Approval
├─ Choose framework: Dash or FastAPI+React
├─ Build approval form UI
├─ Add SQLAlchemy audit table
├─ Implement risk-based routing (auto-approve 80%)
├─ Wire approval outcome to RL reward
└─ Effort: 16 hours | Output: Functional approval workflow

PHASE 2 (Sprint 2): Real-Time Dashboard
├─ Add FastAPI WebSocket endpoint (if Phase 1 used Dash, add real-time layer)
├─ Postgres LISTEN/NOTIFY for state sync
├─ Prometheus metrics endpoint
├─ Grafana dashboard (pending queue, approval rate, time-to-approval)
└─ Effort: 20 hours | Output: Real-time monitoring of HITL queue

PHASE 3 (Sprint 3): RL Integration
├─ Connect approval outcomes to MAB reward computation
├─ Trigger SAO (policy evolution) on rejections
├─ Add feedback signal from approval context
├─ Track policy improvement metrics
└─ Effort: 24 hours | Output: Closed feedback loop (human → policy)

PHASE 4 (Future): Enterprise
├─ Multi-tenant isolation (query-level filtering)
├─ RBAC via Permit.io or custom decorators
├─ SSO/OAuth integration
├─ Embedding in existing admin panel
├─ Row-level security (database-level)
└─ Effort: 32 hours | Output: Production-ready enterprise system
```

---

## Key Decisions

### Framework Choice

**Default: Plotly Dash**
- Why: Callback-driven; explicit control; built-in HITL patterns
- Scaling: Up to 200 concurrent users
- Real-time: Polling (adequate for approval workflows)
- Setup: 2 hours

**Alternative: FastAPI + React**
- Why: WebSocket real-time; can embed anywhere; 1000+ concurrent
- Complexity: Need separate React frontend
- Real-time: < 100ms WebSocket updates
- Setup: 4 hours (initially harder, easier to scale)

**Avoid: Streamlit**
- Sessions crash under load (> 10 concurrent users)
- State resets on every interaction (breaks approval flows)
- No RBAC/auth; no audit logging
- Not suitable for production HITL systems

### Audit Logging

**Use: SQLAlchemy event listeners + immutable Postgres table**
- Why: Auto-log all state changes; zero application code coupling
- Immutability: Prevent `before_update` events
- Compliance: Audit trail for regulatory requirements

### Risk Routing

**Target:** 80% auto-approve (high confidence + low risk), 20% human review
- Why: Reduces approval bottleneck; humans focus on edge cases
- Implementation: Simple logic (confidence > 0.95 AND fpr < 0.05)
- Adjustable: Tune thresholds per use case

### Real-Time Updates

**Use: Postgres LISTEN/NOTIFY + WebSocket broadcast**
- Why: < 100ms latency; efficient; decouples dashboard from business logic
- Heartbeat: Send ping every 30s; reconnect on missed pong
- Scaling: Works up to 10K concurrent with proper resource allocation

---

## Metrics to Implement First

```
HITL Queue Depth:
- pending_approvals (gauge)

Approval Flow:
- approvals_total (counter, by outcome: approved/rejected/auto)
- approval_time_seconds (histogram, buckets: 30s, 1m, 5m, 15m, 1h)
- approval_rate (% approved vs total)

Decision Quality:
- auto_approve_rate (% that bypass human review)
- false_approval_rate (approved but later wrong)
- confidence_trend (7-day rolling average)

RL Integration:
- mab_reward_by_arm (gauge, per policy variant)
- rejections_by_reason (counter, for SAO feedback)
- policy_evolution_triggered (counter, when rejection triggers evolution)
```

---

## Common Questions

**Q: Should we use Streamlit?**  
A: No. Streamlit is for demos/prototypes with < 10 users. Production HITL requires Dash or FastAPI.

**Q: Do we need WebSockets immediately?**  
A: No. Phase 1 can use Dash polling. Phase 2 adds WebSocket if needed for real-time updates.

**Q: How do we scale to 1000+ users?**  
A: Use FastAPI + React with WebSocket. Add Redis for session storage. Database connection pooling.

**Q: What if we need approval chaining (tier 1 → tier 2 → tier 3)?**  
A: Extend audit log with `escalation_level` field. Use same HITL patterns; queue separates by tier.

**Q: How do we handle long-running decisions (> 5 minutes to approve)?**  
A: Use async notifications (Slack digest, email). Don't block on approval. Mark as "pending" in UI.

**Q: Can we embed the dashboard in our existing admin panel?**  
A: Yes. Use FastAPI under `/dashboard` route. Embed via iFrame with CORS/CSRF hardening, or use web components.

---

## Pitfalls to Avoid

1. **Streamlit for production:** Sessions crash; state resets; not designed for HITL
2. **No audit trail:** Compliance failure; can't defend decisions
3. **View-level auth only:** Data leakage; implement row-level security (RLS) at database
4. **Approve everything manually:** Approval bottleneck; implement risk routing (80% auto)
5. **Log full text:** PII exposure; hash or truncate sensitive fields
6. **No WebSocket heartbeat:** Zombie connections; stale UI
7. **Immutable audit log:** Prevent updates with SQLAlchemy `before_update` event
8. **No feedback loop:** Rejections not used to improve policy; implement RL integration

---

## Dependencies (Minimal)

```
Core:
- plotly-dash (250K/week) or fastapi (2M+/week)
- sqlalchemy (2M+/week)  [already in codebase]
- prometheus-client (500K/week)

Optional:
- authlib (150K/week)  [for SSO/OAuth, Phase 4]
- python-audit-log (10K/week)  [lightweight audit wrapper, optional]
```

Total new dependencies for Phase 1: **2** (dash + prometheus-client)

---

## Implementation Checklist

### Phase 1 Checklist (16 hours)

- [ ] Decide: Dash or FastAPI+React
- [ ] Create approval form UI
- [ ] Design ApprovalDecision and AuditLog tables
- [ ] Add SQLAlchemy event listener for auto-logging
- [ ] Implement `should_require_approval()` function
- [ ] Add approval/rejection handlers
- [ ] Wire approval outcome to MAB reward
- [ ] Test with 5-10 sample decisions
- [ ] Document approval reason requirements
- [ ] Deploy to staging; team review

### Phase 2 Checklist (20 hours)

- [ ] Add FastAPI WebSocket endpoint
- [ ] Postgres LISTEN/NOTIFY listener
- [ ] ConnectionManager + broadcast logic
- [ ] WebSocket heartbeat/ping every 30s
- [ ] Prometheus metrics endpoint
- [ ] Basic Grafana dashboard
- [ ] Load test (200 concurrent users)

### Phase 3 Checklist (24 hours)

- [ ] Connect rejection outcome to negative MAB reward
- [ ] Trigger SAO (policy evolution) on human feedback
- [ ] Track policy improvement metrics
- [ ] Document feedback loop for users
- [ ] Integration tests with RL loop

---

## Next Steps

1. **Pick your framework:**
   - Dash: 2-hour setup, scales to 200 users
   - FastAPI+React: 4-hour setup, scales to 1000+ users

2. **Read DASHBOARD-QUICK-START.md:**
   - Copy code examples for your chosen framework
   - Implement audit logging (30 minutes)
   - Add risk routing (1 hour)
   - Test (2 hours)

3. **Integrate with RL loop:**
   - Map approval outcome to MAB reward
   - Trigger SAO on rejections
   - Track metrics (4 hours)

4. **Deploy Phase 1:**
   - Test with team (approval backlog, real decisions)
   - Measure: approval rate, time-to-approval, auto-approve %
   - Iterate on thresholds

---

## Questions?

Refer to:
- **Anti-patterns & fixes:** dashboard-hitl-research.md Part 1 & 6
- **Framework details:** dashboard-hitl-research.md Part 2
- **HITL implementation:** dashboard-hitl-research.md Part 3 + DASHBOARD-QUICK-START.md
- **Observability:** dashboard-hitl-research.md Part 4
- **Enterprise:** dashboard-hitl-research.md Part 5

