# The Convergence

**AI agents that get better every time they run.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.8-orange.svg)](pyproject.toml)

---

Most AI systems are frozen at deployment. You ship a prompt, pick some parameters, and hope they hold up. When the world changes — new user behavior, new data, new requirements — you retune by hand and redeploy.

The Convergence eliminates that cycle. It wraps your AI agent in a **reinforcement learning loop** that continuously learns what works, drops what doesn't, and adapts in real time. No retraining. No redeployment. The system evolves on its own.

---

## What Makes It Different

| | Traditional AI Systems | The Convergence |
|---|---|---|
| **Learning** | Static after deployment | Learns from every interaction |
| **Optimization** | Manual tuning, A/B tests | Automatic via Thompson Sampling |
| **Adaptation** | Redeploy to change behavior | Evolves continuously in production |
| **Safety** | Prompt-level (bypassable) | Framework-level (enforced outside the model) |
| **Observability** | Logs and hope | Built-in metrics, drift detection, calibration tracking |

---

## Use Cases

**Customer support agent** — Your support bot handles thousands of conversations. The Convergence learns which response style (concise vs. detailed, formal vs. casual) gets the best outcomes for each type of question. Resolution rates improve automatically.

**Content generation pipeline** — You generate marketing copy, product descriptions, or reports. The system learns which model parameters produce content that passes your quality bar, and evolves toward better configurations over time.

**Multi-model routing** — You have access to GPT-4, Claude, Gemini, and open-source models. Instead of picking one, the system learns which model performs best for which task — and shifts traffic intelligently as models update.

**Internal knowledge agent** — Your company knowledge lives in Slack, GitHub, Jira, and Google Drive. The Convergence's context graph connects it all, and the agent learns which retrieval paths actually answer questions accurately.

**Autonomous web agents** — Agents that browse, extract, and act on web data. The system learns which interaction patterns succeed and evolves its approach across sessions.

---

## How It Works

The core is a **learning loop** inspired by how slot machines are studied in mathematics (multi-armed bandits):

1. **Your agent has multiple "arms"** — different configurations, prompts, models, or strategies it could use
2. **For each request, the system picks an arm** — balancing exploration (trying new things) with exploitation (using what works)
3. **You report the outcome** — did it work? How well?
4. **The system updates its beliefs** — arms that work get selected more often; arms that don't, less

This isn't random experimentation. It's **Thompson Sampling** — a mathematically principled algorithm that converges on the best option in 15-30 interactions, while never completely abandoning exploration.

On top of this foundation:

- **Evolutionary algorithms** breed new configurations by combining the best traits of top performers
- **Semantic caching** recognizes when a similar question has already been answered, cutting API costs by 70-80%
- **RLP (Reinforced Learned Policy)** teaches the agent to reason before acting, after enough interactions accumulate
- **SAO (Self-Alignment Optimization)** lets the agent generate its own training data from successful episodes

The system starts simple and unlocks more sophisticated capabilities as it gathers experience.

---

## Integrations

The Convergence is designed to wrap around your existing stack, not replace it.

| Category | Supported |
|---|---|
| **LLM Providers** | OpenAI, Anthropic Claude, Google Gemini, Azure OpenAI, Groq, any LiteLLM-compatible provider |
| **Agent Frameworks** | Agno, LangGraph — extend with custom adapters |
| **Platforms** | Discord, Gmail, Reddit (pre-built examples), any API via adapters |
| **Web Automation** | Browserbase for autonomous web browsing agents |
| **Storage** | SQLite (dev), PostgreSQL (prod), Redis (caching), in-memory |
| **Observability** | Weights & Biases Weave for metrics and tracing |

---

## Quick Start

```bash
pip install the-convergence
```

```python
import asyncio
from convergence import configure_runtime, runtime_select, runtime_update

async def main():
    # Define the options your agent can choose between
    await configure_runtime("support_agent", config={
        "arms": [
            {"arm_id": "concise", "params": {"temperature": 0.3, "max_tokens": 500}},
            {"arm_id": "detailed", "params": {"temperature": 0.7, "max_tokens": 2000}},
        ],
        "storage": {"backend": "sqlite", "path": "convergence.db"}
    })

    # The system picks the best option for this request
    selection = await runtime_select("support_agent", user_id="user_123")

    # Use selection.params in your LLM call
    # response = await your_llm_call(**selection.params)

    # Tell the system how it went (1.0 = success, 0.0 = failure)
    await runtime_update(
        "support_agent",
        decision_id=selection.decision_id,
        reward=1.0
    )

asyncio.run(main())
```

Three functions. That's the entire API surface. Everything else — the learning algorithms, storage, exploration/exploitation tradeoffs — is handled for you.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│              THE CONVERGENCE                      │
├──────────────────────────────────────────────────┤
│                                                   │
│  OPTIMIZATION          The learning engine        │
│  Thompson Sampling, evolutionary algorithms,      │
│  semantic caching, confidence extraction          │
│                                                   │
│  KNOWLEDGE             Structured context         │
│  Context graph, relationship traversal,           │
│  progressive disclosure, mergeable graphs         │
│                                                   │
│  SAFETY                Framework-enforced         │
│  Input validation, execution control,             │
│  output validation, full audit trail              │
│                                                   │
│  OBSERVABILITY         Built-in metrics           │
│  Learning curves, calibration, cost tracking,     │
│  drift detection                                  │
│                                                   │
│  STORAGE               Pluggable backends         │
│  SQLite / PostgreSQL / Redis / Memory             │
│                                                   │
└──────────────────────────────────────────────────┘
```

Safety checks happen at the **framework level**, not the prompt level. The model can't be prompted to bypass them because they're enforced outside the model's control.

---

## Current Status

| Component | Status |
|---|---|
| Thompson Sampling | **Production** — converges in 15-30 interactions |
| Storage Backends | **Production** — SQLite, PostgreSQL, Memory |
| Semantic Caching | **Production** — 70-80% cost reduction |
| Confidence Extraction | **Production** — gap detection for human escalation |
| Context Graph | Beta |
| Safety Guardrails | Beta |
| Observability | Beta |
| RLP (Think First) | Experimental — needs 500+ interactions |
| SAO (Self-Training) | Experimental — needs 1000+ interactions |

---

## Documentation

- **[Getting Started](GETTING_STARTED.md)** — Full setup guide
- **[API Reference](docs/API.md)** — Detailed function documentation
- **[Configuration](YAML_CONFIGURATION_REFERENCE.md)** — All config options
- **[Examples](examples/)** — Working code: Discord, Gmail, Reddit, web automation, multi-model

---

## Research Foundation

Built on peer-reviewed work: [Thompson Sampling](https://en.wikipedia.org/wiki/Thompson_sampling) (Bayesian exploration), [RLP](https://arxiv.org/abs/2510.01265) (NVIDIA, 2024), [SAO](https://arxiv.org/abs/2510.06652) (Hugging Face, 2024), [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) (NVIDIA), [Guardrails AI](https://github.com/guardrails-ai/guardrails).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We especially welcome integration examples, safety audit findings, and documentation improvements.

**License:** Apache 2.0

---

<p align="center"><em>Stop tuning. Start evolving.</em></p>
