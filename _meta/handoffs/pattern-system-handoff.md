# Handoff: Pattern System + Convergence Vision

**Date:** 2026-03-12 (Updated)
**Session:** Research synthesis complete, architecture v2 designed
**Branch:** main (clean)
**Status:** CR-004 complete, v2 architecture ready for implementation

---

## Context

FunJoin is building an AI agent using The Convergence. The goal: make Convergence so easy that deployers only provide:
1. **Data inputs** (tools + integrations + APIs)
2. **Storage** (database for all knowledge)
3. **Run** self-optimization (A/B testing, RLP, SAO)

All infrastructure should live IN Convergence. Company-specific code should be minimal.

---

## What Was Done This Session

### 1. Fixed PR Review Issues (COMPLETE)
- `record_outcome` user_id parameter
- `asyncio.get_running_loop()` fix
- PostgreSQL UPDATE scope
- JSON truncation handling
- All CI checks passing

### 2. Research Completed (4 docs in `_meta/research/`)
- `novel-approaches-2026.md` - EvolveR, MAE, Constitutional AI, Thompson Sampling validation
- `funjoin-failure-patterns.md` - 5 failure categories, 95% pilot failure rate, antipatterns
- `funjoin-integration-needs.md` - FunJoin's plug-and-play definition, priority features
- `collabvault-learnings.md` - 47 patterns, decision traces, memory decay formula

### 3. CR-004: Fix Confidence Bugs ✓ COMPLETE
- Added re.IGNORECASE to NEGATION_PATTERNS (precompiled)
- Precompiled all patterns at module level
- Added contraction support: `(?:'[a-z]*)?` suffix

### 4. Architecture v2 Designed
- **File:** `_meta/plans/pattern-system-v2.md`
- **Key pivot:** Static patterns → EvolveR-style principle tracking
- **6 phases, 27 files total**

---

## Key Research Findings

### Novel Approaches (Applied)

| Source | Insight | Application |
|--------|---------|-------------|
| EvolveR | Quality score = (success+1)/(usage+2) | Pattern tracking |
| Constitutional AI | Principles over examples | YAML constitution |
| Thompson Sampling | Validated for LLM alignment | Pattern selection |
| Failure studies | 79% from spec/coordination | Explicit protocols |
| Memory decay | 1/(1 + age/30) | Pattern freshness |

### Critical Statistics

- **95%** of AI pilots fail (MIT 2025)
- **79%** of multi-agent failures from spec/coordination, not tech
- **41-86.7%** production failure rate
- **500+** interactions needed before self-learning calibration
- **80%** cost reduction possible via semantic cache

---

## Revised Contract Architecture

### Phase 0: CR-004 ✓ COMPLETE

### Phase 1: CR-010 — Principle Tracking Foundation (NEW)
```json
{
  "goal": "Add EvolveR-style quality tracking to patterns",
  "files": [
    "convergence/patterns/__init__.py",
    "convergence/patterns/principle.py",
    "convergence/patterns/tracker.py",
    "convergence/storage/patterns.py"
  ],
  "tier": 2,
  "novel": "Quality score = (success+1)/(usage+2)"
}
```

### Phase 2: CR-005-v2 — Learning Observability
```json
{
  "goal": "Watch the learning process, not just outputs",
  "files": [
    "convergence/observability/__init__.py",
    "convergence/observability/protocol.py",
    "convergence/observability/native.py",
    "convergence/observability/metrics.py",
    "convergence/observability/weave.py"
  ],
  "tier": 2,
  "metrics": ["principle_effectiveness", "calibration_drift", "cost_quality_pareto"]
}
```

### Phase 3: CR-006-v2 — Constitutional YAML
```json
{
  "goal": "YAML patterns with constitutional structure",
  "files": [
    "convergence/patterns/loader.py",
    "convergence/patterns/constitution.py",
    "convergence/patterns/schemas/v1.yaml",
    "convergence/patterns/schemas/confidence.yaml",
    "convergence/patterns/schemas/code_quality.yaml"
  ],
  "tier": 2,
  "novel": "Constitution + critique templates"
}
```

### Phase 4: CR-007-v2 — Unified Classifier Protocol
```json
{
  "goal": "Protocol-based classifier with feedback integration",
  "files": [
    "convergence/classifier/__init__.py",
    "convergence/classifier/protocol.py",
    "convergence/classifier/confidence.py",
    "convergence/classifier/code_quality.py",
    "convergence/classifier/factory.py"
  ],
  "tier": 2,
  "depends": ["CR-010", "CR-005-v2", "CR-006-v2"]
}
```

### Phase 5: CR-008-v2 — Thompson Sampling for Patterns
```json
{
  "goal": "Connect patterns to existing MAB infrastructure",
  "files": [
    "convergence/patterns/evolution.py",
    "convergence/patterns/sampler.py",
    "convergence/runtime/pattern_integration.py"
  ],
  "tier": 2,
  "depends": ["CR-010", "CR-007-v2"],
  "novel": "Patterns ARE arms in the bandit"
}
```

### Phase 6: CR-009-v2 — Vision Documentation
```json
{
  "goal": "README that sells the story + FunJoin example",
  "files": [
    "README.md",
    "docs/QUICKSTART.md",
    "docs/PATTERNS.md",
    "examples/funjoin_integration.py"
  ],
  "tier": 1,
  "depends": ["ALL"]
}
```

---

## Implementation Order

| Phase | Contract | Scope | Status |
|-------|----------|-------|--------|
| 0 | CR-004 | Bug fixes | ✓ DONE |
| 1 | CR-010 | Principle tracking | Ready |
| 2 | CR-005-v2 | Learning observability | Ready |
| 3 | CR-006-v2 | Constitutional YAML | Ready |
| 4 | CR-007-v2 | Unified classifier | Blocked on 1,2,3 |
| 5 | CR-008-v2 | Thompson on patterns | Blocked on 1,4 |
| 6 | CR-009-v2 | Documentation | Blocked on ALL |

**Phases 1, 2, 3 can run in parallel** (no dependencies).

---

## Key Pivots from Original Design

1. **Static → Dynamic Patterns**: Quality tracking, Thompson Sampling selection, decay
2. **Observe Outputs → Observe Learning**: Principle effectiveness, calibration drift
3. **YAML Config → Constitutional YAML**: Principles, critique templates, weights
4. **Separate MAB → Unified Loop**: Patterns ARE arms in the bandit
5. **Arbitrary Thresholds → Calibrated**: Track actual success rates

---

## AgentDB Updated

9 key research insights persisted:
- `evolver-principle-tracking`
- `thompson-validated`
- `constitutional-over-rlhf`
- `14-failure-modes`
- `41-86-failure-rate`
- `memory-decay-formula`
- `self-learning-phase-2`
- `observe-learning-not-outputs`
- `plug-and-play-means-3-calls`

---

## Files Modified This Session

- `convergence/evaluators/confidence.py` - CR-004 bug fixes
- `_meta/plans/pattern-system-v2.md` - New architecture (created)
- `_meta/research/novel-approaches-2026.md` - Research (created)
- `_meta/research/funjoin-failure-patterns.md` - Research (created)
- `_meta/research/funjoin-integration-needs.md` - Research (created)
- `_meta/research/collabvault-learnings.md` - Research (created)
- `_meta/handoffs/pattern-system-handoff.md` - Updated

---

## Next Steps

1. **Choose parallelization strategy**:
   - Option A: Run CR-010, CR-005-v2, CR-006-v2 in parallel (fastest)
   - Option B: Sequential for easier review

2. **Start with CR-010** (principle tracking) — foundation for everything else

3. **Validate with FunJoin** after Phase 4 — real consumer test

---

## Questions Resolved

1. **Should patterns evolve globally or per-user?**
   → Global patterns with per-user weighting

2. **What's the canonical feedback signal?**
   → `(success+1)/(usage+2)` — EvolveR's smoothed success rate

3. **Where do evolved patterns persist?**
   → SQLite (existing storage), same RuntimeStorageProtocol

---

*Handoff updated: 2026-03-12*
*Research complete, architecture v2 ready for implementation*
