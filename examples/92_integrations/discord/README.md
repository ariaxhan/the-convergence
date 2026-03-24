# Discord Integration

A self-evolving Discord bot powered by Convergence.

## What It Does

- Responds to messages in Discord servers using LLM-powered agents
- Optimizes response quality, latency, and token efficiency across runs
- Uses evolutionary search to find the best model + temperature + instruction style

## Full Implementation

See `examples/agno_agents/discord/` for the complete code:

- `discord_agent_runner.py` -- Agent lifecycle and Discord API integration
- `discord_evaluator.py` -- Scores responses on accuracy, completeness, latency
- `discord_programmatic_example.py` -- Standalone optimization demo

## Quick Start

```bash
export DISCORD_BOT_TOKEN=your-token
export AZURE_API_KEY=your-key
python examples/agno_agents/discord/discord_programmatic_example.py
```
