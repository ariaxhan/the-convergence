# Quickstart Examples

Progressive examples for The Convergence framework, from basic building blocks
to a full self-evolving system.

## Prerequisites

```bash
pip install the-convergence
```

Some examples require additional dependencies:
- `03_claude_client.py` requires `pip install anthropic` and `ANTHROPIC_API_KEY`

## Examples

| # | File | What You Learn | Deps |
|---|------|---------------|------|
| 01 | `01_basic_runtime.py` | Runtime MAB selection with Thompson Sampling | None |
| 02 | `02_confidence_extraction.py` | Extract confidence scores from text | None |
| 03 | `03_claude_client.py` | ClaudeClient with confidence and gap detection | anthropic |
| 04 | `04_semantic_cache.py` | Semantic caching with similarity matching | None |
| 05 | `05_runtime_with_storage.py` | Persistent runtime with SQLite-backed storage | None |
| 06 | `06_thompson_sampling_loop.py` | Watch Thompson Sampling converge over 50 rounds | None |
| 07 | `07_knowledge_graph.py` | Build and traverse a context graph | None |
| 08 | `08_reward_evaluation.py` | Multi-signal reward evaluation | None |
| 09 | `09_optimization_local.py` | SDK optimization with a local function | None |
| 10 | `10_full_loop.py` | All pieces combined: the convergence moment | None |

## Progression

**Phase 1: Building Blocks (01-04)**
Individual components in isolation. Each runs standalone with no external services.

**Phase 2: Learning Loops (05-08)**
Components that learn from feedback. Persistence, convergence, knowledge, rewards.

**Phase 3: Full Systems (09-10)**
Complete optimization and the full convergence loop tying everything together.

## Running

Each example is self-contained:

```bash
python examples/00_quickstart/01_basic_runtime.py
```

All async examples use `asyncio.run()` and work directly from the command line.
