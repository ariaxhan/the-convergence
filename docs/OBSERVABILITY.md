# Observability

Watch the learning process, not just outputs.

## Overview

The Convergence provides native observability for:

- **Learning Metrics**: Regret, arm distribution, convergence
- **Calibration**: Is 80% confidence actually 80% correct?
- **Costs**: Per-request, per-model, per-session
- **Cache**: Hit rate, false positives

## Quick Setup

```python
from convergence import ConvergenceAgent
from convergence.observability import NativeObserver

observer = NativeObserver()

agent = ConvergenceAgent(
    models=["gpt-4", "gpt-3.5-turbo"],
    observer=observer,
)

# Make requests...

# Export metrics
print(observer.export_json())
```

## Metrics

### Counter

Monotonically increasing values.

```python
counter = observer.counter("requests_total", "Total requests")
counter.inc()           # +1
counter.inc(5)          # +5

# With labels
counter.labels(model="gpt-4", status="success").inc()
```

### Gauge

Values that go up and down.

```python
gauge = observer.gauge("active_sessions", "Active sessions")
gauge.set(10)
gauge.inc()             # +1
gauge.dec(3)            # -3
```

### Histogram

Distribution of values (latency, costs).

```python
histogram = observer.histogram(
    "request_duration",
    "Request duration in seconds",
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0],
)

histogram.observe(0.35)
histogram.observe(1.2)

# Percentiles
p50 = histogram.percentile(50)
p99 = histogram.percentile(99)
```

## Learning Metrics

### Regret Tracking

Cumulative regret measures how much worse the agent performed vs optimal.

```python
# After each decision
observer.track_regret(
    optimal_reward=1.0,    # Best possible
    actual_reward=0.8,     # What we got
)

# Query
total_regret = observer.get_cumulative_regret()
avg_regret = observer.get_average_regret(window=100)  # Last 100

# Regret should decrease over time as agent learns
```

### Arm Distribution

Which models are being selected?

```python
observer.track_arm_selection("gpt-4")
observer.track_arm_selection("gpt-4")
observer.track_arm_selection("gpt-3.5-turbo")

distribution = observer.get_arm_distribution()
# {"gpt-4": 2, "gpt-3.5-turbo": 1}

# Entropy (0 = converged, high = exploring)
entropy = observer.get_selection_entropy()
```

### Calibration

Are confidence scores accurate?

```python
# Track predictions
observer.track_prediction(confidence=0.8, actual_success=True)
observer.track_prediction(confidence=0.8, actual_success=True)
observer.track_prediction(confidence=0.8, actual_success=False)

# Expected Calibration Error (lower = better)
ece = observer.get_calibration_error()
# If 80% confidence predictions succeed 80% of the time, ECE ≈ 0
```

## Cost Tracking

```python
observer.track_cost(0.05, model="gpt-4")
observer.track_cost(0.01, model="gpt-3.5-turbo")

# Total
total = observer.get_total_cost()  # $0.06

# By model
by_model = observer.get_cost_by_model()
# {"gpt-4": 0.05, "gpt-3.5-turbo": 0.01}
```

## Cache Metrics

```python
observer.track_cache_access(hit=True)
observer.track_cache_access(hit=False)

hit_rate = observer.get_cache_hit_rate()  # 0.5 (50%)
```

## Episode Tracking

Group related operations into episodes.

```python
observer.start_episode()

# ... make decisions, track metrics ...

observer.end_episode(total_reward=0.85)

# Query episodes
episodes = observer.get_episodes()
```

## Export

### JSON

```python
json_str = observer.export_json()
# {
#   "metrics": [...],
#   "summary": {
#     "total_cost": 0.06,
#     "cumulative_regret": 0.35,
#     "cache_hit_rate": 0.72
#   }
# }
```

### Prometheus (Coming Soon)

```python
# Export in Prometheus format
prometheus_str = observer.export_prometheus()
```

## Weave Integration

Optional integration with Weights & Biases Weave.

```python
pip install convergence[observability]
```

```python
from convergence.observability import WeaveObserver

observer = WeaveObserver()  # Auto-syncs to Weave dashboard
```

## Dashboards

### Key Metrics to Monitor

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Cumulative Regret | Decreasing | Flat | Increasing |
| Cache Hit Rate | >70% | 50-70% | <50% |
| Calibration Error | <0.05 | 0.05-0.15 | >0.15 |
| Selection Entropy | Decreasing | Stable | Spiking |

### Alerts

```python
# Example: Alert on regret increase
current_regret = observer.get_average_regret(window=100)
previous_regret = observer.get_average_regret(window=100, offset=100)

if current_regret > previous_regret * 1.5:
    alert("Regret increasing - agent may be degrading")
```

## Best Practices

1. **Track regret over time** — Should decrease as agent learns
2. **Monitor calibration** — Recalibrate if ECE exceeds 0.1
3. **Watch cache hit rate** — Tune threshold if too low
4. **Set up alerts** — Catch degradation early
5. **Export regularly** — Don't lose metrics on restart
