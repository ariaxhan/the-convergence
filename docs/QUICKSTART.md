# Quick Start

Get The Convergence running in 5 minutes.

## Installation

```bash
pip install convergence

# With optional dependencies
pip install convergence[safety]       # NeMo Guardrails, Guardrails AI
pip install convergence[observability] # Weave integration
pip install convergence[all]          # Everything
```

## Minimal Example

```python
import asyncio
from convergence import ConvergenceAgent
from convergence.plugins.mab import ThompsonSamplingStrategy

async def main():
    # Create agent with self-learning optimization
    agent = ConvergenceAgent(
        models=["gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
        strategy=ThompsonSamplingStrategy(),
    )

    # Agent learns which model works best for each task
    response = await agent.complete(
        prompt="Explain quantum computing",
        context={"task_type": "explanation"},
    )

    print(response.content)
    print(f"Selected model: {response.model}")
    print(f"Confidence: {response.confidence:.2f}")

asyncio.run(main())
```

## What Just Happened?

1. **Thompson Sampling** selected the model with highest expected reward
2. Agent tracked the response quality for future decisions
3. Over time, agent learns which model works best for each task type

## Next Steps

- [SAFETY.md](SAFETY.md) — Add guardrails and budget enforcement
- [OBSERVABILITY.md](OBSERVABILITY.md) — Monitor learning metrics
- [SELF-LEARNING.md](SELF-LEARNING.md) — Understand the RL algorithms
- [INTEGRATION.md](INTEGRATION.md) — Enterprise deployment

## Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
CONVERGENCE_LOG_LEVEL=INFO
CONVERGENCE_CACHE_PATH=./cache.db
```

### Basic Config

```python
from convergence import ConvergenceConfig

config = ConvergenceConfig(
    # Model selection
    default_models=["gpt-4", "gpt-3.5-turbo"],

    # Learning
    exploration_rate=0.1,  # 10% exploration

    # Cache
    semantic_cache_enabled=True,
    cache_threshold=0.88,

    # Safety (defaults)
    budget_daily_limit=100.0,
    injection_detection=True,
)
```

## Common Patterns

### With Semantic Cache

```python
from convergence.cache import SemanticCache

cache = SemanticCache(
    embedding_fn=get_embedding,
    backend="sqlite",
    sqlite_path="./cache.db",
    threshold=0.88,
)

agent = ConvergenceAgent(
    models=["gpt-4"],
    cache=cache,
)
```

### With Custom Reward Function

```python
def custom_reward(response, context):
    """Define what 'good' means for your use case."""
    # Example: prefer shorter responses for summaries
    if context.get("task_type") == "summary":
        return 1.0 if len(response.content) < 500 else 0.5
    return response.quality_score

agent = ConvergenceAgent(
    models=["gpt-4", "claude-3"],
    reward_fn=custom_reward,
)
```

### Persisting Learning State

```python
from convergence.storage import SQLiteStorage

storage = SQLiteStorage(db_path="./agent_state.db")

agent = ConvergenceAgent(
    models=["gpt-4"],
    storage=storage,  # State persists across restarts
)
```

## Troubleshooting

### "No models configured"

Ensure you've set API keys:

```bash
export OPENAI_API_KEY=sk-...
```

### "Cache miss on similar queries"

Lower the threshold:

```python
cache = SemanticCache(threshold=0.85)  # Default is 0.88
```

### "Slow first request"

First request loads models and builds cache index. Subsequent requests are faster.

## Performance Tips

1. **Use semantic cache** — 70-80% cost reduction on repeated queries
2. **Enable observability** — Find and fix slow paths
3. **Tune threshold** — Use `cache.validate_threshold()` to find optimal value
4. **Persist state** — Don't lose learning progress on restart
