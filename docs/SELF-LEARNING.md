# Self-Learning

How The Convergence learns and improves over time.

## Core Concept

Traditional systems require manual tuning. The Convergence uses reinforcement learning to automatically:

1. **Select the best model** for each task type
2. **Learn from outcomes** to improve future decisions
3. **Adapt to changes** in model performance

## Thompson Sampling

The default selection strategy. Bayesian approach that balances exploration and exploitation.

### How It Works

1. Each model (arm) has a **Beta distribution** of success
2. Sample from each distribution to get expected reward
3. Select model with highest sampled reward
4. Update distribution based on actual outcome

```python
from convergence.plugins.mab import ThompsonSamplingStrategy, ThompsonSamplingConfig

strategy = ThompsonSamplingStrategy(
    config=ThompsonSamplingConfig(
        alpha_prior=1.0,  # Initial success count
        beta_prior=1.0,   # Initial failure count
    )
)

# Select best arm
selected = strategy.select_arm(
    arms=["gpt-4", "gpt-3.5-turbo", "claude-3"],
    context={"task_type": "code"},
)

# Update with reward (0-1)
strategy.update(selected, reward=0.9, context={"task_type": "code"})
```

### Why Thompson Sampling?

| Approach | Pros | Cons |
|----------|------|------|
| Random | Simple | No learning |
| Epsilon-Greedy | Simple | Fixed exploration |
| UCB | Deterministic | Complex tuning |
| **Thompson Sampling** | Adaptive exploration | Slightly more compute |

## Regret

Regret measures how much worse we perform vs always picking the best arm.

```
Cumulative Regret = Σ (optimal_reward - actual_reward)
```

### Interpretation

- **Decreasing average regret**: Agent is learning
- **Flat regret**: Agent has converged
- **Increasing regret**: Something is wrong

```python
from convergence.observability import NativeObserver

observer = NativeObserver()

# Track after each decision
observer.track_regret(optimal_reward=1.0, actual_reward=0.8)

# Monitor trend
avg_regret = observer.get_average_regret(window=100)
```

## Arm Statistics

Each arm tracks:

```python
stats = strategy.arm_stats["gpt-4"]
# {
#   "successes": 45,
#   "failures": 5,
#   "mean": 0.9,
#   "variance": 0.008,
#   "pulls": 50,
# }
```

## Persistence

State survives restarts:

```python
from convergence.plugins.mab import ThompsonPersistence
from convergence.storage import SQLiteStorage

storage = SQLiteStorage(db_path="./mab_state.db")
persistence = ThompsonPersistence(storage)

# Save state
await persistence.save(strategy, key="my_agent")

# Load state (on restart)
await persistence.load(strategy, key="my_agent")
```

## Experimental Methods

Advanced learning methods for specific use cases.

### RLP (Reinforcement Learning from Prompts)

Learn to generate better prompts based on outcomes.

**Requirements:**
- 500+ interactions minimum
- Clear reward signal

**When to use:**
- Prompt engineering at scale
- When human feedback is available

```python
from convergence.plugins.learning import RLPMixin

# Entropy monitoring
entropy = agent.compute_policy_entropy(policy)
if entropy < 0.5:
    print("Warning: Policy is collapsing")

# KL divergence constraint
if agent.is_kl_constraint_violated(old_policy, new_policy, threshold=0.1):
    print("Warning: Policy changed too much")
```

### SAO (Self-Alignment Optimization)

Generate synthetic training data from successful interactions.

**Requirements:**
- 1000+ interactions minimum
- High-quality seed examples

**When to use:**
- Fine-tuning without human labeling
- Domain adaptation

```python
from convergence.plugins.learning import SAOMixin

# Establish baseline
agent.establish_distribution_baseline()

# Detect drift
shift = agent.detect_distribution_shift()
if shift["shift_detected"]:
    print(f"Distribution shift detected: {shift['shift_magnitude']:.2f}")
```

## Convergence Indicators

How to know if learning is working:

| Indicator | Healthy | Warning |
|-----------|---------|---------|
| Regret trend | Decreasing | Flat/Increasing |
| Selection entropy | Decreasing | Spiking |
| Arm pulls | Concentrated | Uniform |
| Confidence accuracy | ECE < 0.1 | ECE > 0.15 |

## Configuration

### Exploration Rate

Higher = more exploration, slower convergence
Lower = less exploration, faster convergence but may miss better arms

```python
strategy = ThompsonSamplingStrategy(
    config=ThompsonSamplingConfig(
        alpha_prior=1.0,   # Start optimistic
        beta_prior=1.0,
    )
)
```

### Context-Aware Selection

Different arms for different contexts:

```python
# Track separately by context
strategy.select_arm(
    arms=["gpt-4", "gpt-3.5"],
    context={"task_type": "code"},
)

strategy.select_arm(
    arms=["gpt-4", "claude-3"],
    context={"task_type": "writing"},
)
```

## Best Practices

1. **Start with Thompson Sampling** — Works out of the box
2. **Monitor regret trend** — Should decrease over time
3. **Persist state** — Don't lose learning on restart
4. **Use clear rewards** — Binary (0/1) or continuous (0-1)
5. **Wait for convergence** — Don't change arms during learning
6. **Use experimental methods carefully** — Require more data
