# Observability Examples

Metrics, monitoring, calibration, and cost tracking patterns for production systems.

## Examples

| File | What It Shows |
|------|---------------|
| `learning_metrics.py` | Track agent improvement: average reward, selection entropy, exploration ratio |
| `confidence_calibration.py` | Compare predicted confidence to actual outcomes; calculate ECE |
| `drift_detection.py` | Detect and adapt to concept drift when arm rewards change mid-run |
| `cost_tracking.py` | Track API costs, cache hit rates, and savings from caching |

## Key Concepts

- **Learning Curve**: Average reward over time should trend upward as the agent learns. Flat or declining curves indicate problems.
- **Selection Entropy**: High entropy = exploring many arms. Low entropy = exploiting one arm. Should decrease over time.
- **Calibration Error (ECE)**: When the agent says "80% confident," it should be right 80% of the time. ECE measures this gap.
- **Concept Drift**: Real-world reward distributions change. A good system detects this and re-explores.
- **Cache Savings**: Semantic caching reduces API calls. Track hit rates and cost savings to justify cache infrastructure.

## Running

```bash
pip install the-convergence
python learning_metrics.py
python confidence_calibration.py
python drift_detection.py
python cost_tracking.py
```
