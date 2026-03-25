# The Convergence

**AI agents that get better every time they run.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/the-convergence.svg)](https://pypi.org/project/the-convergence/)

---

You deploy an AI agent. It works okay. Then you spend weeks tweaking prompts, swapping models, adjusting temperatures — hoping something sticks. When user behavior shifts, you do it all over again.

The Convergence wraps your agent in a **reinforcement learning loop**. The system learns what works, drops what doesn't, and adapts in real time. No retraining. No redeployment. Your agent evolves on its own.

## The API

Three functions. That's it.

```python
import asyncio
from convergence import configure_runtime, runtime_select, runtime_update

async def main():
    # Define the strategies your agent can choose between
    await configure_runtime("my_agent", config={
        "arms": [
            {"arm_id": "concise", "params": {"temperature": 0.3, "max_tokens": 500}},
            {"arm_id": "detailed", "params": {"temperature": 0.7, "max_tokens": 2000}},
            {"arm_id": "creative", "params": {"temperature": 0.9, "max_tokens": 1500}},
        ],
        "storage": {"backend": "sqlite", "path": "convergence.db"}
    })

    # System picks the best strategy using Thompson Sampling
    selection = await runtime_select("my_agent", user_id="user_123")

    # Use selection.params in your LLM call
    response = await your_llm_call(**selection.params)

    # Tell the system how it went (0.0 = bad, 1.0 = good)
    await runtime_update(
        "my_agent",
        decision_id=selection.decision_id,
        reward=1.0
    )

asyncio.run(main())
```

Everything else — learning algorithms, exploration/exploitation tradeoffs, storage, convergence tracking — is handled for you.

---

## Use Cases

### Research agent optimization

You have an agent that runs parallel research tasks — verifying claims, cross-referencing sources, scoring confidence. Different research strategies work better for different domains. The Convergence learns that deep-dive verification works for neuroscience claims while rapid cross-referencing is better for psychology replication studies. Your research agent routes to the right strategy automatically.

### Customer support routing

Your support bot handles thousands of conversations. Some users want concise answers, others want detailed walkthroughs. Instead of one-size-fits-all, the system learns which response style resolves issues fastest for each question type. Resolution rates improve without anyone touching the prompts.

### Multi-model routing

You have access to GPT-4, Claude, Gemini, and open-source models. Each excels at different tasks. Instead of picking one or building manual routing rules, Thompson Sampling learns which model performs best for which task type — and shifts traffic as models update.

### Content generation pipelines

You generate reports, summaries, or scripts from data. The system learns which model parameters, prompt structures, and output formats produce content that passes your quality bar. Configurations that work get selected more; configurations that don't get dropped.

### Knowledge retrieval

Your agent pulls from multiple data sources — databases, APIs, documents. Different retrieval paths work better for different query types. The Convergence learns which retrieval strategy actually answers questions accurately, cutting wasted API calls and improving hit rates.

### Self-improving classifiers

You classify text, images, or data with an LLM. The system learns which prompt/model combinations produce the most accurate classifications for each category, and evolves toward better accuracy over time without retraining.

---

## How It Works

The core is **Thompson Sampling** — a Bayesian algorithm for the multi-armed bandit problem:

1. **Your agent has "arms"** — different configurations, prompts, models, or strategies
2. **For each request, the system picks an arm** — balancing exploration (trying new things) with exploitation (using what works)
3. **You report the outcome** — a reward signal from 0 to 1
4. **The system updates its beliefs** — Bayesian updates shift probability toward what works

This converges on the best option in 15-30 interactions while never fully abandoning exploration (in case conditions change).

On top of this:

- **Evolutionary algorithms** breed new configurations by combining traits of top performers
- **Semantic caching** recognizes similar requests and reuses results, cutting API costs 70-80%
- **Confidence extraction** detects hedging language and uncertainty in LLM outputs
- **RLP (Reinforced Learned Policy)** teaches the agent to reason before acting, after enough data accumulates
- **SAO (Self-Alignment Optimization)** generates training data from successful episodes for self-improvement

The system starts simple (Thompson Sampling only) and progressively unlocks more sophisticated learning as interaction data accumulates.

---

## Install

```bash
pip install the-convergence
```

Or from source:

```bash
git clone https://github.com/ariaxhan/the-convergence.git
cd the-convergence
pip install -e ".[dev]"
```

### Try the examples

```bash
cd examples/00_quickstart
python 02_confidence_extraction.py  # No API key needed
python 06_thompson_sampling_loop.py  # Watch Thompson Sampling converge
```

See the full **[Cookbook](examples/)** for 40+ runnable examples.

---

## What's Inside

| Component | Status | What it does |
|---|---|---|
| **Thompson Sampling** | Production | Bayesian arm selection, converges in 15-30 pulls |
| **Evolutionary Engine** | Production | Breeds new configs from top performers |
| **Storage Backends** | Production | SQLite, PostgreSQL, Redis, in-memory |
| **Semantic Caching** | Production | Embedding-based dedup, 70-80% cost reduction |
| **Confidence Extraction** | Production | Detects hedging, certainty, and calibration gaps |
| **Context Graph** | Beta | Knowledge graph with relationship traversal |
| **Safety Guardrails** | Beta | Framework-level input/output validation |
| **Observability** | Beta | Learning curves, drift detection, cost tracking |
| **RLP** | Experimental | Think-before-acting policy (needs 500+ interactions) |
| **SAO** | Experimental | Self-generated training data (needs 1000+ interactions) |

### Integrations

| Category | Supported |
|---|---|
| **LLM Providers** | OpenAI, Anthropic Claude, Google Gemini, Azure OpenAI, Groq, any LiteLLM-compatible provider |
| **Agent Frameworks** | Agno, LangGraph, or extend with custom adapters |
| **Storage** | SQLite (dev), PostgreSQL (prod), Redis (caching), in-memory |
| **Observability** | Weights & Biases Weave |

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│              THE CONVERGENCE                      │
├──────────────────────────────────────────────────┤
│                                                   │
│  OPTIMIZATION       Learning engine               │
│  Thompson Sampling, evolutionary algorithms,      │
│  semantic caching, confidence extraction          │
│                                                   │
│  KNOWLEDGE          Structured context            │
│  Context graph, relationship traversal,           │
│  progressive disclosure, mergeable graphs         │
│                                                   │
│  SAFETY             Framework-enforced            │
│  Input validation, execution control,             │
│  output validation, full audit trail              │
│                                                   │
│  OBSERVABILITY      Built-in metrics              │
│  Learning curves, calibration, cost tracking,     │
│  drift detection                                  │
│                                                   │
│  STORAGE            Pluggable backends            │
│  SQLite / PostgreSQL / Redis / Memory             │
│                                                   │
└──────────────────────────────────────────────────┘
```

Safety checks run at the **framework level**, not inside prompts. The model can't be prompted to bypass them.

---

## Research Foundation

Built on peer-reviewed work:

- [Thompson Sampling](https://en.wikipedia.org/wiki/Thompson_sampling) — Bayesian exploration/exploitation
- [RLP](https://arxiv.org/abs/2510.01265) — Reinforced Learned Policy (NVIDIA, 2024)
- [SAO](https://arxiv.org/abs/2510.06652) — Self-Alignment Optimization (Hugging Face, 2024)
- [NeMo Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) — Framework-level safety (NVIDIA)

---

## Documentation

- **[Getting Started](GETTING_STARTED.md)** — Full setup guide
- **[API Reference](docs/API.md)** — Function documentation
- **[Configuration](YAML_CONFIGURATION_REFERENCE.md)** — All config options
- **[Examples](examples/)** — 40+ working examples
- **[Changelog](CHANGELOG.md)** — Release history

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

We especially welcome: integration examples, new storage backends, safety audit findings, and documentation improvements.

---

## Credits

The Convergence was originally built at [Persistos](https://github.com/persist-os) by **Aria Han**, **Shreyash Hamal**, and **Myat Pyae Paing**. The original work (v0.1.x) included the optimization engine, SDK interface, evaluators, natural language processor, Agno adapters, Convex storage backend, Weave integration, and CLI.

The 1.0 release and all subsequent development is by **Aria Han**: Thompson Sampling persistence, context graph, knowledge layer, semantic caching, safety guardrails, RLP/SAO plugins, 40+ examples cookbook, and the architecture rewrite from API optimization tool to self-evolving agent framework.

## License

MIT — see [LICENSE](LICENSE).

---

*Stop tuning. Start evolving.*
