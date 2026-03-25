# Vector-Native Optimization — Agent Reference

Patterns for optimizing embedding strategies, similarity search, and cache quality
in production semantic systems. Designed for AI agent implementation.

## Examples

| File | Pattern | Key Concept |
|------|---------|-------------|
| `embedding_strategies.py` | Embedding quality comparison | 4 strategies benchmarked with precision/recall/F1 |
| `similarity_tuning.py` | Threshold calibration | Grid search for F1-optimal similarity threshold |
| `hybrid_search.py` | Semantic + keyword fusion | Weighted blend with fallback and negative filters |
| `cache_quality.py` | Cache effectiveness monitoring | Hit rate, false positives, staleness, cost savings |

## Running

Each file is self-contained and runs independently:

```bash
python embedding_strategies.py
python similarity_tuning.py
python hybrid_search.py
python cache_quality.py
```

## Prerequisites

- `pip install the-convergence`
- No API keys required — all examples use pure-computation embeddings

## Design Principles

- **No external dependencies beyond the-convergence** — uses `math`, `hashlib`, `collections` from stdlib
- **Hash-based embeddings as baseline** — deterministic, reproducible, no network calls
- **Full type annotations** — every function and method is typed
- **Production error handling** — input validation, NaN/Inf guards, graceful fallbacks
- **Async-first** — all cache interactions use `asyncio.run()` in `__main__`
