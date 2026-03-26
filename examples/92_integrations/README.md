# External Service Integrations

Integration with external services. Each subdirectory documents a
self-evolving agent that uses Armature to optimize its behavior
over time.

The full implementation code lives in `examples/agno_agents/`. These
READMEs explain what each integration does and point you to the
working code.

## Integrations

| Service | Agent Location | What It Does |
|---------|---------------|--------------|
| Discord | `agno_agents/discord/` | Bot that optimizes response quality in Discord servers |
| Gmail | `agno_agents/gmail/` | Email assistant that learns from interaction patterns |
| Reddit | `agno_agents/reddit/` | Agent that optimizes content analysis on Reddit |
| BrowserBase | `web_browsing/browserbase/` | Web scraping agent that optimizes browser configs |

## Architecture

Each integration follows the same pattern:

1. **Agent Runner** -- orchestrates the agent lifecycle
2. **Evaluator** -- scores agent performance on service-specific metrics
3. **Test Cases** -- JSON files defining expected behaviors
4. **Armature Config** -- search space and optimization parameters

The agent runner calls the external service, the evaluator scores results,
and Armature optimizes the configuration across runs.

## Getting Started

Pick an integration, read its README, then look at the corresponding
code in `agno_agents/` or `web_browsing/`.
