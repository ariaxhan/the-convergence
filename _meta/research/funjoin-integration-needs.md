# FunJoin Integration Needs: Deep Dive Synthesis

**Date:** 2026-03-11
**Sources:** convergence-integration.md, convergence-enhancements.md, unified-agent-architecture.md, support-agent-strategy.md, knowledge-architecture.md

---

## Summary

FunJoin is building a **unified agent** that handles sales, support, and internal queries through a single codebase with context-aware prompts. They need Convergence to provide plug-and-play optimization with minimal integration code. The core pain points are: (1) cost reduction via semantic caching, (2) confidence/gap detection for human escalation, and (3) PostgreSQL storage to match their stack. FunJoin's "plug-and-play" means: configure once, select per-request, update on outcome - three function calls total.

---

## Mental Model

Think of FunJoin's relationship with Convergence as **framework vs. application**:

```
CONVERGENCE (Framework)           FUNJOIN (Application)
==============================    ==============================
- Thompson Sampling               - Unified agent endpoint
- Arm selection/update            - MCP tool orchestration
- Storage backends                - Business logic (sales/support)
- Semantic caching                - Entry point integrations
- Confidence extraction           - Gap review workflows
- Response wrappers               - Admin UI (MobX/ViewModel)
```

FunJoin wants to import Convergence primitives and compose them, not extend or modify core behavior. They need **batteries included** but also **a la carte** - use what you need, ignore what you don't.

---

## Key Concepts

### 1. Unified Agent Architecture

FunJoin discovered that sales, support, and internal agents are the **same agent** with different entry points:

| Entry Point | Context Source | Same Tools |
|-------------|----------------|------------|
| Website widget | Sales context | GitLab, Guru, Intercom |
| Intercom webhook | Support context | GitLab, Guru, Intercom |
| Slack bot | Internal context | GitLab, Guru, Slack |
| API | Programmatic | All tools |

**Implication for Convergence:** Multi-system configuration. FunJoin needs one runtime instance with context-switching, not separate optimizer instances per use case.

### 2. Knowledge Pillars (MCP Tools)

FunJoin's agent queries 5 live systems on demand:

1. **GitLab** - Code as source of truth (how features work)
2. **Intercom** - Historical conversations (how questions were answered)
3. **Guru** - Knowledge base (pricing, policies)
4. **Jira/Confluence** - Project context (issues, docs)
5. **Slack** - Team context (decisions, discussions)

**Implication for Convergence:** Convergence doesn't need to know about these tools directly. It only optimizes the **response generation** step (temperature, tone, length), not the tool selection.

### 3. Question Categories and Resolution Paths

FunJoin categorized support questions with clear resolution paths:

| Category | % of Questions | Resolution Source |
|----------|----------------|-------------------|
| "How does X work?" | 40% | Code (GitLab) |
| "Why did Y happen?" | 35% | Domain events + Celery tasks |
| "What's status of Z?" | 25% | Live database queries |

**Implication for Convergence:** Different question types may need different optimization strategies. Consider context-aware arm selection (pass question category as context).

---

## Current Integration Pattern

FunJoin's existing Convergence integration follows a three-step pattern:

### Step 1: Configure Runtime (Once at Startup)

```python
await configure_runtime(
    system="funjoin_sales",
    config={
        "storage": {"backend": "sqlite", "path": "data/convergence.db"},
        "arms": [
            {"arm_id": "professional_concise", "params": {"tone": "professional", "temperature": 0.5}},
            {"arm_id": "friendly_detailed", "params": {"tone": "friendly", "temperature": 0.7}},
            {"arm_id": "consultative_balanced", "params": {"tone": "consultative", "temperature": 0.6}}
        ]
    }
)
```

### Step 2: Select Per Request

```python
selection = await runtime_select(
    system="funjoin_sales",
    user_id=user_id,
    context={"channel": "web", "time_of_day": "morning"}
)
# Use selection.params["temperature"], selection.params["tone"]
```

### Step 3: Update on Outcome

```python
await runtime_update(
    system="funjoin_sales",
    decision_id=selection.decision_id,
    reward=1.0 if converted else 0.0
)
```

**This is "plug-and-play" - three function calls.** FunJoin's pain point is everything *around* this pattern that they have to build themselves.

---

## What FunJoin Needs from Convergence

### Priority 1: Semantic Cache Layer (~300 LOC value)

**Pain Point:** 70-80% of support questions are semantically similar. Without semantic caching, FunJoin pays for the same answer repeatedly.

**What They Want:**

```python
# Before calling LLM
cached = await semantic_cache.get(query)
if cached:
    return cached["response"]  # 80% cost reduction

# After generating response
await semantic_cache.set(query, response)
```

**Technical Requirements:**
- Pluggable embedding function (they'll use OpenAI or local)
- Similarity threshold (0.88 default)
- TTL-based expiration (24hr default)
- Backend options: memory (dev), Redis (prod)

**Integration Point:** Should integrate with `runtime_select` - if cache hit, return cached response with `cache_hit=True` metadata.

### Priority 2: PostgreSQL Runtime Storage (~200 LOC value)

**Pain Point:** FunJoin's stack is PostgreSQL. SQLite works but adds operational complexity.

**What They Want:**

```python
await configure_runtime(
    system="funjoin_sales",
    config={
        "storage": {
            "backend": "postgresql",
            "dsn": "postgresql://user:pass@localhost/funjoin"
        }
    }
)
```

**Technical Requirements:**
- asyncpg for async operations
- Auto-schema creation on first connection
- Connection pooling
- Same RuntimeStorageProtocol interface as SQLite

**Schema:**
- `convergence_arms` - arm state (alpha, beta, params)
- `convergence_decisions` - decision history

### Priority 3: Response Wrapper with Confidence (~100 LOC value)

**Pain Point:** Every LLM response needs: content, confidence, decision_id, cache status. FunJoin keeps rebuilding this.

**What They Want:**

```python
from convergence.types import LLMResponse

response = LLMResponse(
    content="...",
    confidence=0.85,
    decision_id="abc123",
    cache_hit=False,
    gap_detected=False
)
```

**Technical Requirements:**
- Pydantic model
- Confidence 0.0-1.0
- Cache metadata (hit, similarity)
- Gap detection flag + reason
- Token usage tracking
- Latency tracking

### Priority 4: Confidence Extraction (~150 LOC value)

**Pain Point:** Claude's confidence is implicit. Extracting it requires parsing hedging language, explicit markers, and certainty indicators.

**What They Want:**

```python
from convergence.evaluators import extract_confidence

confidence = extract_confidence(response.content)
if confidence < 0.6:
    # Route to human
```

**Technical Requirements:**
- Multiple extraction methods (explicit, hedging, certainty)
- Configurable thresholds
- Auto mode that takes most conservative score

### Priority 5: Claude Client Integration (~250 LOC value)

**Pain Point:** Building Claude client with tool_use, convergence selection, and confidence scoring is ~500 LOC in FunJoin. Want turnkey.

**What They Want:**

```python
from convergence.clients import ClaudeClient

client = ClaudeClient(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    system="funjoin_sales"
)

response = await client.chat(
    message="How does payment plan charging work?",
    user_id="user_123",
    tools=[search_code, search_kb]
)
# response.content, response.confidence, response.decision_id
```

**Technical Requirements:**
- Automatic param selection via Thompson Sampling
- Tool use support
- Confidence extraction built-in
- Gap detection built-in
- `record_outcome()` method for learning

---

## Pain Points in Current Setup

### 1. No Semantic Caching

FunJoin currently has no way to avoid redundant LLM calls for similar questions. This is their #1 cost concern. They estimate 80% cost reduction with semantic caching.

### 2. SQLite Lock Contention

Under load, SQLite's single-writer lock causes contention. FunJoin wants PostgreSQL with connection pooling for production.

### 3. Manual Confidence Extraction

Every response requires parsing for confidence signals. This is error-prone and duplicated across all agent code paths.

### 4. Gap Detection is Manual

FunJoin has to manually implement "if confidence < threshold, route to human". This should be a first-class feature.

### 5. No Monitoring API

FunJoin wants to expose arm statistics (alpha, beta, selection distribution) to their admin UI. Currently `arms_state` is in selection metadata but not directly queryable.

### 6. PostgreSQL Backend Missing

FunJoin explicitly calls out that PostgreSQL backend is "NOT YET IMPLEMENTED" and recommends starting with SQLite but notes this is a Phase 2 need.

---

## What "Plug-and-Play" Means to FunJoin

FunJoin's definition of "plug-and-play":

1. **Single import statement** - `from convergence import configure_runtime, runtime_select, runtime_update`

2. **Zero configuration for common cases** - Defaults should work. Only override when needed.

3. **Match their stack** - PostgreSQL, not SQLite. asyncpg, not sync.

4. **Three function calls total:**
   - `configure_runtime()` - once at startup
   - `runtime_select()` - per request
   - `runtime_update()` - on outcome

5. **Everything else is optional** - Semantic caching, confidence extraction, Claude client are bonuses, not requirements.

6. **Types they can trust** - Pydantic models, not raw dicts. TypedDict for kwargs.

7. **Async throughout** - No sync wrappers. FunJoin is async-first.

---

## Knowledge Architecture Requirements

FunJoin's agent uses a **tool-first architecture** - it queries live systems on demand rather than relying on static knowledge dumps.

### Convergence's Role in Knowledge Architecture

Convergence does NOT need to understand FunJoin's knowledge pillars (GitLab, Intercom, Guru, Jira, Slack). Convergence optimizes:

1. **Response generation parameters** - temperature, tone, length
2. **Caching decisions** - when to return cached responses
3. **Confidence scoring** - when to route to human

### Integration Points

| FunJoin Component | Convergence Component |
|-------------------|----------------------|
| `ai_agent` module | `runtime_select`, `runtime_update` |
| MCP tool responses | (No integration - Convergence doesn't see these) |
| Response construction | `LLMResponse` wrapper |
| Gap logging | `gap_detected` flag |
| Admin UI | Arm statistics API |

### What FunJoin Builds (Not Convergence's Concern)

- Tool definitions (search_code, search_kb, etc.)
- Knowledge seeding (Guru, Intercom, GitLab sources)
- Admin UI (MobX/ViewModel pattern)
- Gap review workflows
- Entry point integrations (Intercom webhook, Slack bot, website widget)

---

## Open Questions

### 1. Multi-Context Arms

Should arms be context-aware? FunJoin might want different arm performance for sales vs. support vs. internal contexts.

**Current state:** Context is passed to `runtime_select` but only used for metadata, not arm selection.

**Potential enhancement:** Context-conditional Thompson Sampling (separate alpha/beta per context).

### 2. Multi-Metric Rewards

FunJoin mentions "conversion * quality" as a future reward signal. Current API only supports single reward value.

**Potential enhancement:** Multi-objective optimization or composite reward helper.

### 3. Arm Evolution

FunJoin mentions "prompt template evolution" in Phase 3. This suggests they want to evolve arm configurations, not just select among static arms.

**Potential enhancement:** Genetic operators for arm mutation/crossover.

### 4. Monitoring API

FunJoin wants arm statistics for their admin UI. Current API exposes `arms_state` in selection metadata but no direct query.

**Potential enhancement:** `runtime_get_stats()` function returning arm performance metrics.

---

## Implementation Priorities for Convergence

Based on FunJoin's stated needs:

| Priority | Feature | LOC | FunJoin Impact |
|----------|---------|-----|----------------|
| 1 | Semantic Cache Layer | ~300 | 80% cost reduction |
| 2 | PostgreSQL Storage | ~200 | Zero new deps |
| 3 | Response Wrapper | ~100 | Clean interface |
| 4 | Confidence Extraction | ~150 | Auto gap detection |
| 5 | Claude Client | ~250 | Turnkey integration |

**Total: ~1000 LOC in Convergence = ~3000 LOC saved in FunJoin**

---

## Implications for Convergence Roadmap

### Short-Term (This Sprint)

1. **PostgreSQL backend** - Use asyncpg, same protocol as SQLite
2. **Semantic cache** - Pluggable embeddings, configurable threshold
3. **LLMResponse type** - Pydantic model with confidence + cache fields

### Medium-Term (Next Sprint)

4. **Confidence extractors** - Hedging detection, explicit markers
5. **Claude client** - Optional integration layer
6. **Monitoring API** - Arm statistics for admin UIs

### Long-Term (Future)

6. **Context-aware arms** - Per-context alpha/beta
7. **Multi-metric rewards** - Composite reward helpers
8. **Arm evolution** - Genetic operators for configuration space

---

## Key Takeaways

1. **FunJoin is a perfect first customer** - They're building exactly what Convergence is designed for. Their feedback shapes the API.

2. **Semantic caching is the killer feature** - 80% cost reduction makes Convergence pay for itself.

3. **PostgreSQL is non-negotiable for production** - SQLite works for dev but production needs proper connection pooling.

4. **Confidence/gap detection is core** - Every agent needs this. Build it into Convergence, not FunJoin.

5. **Keep it simple** - Three function calls is the right API surface. Everything else is optional enhancement.

6. **FunJoin's unified agent architecture is elegant** - One agent, multiple entry points, same tools. Convergence optimizes the response generation, not the tool selection.

---

*Synthesized from FunJoin documentation for Convergence roadmap planning.*
