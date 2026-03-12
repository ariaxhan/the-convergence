# Implementation Contracts — Authoritative

**Date:** 2026-03-12
**Status:** ACTIVE
**Supersedes:** UNIFIED-IMPLEMENTATION-PLAN.md, all CR-* contracts prior to this date

---

## Contract Registry

| ID | Goal | Tier | Status | Depends On |
|----|------|------|--------|------------|
| **P0-001** | Foundation Hardening | 2 | ✅ COMPLETE | - |
| **P0-002** | Context Graph MVP | 2 | ✅ COMPLETE | P0-001 ✅ |
| **P1-001** | Safety & Guardrails | 2 | ✅ COMPLETE | P0-001 ✅ |
| **P2-001** | Observability Protocol | 2 | ✅ COMPLETE | P0-001 ✅ |
| **P3-001** | Semantic Cache Enhancement | 2 | READY | P2-001 |
| **P4-001** | Documentation & Examples | 1 | READY | P1-001, P2-001, P3-001 |
| **P5-001** | Experimental Methods Hardening | 2 | BLOCKED | P4-001, 500+ interactions |

---

## Phase 0: Foundation (MUST DO FIRST)

### P0-001: Foundation Hardening

**Goal:** Make existing code production-ready before adding features.

**Critical Issues from Teardown:**
- [ ] Thompson Sampling state not persisted (CRITICAL-2)
- [ ] Add regret tracking, arm distribution metrics
- [ ] Add kill switches

**Files (4):**
```
convergence/plugins/mab/thompson_sampling.py  — Add save/load state
convergence/plugins/mab/persistence.py        — Storage integration
convergence/plugins/learning/rlp.py           — Add entropy monitoring
convergence/plugins/learning/sao.py           — Add validation hooks
```

**Acceptance Criteria:**
- [ ] Thompson Sampling state survives restart
- [ ] RLP has entropy monitoring + KL constraints
- [ ] SAO has distribution shift detection
- [ ] All tests pass

---

### P0-002: Context Graph MVP

**Goal:** Add the KNOWLEDGE layer that README promises but plan lacked.

**Critical Issue from Teardown:**
- [ ] Context Graph Layer missing from Architecture v3 (CRITICAL-1)

**Files (5):**
```
convergence/knowledge/__init__.py        — Package exports
convergence/knowledge/graph.py           — ContextGraph class
convergence/knowledge/schema.py          — Node/Edge models
convergence/knowledge/storage.py         — SQLite/PostgreSQL tables
tests/knowledge/test_graph.py            — Basic operations
```

**Schema:**
```sql
CREATE TABLE graph_nodes (
    id TEXT PRIMARY KEY,
    ontology_type TEXT NOT NULL,  -- 'who', 'what', 'how'
    entity_type TEXT NOT NULL,    -- 'person', 'decision', 'process', etc.
    content TEXT,
    metadata TEXT,                -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE graph_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES graph_nodes(id),
    target_id TEXT REFERENCES graph_nodes(id),
    relationship_type TEXT,
    weight REAL DEFAULT 1.0,
    metadata TEXT
);
```

**Acceptance Criteria:**
- [ ] Can create nodes (who/what/how)
- [ ] Can create edges with relationships
- [ ] Basic traverse operation works
- [ ] Basic extract_context operation works
- [ ] Persists to SQLite

**NOT in MVP:**
- Embeddings (Phase 2)
- Merge operations (Phase 4)
- Graph learning (Future)

---

## Phase 1: Safety & Guardrails

### P1-001: Safety Integration

**Goal:** Make agents safe by default (framework-level, not prompt-level).

**Files (8):**
```
convergence/safety/__init__.py
convergence/safety/nemo_rails.py      — NeMo Guardrails wrapper
convergence/safety/schema_guards.py   — Guardrails AI integration
convergence/safety/budget.py          — Cost enforcement + persistence
convergence/safety/audit.py           — Audit logging
convergence/safety/config/            — Default Colang rules
tests/safety/test_rails.py
tests/safety/test_budget.py
```

**Security Issue from Teardown:**
- [ ] Budget enforcement needs persistence (SEC-2)
- [ ] Need default Colang rules for injection detection (SEC-1)

**Acceptance Criteria:**
- [ ] NeMo blocks basic prompt injection attempts
- [ ] Budget persists across restarts
- [ ] Audit log captures all decisions
- [ ] Tests for injection detection

**Dependencies:**
```toml
[project.optional-dependencies]
safety = [
    "nemoguardrails>=0.10.0",
    "guardrails-ai>=0.5.0",
]
```

---

## Phase 2: Observability

### P2-001: Native Observability Protocol

**Goal:** Watch the learning process, not just outputs.

**Files (6):**
```
convergence/observability/__init__.py
convergence/observability/protocol.py    — Observer Protocol
convergence/observability/native.py      — Built-in implementation
convergence/observability/metrics.py     — Counter, Gauge, Histogram
convergence/observability/weave.py       — Optional Weave adapter
tests/observability/test_native.py
```

**Concern from Teardown:**
- [ ] Weave should be optional, not required (CONCERN-3)

**Metrics to Track:**
| Category | Metric | Why |
|----------|--------|-----|
| Learning | Regret trend | Is MAB converging? |
| Learning | Arm distribution | Which arms winning? |
| Calibration | Confidence accuracy | 80% confidence = 80% success? |
| Cost | Per-request cost | Budget tracking |
| Cost | Cache hit rate | Is caching working? |

**Acceptance Criteria:**
- [ ] Observer protocol defined
- [ ] Native implementation works without Weave
- [ ] Weave adapter is optional extra
- [ ] Can export metrics to JSON

---

## Phase 3: Semantic Cache Enhancement

### P3-001: Semantic Cache with ANN Search

**Goal:** Fix O(n) lookup bottleneck, achieve 70-80% cost reduction.

**Critical Issue from Teardown:**
- [ ] Semantic Cache O(n) lookup (CRITICAL-3)

**Files (4):**
```
convergence/cache/semantic.py           — Enhance existing
convergence/cache/backends.py           — Add vector index support
convergence/cache/embeddings.py         — Embedding model wrapper
tests/cache/test_semantic_performance.py
```

**Options for ANN:**
1. SQLite FTS5 + manual cosine (simple, no deps)
2. Qdrant (fast, requires server)
3. FAISS (fast, requires numpy/faiss)

**Recommendation:** Start with SQLite FTS5 for MVP, document upgrade path.

**Acceptance Criteria:**
- [ ] Lookup is O(log n) or better
- [ ] Threshold validation utility exists
- [ ] False positive tracking in observability
- [ ] Works with 10K+ entries

---

## Phase 4: Documentation

### P4-001: Documentation & Examples

**Goal:** Someone understands and deploys in 10 minutes.

**Files:**
```
README.md                       — Already updated
docs/
  QUICKSTART.md                 — Get running in 5 minutes
  SAFETY.md                     — Guardrails, budget, audit
  OBSERVABILITY.md              — Metrics, dashboards
  SELF-LEARNING.md              — Thompson Sampling, when to enable RLP
  INTEGRATION.md                — Enterprise integration guide
examples/
  basic_agent.py                — Minimal example
  safe_agent.py                 — With all guardrails
  observable_agent.py           — With full metrics
```

**Acceptance Criteria:**
- [ ] New user can deploy in 10 minutes
- [ ] All examples are runnable and tested
- [ ] Safety defaults documented

---

## Phase 5: Experimental Methods (FUTURE)

### P5-001: Experimental Methods Hardening

**Status:** BLOCKED until 500+ interactions collected.

**Goal:** Harden RLP/SAO for optional use.

**Data Gates:**
- RLP: 500+ interactions minimum
- SAO: 1000+ interactions minimum
- Meta-MAB: DEFERRED (no production proof)

**Files:**
```
convergence/experimental/__init__.py    — With warnings
convergence/experimental/rlp.py         — Moved from plugins
convergence/experimental/sao.py         — Moved from plugins
convergence/experimental/gates.py       — Data-gating logic
```

**NOT BUILDING (per Architecture v3):**
- Meta-MAB (no production proof)
- Full Constitutional AI (YAML principles enough)
- Pattern evolution (patterns that work are enough)
- Multi-agent orchestration (single agent for MVP)

---

## Execution Order

```
Week 1:
├── P0-001: Foundation Hardening (2-3 days)
│   └── Thompson persistence, RLP monitoring
└── P0-002: Context Graph MVP (2-3 days)
    └── Basic schema + operations

Week 2:
├── P1-001: Safety & Guardrails (2-3 days)
│   └── NeMo + Guardrails AI + Budget
└── P2-001: Observability Protocol (1-2 days)
    └── Native metrics, optional Weave

Week 3:
├── P3-001: Semantic Cache Enhancement (1-2 days)
│   └── ANN search, threshold validation
└── P4-001: Documentation (1-2 days)
    └── Quickstart, examples

Future (after 500+ interactions):
└── P5-001: Experimental Methods
```

---

## Closed Contracts (Superseded)

All contracts created before 2026-03-12 19:00 UTC are superseded:
- CR-003: ✅ COMPLETE (PR review fixes)
- CR-004: ✅ COMPLETE (confidence.py bugs)
- CR-005 through CR-010: SUPERSEDED by Architecture v3
- CR-005-v2, CR-006-v2: SUPERSEDED by Architecture v3
- META-001: DEFERRED (Meta-MAB not production-ready)

---

## Key Decisions (Immutable)

1. **Safety is an invariant, not a feature** — Framework-level guardrails
2. **Integrate, don't invent** — NeMo, Guardrails AI, sentence-transformers
3. **Data-gate experimental methods** — RLP at 500+, SAO at 1000+
4. **Thompson Sampling first** — Converges in 15-30 interactions
5. **Semantic cache is killer feature** — 80% cost reduction target
6. **Single agent for MVP** — Multi-agent adds complexity
7. **Context Graph is substrate** — Everything operates on the graph

---

## Teardown Tracking

| Critical | Issue | Contract | Status |
|----------|-------|----------|--------|
| CRITICAL-1 | Context Graph missing | P0-002 | READY |
| CRITICAL-2 | Thompson state not persisted | P0-001 | READY |
| CRITICAL-3 | Semantic Cache O(n) | P3-001 | READY |

| Security | Issue | Contract | Status |
|----------|-------|----------|--------|
| SEC-1 | NeMo config undefined | P1-001 | READY |
| SEC-2 | Budget not persisted | P1-001 | READY |

---

*This is the authoritative implementation plan. All work should reference these contracts.*
