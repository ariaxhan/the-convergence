# The Convergence

**Initialized**: 2026-03-08
**Tech Stack**: Python 3.11+, asyncio, Pydantic, LiteLLM, aiosqlite
**Status**: Ready

## What This Project Is

Self-evolving agent framework powered by reinforcement learning. Systems that improve themselves through experience - using Thompson Sampling, evolutionary algorithms, and self-improving policy networks (RLP + SAO).

## Structure

```
convergence/           # Main package
  cli/                 # CLI (typer-based)
  core/                # Core optimization loop
  evaluators/          # Metric evaluation
  generator/           # Configuration generation
  optimization/        # MAB, evolution, RL
  plugins/             # Extension system (pluggy)
  runtime/             # Production runtime selection
  storage/             # SQLite, Convex backends
  types/               # Pydantic models
examples/              # Working examples
_meta/                 # KERNEL artifacts
```

## Key Concepts

- **Optimization Loop**: MAB → Evolution → RL Meta → Storage → Repeat
- **Thompson Sampling**: Bayesian exploration/exploitation
- **Evolution**: Genetic algorithms for configuration breeding
- **RLP**: Reinforcement Learning on Policy (think before acting)
- **SAO**: Self-Alignment Optimization (self-generated training)

## Current Focus

Newly initialized - ready for first task.
