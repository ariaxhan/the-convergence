# Self-Improving Classifier

Text classifier that evolves its own approach using Thompson Sampling.
Selects between four classification strategies, measures certainty with
confidence extraction, and prints an ASCII convergence chart.

## Modules Demonstrated

- **Runtime MAB** -- four arms: keyword, semantic, hybrid, zero-shot
- **Confidence Extraction** -- measures certainty of each classification
- **MemoryRuntimeStorage** -- in-memory bandit state

## Run

```bash
python app.py
```

No API key required. Classification results are simulated with per-strategy
accuracy profiles.
