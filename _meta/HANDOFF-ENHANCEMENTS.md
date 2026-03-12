# HANDOFF: Convergence Enhancements for FunJoin

**From:** FunJoin project agent
**To:** Convergence development agent
**Date:** 2026-03-11
**Priority:** HIGH - Blocking FunJoin v1 sales agent

---

## CONTEXT

FunJoin is building a sales agent and needs features in `the-convergence` to reduce implementation work. These are generic, reusable features that benefit any project using convergence.

**FunJoin plan:** `/Users/ariaxhan/Downloads/Vaults/CodingVault/funjoin/_meta/plans/convergence-enhancements.md`

---

## TASK: Add 5 Features (~1000 LOC total)

### Feature 1: Semantic Cache Layer (Priority 1)

**Location:** `convergence/cache/` (new directory)

**Files to create:**
- `convergence/cache/__init__.py`
- `convergence/cache/semantic.py`
- `convergence/cache/backends.py` (Redis, memory, SQLite)

**What it does:**
- Caches LLM responses by semantic similarity (not exact match)
- Uses embeddings + cosine similarity
- Configurable threshold (default 0.88)
- Pluggable backends (Redis, memory, SQLite)

**Interface:**
```python
from convergence.cache import SemanticCache

cache = SemanticCache(
    embedding_fn=my_embed_fn,
    threshold=0.88,
    backend="redis",
    redis_url="redis://localhost"
)

# Check cache
cached = await cache.get("How do I reset my password?")
if cached:
    return cached["response"]  # Similar question was asked before

# Miss - generate and cache
response = await llm.chat(query)
await cache.set(query, response)
```

**Why:** 70-80% cache hit rate for similar questions. 80% cost reduction.

---

### Feature 2: PostgreSQL Runtime Storage (Priority 2)

**Location:** `convergence/storage/postgresql.py`

**What it does:**
- Implements `RuntimeStorageProtocol` for PostgreSQL
- Uses `asyncpg` for async operations
- Auto-creates schema on connect
- Stores arms, decisions, rewards

**Interface:**
```python
from convergence.storage import PostgreSQLRuntimeStorage

storage = PostgreSQLRuntimeStorage(
    dsn="postgresql://user:pass@localhost/db"
)
await storage.connect()

# Then use with runtime_configure
await configure_runtime("sales", config={
    "storage": {"backend": "postgresql", "dsn": "..."}
})
```

**Schema:**
```sql
CREATE TABLE convergence_arms (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    arm_id TEXT NOT NULL,
    params JSONB,
    alpha FLOAT DEFAULT 1.0,
    beta FLOAT DEFAULT 1.0,
    total_pulls INT DEFAULT 0,
    UNIQUE(user_id, agent_type, arm_id)
);

CREATE TABLE convergence_decisions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    arm_id TEXT NOT NULL,
    params JSONB,
    reward FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Why:** FunJoin uses PostgreSQL. Zero new dependencies.

---

### Feature 3: LLM Response Wrapper (Priority 3)

**Location:** `convergence/types/response.py`

**What it does:**
- Standard response type for all LLM outputs
- Includes: content, confidence, decision_id, cache status, metadata

**Interface:**
```python
from convergence.types import LLMResponse

response = LLMResponse(
    content="Here's how to reset your password...",
    confidence=0.85,
    decision_id="dec_abc123",
    cache_hit=False,
    model="claude-haiku-4-5",
    tokens_used=150
)

# Gap detection helper
from convergence.types import detect_gap
response = detect_gap(response, threshold=0.6)
if response.gap_detected:
    await log_gap(response)
```

**Why:** Every LLM app needs this. Standardize it.

---

### Feature 4: Confidence Extraction (Priority 4)

**Location:** `convergence/evaluators/confidence.py`

**What it does:**
- Extracts confidence from LLM response text
- Methods: explicit ("confidence: 85%"), hedging detection, certainty markers
- Returns 0.0-1.0 score

**Interface:**
```python
from convergence.evaluators import extract_confidence

confidence = extract_confidence(response_text, method="auto")
# Returns 0.0-1.0

# Methods:
# - "explicit": Look for "confidence: X%"
# - "hedging": Detect "I think", "maybe", "possibly" (lower score)
# - "certainty": Detect "definitely", "always" (higher score)
# - "auto": Try all, take most conservative
```

**Why:** Auto gap detection without explicit confidence markers.

---

### Feature 5: Claude Client Integration (Priority 5)

**Location:** `convergence/clients/` (new directory)

**Files to create:**
- `convergence/clients/__init__.py`
- `convergence/clients/claude.py`

**What it does:**
- Pre-built Claude API client
- Integrates with runtime_select for param selection
- Auto-extracts confidence
- Supports tool_use

**Interface:**
```python
from convergence.clients import ClaudeClient

client = ClaudeClient(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    system="sales_chat"
)

# Chat with auto param selection + confidence
response = await client.chat(
    message="How much does FunJoin cost?",
    user_id="user_123",
    tools=[search_kb_tool, search_code_tool]
)

print(response.content)       # "FunJoin pricing starts at..."
print(response.confidence)    # 0.85
print(response.decision_id)   # "dec_abc123"
print(response.gap_detected)  # False

# Record outcome
await client.record_outcome(response.decision_id, converted=True)
```

**Why:** Turnkey Claude integration with convergence.

---

## IMPLEMENTATION ORDER

```
1. cache/semantic.py        (~300 LOC)  - Highest value
2. storage/postgresql.py    (~200 LOC)  - FunJoin needs this
3. types/response.py        (~100 LOC)  - Foundation for 4 & 5
4. evaluators/confidence.py (~150 LOC)  - Used by 5
5. clients/claude.py        (~250 LOC)  - Depends on 3 & 4
```

---

## EXISTING CODE TO REFERENCE

| Feature | Reference |
|---------|-----------|
| Storage protocol | `storage/runtime_protocol.py` |
| SQLite implementation | `storage/sqlite.py` |
| Multi-backend pattern | `storage/multi_backend.py` |
| Evaluators pattern | `evaluators/text_quality.py` |
| Types pattern | `types/runtime.py` |

---

## DEPENDENCIES TO ADD

```toml
# pyproject.toml additions
[project.optional-dependencies]
postgresql = ["asyncpg>=0.29.0"]
redis = ["redis>=5.0.0"]
claude = ["anthropic>=0.25.0"]
all = ["the-convergence[postgresql,redis,claude,agents]"]
```

---

## TESTS NEEDED

```
tests/
├── cache/
│   ├── test_semantic_cache.py
│   └── test_cache_backends.py
├── storage/
│   └── test_postgresql_storage.py
├── evaluators/
│   └── test_confidence.py
└── clients/
    └── test_claude_client.py
```

---

## SUCCESS CRITERIA

- [ ] `pip install the-convergence[postgresql]` works
- [ ] Semantic cache reduces API calls by 70%+ in tests
- [ ] PostgreSQL storage passes all RuntimeStorageProtocol tests
- [ ] Confidence extraction works on sample responses
- [ ] Claude client integrates with runtime_select

---

## BRANCH STRATEGY

```bash
git checkout -b feature/funjoin-enhancements
# Implement features
# Test with FunJoin as consumer
git push origin feature/funjoin-enhancements
# Create PR
# After merge, bump version to 0.2.0
```

---

## QUESTIONS FOR FUNJOIN

None - all requirements are clear. Proceed with implementation.

---

*Handoff complete. Agent in convergence folder should read this first.*
