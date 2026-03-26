# Armature — Agent Implementation Reference

> Structured context for AI agents implementing self-evolving systems.
> Not a tutorial. A decision-complete reference for flawless production execution.

**Version:** 0.1.8 | **Python:** 3.11+ | **License:** Apache 2.0

---

## Quick Reference: Complete Import Map

```python
# --- Runtime (online MAB selection) ---
from armature import configure_runtime, runtime_select, runtime_update, runtime_get_decision
from armature.types import (
    RuntimeConfig,
    RuntimeArmTemplate,
    RuntimeSelection,      # returned by runtime_select
    RuntimeDecision,       # returned by runtime_get_decision
    RuntimeArm,            # arm with learned stats
    RuntimeArmState,       # snapshot at decision time
    SelectionStrategyConfig,
)

# --- Storage backends ---
from armature.storage.memory import MemoryRuntimeStorage      # dev/test (non-persistent)
from armature.storage.postgresql import PostgreSQLRuntimeStorage  # production (requires asyncpg)
# from armature.storage.sqlite import SQLiteStorage             # general storage, NOT runtime storage

# --- Semantic cache ---
from armature.cache.semantic import SemanticCache
from armature.cache.backends import MemoryCacheBackend, SQLiteCacheBackend, RedisCacheBackend

# --- LLM clients ---
from armature.clients.claude import ClaudeClient

# --- Evaluation ---
from armature.evaluators.confidence import extract_confidence
from armature.runtime.reward_evaluator import (
    RuntimeRewardEvaluator,
    RewardEvaluatorConfig,
    RewardMetricConfig,
)

# --- Types ---
from armature.types.response import LLMResponse, detect_gap
from armature.types.config import ArmatureConfig, ApiConfig, SearchSpaceConfig, RunnerConfig, EvaluationConfig

# --- Knowledge ---
from armature.knowledge.graph import ContextGraph
from armature.knowledge.schema import GraphNode, GraphEdge, EntityType, OntologyType

# --- SDK (batch optimization) ---
from armature.sdk import run_optimization, run_optimization_sync

# --- Agent simulation ---
from armature.core.runtime import CivilizationRuntime, Environment, CivilizationState
from armature.core.protocols import Agent, LLMProvider, MABStrategy, Plugin
```

---

## API Surface: Type Signatures

### Runtime Loop (Primary API)

```python
async def configure_runtime(
    system: str, *, config: RuntimeConfig, storage: RuntimeStorageProtocol
) -> None

async def runtime_select(
    system: str, *, user_id: str, agent_type: str | None = None,
    context: dict[str, object] | None = None
) -> RuntimeSelection

async def runtime_update(
    system: str, *, user_id: str, decision_id: str,
    reward: float | None = None, signals: dict[str, float] | None = None,
    agent_type: str | None = None,
    engagement_score: float | None = None, grading_score: float | None = None,
    metadata: dict[str, object] | None = None
) -> dict[str, object]
```

**CRITICAL GOTCHAS:**
- `user_id` is REQUIRED in both `runtime_select` AND `runtime_update`. Missing it raises TypeError.
- `decision_id` comes from `selection.decision_id` — can be None if storage fails. Always check.
- `reward` is clamped to [0.0, 1.0] internally. Values outside this range are silently clamped.
- `signals` is used with `RewardEvaluatorConfig` — if config has evaluator, signals take precedence over raw reward.
- Calling `configure_runtime` multiple times for the same system overwrites the previous config.

### RuntimeConfig Fields

```python
RuntimeConfig(
    system: str,                          # REQUIRED — unique system identifier
    agent_type: str | None = None,        # optional sub-type tag
    min_arms: int = 1,                    # minimum arms (validation)
    cache_ttl_seconds: int = 30,          # how long to cache arm state
    default_arms: list[RuntimeArmTemplate] = [],  # cold-start arms
    selection_strategy: SelectionStrategyConfig | None = None,
    reward_evaluator: RewardEvaluatorConfig | None = None,
)
```

### RuntimeArmTemplate Fields

```python
RuntimeArmTemplate(
    arm_id: str,           # REQUIRED — unique within system
    name: str | None,      # human-readable label
    params: dict = {},     # arbitrary payload passed to caller on selection
    description: str | None,
)
```

### SelectionStrategyConfig Fields

```python
SelectionStrategyConfig(
    exploration_bonus: float = 0.0,             # [0, 1] bonus for under-explored arms
    exploration_min_pulls: int = 5,             # pulls before bonus removed
    use_stability: bool = False,                # enable stability check
    stability_min_pulls: int = 10,              # pulls before arm considered stable
    stability_confidence_threshold: float = 0.2, # CI width below which arm is "stable"
    stability_improvement_threshold: float = 0.05, # min improvement to switch from stable arm
)
```

### RuntimeSelection (return type of runtime_select)

```python
RuntimeSelection(
    decision_id: str | None,   # None if storage failed — ALWAYS check before using in update
    arm_id: str,               # which arm was selected
    params: dict[str, Any],    # the arm's parameter payload — use this in your LLM call
    sampled_value: float,      # Thompson Sampling sampled value (for debugging)
    arms_state: list[RuntimeArmState],  # snapshot of all arms at decision time
    metadata: dict,            # includes system, agent_type, samples
)
```

### SemanticCache

```python
SemanticCache(
    embedding_fn: Callable[[str], list[float]] | Callable[[str], Awaitable[list[float]]],
    backend: str = "memory",       # "memory" | "sqlite" | "redis"
    threshold: float = 0.88,       # cosine similarity threshold for cache hit
    ttl_seconds: int | None = None,
    sqlite_path: str | None = None,  # REQUIRED if backend="sqlite"
    redis_url: str | None = None,    # REQUIRED if backend="redis"
    namespace: str = "armature_cache",
)
# .get(query: str) -> dict | None    — returns {content, similarity, original_query, created_at, ...} or None
# .set(query: str, response: dict)   — store query → response mapping
# .clear()                           — remove all entries
```

### ClaudeClient

```python
ClaudeClient(
    *, api_key: str | None = None,  # falls back to ANTHROPIC_API_KEY env var
    system: str,                     # system identifier for runtime tracking
    system_prompt: str | None = None,
    model: str = "claude-sonnet-4-5",
    max_tokens: int = 1024,
    gap_threshold: float = 0.6,     # confidence below this = gap_detected=True
)
# .chat(*, message: str, user_id: str, tools: list | None = None) -> LLMResponse
# .record_outcome(*, decision_id: str, user_id: str, reward: float) -> None
```

### LLMResponse Fields

```python
LLMResponse(
    content: str,                    # response text
    confidence: float | None,       # 0.0-1.0 extracted confidence
    decision_id: str | None,        # for recording outcomes
    cache_hit: bool = False,
    similarity: float | None,       # cache hit similarity score
    model: str | None,
    tokens_used: int | None,
    params: dict | None,
    gap_detected: bool = False,     # True if confidence < gap_threshold
    metadata: dict | None,
)
```

### ContextGraph

```python
graph = ContextGraph()
graph.add_node(GraphNode(id=str, entity_type=EntityType, label=str, properties=dict))
graph.add_edge(GraphEdge(id=str, source_id=str, target_id=str, ontology_type=OntologyType, weight=float, properties=dict))
graph.get_node(node_id: str) -> GraphNode          # raises KeyError if not found
graph.has_node(node_id: str) -> bool
graph.remove_node(node_id: str) -> None
graph.get_neighbors(node_id: str) -> list           # returns [(edge, node), ...]
graph.get_nodes_by_type(entity_type) -> list
graph.traverse(start_id: str, max_depth: int) -> list
graph.node_count() -> int
```

**EntityType values:** WHO, WHAT, HOW
**OntologyType values:** OWNS, USES, DEPENDS_ON, PRODUCES, CONSUMES

### Confidence Extraction

```python
extract_confidence(text: str, method: str = "auto") -> float | None
# method: "auto" | "explicit" | "hedging" | "certainty"
# "auto" checks explicit markers first, then hedging/certainty language
# Returns 0.0-1.0 or None (if no signal detected)
```

### Reward Evaluator

```python
config = RewardEvaluatorConfig(
    metrics={
        "quality": RewardMetricConfig(name="quality", weight=0.6, normalize=True),
        "speed": RewardMetricConfig(name="speed", weight=0.4, normalize=True),
    },
)
evaluator = RuntimeRewardEvaluator(config)
reward = evaluator.evaluate({"quality": 0.9, "speed": 0.7})  # -> 0.82
```

---

## Architecture Decision Records

### ADR-1: When to use Runtime vs SDK

| Scenario | Use | Why |
|----------|-----|-----|
| Per-request parameter optimization | **Runtime** (configure/select/update) | Online learning, per-user personalization |
| Batch parameter search | **SDK** (run_optimization) | Offline optimization, grid/evolutionary search |
| A/B testing | **Runtime** with 2 arms | Thompson Sampling naturally allocates traffic |
| Feature flags | **Runtime** with exploration_bonus=0 | Deterministic once converged |

### ADR-2: Storage Backend Selection

| Backend | Use When | Latency | Persistence | Multi-process |
|---------|----------|---------|-------------|---------------|
| MemoryRuntimeStorage | Dev, tests, single-process | <1ms | No | No |
| PostgreSQLRuntimeStorage | Production | 2-10ms | Yes | Yes |
| SQLiteStorage | General persistence | 1-5ms | Yes | No (WAL helps) |

**IMPORTANT:** `MemoryRuntimeStorage` is per-process. In multi-worker deployments (gunicorn, uvicorn), each worker has isolated state. Use PostgreSQL for shared state.

### ADR-3: Embedding Strategy Selection

| Strategy | Quality | Speed | Dependencies | Use When |
|----------|---------|-------|-------------|----------|
| Hash (SHA-256) | Poor | <1ms | None | Testing, deterministic behavior |
| Character n-gram | Fair | <5ms | None | Light-weight, no external deps |
| TF-IDF | Good | <10ms | None (self-built vocab) | Known domain, stable vocabulary |
| OpenAI embeddings | Excellent | 100-500ms | openai package + API key | Production semantic search |
| Sentence transformers | Excellent | 50-200ms | sentence-transformers + torch | On-premise, no API dependency |

### ADR-4: Cache Threshold Selection

```
threshold=0.95+ → High precision, low recall (only near-exact matches)
threshold=0.88  → Balanced (default, good for most use cases)
threshold=0.80  → High recall, lower precision (more hits but more false positives)
threshold=0.70  → Aggressive caching (only for fuzzy/exploratory use cases)
```

**Calibration method:** Use `examples/11_vector_native/similarity_tuning.py` with labeled pairs from your domain.

### ADR-5: Armature Timeline

| Mechanism | Armature Speed | Data Needed | When to Use |
|-----------|-------------------|-------------|-------------|
| Thompson Sampling | 15-30 interactions | Binary reward (0/1) | Most cases — start here |
| Thompson + exploration_bonus | 20-40 interactions | Same | Cold start, need to sample all arms |
| Thompson + stability | 30-50 interactions | Same | Production, minimize unnecessary switching |
| Reward Evaluator (multi-signal) | 30-50 interactions | Multiple float signals | Rich feedback available |

---

## Edge Case Catalog

### Runtime Edge Cases

| Edge Case | What Happens | Fix |
|-----------|-------------|-----|
| `decision_id` is None | Storage failed during create_decision | Check before passing to runtime_update; skip update or log warning |
| All arms have alpha=1, beta=1 | Cold start — pure random sampling | Expected behavior. Add exploration_bonus to accelerate learning |
| Single arm configured | Always selects that arm | Thompson Sampling degrades gracefully to deterministic |
| Same user_id for all requests | Single Bayesian posterior per user | Use unique user_ids OR shared "global" user for system-level learning |
| Different user_id per request | Separate learning per user | Cold start for each new user. Use default_arms for reasonable fallback |
| Storage throws exception | RuntimeManager returns fallback selection | Fallback uses first default_arm with sampled_value=0.5 |
| Reward of exactly 0.0 or 1.0 | Alpha or beta incremented by 1.0 | Valid. Extreme values learn faster but are more confident |
| Reward of 0.5 | Neutral signal — alpha and beta both increment by 0.5 | System learns slowly. Prefer binary (0/1) or extreme values |
| cache_ttl_seconds=0 | Arms reloaded from storage every call | High storage load. Use >=5 for production |
| configure_runtime called twice | Second config overwrites first | Safe — but in-flight requests may see old config |

### Cache Edge Cases

| Edge Case | What Happens | Fix |
|-----------|-------------|-----|
| embedding_fn returns wrong dimensions | Cosine similarity undefined | Validate dimensions on first call; SemanticCache doesn't check |
| embedding_fn returns NaN/Inf | Cosine similarity returns NaN | Validate embeddings before storage; replace NaN with 0.0 |
| Two queries with identical embeddings | Similarity = 1.0, always cache hit | Expected. Hash-based embeddings have high collision rate |
| Cache full (memory backend) | No limit — grows unbounded | Implement TTL or max_entries eviction |
| SQLite backend with WAL mode | Supports concurrent readers | Default. Don't disable WAL in production |
| Redis connection lost | RedisCacheBackend raises on get/set | Wrap in try/except, fall back to memory |
| threshold=1.0 | Only exact embedding matches hit | Effectively disables caching for all but identical queries |

### ClaudeClient Edge Cases

| Edge Case | What Happens | Fix |
|-----------|-------------|-----|
| ANTHROPIC_API_KEY not set | ValueError on init | Check env var before creating client |
| Empty message string | ValueError("Message cannot be empty") | Validate input before calling chat() |
| Runtime not configured | Selection silently fails, uses model defaults | ClaudeClient works without runtime — confidence still extracted |
| API rate limit hit | anthropic.RateLimitError | Implement retry with exponential backoff |
| API timeout | anthropic.APITimeoutError | Set reasonable timeout, return degraded response |
| Response has no text blocks | content="" | ClaudeClient handles this — confidence will be low |

---

## Security Hardening Checklist

### Input Validation (REQUIRED)

```python
# 1. Reject empty/whitespace inputs
if not message or not message.strip():
    raise ValueError("Empty input")

# 2. Length limits (prevent token bombs)
MAX_INPUT_LENGTH = 10000  # characters
if len(message) > MAX_INPUT_LENGTH:
    message = message[:MAX_INPUT_LENGTH]

# 3. Prompt injection detection (basic patterns)
INJECTION_PATTERNS = [
    r"ignore (all |previous |above )?instructions",
    r"you are now",
    r"system:\s",
    r"<\|im_start\|>",
    r"\[INST\]",
]

# 4. Control character stripping
import re
message = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', message)
```

### Output Validation (REQUIRED)

```python
# 1. PII detection before returning to user
PII_PATTERNS = {
    "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
    "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
}

# 2. Confidence validation
if response.confidence is not None:
    assert 0.0 <= response.confidence <= 1.0

# 3. Content length check (detect truncation)
if response.tokens_used and response.tokens_used >= max_tokens:
    # Response may be truncated — flag for review
    pass
```

### Storage Security

```python
# PostgreSQL: Always use parameterized queries (the framework does this)
# SQLite: Use WAL mode for concurrent access
# Memory: Never store PII in MemoryRuntimeStorage (no encryption at rest)
# Redis: Use redis_url with TLS (rediss://) in production
```

### API Key Management

```python
# NEVER hardcode keys
# ALWAYS use environment variables
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise EnvironmentError("ANTHROPIC_API_KEY must be set")

# For multi-tenant: use per-tenant keys, not a single shared key
```

---

## Production Patterns

### Pattern 1: Resilient Select-Update Loop

```python
async def safe_select_and_update(
    system: str,
    user_id: str,
    process_fn: Callable,
    max_retries: int = 3,
) -> dict:
    """Production-grade select → process → update loop."""
    for attempt in range(max_retries):
        try:
            selection = await asyncio.wait_for(
                runtime_select(system, user_id=user_id),
                timeout=5.0,
            )

            # ALWAYS check decision_id before proceeding
            if selection.decision_id is None:
                log.warning("Storage unavailable, using fallback arm", extra={
                    "arm_id": selection.arm_id, "user_id": user_id
                })

            result = await process_fn(selection.params)
            reward = compute_reward(result)

            if selection.decision_id:
                await asyncio.wait_for(
                    runtime_update(
                        system,
                        user_id=user_id,
                        decision_id=selection.decision_id,
                        reward=reward,
                    ),
                    timeout=5.0,
                )

            return {"success": True, "result": result, "arm_id": selection.arm_id}

        except asyncio.TimeoutError:
            log.warning("Timeout on attempt %d/%d", attempt + 1, max_retries)
            if attempt == max_retries - 1:
                return {"success": False, "error": "timeout", "result": fallback_result()}
            await asyncio.sleep(2 ** attempt)  # exponential backoff

        except Exception as e:
            log.error("Error on attempt %d/%d: %s", attempt + 1, max_retries, e)
            if attempt == max_retries - 1:
                return {"success": False, "error": str(e), "result": fallback_result()}
            await asyncio.sleep(2 ** attempt)
```

### Pattern 2: Cache-First with Fallback

```python
async def query_with_cache(
    cache: SemanticCache,
    client: ClaudeClient,  # or any LLM
    query: str,
    user_id: str,
) -> LLMResponse:
    """Cache-first query with graceful degradation."""
    # Try cache first
    try:
        cached = await cache.get(query)
        if cached:
            return LLMResponse(
                content=cached["content"],
                confidence=cached.get("confidence"),
                cache_hit=True,
                similarity=cached.get("similarity"),
            )
    except Exception as e:
        log.warning("Cache error (non-fatal): %s", e)

    # Cache miss or error — call LLM
    try:
        response = await client.chat(message=query, user_id=user_id)

        # Store in cache (fire-and-forget, don't block on cache write)
        try:
            await cache.set(query, {
                "content": response.content,
                "confidence": response.confidence,
            })
        except Exception:
            pass  # Cache write failure is non-fatal

        return response

    except Exception as e:
        log.error("LLM error: %s", e)
        return LLMResponse(
            content="I'm having trouble processing your request. Please try again.",
            confidence=0.0,
            gap_detected=True,
        )
```

### Pattern 3: Multi-Signal Reward

```python
# When you have multiple feedback signals, use RewardEvaluator
config = RewardEvaluatorConfig(
    metrics={
        "user_rating": RewardMetricConfig(name="user_rating", weight=0.4),
        "task_completion": RewardMetricConfig(name="task_completion", weight=0.3),
        "response_time": RewardMetricConfig(name="response_time", weight=0.2),
        "no_escalation": RewardMetricConfig(name="no_escalation", weight=0.1),
    },
)
evaluator = RuntimeRewardEvaluator(config)

# After each interaction, collect signals and compute composite reward
signals = {
    "user_rating": user_gave_thumbs_up,      # 0.0 or 1.0
    "task_completion": task_was_completed,     # 0.0 or 1.0
    "response_time": 1.0 - min(latency_s / 10.0, 1.0),  # normalize to [0, 1]
    "no_escalation": 0.0 if escalated else 1.0,
}
reward = evaluator.evaluate(signals)

# Use with runtime_update via signals parameter
await runtime_update(system, user_id=uid, decision_id=did, signals=signals)
```

---

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|-------------|---------------|-----------------|
| `reward=0.5` for everything | No learning signal — arms never converge | Use binary 0/1 or extreme values when possible |
| Same `user_id` for all users | Single posterior — can't personalize | Use actual user identifiers |
| `cache_ttl_seconds=0` | Reloads arms from storage every call | Use >=5 seconds for production |
| Ignoring `decision_id=None` | Passing None to runtime_update crashes | Always check before updating |
| Bare `except: pass` on storage errors | Hides real failures | Log errors, track error rate, alert on threshold |
| Creating new RuntimeConfig per request | Reinitializes arms every time | Configure once at startup |
| Hardcoding `threshold=0.88` | May not fit your domain | Calibrate with labeled data using similarity_tuning.py |
| Using MemoryRuntimeStorage in production | Lost on restart, not shared across workers | Use PostgreSQLRuntimeStorage |
| Not setting `exploration_bonus` on cold start | First arm selected gets all traffic | Set bonus=0.1, min_pulls=5 to ensure sampling |
| Using `extract_confidence` on structured output | Designed for natural language text | Use explicit confidence fields for structured responses |

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `TypeError: update() missing 'user_id'` | `user_id` is required keyword arg | Add `user_id=...` to runtime_update call |
| `ValueError: threshold must be between 0.0 and 1.0` | Invalid cache threshold | Check threshold value |
| `ImportError: anthropic package required` | ClaudeClient needs anthropic | `pip install anthropic` |
| `ValueError: No API key provided` | ANTHROPIC_API_KEY not set | `export ANTHROPIC_API_KEY=...` |
| Arms never converge | Rewards are always ~0.5, or too few interactions | Use binary rewards, increase interactions to 30+ |
| Cache never hits | Threshold too high for your embeddings | Lower threshold, or use better embeddings |
| `KeyError: Node 'x' not found` | ContextGraph.get_node on missing node | Use has_node() first, or try/except KeyError |
| Runtime returns same arm always | One arm has much higher alpha/beta (converged) | Expected if that arm is genuinely better |
| PostgreSQL connection refused | Wrong DSN or DB not running | Check DSN, ensure PostgreSQL is running |
| `weave` import error in CivilizationRuntime | weave package not installed | `pip install weave` or use Runtime API instead |

---

## File Map: What to Read for What

| I need to... | Read this file |
|-------------|---------------|
| Understand the full API | This file (AGENT.md) |
| See a minimal working example | `examples/00_quickstart/01_basic_runtime.py` |
| Build a production runtime wrapper | `examples/10_agent_patterns/production_runtime.py` |
| Add security hardening | `examples/10_agent_patterns/secure_client.py` |
| Implement resilient caching | `examples/10_agent_patterns/resilient_cache.py` |
| Build an observable pipeline | `examples/10_agent_patterns/observable_pipeline.py` |
| Add evolution with safety bounds | `examples/10_agent_patterns/safe_evolution.py` |
| Choose an embedding strategy | `examples/11_vector_native/embedding_strategies.py` |
| Calibrate cache thresholds | `examples/11_vector_native/similarity_tuning.py` |
| Implement hybrid search | `examples/11_vector_native/hybrid_search.py` |
| Monitor cache quality | `examples/11_vector_native/cache_quality.py` |
| Understand the YAML config path | `YAML_CONFIGURATION_REFERENCE.md` |
| See all available modules | `llms.txt` |
| Choose the right module | `USE_CASES.md` |

---

## Storage Protocol: Custom Backend Implementation

To implement a custom storage backend:

```python
from armature.storage.runtime_protocol import RuntimeStorageProtocol

class MyCustomStorage:
    """Must implement all 5 methods with exact signatures."""

    async def get_arms(self, *, user_id: str, agent_type: str) -> list[Any]:
        """Return arm dicts with: arm_id, name, params, alpha, beta, total_pulls, total_reward, mean_estimate, metadata"""

    async def initialize_arms(self, *, user_id: str, agent_type: str, arms: list[dict]) -> Any:
        """Seed arms. MUST be idempotent (no-op if arms already exist)."""

    async def create_decision(
        self, *, user_id: str, agent_type: str, arm_pulled: str,
        strategy_params: dict, arms_snapshot: list[dict], metadata: dict | None = None,
    ) -> str | None:
        """Persist decision, return decision_id. Return None on failure (don't raise)."""

    async def update_performance(
        self, *, user_id: str, agent_type: str, decision_id: str, reward: float,
        engagement: float | None = None, grading: float | None = None,
        metadata: dict | None = None, computed_update: dict | None = None,
    ) -> Any:
        """Apply reward. If computed_update provided, use those pre-computed Bayesian values."""

    async def get_decision(self, *, user_id: str, decision_id: str) -> dict:
        """Fetch decision record. Return empty dict if not found."""
```

**IMPORTANT:** The `computed_update` dict contains pre-computed `alpha`, `beta`, `total_pulls`, `total_reward`, `avg_reward`, `mean_estimate`. Use these directly — do NOT recompute Bayesian updates in storage.

---

## Agent Protocol: Custom Agent Implementation

For CivilizationRuntime:

```python
class MyAgent:
    """Minimum viable agent for CivilizationRuntime."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.config: dict = {}
        self._history: list = []

    async def act(self, state: dict) -> dict:
        """
        Must return dict with:
        - "thought": str (reasoning, used for RLP scoring)
        - "strategy": str ("explore" or "exploit", used for MAB tracking)
        - "action": str (what was done)
        """
        return {
            "thought": f"Analyzing task: {state.get('task', {}).get('type', 'unknown')}",
            "strategy": "explore",
            "action": "completed",
        }

    async def learn(self, experience: dict) -> None:
        """
        experience contains: state, thought, strategy, action, reward, task
        Use this to update internal state/strategy.
        """
        self._history.append(experience)
```
