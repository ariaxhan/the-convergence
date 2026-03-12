# Handoff: Dashboard Feature (DEFERRED)

**Date:** 2026-03-12
**Branch:** main
**Status:** Research complete, deferred until backend refinement done

---

## Summary

Dashboard + HITL feature fully researched, scoped as Tier 3 (17+ files). Deferred by user decision to complete backend refinement first.

---

## Research Completed

**Location:** `_meta/research/`
- `dashboard-hitl-research.md` (984 lines) - Comprehensive reference
- `DASHBOARD-HITL-SUMMARY.md` (246 lines) - Executive summary
- `DASHBOARD-QUICK-START.md` (420 lines) - Phase 1 implementation guide
- `README-DASHBOARD-HITL.md` (360 lines) - Navigation by role

### Key Decisions Made

| Decision | Choice | Why |
|----------|--------|-----|
| Framework | FastAPI + Dash hybrid | Real-time WebSocket + embeddable + multi-persona |
| State | Postgres (not in-memory) | Multi-server, persistence |
| Audit | SQLAlchemy events + immutable table | Compliance |
| Real-time | WebSocket + heartbeat | Avoid stale data |
| HITL routing | Risk-based (80% auto/20% manual) | Avoid approval bottleneck |
| Rejection handling | Feed to MAB as negative reward | Self-improvement |

### Anti-Patterns to Avoid

1. **Streamlit for production** → Use Dash/FastAPI
2. **No audit trail** → SQLAlchemy event listeners + immutable Postgres
3. **WebSocket without heartbeat** → ping every 30s, reconnect on missed pong
4. **View-level auth only** → Row-level security at query layer
5. **Log everything** → Scrub PII, hash text, structlog processors

### Target Users (All)

- ML Engineers: arm selection, reward tracking, policy evolution
- DevOps/SRE: system health, latency, throughput, error rates
- Product Managers: business outcomes, A/B results, ROI

### HITL Scope (All)

- Arm selection overrides
- Reward signal adjustment
- Policy freezing/unfreezing
- Full audit trail

### Integration Mode

Both standalone + embeddable widgets

---

## Proposed Implementation (17+ files)

### Phase 1: Core HITL (~8 files)
```
convergence/dashboard/__init__.py
convergence/dashboard/server.py
convergence/dashboard/hitl.py
convergence/dashboard/audit.py
convergence/dashboard/observability.py
convergence/runtime/hooks.py (new)
convergence/runtime/online.py (modify - add hooks)
tests/dashboard/test_hitl.py
```

### Phase 2: Real-time (~3 files)
```
convergence/dashboard/websocket.py
convergence/dashboard/auth.py
tests/dashboard/test_realtime.py
```

### Phase 3: Multi-persona (~6 files)
```
convergence/dashboard/views/__init__.py
convergence/dashboard/views/ml_engineer.py
convergence/dashboard/views/devops.py
convergence/dashboard/views/product.py
tests/dashboard/test_views.py
```

---

## Existing Integration Points

- `WeaveLogger` (`convergence/core/weave_logger.py`) - WandB observability
- `RuntimeManager` (`convergence/runtime/online.py`) - select/update hooks
- No event system yet - dashboard needs hooks layer

---

## Blockers (Why Deferred)

Backend refinement must come first:
1. **Architecture v3** - Knowledge layer, safety guardrails, observability layer
2. **Phase 0** - Foundation hardening (Thompson metrics, RLP monitoring)
3. **Phases 1-5** - Principle tracking, constitutional YAML, unified classifier

Dashboard builds ON TOP of these. Can't observe what doesn't exist yet.

---

## Current Backend State

### Active Plan: ARCHITECTURE-v3-RESEARCH-INFORMED.md

| Phase | Focus | Status |
|-------|-------|--------|
| 0 | Foundation hardening | Ready |
| 1 | Knowledge layer | Ready |
| 2 | Observability layer | Ready |
| 3 | Optimization refinement | Blocked on 1,2 |
| 4 | Experimental methods | Blocked on 3 |
| 5 | Storage unification | Blocked on 1 |

### Contracts Closed
- CR-004: Fix confidence.py bugs ✓

### Research Insights Applied
- EvolveR principle tracking (quality score formula)
- Thompson Sampling validated
- Constitutional AI over RLHF
- 14 failure modes (79% spec/coordination)
- Memory decay formula: `1/(1 + age/30)`
- Self-learning is Phase 2, not Phase 1

---

## When to Resume Dashboard

Resume dashboard implementation AFTER:
1. ✓ Backend foundation hardened (Phase 0)
2. ✓ Observability layer exists (Phase 2)
3. ✓ Runtime hooks infrastructure exists

**Trigger:** When `convergence/observability/` package exists and `convergence/runtime/hooks.py` is implemented.

---

## Continuation Prompt

```
/kernel:ingest Add observability dashboard package with HITL capabilities.
Research complete in _meta/research/dashboard-*.
Read _meta/handoffs/dashboard-deferred-handoff.md for full context.
Start with Phase 1 (Core HITL) - 8 files.
```

---

## Files This Session

Created:
- `_meta/research/dashboard-hitl-research.md`
- `_meta/research/DASHBOARD-HITL-SUMMARY.md`
- `_meta/research/DASHBOARD-QUICK-START.md`
- `_meta/research/README-DASHBOARD-HITL.md`
- `_meta/handoffs/dashboard-deferred-handoff.md` (this file)

---

*Handoff created: 2026-03-12*
*Status: Deferred until backend refinement complete*
