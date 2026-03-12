# The Convergence: Research-Informed Architecture v3

**Date:** 2026-03-12
**Status:** Ready for review
**Based On:** 3 research documents (65+ sources), AgentDB learnings, FunJoin requirements

---

## Vision

**The Convergence** is an enterprise self-evolving agent framework that makes AI agents:
- **Safe** by default (guardrails, not prompts)
- **Observable** (watch learning, not just outputs)
- **Self-improving** (Thompson Sampling → experimental RL)
- **Easy to deploy** (3 function calls to production)

**Target Market:** Companies with scattered knowledge (code, Slack, integrations) who need intelligent agents beyond basic RAG.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THE CONVERGENCE                                    │
│                     "Safe, Observable, Self-Improving"                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LAYER 1: SAFETY & GUARDRAILS (The Real Core)                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  NeMo Guardrails (input/output/execution rails)                     │    │
│  │  + Guardrails AI (schema validation)                                │    │
│  │  + Budget enforcement (cost caps, rate limiting)                    │    │
│  │  + Audit logging (every decision traceable)                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  LAYER 2: OBSERVABILITY                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Learning metrics (regret, arm distribution, reward variance)       │    │
│  │  Calibration tracking (is 80% confidence = 80% success?)            │    │
│  │  Cost tracking (per-request, per-user, per-system)                  │    │
│  │  Drift detection (are patterns changing?)                           │    │
│  │  Native backend | Weave adapter | Custom adapters                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  LAYER 3: OPTIMIZATION LOOP (Production-Ready)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Thompson Sampling MAB (15-30 interactions to converge)             │    │
│  │  Semantic Caching (70-80% cost reduction)                           │    │
│  │  Confidence Extraction (gap detection → human escalation)           │    │
│  │  Arm Evolution (genetic operators for configuration space)          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  LAYER 4: EXPERIMENTAL METHODS (Labeled, Opt-In, Data-Gated)                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  RLP (>500 interactions, entropy monitoring, kill switch)           │    │
│  │  SAO (>1000 interactions, external validation, fine-tuning only)    │    │
│  │  MemRL (episodic memory, sentence-transformers + chromadb)          │    │
│  │  Constitutional AI (YAML principles, critique templates)            │    │
│  │  [Future: Meta-MAB when data supports, pattern evolution]           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│  LAYER 5: STORAGE & PERSISTENCE                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  SQLite (dev) | PostgreSQL (prod) | Memory (test)                   │    │
│  │  Redis (semantic cache) | Qdrant/Chroma (vectors, optional)         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 0: Foundation Hardening (BEFORE New Features)

**Goal:** Ensure existing code is production-ready.

**What exists:**
- ✓ Thompson Sampling MAB
- ✓ Storage backends (SQLite, PostgreSQL, Memory)
- ✓ Confidence extraction
- ✓ RLP/SAO plugins (exist, need hardening)

**What needs hardening:**
1. **Thompson Sampling metrics** — Add regret tracking, arm distribution, kill switches
2. **RLP monitoring** — Add entropy monitoring, KL constraints, automated fallback
3. **SAO validation** — Add distribution shift detection, external validation hooks
4. **Test coverage** — Ensure 80%+ coverage on critical paths

**Effort:** ~24 hours total
**Files:** 5-8 modifications to existing code
**Dependencies:** None

---

### Phase 1: Safety & Guardrails (REAL CORE)

**Goal:** Make agents safe by default, not by prompting.

**Components:**

#### 1a. NeMo Guardrails Integration
```python
# convergence/safety/nemo_rails.py
from nemo_guardrails import LLMRails

class ConvergenceRails:
    """Wrap NeMo Guardrails for Convergence agents."""

    def __init__(self, config_path: str = "guardrails_config"):
        self.rails = LLMRails.load(config_path)

    async def validate_input(self, message: str) -> ValidationResult:
        """Input rails: jailbreak, injection detection."""
        ...

    async def validate_output(self, response: str) -> ValidationResult:
        """Output rails: hallucination, sensitive data detection."""
        ...

    async def validate_tool_call(self, tool: str, args: dict) -> ValidationResult:
        """Execution rails: tool authorization before execution."""
        ...
```

#### 1b. Guardrails AI Integration
```python
# convergence/safety/schema_guards.py
from guardrails import Guard
from pydantic import BaseModel

class AgentResponse(BaseModel):
    content: str
    confidence: float
    sources: list[str]
    gap_detected: bool

guard = Guard.from_pydantic(AgentResponse)
```

#### 1c. Budget Enforcement
```python
# convergence/safety/budget.py
class BudgetEnforcer:
    """Prevent runaway costs."""

    def __init__(self, daily_limit: float = 100.0):
        self.daily_limit = daily_limit
        self.spent_today: float = 0.0

    async def check_budget(self, estimated_cost: float) -> bool:
        """Return False if over budget."""
        if self.spent_today + estimated_cost > self.daily_limit:
            return False
        return True

    async def record_cost(self, actual_cost: float):
        self.spent_today += actual_cost
```

**Files (8):**
```
convergence/safety/__init__.py
convergence/safety/nemo_rails.py      — NeMo integration
convergence/safety/schema_guards.py   — Guardrails AI integration
convergence/safety/budget.py          — Cost enforcement
convergence/safety/audit.py           — Audit logging
convergence/safety/config/            — Guardrails configuration
tests/safety/test_rails.py
tests/safety/test_budget.py
```

**Packages to add:**
```toml
[project.optional-dependencies]
safety = [
    "nemoguardrails>=0.10.0",
    "guardrails-ai>=0.5.0",
]
```

**Effort:** 2-3 days
**Dependencies:** None

---

### Phase 2: Observability (REAL CORE)

**Goal:** Watch the learning process, not just outputs.

**Metrics to track:**

| Category | Metric | Why |
|----------|--------|-----|
| Learning | Regret trend | Is MAB converging? |
| Learning | Arm distribution | Which arms are winning? |
| Learning | Reward variance | Is signal stable? |
| Calibration | Confidence accuracy | 80% confidence = 80% success? |
| Cost | Per-request cost | Budget tracking |
| Cost | Cache hit rate | Is caching working? |
| Drift | Pattern hash | Are selections changing? |
| Safety | Guardrail triggers | What's being blocked? |

**Implementation:**
```python
# convergence/observability/protocol.py
from typing import Protocol

class Observer(Protocol):
    """Watch the learning process."""

    async def record_selection(self, arm_id: str, context: dict) -> None: ...
    async def record_outcome(self, arm_id: str, reward: float, success: bool) -> None: ...
    async def record_calibration(self, predicted: float, actual: bool) -> None: ...
    async def record_cost(self, tokens: int, cost: float) -> None: ...
    async def record_guardrail_trigger(self, rail: str, action: str) -> None: ...

    async def get_regret(self, window: int = 100) -> float: ...
    async def get_calibration_error(self) -> float: ...
    async def get_arm_distribution(self) -> dict[str, float]: ...
```

**Files (6):**
```
convergence/observability/__init__.py
convergence/observability/protocol.py    — Observer interface
convergence/observability/native.py      — Built-in implementation
convergence/observability/metrics.py     — Counter, Gauge, Histogram
convergence/observability/weave.py       — Optional Weave adapter
tests/observability/test_native.py
```

**Effort:** 1-2 days
**Dependencies:** None

---

### Phase 3: Semantic Cache (FunJoin Killer Feature)

**Goal:** 70-80% cost reduction via semantic caching.

**Implementation:**
```python
# convergence/cache/semantic.py
from sentence_transformers import SentenceTransformer

class SemanticCache:
    """Cache LLM responses by semantic similarity."""

    def __init__(
        self,
        embed_model: str = "sentence-transformers/all-mpnet-base-v2",
        similarity_threshold: float = 0.88,
        ttl_seconds: int = 86400,
        backend: Literal["memory", "redis"] = "memory",
    ):
        self.embedder = SentenceTransformer(embed_model)
        self.threshold = similarity_threshold
        self.ttl = ttl_seconds
        self.backend = self._init_backend(backend)

    async def get(self, query: str) -> CacheResult | None:
        """Return cached response if similarity > threshold."""
        embedding = self.embedder.encode(query)
        # Find nearest neighbor in cache
        # Return if similarity > threshold, else None
        ...

    async def set(self, query: str, response: str, metadata: dict = None):
        """Store response with embedding for future retrieval."""
        ...
```

**Critical:** Validate threshold empirically. 0.7 → 99% false positives. Start at 0.92.

**Files (5):**
```
convergence/cache/__init__.py
convergence/cache/semantic.py        — Core cache logic (EXISTING, enhance)
convergence/cache/backends.py        — Memory/Redis backends (EXISTING, enhance)
convergence/cache/embeddings.py      — Embedding model wrapper
tests/cache/test_semantic_cache.py
```

**Packages:**
```toml
[project.optional-dependencies]
cache = [
    "sentence-transformers>=2.5.0",
    "redis>=5.0.0",
]
```

**Effort:** 1-2 days
**Dependencies:** None

---

### Phase 4: Documentation & Examples

**Goal:** Make it sellable. Someone understands + deploys in 10 minutes.

**Structure:**
```
README.md                           — Vision + 3-call quick start
docs/
  QUICKSTART.md                     — Get running in 5 minutes
  SAFETY.md                         — Guardrails, budget, audit
  OBSERVABILITY.md                  — Metrics, dashboards, alerts
  SELF-LEARNING.md                  — Thompson Sampling, when to add RLP
  INTEGRATION.md                    — FunJoin-style integration guide
examples/
  basic_agent.py                    — Minimal example
  sales_agent.py                    — FunJoin-style
  safe_agent.py                     — With all guardrails
  observable_agent.py               — With full metrics
```

**Effort:** 1-2 days
**Dependencies:** Phases 1-3 complete

---

### Phase 5: Experimental Methods (Labeled, Opt-In)

**Goal:** Pack in power, but gate by data and label as experimental.

**Implementation pattern:**
```python
# convergence/experimental/__init__.py
"""
⚠️ EXPERIMENTAL METHODS
These methods require sufficient data to work safely.
Enable only after reviewing minimum data requirements.

| Method | Min Data | Risk Level |
|--------|----------|------------|
| RLP    | 500+     | Medium     |
| SAO    | 1000+    | Medium-High|
| MemRL  | 100+     | Low        |
"""

from convergence.experimental.rlp import RLPMixin
from convergence.experimental.sao import SAOMixin
from convergence.experimental.memrl import MemRLMixin
```

**Data gates:**
```python
class ExperimentalMethod:
    """Base class with data-gating."""

    MIN_INTERACTIONS: int = 500

    async def should_enable(self, interactions: int) -> bool:
        if interactions < self.MIN_INTERACTIONS:
            logger.warning(
                f"{self.__class__.__name__} requires {self.MIN_INTERACTIONS}+ "
                f"interactions. Current: {interactions}. Using heuristic fallback."
            )
            return False
        return True
```

**Files:**
```
convergence/experimental/__init__.py
convergence/experimental/rlp.py          — Move from plugins, add monitoring
convergence/experimental/sao.py          — Move from plugins, add validation
convergence/experimental/memrl.py        — New: episodic memory
convergence/experimental/gates.py        — Data-gating logic
tests/experimental/test_rlp.py
tests/experimental/test_sao.py
tests/experimental/test_memrl.py
```

**Packages:**
```toml
[project.optional-dependencies]
experimental = [
    "trl>=0.8.0",                    # DPO for SAO
    "sentence-transformers>=2.5.0",  # Embeddings for MemRL
    "chromadb>=0.4.0",               # Vector storage for MemRL
]
```

**Effort:** 3-5 days
**Dependencies:** Phase 0 (hardening)

---

## Summary: What Gets Built

### Immediate (This Sprint)

| Component | LOC | Impact | Buy vs Build |
|-----------|-----|--------|--------------|
| Safety integration (NeMo + Guardrails AI) | ~200 | Enterprise-ready | Integrate |
| Budget enforcement | ~100 | Prevent runaway costs | Build |
| Observability (native) | ~300 | See learning process | Build |
| Semantic cache (enhance) | ~200 | 80% cost reduction | Enhance existing |
| Documentation | ~1000 | Sellable | Build |

**Total: ~1800 LOC new/enhanced**

### Next Sprint

| Component | LOC | Impact |
|-----------|-----|--------|
| Experimental methods hardening | ~500 | Unlock RLP/SAO |
| MemRL plugin | ~300 | Episodic memory |
| Agentic RAG primitives | ~400 | Multi-hop reasoning |

### Future

| Component | When |
|-----------|------|
| Meta-MAB method selection | After 2000+ interactions across methods |
| Pattern evolution | After pattern tracking proves value |
| Multi-agent validation | For high-stakes decisions |

---

## What We're NOT Building (Avoid Overengineering)

1. **Meta-MAB** — No production proof, unknown stability. Skip for now.
2. **Graph RAG** — Nice-to-have for <5% of queries. Not MVP.
3. **Full Constitutional AI** — YAML principles are enough. Don't need full RLAIF loop.
4. **Pattern evolution** — Patterns that WORK are enough. Evolution can wait.
5. **Multi-agent orchestration** — Single agent is right for FunJoin. Add when needed.

---

## Success Criteria

### Phase 1 (Safety)
- [ ] NeMo Guardrails blocks prompt injection attempts
- [ ] Execution rails require approval for mutations
- [ ] Budget enforcement prevents overspend
- [ ] Audit log captures every decision

### Phase 2 (Observability)
- [ ] Dashboard shows regret trend, arm distribution
- [ ] Calibration error tracked and alertable
- [ ] Cost per request visible

### Phase 3 (Cache)
- [ ] 70%+ hit rate on repeated queries
- [ ] P95 latency < 100ms for cache hits
- [ ] Threshold validated on 100+ test queries

### Phase 4 (Documentation)
- [ ] New user deploys in 10 minutes
- [ ] FunJoin integration example works end-to-end

### Final
- [ ] FunJoin in production with 80% cost reduction
- [ ] Zero security incidents from guardrail bypasses
- [ ] Sellable to next customer

---

## Key Decisions

1. **Safety is an invariant, not a feature** — Guardrails at framework level, not prompt level.

2. **Integrate, don't invent** — NeMo Guardrails, Guardrails AI, GPTCache are battle-tested. Don't reinvent.

3. **Data-gate experimental methods** — RLP at 500+, SAO at 1000+, Meta-MAB never (for now).

4. **Start with Thompson Sampling** — It converges in 15-30 interactions. Everything else needs more data.

5. **Semantic cache is the killer feature** — 80% cost reduction is the selling point. Get it right.

6. **Single agent for now** — Multi-agent adds complexity. FunJoin doesn't need it.

---

## Sources

All research documented in `_meta/research/`:
- `enterprise-agent-foundations.md` (662 lines, 25+ sources)
- `self-learning-production-readiness.md` (526 lines, 15+ sources)
- `knowledge-retrieval-2026.md` (585 lines, 20+ sources)

---

*Architecture v3: Research-informed, production-focused*
*Created: 2026-03-12*
