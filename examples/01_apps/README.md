# 01_apps: End-to-End Sample Applications

Three self-contained applications demonstrating multiple Convergence modules
working together in realistic scenarios. All run locally without API keys.

## Applications

| App | Modules Used | What It Shows |
|-----|-------------|---------------|
| [customer_support_bot](customer_support_bot/) | Runtime MAB, SemanticCache, Confidence | Thompson Sampling selects response tone; cache handles FAQ; low-confidence triggers escalation |
| [research_assistant](research_assistant/) | Runtime MAB, ContextGraph, Knowledge Schema | Builds a knowledge graph while optimizing search strategy selection |
| [self_improving_classifier](self_improving_classifier/) | Runtime MAB, Confidence Extraction | Evolves classification strategy over 40 texts; tracks accuracy convergence with ASCII chart |

## Running

```bash
# From the repo root (ensure convergence is installed or on PYTHONPATH)
python examples/01_apps/customer_support_bot/app.py
python examples/01_apps/research_assistant/app.py
python examples/01_apps/self_improving_classifier/app.py
```

Each app prints its learning progress to stdout so you can watch the bandit
converge in real time.
