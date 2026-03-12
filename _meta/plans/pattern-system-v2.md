# Pattern System v2: Research-Informed Architecture

**Date:** 2026-03-11
**Status:** Design proposal based on research synthesis
**Sources:** novel-approaches-2026.md, funjoin-failure-patterns.md, funjoin-integration-needs.md, collabvault-learnings.md

---

## Executive Summary

Research reveals the original contracts were too narrow. The pattern system isn't just "text classification" — it's the **principle distillation layer** for self-evolving agents. Key pivots:

1. **EvolveR-style principle tracking** replaces static pattern lists
2. **Constitutional alignment** replaces hardcoded confidence thresholds
3. **Native observability watches the learning process**, not just outputs
4. **Thompson Sampling is the canonical approach** (validated across 4+ sources)
5. **Phase 1 is manual calibration** — self-learning requires 500+ interactions

---

## Architectural Insights from Research

### 1. EvolveR's Principle Distillation (Novel)

Instead of static `HEDGING_PHRASES` and `CERTAINTY_PHRASES`, treat each phrase as a **principle with quality tracking**:

```python
# Current (static)
HEDGING_PHRASES = ["maybe", "possibly", "uncertain", ...]

# Proposed (EvolveR-inspired)
class PatternPrinciple:
    phrase: str
    success_count: int = 0
    usage_count: int = 0

    @property
    def quality_score(self) -> float:
        # EvolveR's scoring: (success + 1) / (usage + 2)
        return (self.success_count + 1) / (self.usage_count + 2)
```

**Integration point:** When confidence extraction succeeds/fails, update the phrase's quality score. Low-performing phrases decay. High-uncertainty phrases get explored (Thompson Sampling on phrase selection).

### 2. Constitutional Alignment for Patterns

Instead of RLHF-style training data, define **pattern principles** that the system critiques against:

```yaml
# patterns/constitution/confidence.yaml
principles:
  - name: hedging_detection
    description: "Phrases indicating uncertainty should reduce confidence"
    examples:
      positive: ["I'm not sure", "possibly", "maybe"]
      negative: ["I am sure", "definitely", "without a doubt"]
    critique_template: |
      Does this text contain hedging language?
      If yes, confidence should decrease.

  - name: negation_cancellation
    description: "Negation of hedging restores confidence"
    examples:
      positive: ["I am NOT uncertain", "definitely not maybe"]
      negative: ["I am uncertain", "maybe"]
```

**Advantage:** Update constitution without retraining. Explicit, auditable principles.

### 3. Native Observability: Watch the Learning

Standard LLMOps watches outputs. Self-learning systems need to watch **the learning process itself**:

| Metric Category | What to Track |
|-----------------|---------------|
| **Principle Effectiveness** | Which patterns hit often? Which succeed when used? |
| **Calibration Drift** | Does 80% confidence = 80% success? |
| **Cost-Quality Pareto** | Are we sacrificing quality for cost? |
| **Reasoning Drift** | Is confidence extraction changing over time? |

### 4. Thompson Sampling for Pattern Selection

Research confirms Thompson Sampling as canonical for LLM alignment. Apply to pattern evolution:

```python
# Each phrase is an arm
# Beta(alpha, beta) tracks success/failure
# Sample from posterior to select which patterns to apply
# Update posterior on outcome

class PatternArm:
    phrase: str
    alpha: float = 1.0  # Success prior
    beta: float = 1.0   # Failure prior

    def sample_priority(self) -> float:
        return np.random.beta(self.alpha, self.beta)

    def update(self, success: bool):
        if success:
            self.alpha += 1
        else:
            self.beta += 1
```

### 5. Memory Decay for Pattern Freshness

From CollabVault: `1/(1 + age/30)` halves score at 30 days.

```python
def pattern_freshness(last_used: datetime) -> float:
    age_days = (datetime.now() - last_used).days
    return 1.0 / (1 + age_days / 30)
```

**Application:** Old patterns that haven't been used decay in selection priority. Forces exploration of newer patterns.

---

## Revised Contract Architecture

### Phase 0: CR-004 (COMPLETE)
Bug fixes in confidence.py — already done.

### Phase 1: CR-010 (NEW) — Principle Tracking Foundation

**Goal:** Add quality tracking to existing patterns WITHOUT changing API.

**Files:**
- `convergence/patterns/__init__.py`
- `convergence/patterns/principle.py`
- `convergence/patterns/tracker.py`
- `convergence/storage/patterns.py` (SQLite persistence)

**Schema:**
```sql
CREATE TABLE pattern_principles (
    phrase TEXT PRIMARY KEY,
    domain TEXT,  -- 'hedging', 'certainty', 'code_quality'
    success_count INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    last_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**Interface:**
```python
# Track pattern usage
await tracker.record_usage("maybe", domain="hedging")

# Track pattern success
await tracker.record_outcome("maybe", success=True)

# Get quality-weighted patterns
patterns = await tracker.get_active_patterns(domain="hedging")
```

**Tier:** 2 (4 files)
**Dependencies:** None
**Novel aspect:** EvolveR-style quality tracking

---

### Phase 2: CR-005-v2 — Protocol-Based Observability

**Goal:** Watch the learning process, not just outputs.

**Files:**
- `convergence/observability/__init__.py`
- `convergence/observability/protocol.py` (Observer protocol)
- `convergence/observability/native.py` (Built-in metrics)
- `convergence/observability/metrics.py` (Counters, histograms)
- `convergence/observability/weave.py` (Optional adapter)

**Metrics to Track:**
```python
# Principle effectiveness
principle_usage_count: Counter  # How often each phrase is used
principle_success_rate: Gauge   # Success rate per phrase
principle_staleness: Histogram  # Age distribution

# Calibration
calibration_error: Gauge        # |predicted_confidence - actual_success|
cost_quality_ratio: Gauge       # Quality score / token cost

# Drift detection
reasoning_pattern_hash: str     # Hash of recent pattern selections
drift_detected: bool            # True if hash changed significantly
```

**Protocol:**
```python
class Observer(Protocol):
    async def record_pattern_usage(self, phrase: str, domain: str) -> None: ...
    async def record_pattern_outcome(self, phrase: str, success: bool) -> None: ...
    async def record_calibration_point(self, predicted: float, actual: bool) -> None: ...
    async def get_principle_stats(self) -> PrincipleStats: ...
```

**Tier:** 2 (5 files)
**Dependencies:** None
**Novel aspect:** Observes learning, not just inference

---

### Phase 3: CR-006-v2 — YAML Patterns + Constitution

**Goal:** Move patterns to YAML with constitutional structure.

**Files:**
- `convergence/patterns/loader.py`
- `convergence/patterns/constitution.py`
- `convergence/patterns/schemas/v1.yaml`
- `convergence/patterns/schemas/confidence.yaml`
- `convergence/patterns/schemas/code_quality.yaml`

**Schema (confidence.yaml):**
```yaml
version: 1
domain: confidence

constitution:
  - principle: hedging_detection
    description: "Uncertainty language reduces confidence"
    weight: -0.15  # Per match

  - principle: certainty_detection
    description: "Certainty language increases confidence"
    weight: +0.10

  - principle: negation_cancellation
    description: "Negation of hedging restores confidence"
    priority: high  # Check first

patterns:
  hedging:
    multi_word:
      - "i'm not sure"
      - "not entirely sure"
      - "it seems like"
    single_word:
      - maybe
      - possibly
      - perhaps
    negators:
      - "i am sure"
      - "am certain"

  certainty:
    multi_word:
      - "without a doubt"
      - "for sure"
    single_word:
      - definitely
      - certainly
      - absolutely
```

**Loader:**
```python
class PatternLoader:
    async def load(self, domain: str) -> PatternSet: ...
    async def reload(self) -> None: ...  # Hot reload
    async def validate(self, yaml_content: str) -> ValidationResult: ...
```

**Tier:** 2 (5 files)
**Dependencies:** None
**Novel aspect:** Constitutional structure, hot-reload

---

### Phase 4: CR-007-v2 — Multi-Mode Classifier with Protocol

**Goal:** Unified classifier interface with mode switching.

**Files:**
- `convergence/classifier/__init__.py`
- `convergence/classifier/protocol.py`
- `convergence/classifier/confidence.py`
- `convergence/classifier/code_quality.py`
- `convergence/classifier/factory.py`

**Protocol:**
```python
class ClassifierMode(Protocol):
    mode_id: str
    domain: str

    async def classify(self, text: str) -> ClassifierResult: ...
    async def record_outcome(self, result_id: str, success: bool) -> None: ...

@dataclass
class ClassifierResult:
    score: float              # 0.0 - 1.0
    mode_id: str
    patterns_matched: list[str]
    confidence_in_score: float  # Meta-confidence
    result_id: str            # For feedback
```

**Factory:**
```python
classifier = ClassifierFactory.create(
    mode="confidence",
    observer=native_observer,
    tracker=pattern_tracker
)

result = await classifier.classify(text)
# Later...
await classifier.record_outcome(result.result_id, success=True)
```

**Tier:** 2 (5 files)
**Dependencies:** CR-010, CR-005-v2, CR-006-v2
**Novel aspect:** Unified protocol, feedback integration

---

### Phase 5: CR-008-v2 — Thompson Sampling for Patterns

**Goal:** Connect patterns to existing MAB infrastructure.

**Files:**
- `convergence/patterns/evolution.py`
- `convergence/patterns/sampler.py`
- `convergence/runtime/pattern_integration.py`

**Mechanism:**
```python
class PatternSampler:
    """Thompson Sampling over pattern effectiveness."""

    async def sample_active_patterns(self, domain: str, k: int = 20) -> list[str]:
        """Select top-k patterns by posterior sampling."""
        patterns = await self.tracker.get_all(domain)

        # Sample from Beta posteriors
        scores = [
            (p.phrase, np.random.beta(p.alpha, p.beta) * pattern_freshness(p.last_used))
            for p in patterns
        ]

        # Return top-k by sampled score
        scores.sort(key=lambda x: x[1], reverse=True)
        return [phrase for phrase, _ in scores[:k]]

    async def record_feedback(self, phrases_used: list[str], success: bool):
        """Update posteriors based on classification outcome."""
        for phrase in phrases_used:
            await self.tracker.record_outcome(phrase, success)
```

**Integration:**
```python
# In classifier
active_patterns = await sampler.sample_active_patterns("hedging")
result = await self._classify_with_patterns(text, active_patterns)

# On outcome feedback
await sampler.record_feedback(result.patterns_matched, success=outcome.success)
```

**Tier:** 2 (3 files)
**Dependencies:** CR-010, CR-007-v2
**Novel aspect:** Actual MAB integration (missing in original)

---

### Phase 6: CR-009-v2 — Documentation + FunJoin Example

**Goal:** README that sells the vision + practical integration guide.

**Files:**
- `README.md` (full rewrite)
- `docs/QUICKSTART.md`
- `docs/PATTERNS.md`
- `examples/funjoin_integration.py`

**README Structure:**
1. **Vision:** Self-evolving agents, not API optimization
2. **How It Works:** MAB → Evolution → RL Meta → Storage
3. **Quick Start:** 3 function calls (FunJoin style)
4. **Pattern System:** Constitutional alignment + Thompson Sampling
5. **Observability:** Watch your system learn
6. **Production:** What "phase 1 vs phase 2" means

**Tier:** 1 (4 files)
**Dependencies:** All above
**Novel aspect:** Sells the story, not the features

---

## Implementation Order (Revised)

| Phase | Contract | Files | Deps | Novel Element |
|-------|----------|-------|------|---------------|
| 0 | CR-004 | 1 | - | ✓ DONE |
| 1 | CR-010 | 4 | - | EvolveR tracking |
| 2 | CR-005-v2 | 5 | - | Learning observability |
| 3 | CR-006-v2 | 5 | - | Constitutional YAML |
| 4 | CR-007-v2 | 5 | 1,2,3 | Unified protocol |
| 5 | CR-008-v2 | 3 | 1,4 | Thompson on patterns |
| 6 | CR-009-v2 | 4 | ALL | Vision docs |

**Total:** 27 files, Tier 3 overall (but each phase is Tier 2 or less)

---

## Key Pivots from Original Design

### 1. Static → Dynamic Patterns
**Original:** Hardcoded `HEDGING_PHRASES` list
**New:** Patterns with quality tracking, Thompson Sampling selection, decay

### 2. Observe Outputs → Observe Learning
**Original:** Weave logging of LLM calls
**New:** Metrics on principle effectiveness, calibration drift, cost-quality pareto

### 3. YAML Config → Constitutional YAML
**Original:** Move patterns to YAML file
**New:** YAML with constitutional principles, critique templates, explicit weights

### 4. Separate MAB → Unified Loop
**Original:** Pattern system disconnected from Thompson Sampling
**New:** Patterns ARE arms in the bandit, same infrastructure

### 5. Arbitrary Thresholds → Calibrated Thresholds
**Original:** `confidence < 0.6` is hardcoded
**New:** Track calibration error, adjust thresholds based on actual success rates

---

## Questions Resolved by Research

### Q1: Should patterns evolve globally or per-user?
**Answer (from CollabVault):** Global patterns with per-user weighting. Patterns are shared; thresholds adapt per-user.

### Q2: What's the canonical feedback signal?
**Answer (from EvolveR):** `(success_count + 1) / (usage_count + 2)` — smoothed success rate with Bayesian prior.

### Q3: Where do evolved patterns persist?
**Answer (from FunJoin needs):** SQLite by default (already in storage layer). Same RuntimeStorageProtocol.

---

## Risk Mitigations

### Risk: Self-learning amplifies bias
**Mitigation (from FunJoin failures):**
- Adversarial validation in training pipeline
- Diverse fitness evaluation
- Human review of pattern changes (not just outputs)

### Risk: Calibration drift
**Mitigation (from novel approaches):**
- Track `|predicted_confidence - actual_success|`
- Alert when drift exceeds threshold
- Monthly recalibration cadence

### Risk: Cold start (new patterns have no history)
**Mitigation (from teardown):**
- Seed initial patterns with reasonable priors (e.g., Beta(5, 1) for known-good)
- Conservative exploration in first 500 interactions

### Risk: Pattern explosion (500+ patterns become unmaintainable)
**Mitigation (from CollabVault):**
- Decay formula: `1/(1 + age/30)`
- Prune patterns below quality threshold
- Partition by domain (hedging/, certainty/, code_quality/)

---

## FunJoin Integration Test

After all phases complete, validate with FunJoin's use case:

```python
# 1. Configure once
await configure_runtime("funjoin_agent", config={
    "arms": [...],
    "storage": {"backend": "postgresql"},
    "patterns": {"domains": ["confidence"]},
    "observability": {"backend": "native"}
})

# 2. Select per request
selection = await runtime_select("funjoin_agent", user_id=user_id)

# 3. Generate response with confidence
response = await claude.chat(message, **selection.params)
confidence = await classifier.classify(response.content)

# 4. Update on outcome + pattern feedback
await runtime_update(
    "funjoin_agent",
    decision_id=selection.decision_id,
    reward=outcome.reward
)
await classifier.record_outcome(
    confidence.result_id,
    success=outcome.success
)
```

**Expected results:**
- Patterns improve over 500+ interactions
- Confidence calibration error < 5%
- 80% cache hit rate on semantic similar queries
- Observability shows learning trajectory

---

*Plan generated: 2026-03-11*
*Based on: 4 research documents, 1200+ lines of synthesis*
*Status: Ready for implementation*
