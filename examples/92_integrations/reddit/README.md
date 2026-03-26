# Reddit Integration

A self-evolving Reddit analysis agent powered by Armature.

## What It Does

- Analyzes Reddit content using LLM-powered agents
- Optimizes content analysis quality across runs
- Learns which configurations produce the best analysis results

## Full Implementation

See `examples/agno_agents/reddit/` for the complete code:

- `reddit_agent_runner.py` -- Agent lifecycle and Reddit API integration
- `reddit_evaluator.py` -- Scores analysis quality and completeness

## Quick Start

```bash
# Requires Reddit API credentials
python examples/agno_agents/reddit/reddit_agent_runner.py
```
