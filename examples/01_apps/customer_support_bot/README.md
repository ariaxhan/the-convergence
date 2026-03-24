# Customer Support Bot

Self-evolving customer support bot that learns which response strategy works
best per question type. Uses Thompson Sampling to select between formal,
casual, and technical tones. Caches frequent questions with SemanticCache.
Flags low-confidence queries for human escalation.

## Modules Demonstrated

- **Runtime MAB** -- online Thompson Sampling to pick response tone
- **SemanticCache** -- deduplicates repeated FAQ queries
- **Confidence Extraction** -- detects uncertain responses for escalation

## Run

```bash
python app.py
```

No API key required. All LLM responses are simulated.
