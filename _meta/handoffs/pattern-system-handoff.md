# Handoff: Pattern System + Convergence Vision

**Date:** 2026-03-12
**Session:** Pattern matching redesign, native observability, self-evolving patterns
**Branch:** main (clean)
**Status:** CR-004 complete, remaining contracts ready for implementation

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

### 2. Research Completed (3 docs in `_meta/research/`)
- `regex-alternatives.md` - Stick with regex, but optimize
- `observability-patterns.md` - Native observability design
- `pattern-fragility.md` - YAML config + golden tests

### 3. Tear-Down Review (REVISE verdict)
- **File:** `_meta/reviews/pattern-system-teardown.md`
- **4 Critical Issues:**
  1. Patterns not connected to existing MAB
  2. Weave vendor lock-in (no native observability)
  3. 3 bugs in confidence.py
  4. No classifier mode protocol

---

## Contracts Ready for Implementation

### CR-004: Fix Confidence Bugs (Tier 1) ✓ COMPLETE
```json
{
  "goal": "Fix 3 bugs in confidence.py",
  "files": ["convergence/evaluators/confidence.py"],
  "tier": 1,
  "status": "complete",
  "fixes": [
    "Added re.IGNORECASE to NEGATION_PATTERNS (now precompiled)",
    "Precompiled all patterns at module level (_HEDGING_SINGLE_WORD_PATTERNS, etc.)",
    "Added contraction support: (?:'[a-z]*)? suffix for word boundary patterns"
  ]
}
```

### CR-005: Native Observability (Tier 2)
```json
{
  "goal": "Create protocol-based observability without Weave dependency",
  "files": [
    "convergence/observability/__init__.py",
    "convergence/observability/base.py",
    "convergence/observability/native.py",
    "convergence/observability/metrics.py",
    "convergence/observability/weave.py"
  ],
  "tier": 2,
  "design": "BaseObserver protocol + pluggable backends"
}
```

### CR-006: Pattern YAML + Loader (Tier 2)
```json
{
  "goal": "Move patterns to YAML with hot-reload",
  "files": [
    "convergence/patterns/__init__.py",
    "convergence/patterns/loader.py",
    "convergence/patterns/schemas/v1.yaml",
    "convergence/evaluators/confidence.py (update to use loader)"
  ],
  "tier": 2
}
```

### CR-007: Multi-Mode Classifier (Tier 2)
```json
{
  "goal": "Create centralized classifier with mode switching",
  "files": [
    "convergence/classifier/__init__.py",
    "convergence/classifier/base.py",
    "convergence/classifier/confidence.py",
    "convergence/classifier/matcher.py"
  ],
  "tier": 2,
  "modes": ["explicit", "hedging", "certainty", "code_quality", "custom"]
}
```

### CR-008: Pattern Evolution (Tier 3)
```json
{
  "goal": "Connect patterns to Thompson Sampling for self-evolution",
  "files": [
    "convergence/patterns/evolution.py",
    "convergence/runtime/online.py (integrate pattern feedback)",
    "convergence/plugins/mab/thompson_sampling.py (phrase arms)",
    "convergence/storage/sqlite.py (pattern stats)"
  ],
  "tier": 3,
  "design": "Each phrase = arm. Success/fail updates Beta distribution. Low performers pruned."
}
```

### CR-009: README + Docs Update (Tier 1)
```json
{
  "goal": "Update README for plug-and-play vision",
  "files": [
    "README.md",
    "docs/QUICKSTART.md"
  ],
  "tier": 1,
  "vision": "Install → provide data → run self-optimization"
}
```

---

## Implementation Order

| Phase | Contract | Scope | Dependencies | Status |
|-------|----------|-------|--------------|--------|
| 0 | CR-004 | Fix confidence bugs | None | ✓ DONE |
| 1 | CR-005 | Native observability | None | Ready |
| 2 | CR-006 | YAML patterns | None | Ready |
| 3 | CR-007 | Multi-mode classifier | CR-006 | Blocked |
| 4 | CR-008 | Pattern evolution | CR-006, CR-007 | Blocked |
| 5 | CR-009 | README update | All above | Blocked |

---

## Key Insight: Use Existing Infrastructure

The Convergence ALREADY HAS:
- `bayesian_update.py` - Beta distribution math
- `thompson_sampling.py` - Arm selection
- `runtime/evolution.py` - Mutation/crossover
- `storage/` - Persistence layer

**Just connect patterns to this loop.** Don't rebuild.

---

## FunJoin Integration Pattern

From `funjoin/_meta/docs/convergence-integration.md`:

```python
# Configure once
await configure_runtime("funjoin_sales", config={
    "arms": [...],  # Response variants
    "storage": {"backend": "sqlite"}
})

# Select per request
selection = await runtime_select("funjoin_sales", user_id=user_id)
response = await claude.chat(message, **selection.params)

# Update on outcome
await runtime_update("funjoin_sales", decision_id=selection.decision_id, reward=1.0)
```

**Goal:** Same simplicity for pattern evolution. Patterns auto-improve based on success signals.

---

## Files Modified This Session

- `convergence/clients/claude.py` - Added user_id to record_outcome
- `convergence/cache/semantic.py` - Fixed get_running_loop
- `convergence/evaluators/confidence.py` - Sorted VALID_METHODS, **CR-004: precompiled patterns, IGNORECASE, contraction support**
- `convergence/storage/postgresql.py` - Scoped UPDATE by user_id
- `convergence/generator/natural_language_processor.py` - Fixed JSON handling
- `.claude/rules/project.md` - Added known tech debt section

---

## Next Steps

1. ~~**Run CR-004** (bug fix)~~ ✓ DONE
2. **Start CR-005** - Native observability protocol (Tier 2, no deps)
3. **Start CR-006** - YAML patterns foundation (Tier 2, no deps)
4. **CR-007** - Multi-mode classifier (depends on CR-006)
5. **CR-008** - Pattern evolution via MAB (depends on CR-006, CR-007)
6. **Test with FunJoin** - Real consumer validation

---

## Questions for Next Session

1. Should patterns evolve **globally** or **per-user**?
2. What's the canonical **feedback signal** for pattern success?
3. How much of pattern config should be **user-facing** vs internal?

---

*Handoff prepared: 2026-03-12*
