# The Convergence Cookbook

Runnable examples for self-evolving AI agents. Copy. Paste. Run.

## Where to Start

- **New to Convergence?** Start with [`00_quickstart/`](00_quickstart/) — 10 progressive examples, each adding one concept
- **Want real applications?** Jump to [`01_apps/`](01_apps/) — 3 production-realistic sample apps
- **Looking for a specific module?** Browse by topic below

## By Topic

### Core Concepts (start here)
| Directory | What You'll Learn |
|-----------|------------------|
| [`00_quickstart/`](00_quickstart/) | Progressive introduction: runtime, confidence, caching, Thompson Sampling, knowledge graphs |
| [`01_apps/`](01_apps/) | End-to-end apps: support bot, research assistant, self-improving classifier |

### Deep Dives
| Directory | What You'll Learn |
|-----------|------------------|
| [`02_optimization/`](02_optimization/) | Thompson Sampling, MAB strategies, convergence visualization, parameter evolution |
| [`03_knowledge/`](03_knowledge/) | Context graphs, WHO/WHAT/HOW triad, graph traversal, progressive disclosure |
| [`04_safety/`](04_safety/) | Input validation, output guardrails, budget limits, PII detection |
| [`05_observability/`](05_observability/) | Learning metrics, confidence calibration, drift detection, cost tracking |

### Agent Patterns (production-grade, enterprise-ready)
| Directory | What You'll Learn |
|-----------|------------------|
| [`10_agent_patterns/`](10_agent_patterns/) | Production runtime, secure client, resilient cache, observable pipeline, safe evolution |
| [`11_vector_native/`](11_vector_native/) | Embedding strategies, similarity tuning, hybrid search, cache quality monitoring |

> **AI Agents:** Start with [`AGENT.md`](../AGENT.md) for the complete implementation reference, then use these patterns.

### Integrations
| Directory | What You'll Learn |
|-----------|------------------|
| [`90_models/`](90_models/) | Claude, OpenAI, Groq, Azure, local models (Ollama) |
| [`91_tools/`](91_tools/) | Custom tool implementations |
| [`92_integrations/`](92_integrations/) | Discord, Gmail, Reddit, Browserbase |
| [`93_testing/`](93_testing/) | Test cases, evaluation patterns |

## Quick Start

```bash
pip install the-convergence
cd examples/00_quickstart
python 01_basic_runtime.py
```

## Contributing

See [STYLE_GUIDE.md](STYLE_GUIDE.md) for the example template all contributions must follow.
