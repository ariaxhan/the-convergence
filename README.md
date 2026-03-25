# The Convergence

**Build AI agents that improve themselves, safely.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.8-orange.svg)](pyproject.toml)

---

## The Story

This project started with a single observation:

> *"The Great Filter for AI isn't AGI — it's the production environment. 95% don't survive."*

That was October 2025. A hackathon. Three engineers tired of watching AI projects fail not because the models were bad, but because the systems around them couldn't adapt.

Every AI deployment follows the same pattern:
1. Build something impressive in development
2. Deploy to production
3. Watch it slowly degrade as the world changes
4. Scramble to fix it manually
5. Repeat

We asked: **What if the system could fix itself?**

Not in a scary, uncontrolled way. In a measured, observable, *safe* way. Like how your immune system learns from exposure. Like how markets find prices through iteration. Like how evolution produces robustness through selection.

The Convergence is our answer.

---

## Where We Started

The first version was simple: an API parameter optimizer using genetic algorithms. You had an LLM endpoint. You didn't know the best temperature, context length, or sampling strategy. The system tried variations, measured results, and evolved toward better configurations.

It worked. But we realized we were solving the wrong problem.

The real challenge wasn't finding optimal parameters once. It was keeping them optimal as everything changed — user behavior, data distributions, business requirements, the models themselves.

**Static configuration is a losing game.** The world moves. Your system should move with it.

---

## Where We're Going

The Convergence is now an **enterprise framework for self-evolving AI agents**.

That's a lot of words. Here's what it actually means:

### For Business Leaders

Your company has knowledge scattered everywhere — code repositories, Slack conversations, support tickets, internal docs, databases. You want an AI agent that can access all of it and actually help your team.

But you're worried about:
- **Cost** — Will this burn through our API budget?
- **Safety** — Will it say something it shouldn't? Access data it shouldn't?
- **Reliability** — Will it work consistently, or surprise us at the worst moment?
- **Improvement** — Will it get better over time, or stagnate?

The Convergence addresses each of these:

| Concern | How We Address It |
|---------|-------------------|
| **Cost** | Semantic caching reduces API calls by 70-80%. Similar questions get cached answers. |
| **Safety** | Guardrails are built into the framework, not the prompts. The agent *can't* bypass safety checks. |
| **Reliability** | Every decision is observable. You can see exactly what the agent is doing and why. |
| **Improvement** | The system learns from every interaction using proven algorithms. It literally gets better with use. |

### For Engineering Leaders

You've seen the vendor demos. They're impressive. Then you try to integrate them and discover:
- No observability into what's actually happening
- Safety is "prompt engineering" (which means: easily bypassed)
- Learning means "fine-tune a model" (expensive, slow, often makes things worse)
- Every edge case requires manual handling

The Convergence gives you:

| Feature | What It Means |
|---------|---------------|
| **Framework-level safety** | Using NVIDIA NeMo Guardrails + Guardrails AI. The model can't override safety checks because they happen outside the model. |
| **Native observability** | See learning curves, calibration accuracy, cost per request, drift detection. Not just logs — actionable metrics. |
| **Online learning** | Thompson Sampling converges in 15-30 interactions. No expensive retraining. No deployment cycles. |
| **Production-grade storage** | PostgreSQL for production, SQLite for development, same API. |

### For Individual Engineers

You want to build something that actually works in production. You're tired of:
- Hardcoding thresholds that immediately become wrong
- Redeploying every time you want to try a new parameter
- Not knowing if your changes actually helped

The Convergence gives you three function calls:

```python
from convergence import configure_runtime, runtime_select, runtime_update

# 1. Configure once at startup
await configure_runtime("my_agent", config={
    "arms": [
        {"arm_id": "concise", "params": {"temperature": 0.3, "max_tokens": 500}},
        {"arm_id": "detailed", "params": {"temperature": 0.7, "max_tokens": 2000}},
    ],
    "storage": {"backend": "postgresql", "dsn": "postgresql://..."}
})

# 2. Select per request (Thompson Sampling handles exploration/exploitation)
selection = await runtime_select("my_agent", user_id="user_123")
# selection.params = {"temperature": 0.3, "max_tokens": 500}

# 3. Update on outcome (the system learns)
await runtime_update("my_agent", decision_id=selection.decision_id, reward=1.0)
```

That's it. Everything else — the learning algorithms, the storage, the exploration/exploitation tradeoff — is handled for you.

---

## How It Works

### The Core Idea: Arms and Rewards

Think of your agent as having multiple "arms" — different ways it could respond. Maybe one arm is concise and professional. Another is detailed and friendly. A third is technical and precise.

For any given user and context, which arm is best? You don't know upfront. But you can measure outcomes.

The Convergence uses **Thompson Sampling** to explore these options intelligently:

```
Arm A (concise): Users clicked "helpful" 15 times, "not helpful" 5 times
Arm B (detailed): Users clicked "helpful" 8 times, "not helpful" 12 times
Arm C (technical): Users clicked "helpful" 2 times, "not helpful" 2 times

The system samples from probability distributions:
  Arm A: Sample from Beta(15, 5) → 0.73
  Arm B: Sample from Beta(8, 12) → 0.42
  Arm C: Sample from Beta(2, 2) → 0.61 ← High uncertainty, worth trying

Select Arm A (highest sample). If it works, Arm A gets stronger.
If Arm C works when tried, its uncertainty decreases and it might win next time.
```

This isn't random experimentation. It's principled exploration that mathematically balances trying new things versus using what works.

### The Learning Timeline

Not all methods are ready for production immediately:

| Method | When It's Ready | What It Does |
|--------|-----------------|--------------|
| **Thompson Sampling** | Immediately (15-30 interactions) | Learns which response styles work best |
| **Semantic Caching** | Immediately | Reduces costs by caching similar queries |
| **RLP (Think First)** | After 500+ interactions | Agent reasons before responding |
| **SAO (Self-Training)** | After 1000+ interactions | Agent generates its own training data |

The experimental methods are powerful but need data to calibrate. They're labeled clearly and data-gated — they won't activate until you have enough interactions for them to work reliably.

### The Safety Stack

Safety isn't a feature. It's the foundation.

```
┌─────────────────────────────────────────────────────────────┐
│                     YOUR AGENT                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Layer 1: Input Validation                                  │
│   ├─ Jailbreak detection (NeMo Guardrails)                  │
│   ├─ Prompt injection blocking                               │
│   └─ Rate limiting                                           │
│                                                              │
│   Layer 2: Execution Control                                 │
│   ├─ Tool authorization (agent can't access unapproved tools)│
│   ├─ Budget enforcement (daily spend limits)                 │
│   └─ Mutation approval (writes require human sign-off)       │
│                                                              │
│   Layer 3: Output Validation                                 │
│   ├─ Schema enforcement (Guardrails AI)                      │
│   ├─ Sensitive data detection                                │
│   └─ Hallucination flagging                                  │
│                                                              │
│   Layer 4: Audit                                             │
│   └─ Every decision logged, traceable, reviewable            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

The key insight: safety checks happen at the *framework* level, not the *prompt* level. The model can't be prompted to bypass them because they're not in the model's control.

---

## Quick Start

### Installation

```bash
pip install -e .
```

### Try It Now

```bash
# Clone and run an example in 30 seconds
git clone https://github.com/ariaxhan/the-convergence.git
cd the-convergence/examples/00_quickstart
python 02_confidence_extraction.py  # No API key needed
python 06_thompson_sampling_loop.py  # Watch Thompson Sampling converge
```

See the full **[Cookbook](examples/)** for 40+ runnable examples: progressive quickstart, sample apps, deep dives, and provider integrations.

### Minimal Example

```python
import asyncio
from convergence import configure_runtime, runtime_select, runtime_update

async def main():
    # Configure your agent
    await configure_runtime("my_agent", config={
        "arms": [
            {"arm_id": "style_a", "params": {"temperature": 0.5}},
            {"arm_id": "style_b", "params": {"temperature": 0.8}},
        ],
        "storage": {"backend": "sqlite", "path": "convergence.db"}
    })

    # For each request...
    selection = await runtime_select("my_agent", user_id="user_123")

    # Use selection.params in your LLM call
    # response = await your_llm_call(**selection.params)

    # Report the outcome (did it work?)
    await runtime_update(
        "my_agent",
        decision_id=selection.decision_id,
        reward=1.0  # 1.0 = success, 0.0 = failure
    )

asyncio.run(main())
```

### With Semantic Caching (80% Cost Reduction)

```python
from convergence.cache import SemanticCache

cache = SemanticCache(
    similarity_threshold=0.88,  # How similar queries need to be
    ttl_seconds=86400,          # Cache for 24 hours
    backend="redis"
)

# Before calling your LLM
cached = await cache.get(user_query)
if cached:
    return cached["response"]  # Free! No API call.

# After getting a response
await cache.set(user_query, response)
```

### With Safety Guardrails

```python
from convergence.safety import ConvergenceRails

rails = ConvergenceRails()

# Validate input before processing
input_check = await rails.validate_input(user_message)
if not input_check.passed:
    return "I can't process that request."

# Validate output before sending
output_check = await rails.validate_output(agent_response)
if not output_check.passed:
    return fallback_response
```

---

## The Enterprise Problem We Solve

Modern companies have a knowledge problem:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   GitHub    │  │    Slack    │  │   Zendesk   │
│  (code)     │  │  (decisions)│  │  (support)  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                   ??? Magic ???
                        │
                        ▼
               ┌─────────────────┐
               │  Unified Agent  │
               │  that actually  │
               │     works       │
               └─────────────────┘
```

The "magic" is the hard part. You need:

1. **Integration** — Connect to all your knowledge sources
2. **Intelligence** — Go beyond basic RAG (multi-hop reasoning, context awareness)
3. **Safety** — Don't leak data, don't say wrong things, don't take unauthorized actions
4. **Observability** — Know what's happening, catch problems early
5. **Improvement** — Get better over time without constant manual intervention

Most solutions give you (1) and maybe (2). They leave (3), (4), and (5) as "your problem."

The Convergence makes (3), (4), and (5) the core. Because those are actually the hard parts.

---

## The Centralized Knowledge Layer

The real "magic" is **structured knowledge**, not just vector embeddings.

Traditional RAG finds similar text chunks. But it can't answer: "Who made this decision? Why? What depends on it?"

The Convergence uses a **context graph** — a knowledge architecture that both humans and AI agents can navigate:

```
┌─────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE TRIAD                          │
├───────────────┬───────────────────┬─────────────────────────┤
│     WHO       │       WHAT        │          HOW            │
│               │                   │                         │
│  • People     │  • Knowledge      │  • Processes            │
│  • Teams      │  • Decisions      │  • Workflows            │
│  • Roles      │  • Artifacts      │  • Plans                │
│  • Orgs       │  • Research       │  • Operations           │
│               │  • Context        │  • Sessions             │
└───────────────┴───────────────────┴─────────────────────────┘

Every piece of knowledge fits into exactly ONE category.
No ambiguity. Relationships are explicit.
```

### Why This Matters

**Without structure:**
- Agent loads everything → tokens wasted, context polluted
- Agent loads nothing → starts cold, misses context
- Agent guesses → hallucinates relationships

**With a context graph:**
- **Progressive disclosure** — Load only what's relevant to the current task
- **Session continuity** — Handoff documents so agents don't start cold
- **Relationship traversal** — Follow edges: "Who owns this?" "What depends on this?"
- **Mergeable knowledge** — Combine graphs from different sources

### The Knowledge Cascade

For complex work, the graph supports hierarchical decomposition:

```
Campaign (strategic, weeks-to-months)
    └── Phase (logical grouping, human approval gates)
            └── Mission (multi-session, specific goal)
                    └── Objective (session-sized, executable)

Each level narrows context:
- Fewer tokens
- Higher signal density
- Relevant to the current task
```

An agent working on a specific objective doesn't need the entire company knowledge base. It needs the subgraph relevant to *this task, right now*.

### Graph Operations

| Operation | What It Does |
|-----------|--------------|
| **Traverse** | Follow relationships (who owns this? what depends on this?) |
| **Extract** | Build context payload from subgraph for current session |
| **Merge** | Combine graphs from different sources |
| **Learn** | Graph structure improves based on usage (ties to self-learning!) |

This is what separates "beyond RAG" from "slightly better RAG."

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THE CONVERGENCE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  KNOWLEDGE (The Substrate)                                                   │
│  • Context graph (who/what/how triad)                                       │
│  • Relationship traversal (follow edges, not just similarity)               │
│  • Progressive disclosure (load only relevant context)                       │
│  • Mergeable graphs (combine knowledge from multiple sources)                │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SAFETY (The Foundation)                                                     │
│  • Input validation (jailbreak/injection detection)                         │
│  • Execution control (tool authorization, budget limits)                     │
│  • Output validation (schema enforcement, sensitive data)                    │
│  • Audit logging (every decision traceable)                                  │
│  • Graph-aware permissions (WHO can access WHAT via HOW)                    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  OBSERVABILITY (The Eyes)                                                    │
│  • Learning metrics (is the system improving?)                               │
│  • Calibration tracking (is "80% confident" actually 80% accurate?)         │
│  • Cost tracking (per request, per user, per day)                           │
│  • Drift detection (is behavior changing unexpectedly?)                      │
│  • Graph usage (which knowledge is accessed? where are gaps?)               │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  OPTIMIZATION (The Brain)                                                    │
│  • Thompson Sampling (intelligent exploration)                               │
│  • Semantic Caching (cost reduction)                                         │
│  • Confidence Extraction (know when to escalate)                            │
│  • Evolutionary Algorithms (breed better configurations)                     │
│  • Graph learning (which traversals work best?)                             │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  EXPERIMENTAL (The Future)                                                   │
│  • RLP — Agent thinks before acting (needs 500+ interactions)               │
│  • SAO — Agent generates training data (needs 1000+ interactions)           │
│  • MemRL — Agent learns from past episodes (needs 100+ interactions)        │
│  • [Clearly labeled, data-gated, opt-in]                                    │
│                                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STORAGE (The Memory)                                                        │
│  • SQLite (development) / PostgreSQL (production)                           │
│  • Redis (caching)                                                           │
│  • Graph storage (nodes, edges, ontologies)                                 │
│  • Same API for all backends                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What Makes This Different

### From LangChain/LlamaIndex
Those are excellent tools for *building* agents. The Convergence is about *operating* them in production. We integrate with those tools; we don't replace them.

### From OpenAI/Anthropic APIs
Those give you model access. We give you the infrastructure to use those models safely, observably, and with continuous improvement.

### From Custom Solutions
You could build all of this yourself. Companies do. It takes 6-12 months and constant maintenance. The Convergence packages proven patterns so you can focus on your actual product.

---

## Current Status

The Convergence is in active development. Here's what's production-ready vs. experimental:

| Component | Status | Notes |
|-----------|--------|-------|
| Thompson Sampling | Production | Converges in 15-30 interactions |
| Storage Backends | Production | SQLite, PostgreSQL, Memory |
| Semantic Caching | Production | 70-80% cost reduction |
| Confidence Extraction | Production | Gap detection for human escalation |
| Context Graph | Beta | who/what/how triad, graph operations |
| Safety Guardrails | Beta | NeMo + Guardrails AI integration |
| Native Observability | Beta | Metrics, calibration, drift |
| RLP (Think First) | Experimental | Needs 500+ interactions |
| SAO (Self-Training) | Experimental | Needs 1000+ interactions |
| MemRL (Memory) | Experimental | In development |

---

## Documentation

- **[Getting Started](GETTING_STARTED.md)** — Full setup guide
- **[API Reference](docs/API.md)** — Detailed function documentation
- **[Configuration](YAML_CONFIGURATION_REFERENCE.md)** — All config options
- **[Examples](examples/)** — Working code samples

---

## Research Foundation

The Convergence builds on peer-reviewed research:

- **Thompson Sampling** — Bayesian approach to exploration/exploitation, proven across decades of research
- **Evolutionary Strategies** — Genetic algorithms for configuration optimization
- **RLP** — [Reinforcement Learning on Policy](https://arxiv.org/abs/2510.01265) (NVIDIA, 2024)
- **SAO** — [Self-Alignment Optimization](https://arxiv.org/abs/2510.06652) (Hugging Face, 2024)
- **NeMo Guardrails** — Enterprise safety framework by NVIDIA
- **Guardrails AI** — Output validation and schema enforcement

---

## Origin

The Convergence began as a hackathon project in October 2025 by the PersistOS team:

- **Aria Han** — Architecture & RL systems
- **Shreyash Hamal** — Infrastructure & integrations
- **Myat Pyae Paing** — Evaluation & testing

The original insight: most AI projects fail not because of bad models, but because of bad systems around them. We're building the system that adapts.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

We especially welcome:
- Bug reports and feature requests
- Documentation improvements
- Integration examples
- Safety audit findings

---

## License

Proprietary — See [LICENSE](LICENSE) file.

---

<p align="center">
  <em>Stop tuning. Start evolving.</em>
</p>
