# YAML Configuration Examples

Configure Armature optimization runs with YAML files instead of Python code.

## When to Use YAML vs SDK

| Feature | YAML + CLI | SDK |
|---------|-----------|-----|
| Setup | Write .yaml file | Write Python code |
| Execution | `armature optimize config.yaml` | `await run_optimization(config)` |
| Best for | Quick experiments, non-developers | Production integration, custom logic |
| Custom evaluators | dotted path string | Direct callable |
| Test cases | JSON file or inline YAML | List of dicts or iterator |

**Use YAML** when you want fast iteration, sharable configs, or your team isn't Python-native.
**Use SDK** when you need programmatic control, custom logic, or production integration.

## Examples

### basic_optimization.yaml + basic_optimization_run.py

Minimal config: one endpoint, two parameters, single metric. Start here.

```bash
armature optimize basic_optimization.yaml
```

### multi_metric.yaml + multi_metric_run.py

Weighted multi-metric optimization with thresholds and early stopping.

```bash
armature optimize multi_metric.yaml
```

### custom_evaluator.yaml + evaluator.py

Reference a custom Python evaluator function from YAML. The evaluator scores
responses on keyword match, length, and format.

```bash
armature optimize custom_evaluator.yaml
```

## Loading YAML from Python

```python
from armature.optimization.config_loader import ConfigLoader
from armature.optimization.runner import OptimizationRunner

config = ConfigLoader.load("basic_optimization.yaml")
runner = OptimizationRunner(config)
result = await runner.run()
```
