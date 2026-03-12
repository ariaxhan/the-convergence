# Tear Down: Pattern Matching System Redesign

**Reviewed:** 2026-03-12
**Scope:** Centralized classifier, self-evolving patterns, native observability, YAML config
**Files Analyzed:** confidence.py, code_quality.py, text_quality.py, weave_logger.py, bayesian_update.py, thompson_sampling.py

---

## Critical Issues

### CRITICAL-1: No Self-Evolution Mechanism for Patterns

**Problem:** The proposal mentions "self-evolving patterns" but The Convergence already HAS the machinery for this:
- `bayesian_update.py` - Computes Beta distribution updates
- `thompson_sampling.py` - Selects arms based on posterior sampling
- `runtime/evolution.py` - Genetic crossover and mutation

**But patterns (HEDGING_PHRASES, CERTAINTY_PHRASES) are NOT connected to this loop.**

**Impact:** You'll build pattern evolution from scratch when 80% of it already exists.

**Fix:** Treat each phrase as an "arm" in a MAB. When confidence extraction succeeds/fails, update the phrase's Beta distribution. Low-performing phrases get pruned. High-uncertainty phrases get explored.

---

### CRITICAL-2: Weave Dependency Creates Vendor Lock-In

**Problem:** User explicitly requested native observability, not Weave dependency. Current code:
- `weave_logger.py` - 365 lines tightly coupled to Weave
- `thompson_sampling.py` - Uses `@weave.op()` decorators directly
- All observability goes through W&B infrastructure

**Impact:** Users without W&B accounts get no observability. Library is unusable offline.

**Fix:** Create `convergence/observability/` with protocol-based backends:
1. `BaseObserver` protocol (native)
2. `WeaveObserver` (optional adapter)
3. `StructlogObserver` (lightweight structured logging)
4. `MetricsCollector` (prometheus-style counters, no external deps)

---

### CRITICAL-3: Pattern Bugs in Production Code

**Problem:** Research identified 3 bugs in `confidence.py`:

1. **Line 145-146:** `NEGATION_PATTERNS` used without `re.IGNORECASE`
   - "I AM SURE" won't cancel hedging detection

2. **Line 158:** Patterns recompile on every function call
   - 5-10x performance degradation
   - Should compile once at module level

3. **Word boundary handling:** Single-word phrases use `\b{phrase}\b`, but:
   - Fails with possessives: "maybe's" won't match "maybe"
   - Fails with contractions: "I'm" boundary issues

**Impact:** Confidence extraction produces wrong results in production.

---

### CRITICAL-4: Missing Protocol for Classifier Modes

**Problem:** User asked "can we make a centralized one with different modes?" but no design exists for:
- How modes switch (explicit vs hedging vs certainty vs auto)
- How modes share patterns vs have independent patterns
- How mode-specific patterns evolve independently
- How to add new modes without code changes

**Impact:** Will build ad-hoc mode switching, creating maintenance burden.

**Fix:** Design `ClassifierMode` protocol:
```python
class ClassifierMode(Protocol):
    mode_id: str
    patterns: PatternSet
    def classify(self, text: str) -> ClassifierResult: ...
    def update_patterns(self, feedback: Feedback) -> None: ...
```

---

## Security Review

### SEC-1: Pattern Injection (Low Risk)

**Problem:** If YAML patterns are user-supplied, regex patterns could contain ReDoS attacks.

**Mitigation:** Validate pattern syntax on load. Timeout regex matching. Use `re2` library for untrusted patterns.

### SEC-2: Sensitive Text Logging

**Problem:** Observability will log text for classification. This may contain PII.

**Mitigation:** Hash or truncate text in logs. Never log raw input > 100 chars.

---

## Concerns

### CONCERN-1: Pattern YAML Could Become Unmaintainable

**Risk:** Starting with 45 phrases, but as system evolves patterns, could grow to 500+.

**Mitigation:** Partition by domain (confidence/, code_quality/, text_quality/). Add pruning for low-hit-rate patterns.

### CONCERN-2: Cold Start for Pattern Evolution

**Risk:** New patterns have no history. Thompson Sampling with uniform priors will over-explore.

**Mitigation:** Seed initial patterns with reasonable priors (e.g., Beta(5, 1) for known-good patterns).

### CONCERN-3: Test Coverage for Pattern Changes

**Risk:** Patterns evolve, tests don't. Regression risk.

**Mitigation:** Golden test sets that run on EVERY pattern change. Snapshot tests for pattern file hashes.

### CONCERN-4: No Feedback Loop from Claude Client

**Risk:** `ClaudeClient` extracts confidence but doesn't feed results back to pattern system.

**Mitigation:** Add `ConfidenceTracker` that records (text, extracted_confidence, user_feedback) and feeds into pattern evolution.

---

## Questions

### Q1: What's the canonical feedback signal?

For pattern evolution, what constitutes "success"?
- User explicitly says confidence was wrong?
- Downstream task succeeded?
- LLM self-verification?

**Recommendation:** Start with explicit user feedback via `record_outcome()`. Later add implicit signals.

### Q2: Should patterns evolve globally or per-user?

Thompson Sampling already tracks per-user arms in `runtime_select()`.

**Recommendation:** Global patterns with per-user weighting. Patterns themselves are shared; confidence thresholds adapt per-user.

### Q3: Where do evolved patterns persist?

SQLite? YAML files? PostgreSQL?

**Recommendation:** SQLite by default (already in storage). YAML export for human inspection.

---

## Architecture Assessment

### Separation of Concerns: POOR

Current code mixes:
- Pattern definition (hardcoded lists)
- Pattern matching (regex in functions)
- Confidence calculation (heuristic scoring)
- Result formatting (return values)

**Fix:** Split into:
```
convergence/patterns/
├── __init__.py
├── config.py          # Load YAML patterns
├── matcher.py         # Pattern matching engine
├── classifier.py      # Multi-mode classifier
├── evolution.py       # Pattern MAB + mutation
└── patterns/
    ├── v1.yaml        # Base patterns
    └── evolved.yaml   # Learned patterns
```

### Coupling: HIGH

`confidence.py` is imported by:
- `claude.py` (via weird import hack)
- `text_quality.py` (implicit via conventions)

**Fix:** Create `convergence.classifier` as the single entry point. Other modules import the classifier, not raw pattern functions.

### Interface Stability: NOT DESIGNED

No clear API boundary. If patterns change structure, all consumers break.

**Fix:** Define `ClassifierResult` dataclass. Consumers only depend on the result type, not internals.

### Pattern Consistency: MIXED

Some patterns precompiled, some not. Some use word boundaries, some don't. No consistent escaping.

**Fix:** All patterns go through `PatternLoader` which normalizes and compiles.

---

## What The Convergence Is Currently Weak On

### WEAK-1: No Native Observability

All observability is Weave. No fallback. No metrics without W&B.

### WEAK-2: Pattern System Is Static

The framework is about self-evolution, but patterns don't evolve. They're hardcoded.

### WEAK-3: No Classification Abstractions

Confidence extraction is a special case of text classification. No reusable abstraction.

### WEAK-4: No Feedback From Clients

`ClaudeClient` extracts confidence but results don't feed back into learning.

### WEAK-5: README Doesn't Mention Text Classification

The core selling point is self-evolution, but the README doesn't show how text patterns can evolve.

---

## Verdict: REVISE

**Addressable issues, but significant design work needed before implementation.**

### Required Changes Before Proceeding:

1. **Design `ClassifierMode` protocol** - How modes work, how they share/isolate patterns
2. **Design native observability protocol** - `BaseObserver` with pluggable backends
3. **Design pattern evolution integration** - Connect patterns to existing Thompson Sampling
4. **Fix the 3 bugs in confidence.py first** - Before any architectural changes
5. **Define feedback loop** - How does user feedback flow into pattern updates?
6. **Partition work into phases** - Don't try to do everything at once

### Recommended Implementation Order:

| Phase | Scope | Files |
|-------|-------|-------|
| 0 | Fix bugs in confidence.py | 1 |
| 1 | Create native observability protocol | 4-5 |
| 2 | Centralize patterns into YAML + loader | 4-5 |
| 3 | Create multi-mode classifier | 3-4 |
| 4 | Connect patterns to MAB evolution | 3-4 |
| 5 | Add feedback loop from ClaudeClient | 2-3 |
| 6 | Update README with pattern evolution story | 1 |

---

## Files To Create/Modify

**New Package Structure:**
```
convergence/
├── classifier/           # NEW
│   ├── __init__.py
│   ├── base.py           # ClassifierResult, ClassifierMode protocol
│   ├── confidence.py     # Confidence-specific classifier
│   ├── code_quality.py   # Code-specific classifier
│   └── matcher.py        # Unified pattern matching engine
├── patterns/             # NEW
│   ├── __init__.py
│   ├── loader.py         # YAML loading + validation
│   ├── evolution.py      # Pattern MAB integration
│   └── schemas/
│       └── v1.yaml       # Pattern definitions
├── observability/        # NEW
│   ├── __init__.py
│   ├── base.py           # Observer protocol
│   ├── native.py         # Built-in metrics + structured logging
│   ├── weave.py          # Optional Weave adapter
│   └── metrics.py        # Counter/gauge/histogram implementations
└── evaluators/
    ├── confidence.py     # MODIFY - use classifier/
    ├── code_quality.py   # MODIFY - use classifier/
    └── text_quality.py   # MODIFY - use classifier/
```

**Total: 15-20 files, Tier 3 implementation**

---

## Sources

- Research docs: `_meta/research/regex-alternatives.md`, `observability-patterns.md`, `pattern-fragility.md`
- Existing code: `bayesian_update.py`, `thompson_sampling.py`, `weave_logger.py`
- User requirements: Native observability, self-evolving patterns, centralized classifier, production-grade robustness
