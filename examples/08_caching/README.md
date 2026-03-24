# 08 - Advanced Caching

Beyond basic get/set -- persistence, analytics, invalidation, and embedding strategies.

## Examples

| File | Concept | Key takeaway |
|------|---------|--------------|
| `sqlite_cache.py` | Persistent caching | Cache survives restarts via SQLite backend |
| `cache_analytics.py` | Performance tracking | Measure hit rates and estimate cost savings |
| `cache_invalidation.py` | TTL and manual expiry | Entries auto-expire; clear() for manual reset |
| `embedding_comparison.py` | Embedding strategies | Embedding quality directly controls cache effectiveness |

## Prerequisites

```bash
pip install the-convergence
```

No API keys required. All examples use local embedding functions.

## Quick start

```bash
# Run any example directly
python sqlite_cache.py
python cache_analytics.py
python cache_invalidation.py
python embedding_comparison.py
```

## Key concepts

- **Semantic caching** matches queries by meaning, not exact string match
- **Threshold tuning** controls the tradeoff between cache hits and accuracy
- **Backend choice** determines persistence, speed, and scalability
- **Embedding quality** is the single biggest factor in cache effectiveness
