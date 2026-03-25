# 09 - Production Deployment

Production patterns for running Convergence in real systems.

## Examples

| File | What it shows |
|------|---------------|
| `postgresql_setup.py` | PostgreSQL storage config, stability-tuned selection strategy |
| `monitoring_dashboard.py` | Metrics export for Prometheus/Grafana: pulls, rewards, regret, CIs |
| `ab_testing.py` | A/B testing with statistical significance (z-test) |
| `gradual_rollout.py` | Canary deployment with phased exploration reduction |

## Running

All examples use `MemoryRuntimeStorage` so they run without external dependencies.
Comments show the production equivalents (PostgreSQL, Prometheus, etc.).

```bash
pip install the-convergence
python postgresql_setup.py
python monitoring_dashboard.py
python ab_testing.py
python gradual_rollout.py
```

## Production Checklist

1. **Storage** -- Use `PostgreSQLRuntimeStorage` or `SQLiteRuntimeStorage` for persistence
2. **Monitoring** -- Export arm pulls, rewards, and regret to your metrics system
3. **Stability** -- Configure `SelectionStrategyConfig` to avoid unnecessary arm switches
4. **Rollouts** -- Use phased exploration to safely introduce new arms
