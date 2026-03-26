# Gmail Integration

A self-evolving email assistant powered by Armature.

## What It Does

- Processes and responds to Gmail messages using LLM-powered agents
- Optimizes email response quality and relevance across runs
- Learns which configurations produce the best email interactions

## Full Implementation

See `examples/agno_agents/gmail/` for the complete code:

- `gmail_agent_runner.py` -- Agent lifecycle and Gmail API integration
- `gmail_evaluator.py` -- Scores responses on quality and appropriateness

## Quick Start

```bash
# Requires Gmail API credentials (OAuth2)
python examples/agno_agents/gmail/gmail_agent_runner.py
```
