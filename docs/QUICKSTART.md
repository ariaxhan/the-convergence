# Quick Start

Get The Convergence running in 5 minutes.

## Installation

```bash
pip install convergence

# With optional dependencies
pip install convergence[safety]       # Injection detection, budget enforcement
pip install convergence[observability] # Weave integration
pip install convergence[all]          # Everything
```

## Minimal Example

```python
import asyncio
from convergence.runtime.online import configure, select, update
from convergence.types import RuntimeConfig, RuntimeArmTemplate
from convergence.storage.sqlite import SQLiteStorage

async def main():
    # Configure storage
    storage = SQLiteStorage(db_path="./convergence.db")
    await storage.initialize()

    # Define arms (models to choose from)
    config = RuntimeConfig(
        system="my-agent",
        default_arms=[
            RuntimeArmTemplate(arm_id="gpt-4", name="GPT-4", params={"model": "gpt-4"}),
            RuntimeArmTemplate(arm_id="gpt-3.5", name="GPT-3.5", params={"model": "gpt-3.5-turbo"}),
            RuntimeArmTemplate(arm_id="claude-3", name="Claude 3", params={"model": "claude-3-sonnet"}),
        ],
    )

    # Register runtime
    await configure("my-agent", config=config, storage=storage)

    # Select best arm (Thompson Sampling)
    selection = await select("my-agent", user_id="user-123")
    print(f"Selected: {selection.arm_id}")
    print(f"Params: {selection.params}")

    # Simulate using the model and getting feedback
    # In reality, you'd call the LLM and evaluate the response
    reward = 0.9  # 0-1 scale

    # Update with reward (agent learns)
    await update(
        "my-agent",
        user_id="user-123",
        decision_id=selection.decision_id,
        reward=reward,
    )

asyncio.run(main())
```

## What Just Happened?

1. **Thompson Sampling** selected the model with highest expected reward
2. Agent tracked the response quality for future decisions
3. Over time, agent learns which model works best

## Next Steps

- [SAFETY.md](SAFETY.md) — Add guardrails and budget enforcement
- [OBSERVABILITY.md](OBSERVABILITY.md) — Monitor learning metrics
- [SELF-LEARNING.md](SELF-LEARNING.md) — Understand the RL algorithms
- [INTEGRATION.md](INTEGRATION.md) — Enterprise deployment

## Configuration

### Environment Variables

```bash
# Required for LLM calls
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
CONVERGENCE_LOG_LEVEL=INFO
```

### Selection Strategy

```python
from convergence.types import RuntimeConfig, SelectionStrategyConfig

config = RuntimeConfig(
    system="my-agent",
    selection_strategy=SelectionStrategyConfig(
        exploration_bonus=0.1,       # Bonus for under-explored arms
        exploration_min_pulls=5,     # Min pulls before bonus stops
        use_stability=True,          # Avoid switching when converged
        stability_min_pulls=20,      # Min pulls for stability check
    ),
    default_arms=[...],
)
```

### Reward Evaluation

```python
from convergence.runtime.reward_evaluator import RewardEvaluatorConfig, RewardMetricConfig

config = RuntimeConfig(
    system="my-agent",
    reward_evaluator=RewardEvaluatorConfig(
        metrics=[
            RewardMetricConfig(name="quality", weight=0.5),
            RewardMetricConfig(name="latency", weight=0.3, invert=True),
            RewardMetricConfig(name="cost", weight=0.2, invert=True),
        ],
    ),
    default_arms=[...],
)

# Then pass signals instead of raw reward
await update(
    "my-agent",
    user_id="user-123",
    decision_id=selection.decision_id,
    signals={"quality": 0.9, "latency": 0.2, "cost": 0.05},
)
```

## Troubleshooting

### "No arms found"

Make sure you've configured default arms:

```python
config = RuntimeConfig(
    system="my-agent",
    default_arms=[
        RuntimeArmTemplate(arm_id="default", name="Default", params={}),
    ],
)
```

### "Decision not found"

Ensure you're using the correct `decision_id` from the selection:

```python
selection = await select("my-agent", user_id="user-123")
# Use selection.decision_id, not a made-up ID
await update("my-agent", decision_id=selection.decision_id, ...)
```

## Performance Tips

1. **Use SQLite storage** — State persists across restarts
2. **Enable observability** — Find and fix slow paths
3. **Tune exploration** — Lower `exploration_bonus` after initial learning
4. **Use stability** — Avoid thrashing between similar arms
