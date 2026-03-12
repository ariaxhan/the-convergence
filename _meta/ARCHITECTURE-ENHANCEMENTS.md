# Convergence Enhancement Architecture

**Version:** 0.2.0 (planned)
**Date:** 2026-03-11

---

## Module Structure After Enhancements

```
convergence/
├── __init__.py                 # Add new exports
├── sdk.py                      # Existing
├── cli/                        # Existing
├── core/                       # Existing
├── evaluators/
│   ├── __init__.py
│   ├── base.py
│   ├── text_quality.py
│   ├── code_quality.py
│   ├── json_structure.py
│   └── confidence.py           # NEW: Confidence extraction
├── cache/                      # NEW DIRECTORY
│   ├── __init__.py
│   ├── semantic.py             # Semantic similarity cache
│   └── backends.py             # Redis, memory, SQLite backends
├── clients/                    # NEW DIRECTORY
│   ├── __init__.py
│   └── claude.py               # Claude API integration
├── storage/
│   ├── __init__.py             # Add PostgreSQL export
│   ├── base.py
│   ├── sqlite.py
│   ├── file.py
│   ├── memory.py
│   ├── convex.py
│   ├── postgresql.py           # NEW: PostgreSQL backend
│   └── runtime_protocol.py
├── runtime/
│   ├── __init__.py
│   ├── online.py               # MODIFY: Add cache integration
│   ├── bayesian_update.py
│   └── evolution.py
├── types/
│   ├── __init__.py             # Add LLMResponse export
│   ├── config.py
│   ├── runtime.py
│   ├── results.py
│   └── response.py             # NEW: LLMResponse type
└── plugins/                    # Existing
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER REQUEST                                       │
│                    "How do I reset my password?"                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SEMANTIC CACHE LAYER                                  │
│                        cache/semantic.py                                    │
│                                                                             │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│  │  Embed Query     │───▶│  Search Similar  │───▶│  Return Cached   │     │
│  │  (embedding_fn)  │    │  (threshold 0.88)│    │  or MISS         │     │
│  └──────────────────┘    └──────────────────┘    └──────────────────┘     │
│                                                                             │
│  Backends: Redis (production) │ Memory (dev) │ SQLite (standalone)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                          CACHE HIT │ CACHE MISS
                      ┌─────────────┴─────────────┐
                      │                           │
                      ▼                           ▼
            ┌─────────────────┐         ┌─────────────────────────────────────┐
            │ Return Cached   │         │        RUNTIME SELECTION            │
            │ Response        │         │        runtime/online.py            │
            │                 │         │                                     │
            │ LLMResponse(    │         │  ┌────────────────────────────────┐│
            │   cache_hit=True│         │  │ runtime_select()               ││
            │   similarity=.92│         │  │ - Load arms from storage       ││
            │ )               │         │  │ - Thompson Sample each arm     ││
            └─────────────────┘         │  │ - Select highest sample        ││
                                        │  │ - Persist decision             ││
                                        │  └────────────────────────────────┘│
                                        │                                     │
                                        │  Storage: PostgreSQL │ SQLite       │
                                        └─────────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │         CLAUDE CLIENT               │
                                        │         clients/claude.py           │
                                        │                                     │
                                        │  ┌────────────────────────────────┐│
                                        │  │ chat()                         ││
                                        │  │ - Apply selected params        ││
                                        │  │ - Call Claude API              ││
                                        │  │ - Extract confidence           ││
                                        │  │ - Detect gaps                  ││
                                        │  └────────────────────────────────┘│
                                        └─────────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │         CONFIDENCE EXTRACTION       │
                                        │         evaluators/confidence.py    │
                                        │                                     │
                                        │  Methods:                           │
                                        │  - explicit: "confidence: 85%"      │
                                        │  - hedging: "I think", "maybe"      │
                                        │  - certainty: "definitely"          │
                                        │  - auto: all methods, min score     │
                                        └─────────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │         LLM RESPONSE                │
                                        │         types/response.py           │
                                        │                                     │
                                        │  LLMResponse(                       │
                                        │    content="...",                   │
                                        │    confidence=0.85,                 │
                                        │    decision_id="dec_abc123",        │
                                        │    gap_detected=False,              │
                                        │    cache_hit=False,                 │
                                        │    params={temperature: 0.7, ...}   │
                                        │  )                                  │
                                        └─────────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │         CACHE UPDATE                │
                                        │                                     │
                                        │  await cache.set(query, response)   │
                                        │  # Future similar queries hit cache │
                                        └─────────────────────────────────────┘
                                                        │
                                                        ▼
                                        ┌─────────────────────────────────────┐
                                        │         OUTCOME (later)             │
                                        │                                     │
                                        │  await runtime_update(              │
                                        │    decision_id="dec_abc123",        │
                                        │    reward=1.0  # converted          │
                                        │  )                                  │
                                        │                                     │
                                        │  # Updates arm's alpha/beta         │
                                        │  # Improves future selections       │
                                        └─────────────────────────────────────┘
```

---

## Semantic Cache Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     SEMANTIC CACHE                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐                                             │
│  │  EmbeddingFn   │  User provides: OpenAI, Cohere, local, etc  │
│  │  (pluggable)   │                                             │
│  └───────┬────────┘                                             │
│          │                                                       │
│          ▼                                                       │
│  ┌────────────────┐     ┌────────────────┐                      │
│  │  Query         │────▶│  Embedding     │  vector(1536)        │
│  │  "How to..."   │     │  [0.12, ...]   │                      │
│  └────────────────┘     └───────┬────────┘                      │
│                                 │                                │
│                                 ▼                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    BACKEND STORAGE                        │   │
│  │                                                           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐         │   │
│  │  │   Redis    │  │   Memory   │  │   SQLite   │         │   │
│  │  │  (prod)    │  │   (dev)    │  │ (standalone)│         │   │
│  │  │            │  │            │  │            │         │   │
│  │  │ HSET cache │  │ Dict cache │  │ Table cache│         │   │
│  │  │ :query_id  │  │            │  │            │         │   │
│  │  │ embedding  │  │            │  │            │         │   │
│  │  │ response   │  │            │  │            │         │   │
│  │  │ created_at │  │            │  │            │         │   │
│  │  └────────────┘  └────────────┘  └────────────┘         │   │
│  │                                                           │   │
│  │  Vector search: cosine_similarity(query_emb, stored_embs) │   │
│  │  Threshold: 0.88 default (configurable)                   │   │
│  │  TTL: 24 hours default                                    │   │
│  │                                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## PostgreSQL Storage Schema

```sql
-- Arms table (Thompson Sampling state)
CREATE TABLE convergence_arms (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    arm_id TEXT NOT NULL,
    name TEXT,
    params JSONB NOT NULL DEFAULT '{}',

    -- Beta distribution parameters
    alpha FLOAT NOT NULL DEFAULT 1.0,
    beta FLOAT NOT NULL DEFAULT 1.0,

    -- Statistics
    total_pulls INT NOT NULL DEFAULT 0,
    total_reward FLOAT NOT NULL DEFAULT 0.0,
    mean_estimate FLOAT,
    confidence_interval FLOAT,

    -- Metadata
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(user_id, agent_type, arm_id)
);

-- Decisions table (audit trail)
CREATE TABLE convergence_decisions (
    id TEXT PRIMARY KEY,  -- UUID
    user_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    arm_id TEXT NOT NULL,
    params JSONB NOT NULL,
    sampled_value FLOAT NOT NULL,

    -- Outcome (filled in later)
    reward FLOAT,
    rewarded_at TIMESTAMPTZ,

    -- Context
    context JSONB,
    metadata JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_arms_lookup ON convergence_arms(user_id, agent_type);
CREATE INDEX idx_decisions_user ON convergence_decisions(user_id, created_at DESC);
CREATE INDEX idx_decisions_pending ON convergence_decisions(reward) WHERE reward IS NULL;
```

---

## Confidence Extraction Logic

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONFIDENCE EXTRACTION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Input: "I think the price starts at $99, but I'm not certain." │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Method: EXPLICIT                                           │ │
│  │ Pattern: /confidence[:\s]+(\d+)%/                          │ │
│  │ Result: None (no explicit marker)                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Method: HEDGING                                            │ │
│  │ Markers: "I think", "not certain"                          │ │
│  │ Count: 2                                                   │ │
│  │ Result: 0.5 (2 hedging phrases = medium-low confidence)    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Method: CERTAINTY                                          │ │
│  │ Markers: None found                                        │ │
│  │ Result: 0.7 (neutral - no certainty markers)               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Method: AUTO (default)                                     │ │
│  │ Logic: min(explicit, hedging, certainty)                   │ │
│  │ Result: min(None, 0.5, 0.7) = 0.5                          │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Output: 0.5 confidence → gap_detected=True if threshold=0.6    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Integration Points

### 1. Cache + Runtime Integration

```python
# runtime/online.py modification
class RuntimeManager:
    def __init__(self, *, config: RuntimeConfig, storage: RuntimeStorageProtocol,
                 semantic_cache: Optional[SemanticCache] = None):
        self.semantic_cache = semantic_cache
        # ...

    async def select(self, *, user_id: str, query: str = None, **kwargs):
        # Check semantic cache FIRST
        if self.semantic_cache and query:
            cached = await self.semantic_cache.get(query)
            if cached:
                return RuntimeSelection(
                    decision_id=f"cache_{hash}",
                    arm_id="cached",
                    params={},
                    metadata={"cache_hit": True, "similarity": cached["similarity"]}
                )

        # Normal Thompson Sampling...
```

### 2. Client + Response Integration

```python
# clients/claude.py
from convergence.types import LLMResponse
from convergence.evaluators import extract_confidence
from convergence import runtime_select, runtime_update

class ClaudeClient:
    async def chat(self, message: str, user_id: str, **kwargs) -> LLMResponse:
        selection = await runtime_select(self.system, user_id=user_id)

        response = await self._call_claude(message, selection.params)

        return LLMResponse(
            content=response.text,
            confidence=extract_confidence(response.text),
            decision_id=selection.decision_id,
            params=selection.params
        )
```

---

## Version Plan

```
v0.1.8 (current)
├── Runtime selection
├── Thompson Sampling
├── SQLite/Convex/File/Memory storage
└── Evaluators (text, code, json)

v0.2.0 (this enhancement)
├── + Semantic cache layer
├── + PostgreSQL storage
├── + LLMResponse type
├── + Confidence extraction
└── + Claude client integration
```

---

*Architecture document for convergence enhancements.*
