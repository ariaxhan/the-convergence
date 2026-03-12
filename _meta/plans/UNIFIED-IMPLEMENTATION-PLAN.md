# UNIFIED IMPLEMENTATION PLAN

**Date:** 2026-03-12
**Status:** Active
**Consolidates:** pattern-system-v2.md, learning-system-2026-03-12.md, CR-005 through CR-010

---

## Executive Summary

This plan unifies two parallel threads:
1. **Pattern System v2** — Make patterns self-evolving (EvolveR-style tracking, Thompson Sampling)
2. **Adaptive Learning** — Meta-MAB selects learning methods (RLP, SAO, MemRL, CAI) per use case

Both share the same infrastructure: Thompson Sampling, quality tracking, storage. Build once, use everywhere.

---

## Architecture Vision

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THE CONVERGENCE v2                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     META-MAB (Method Selector)                       │    │
│  │   Thompson Sampling over: [RLP, SAO, MemRL, CAI, SELAUR, MAE]       │    │
│  │   Context: task_type, domain, user_history                           │    │
│  │   Reward: downstream task success                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│       ┌────────────────────────────┴────────────────────────────┐           │
│       ▼                            ▼                            ▼           │
│  ┌─────────┐              ┌─────────────────┐           ┌─────────────┐     │
│  │ METHODS │              │ PATTERN SAMPLER │           │ OBSERVABILITY│    │
│  │         │              │                 │           │              │    │
│  │  RLP    │              │ Thompson over   │           │ Native/Weave │    │
│  │  SAO    │              │ patterns        │           │ Learning     │    │
│  │  MemRL  │◄────────────►│ EvolveR scoring │◄─────────►│ Metrics      │    │
│  │  CAI    │              │ Decay formula   │           │ Calibration  │    │
│  └────┬────┘              └────────┬────────┘           └──────┬───────┘    │
│       │                            │                            │           │
│       └────────────────────────────┴────────────────────────────┘           │
│                                    │                                         │
│                                    ▼                                         │
│              ┌─────────────────────────────────────────┐                    │
│              │          UNIFIED TRACKER                 │                    │
│              │   quality_score = (success+1)/(usage+2) │                    │
│              │   freshness = 1/(1 + age/30)            │                    │
│              │   SQLite/PostgreSQL storage             │                    │
│              └─────────────────────────────────────────┘                    │
│                                    │                                         │
│                                    ▼                                         │
│              ┌─────────────────────────────────────────┐                    │
│              │          EXISTING RUNTIME               │                    │
│              │   configure_runtime()                   │                    │
│              │   runtime_select()                      │                    │
│              │   runtime_update()                      │                    │
│              └─────────────────────────────────────────┘                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 0: Foundation — Unified Tracker (CR-010)

**Goal:** Build the shared tracking infrastructure that BOTH patterns and methods will use.

**Why First:** Everything else depends on quality tracking. Build once, reuse everywhere.

**Files (4):**
```
convergence/tracking/__init__.py      — Package exports
convergence/tracking/principle.py     — Principle dataclass with quality_score
convergence/tracking/tracker.py       — Async tracker with Thompson Sampling
convergence/tracking/storage.py       — SQLite/PostgreSQL persistence
```

**Schema:**
```sql
CREATE TABLE tracked_items (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,       -- 'pattern:hedging', 'method:rlp', etc.
    alpha REAL DEFAULT 1.0,     -- Beta distribution success prior
    beta REAL DEFAULT 1.0,      -- Beta distribution failure prior
    usage_count INTEGER DEFAULT 0,
    last_used TEXT,
    metadata TEXT,              -- JSON for domain-specific data
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_tracked_domain ON tracked_items(domain);
```

**Interface:**
```python
class TrackedItem:
    id: str
    domain: str
    alpha: float = 1.0
    beta: float = 1.0
    usage_count: int = 0
    last_used: datetime | None = None

    @property
    def quality_score(self) -> float:
        """EvolveR: (success+1)/(usage+2) = alpha/(alpha+beta)"""
        return self.alpha / (self.alpha + self.beta)

    @property
    def freshness(self) -> float:
        """CollabVault: 1/(1 + age/30)"""
        if not self.last_used:
            return 1.0
        age_days = (datetime.now() - self.last_used).days
        return 1.0 / (1 + age_days / 30)

    def sample_priority(self) -> float:
        """Thompson Sampling posterior sample."""
        return np.random.beta(self.alpha, self.beta) * self.freshness

class Tracker(Protocol):
    async def record_usage(self, id: str, domain: str) -> None: ...
    async def record_outcome(self, id: str, success: bool) -> None: ...
    async def sample_top_k(self, domain: str, k: int) -> list[TrackedItem]: ...
    async def get_all(self, domain: str) -> list[TrackedItem]: ...
```

**Tests First:**
```
tests/tracking/test_principle.py       — Quality score, freshness formulas
tests/tracking/test_tracker.py         — Record, sample, persistence
tests/tracking/test_storage.py         — SQLite + PostgreSQL backends
```

**Tier:** 2 (4 files)
**Dependencies:** None
**Packages:** numpy (existing)

---

### Phase 1a: Native Observability (CR-005-v2)

**Goal:** Watch the learning process, not just outputs.

**Files (5):**
```
convergence/observability/__init__.py  — Package exports
convergence/observability/protocol.py  — Observer protocol
convergence/observability/native.py    — Built-in implementation
convergence/observability/metrics.py   — Counter, Gauge, Histogram
convergence/observability/weave.py     — Optional Weave adapter
```

**Metrics:**
```python
# Learning effectiveness
item_usage_count: Counter[domain, id]
item_success_rate: Gauge[domain, id]
item_staleness: Histogram[domain]

# Calibration
calibration_error: Gauge  # |predicted - actual|
cost_quality_ratio: Gauge

# Drift detection
selection_hash: str       # Hash of recent selections
drift_detected: bool
```

**Tests First:**
```
tests/observability/test_native.py
tests/observability/test_metrics.py
```

**Tier:** 2 (5 files)
**Dependencies:** None
**Packages:** None (native Python)

---

### Phase 1b: Constitutional YAML (CR-006-v2)

**Goal:** Patterns in YAML with constitutional structure. Hot-reload without restart.

**Files (5):**
```
convergence/patterns/__init__.py           — Package exports
convergence/patterns/loader.py             — YAML loader with hot-reload
convergence/patterns/constitution.py       — Constitution class
convergence/patterns/schemas/v1.yaml       — Schema definition
convergence/patterns/schemas/confidence.yaml — Default patterns
```

**YAML Schema:**
```yaml
version: 1
domain: confidence

constitution:
  - principle: hedging_detection
    description: "Uncertainty language reduces confidence"
    weight: -0.15

  - principle: negation_cancellation
    description: "Negation of hedging restores confidence"
    priority: high

patterns:
  hedging:
    multi_word:
      - "i'm not sure"
      - "not entirely sure"
    single_word:
      - maybe
      - possibly
    negators:
      - "i am sure"
```

**Tests First:**
```
tests/patterns/test_loader.py
tests/patterns/test_constitution.py
```

**Tier:** 2 (5 files)
**Dependencies:** None
**Packages:** PyYAML (existing)

---

### Phase 2: Meta-MAB for Methods (NEW)

**Goal:** Thompson Sampling to select learning methods (RLP, SAO, MemRL, CAI) per task.

**Files (4):**
```
convergence/meta/__init__.py              — Package exports
convergence/meta/method_selector.py       — Meta-MAB implementation
convergence/meta/methods.py               — Method registry
convergence/meta/integration.py           — Connect to runtime
```

**Interface:**
```python
class MethodSelector:
    """Meta-MAB over learning methods."""

    def __init__(self, tracker: Tracker, methods: list[str]):
        self.tracker = tracker
        self.methods = methods
        self.domain = "method"

    async def select_methods(
        self,
        context: TaskContext,
        k: int = 2
    ) -> list[str]:
        """Select top-k methods for this task type."""
        # Context informs selection (reasoning task → RLP likely)
        # Thompson Sampling handles exploration
        return await self.tracker.sample_top_k(
            domain=f"{self.domain}:{context.task_type}",
            k=k
        )

    async def record_outcome(
        self,
        methods_used: list[str],
        context: TaskContext,
        success: bool
    ):
        """Update method posteriors based on task outcome."""
        for method in methods_used:
            await self.tracker.record_outcome(
                id=f"{method}:{context.task_type}",
                success=success
            )

@dataclass
class TaskContext:
    task_type: str  # 'reasoning', 'alignment', 'memory', 'generation'
    domain: str | None = None
    user_id: str | None = None
```

**Method Compatibility Matrix:**
```python
COMPATIBLE_METHODS = {
    ('rlp', 'memrl'): 'complement',   # Both online
    ('sao', 'cai'): 'complement',     # Both offline data gen
    ('rlp', 'sao'): 'sequential',     # Online + offline
}
```

**Tests First:**
```
tests/meta/test_method_selector.py
tests/meta/test_integration.py
```

**Tier:** 2 (4 files)
**Dependencies:** CR-010 (Unified Tracker)
**Packages:** None (uses existing Thompson Sampling)

---

### Phase 3: Connect Existing Methods (UPGRADE)

**Goal:** Wire RLP and SAO to the new infrastructure.

**Changes (2 files, modifications):**
```
convergence/plugins/learning/rlp.py    — Add tracker integration
convergence/plugins/learning/sao.py    — Add DPO via trl
```

**RLP Changes:**
```python
# Before: Information gain reward uses text similarity (broken)
# After: Connect to meta-MAB, track thought effectiveness

class RLPMixin:
    tracker: Tracker  # NEW: injected dependency

    async def record_thought_outcome(self, thought_id: str, success: bool):
        """Track which thoughts lead to success."""
        await self.tracker.record_outcome(
            id=thought_id,
            domain="rlp:thought",
            success=success
        )
```

**SAO Changes:**
```python
# Before: Generates preference pairs but doesn't train
# After: Use trl.DPOTrainer for actual preference learning

from trl import DPOTrainer, DPOConfig

class SAOMixin:
    async def train_preferences(
        self,
        pairs: list[PreferencePair]
    ) -> TrainingResult:
        """Train model using DPO on preference pairs."""
        # Convert to trl format
        dataset = self._pairs_to_dataset(pairs)

        # Use trl's DPOTrainer
        trainer = DPOTrainer(
            model=self.model,
            ref_model=self.ref_model,
            train_dataset=dataset,
            args=DPOConfig(
                per_device_train_batch_size=4,
                gradient_accumulation_steps=4,
                learning_rate=5e-7,
            )
        )
        return trainer.train()
```

**Tests First:**
```
tests/plugins/test_rlp_tracking.py
tests/plugins/test_sao_dpo.py
```

**Tier:** 2 (2 files, modifications)
**Dependencies:** CR-010, Phase 2
**Packages:** trl, transformers (add to pyproject.toml)

---

### Phase 4: MemRL Plugin (NEW)

**Goal:** Episodic memory RL without model updates.

**Files (3):**
```
convergence/plugins/learning/memrl/__init__.py
convergence/plugins/learning/memrl/memory.py     — Episode storage
convergence/plugins/learning/memrl/retriever.py  — Two-phase retrieval
```

**Interface:**
```python
class MemRLPlugin:
    """Episodic memory RL - store experiences, retrieve at inference."""

    def __init__(
        self,
        embedder: SentenceTransformer,
        storage: chromadb.Collection,
        tracker: Tracker
    ):
        self.embedder = embedder
        self.storage = storage
        self.tracker = tracker

    async def store_episode(
        self,
        state: str,
        action: str,
        reward: float,
        outcome: str
    ):
        """Store experience for later retrieval."""
        embedding = self.embedder.encode(state)
        await self.storage.add(
            embeddings=[embedding],
            documents=[json.dumps({
                "state": state,
                "action": action,
                "reward": reward,
                "outcome": outcome
            })],
            ids=[str(uuid4())]
        )

    async def retrieve_relevant(
        self,
        current_state: str,
        k: int = 5
    ) -> list[Episode]:
        """Two-phase retrieval: semantic + Q-value ranking."""
        # Phase 1: Semantic similarity
        embedding = self.embedder.encode(current_state)
        candidates = await self.storage.query(
            query_embeddings=[embedding],
            n_results=k * 3  # Over-retrieve
        )

        # Phase 2: Rank by Q-value (learned reward estimate)
        ranked = sorted(
            candidates,
            key=lambda e: e.reward * self.q_estimate(e),
            reverse=True
        )
        return ranked[:k]
```

**Tests First:**
```
tests/plugins/test_memrl.py
```

**Tier:** 2 (3 files)
**Dependencies:** CR-010
**Packages:** sentence-transformers, chromadb (add to pyproject.toml)

---

### Phase 5: Unified Classifier (CR-007-v2)

**Goal:** One interface for all classification modes with feedback integration.

**Files (5):**
```
convergence/classifier/__init__.py
convergence/classifier/protocol.py       — ClassifierMode protocol
convergence/classifier/confidence.py     — Migrated from evaluators
convergence/classifier/code_quality.py   — Migrated from evaluators
convergence/classifier/factory.py        — Factory for modes
```

**Interface:**
```python
class ClassifierMode(Protocol):
    mode_id: str
    domain: str

    async def classify(self, text: str) -> ClassifierResult: ...
    async def record_outcome(self, result_id: str, success: bool) -> None: ...

@dataclass
class ClassifierResult:
    score: float
    mode_id: str
    patterns_matched: list[str]
    confidence_in_score: float
    result_id: str

# Usage
classifier = ClassifierFactory.create(
    mode="confidence",
    tracker=tracker,
    observer=observer
)
result = await classifier.classify(text)
await classifier.record_outcome(result.result_id, success=True)
```

**Tier:** 2 (5 files)
**Dependencies:** CR-010, CR-006-v2 (patterns)

---

### Phase 6: Pattern MAB Evolution (CR-008-v2)

**Goal:** Patterns ARE arms in the bandit.

**Files (2):**
```
convergence/patterns/sampler.py          — Thompson Sampling over patterns
convergence/patterns/evolution.py        — Pattern mutation/crossover
```

**Already have infrastructure from CR-010.** This phase just:
1. Registers patterns in unified tracker (domain="pattern:hedging", etc.)
2. Applies Thompson Sampling at classification time
3. Records outcomes to update posteriors

**Tier:** 1 (2 files, leverage existing)
**Dependencies:** CR-010, CR-006-v2

---

### Phase 7: Documentation (CR-009-v2)

**Goal:** README that sells the vision.

**Files (4):**
```
README.md                              — Full rewrite
docs/QUICKSTART.md                     — 3-call integration
docs/PATTERNS.md                       — Pattern system guide
examples/funjoin_integration.py        — Working example
```

**Tier:** 1 (4 files)
**Dependencies:** ALL previous phases

---

## Dependency Graph

```
          CR-010 (Unified Tracker)
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
 CR-005-v2    CR-006-v2     Phase 2
(Observability) (Patterns)  (Meta-MAB)
     │             │             │
     │             ▼             │
     │         CR-008-v2        │
     │      (Pattern MAB)       │
     │             │             │
     └─────────────┼─────────────┘
                   ▼
              CR-007-v2
          (Unified Classifier)
                   │
                   ▼
            Phase 3 & 4
        (RLP/SAO + MemRL)
                   │
                   ▼
              CR-009-v2
           (Documentation)
```

---

## Implementation Order

| Order | Contract | Files | Deps | Parallelizable With |
|-------|----------|-------|------|---------------------|
| 1 | CR-010 | 4 | None | — |
| 2a | CR-005-v2 | 5 | CR-010 | 2b, 2c |
| 2b | CR-006-v2 | 5 | CR-010 | 2a, 2c |
| 2c | Phase 2 (Meta-MAB) | 4 | CR-010 | 2a, 2b |
| 3 | CR-008-v2 | 2 | CR-006-v2 | — |
| 4 | CR-007-v2 | 5 | CR-005-v2, CR-006-v2 | — |
| 5a | Phase 3 (RLP/SAO) | 2 | CR-010, Phase 2 | 5b |
| 5b | Phase 4 (MemRL) | 3 | CR-010 | 5a |
| 6 | CR-009-v2 | 4 | ALL | — |

**Total:** 34 files (~5 new directories)

---

## Package Additions

Add to `pyproject.toml`:

```toml
dependencies = [
    # ... existing ...
    "trl>=0.8.0",                    # DPO training for SAO
    "sentence-transformers>=2.5.0",  # Embeddings for MemRL
    "chromadb>=0.4.0",               # Vector storage for MemRL
]

[project.optional-dependencies]
memrl = [
    "sentence-transformers>=2.5.0",
    "chromadb>=0.4.0",
]
training = [
    "trl>=0.8.0",
]
```

---

## Test-First Checklist

Before implementing each phase:

- [ ] Write test file(s) defining expected behavior
- [ ] Run tests (should fail)
- [ ] Implement minimum code to pass
- [ ] Refactor if needed
- [ ] Update AgentDB with checkpoint

---

## Success Criteria

### Phase 0 (CR-010)
- [ ] `TrackedItem.quality_score` matches EvolveR formula
- [ ] `TrackedItem.freshness` matches CollabVault decay
- [ ] Thompson Sampling samples from correct Beta posteriors
- [ ] Persistence works for both SQLite and PostgreSQL

### Phase 2 (Meta-MAB)
- [ ] Method selection uses Thompson Sampling
- [ ] Context (task_type) influences arm selection
- [ ] Outcomes update method posteriors
- [ ] Compatible methods can be selected together

### Phase 4 (MemRL)
- [ ] Episodes persist to chromadb
- [ ] Two-phase retrieval works (semantic + Q-value)
- [ ] Retrieval improves with more episodes

### Final
- [ ] FunJoin integration example runs end-to-end
- [ ] All tests pass (target: 200+)
- [ ] Type checking clean
- [ ] Documentation covers all new features

---

## Warnings (From AgentDB Failures)

1. **Don't write DPO from scratch** — trl already has it
2. **Don't use all methods simultaneously** — Meta-MAB selects
3. **Don't deploy arbitrary thresholds** — Need 500+ interactions to calibrate
4. **Don't trust self-generated data blindly** — Model collapse is real
5. **Don't skip tests** — Methods interact in subtle ways
6. **79% of multi-agent failures are from specification/coordination** — Be explicit

---

## Contract Updates

Close old contracts, open unified:

```bash
# Close superseded contracts
agentdb contract '{"id":"CR-005","status":"superseded","note":"Evolved to CR-005-v2"}'
agentdb contract '{"id":"CR-006","status":"superseded","note":"Evolved to CR-006-v2"}'
agentdb contract '{"id":"CR-007","status":"superseded","note":"Evolved to CR-007-v2"}'
agentdb contract '{"id":"CR-008","status":"superseded","note":"Evolved to CR-008-v2"}'
agentdb contract '{"id":"CR-009","status":"superseded","note":"Evolved to CR-009-v2"}'

# Open new contracts
agentdb contract '{"id":"CR-010","goal":"Unified Tracker (EvolveR + Thompson)","files":["convergence/tracking/"],"tier":2,"status":"ready"}'
agentdb contract '{"id":"CR-005-v2","goal":"Native Observability","files":["convergence/observability/"],"tier":2,"status":"ready","depends":["CR-010"]}'
agentdb contract '{"id":"CR-006-v2","goal":"Constitutional YAML Patterns","files":["convergence/patterns/"],"tier":2,"status":"ready","depends":["CR-010"]}'
agentdb contract '{"id":"META-001","goal":"Meta-MAB Method Selection","files":["convergence/meta/"],"tier":2,"status":"ready","depends":["CR-010"]}'
```

---

*Plan created: 2026-03-12*
*Consolidates: pattern-system-v2.md + learning-system handoff*
*Status: Ready for implementation*
