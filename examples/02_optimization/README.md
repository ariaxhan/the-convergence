# Optimization Examples

Deep dives into Thompson Sampling, reward evaluation, and convergence behavior.

## Examples

| File | What It Shows |
|------|---------------|
| `thompson_basic.py` | Two-arm Thompson Sampling with Beta distribution evolution |
| `thompson_strategies.py` | Comparing selection strategies: default, exploration-bonus, stability |
| `reward_evaluation.py` | Multi-metric reward evaluation with weighted aggregation |
| `convergence_visualization.py` | ASCII visualization of 4-arm convergence and cumulative regret |

## Key Concepts

- **Thompson Sampling**: Bayesian approach to exploration-exploitation. Sample from each arm's posterior (Beta distribution), pick the highest sample.
- **Beta Distribution**: Parameterized by alpha (successes) and beta (failures). Starts at Beta(1,1) = uniform, concentrates as evidence accumulates.
- **Reward Evaluator**: Aggregates multiple metric signals (quality, speed, cost) into a single reward using weighted sums.
- **Cumulative Regret**: Difference between optimal arm's expected reward and the reward we actually received. Should flatten as the algorithm converges.

## Running

```bash
pip install -e .
python thompson_basic.py
python thompson_strategies.py
python reward_evaluation.py
python convergence_visualization.py
```
