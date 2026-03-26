# Changelog

All notable changes to Armature will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-24

### The Self-Evolving Agent Framework

Armature reaches 1.0. This release marks the transition from research prototype to production-ready framework for building AI agents that improve themselves through reinforcement learning.

### Added

#### Comprehensive Example Library (40+ examples)
- **Quickstart series** (00): 10 progressive examples from basic runtime to full optimization loop
- **Sample apps** (01): Customer support bot, research assistant, self-improving classifier
- **Optimization deep dives** (02): Thompson Sampling strategies, reward evaluation, armature visualization
- **Knowledge graph** (03): Graph construction, relationship patterns, queries
- **Safety** (04): Budget tracking, confidence thresholds, input validation, reward bounds
- **Observability** (05): Calibration, cost tracking, drift detection, learning metrics
- **Team patterns** (06): Multi-agent teams, competitive selection, specialist routing
- **Workflows** (07): Branching, human-in-the-loop, retry with learning, sequential pipelines
- **Caching** (08): Analytics, invalidation, embedding comparison, SQLite cache
- **Production** (09): A/B testing, gradual rollout, monitoring, PostgreSQL setup
- **Agent patterns** (10): Observable pipelines, production runtime, resilient cache, safe evolution, secure clients
- **Vector native** (11): Cache quality, embedding strategies, hybrid search, similarity tuning
- **Model providers** (90): Azure, Claude, Groq, OpenAI, Ollama
- **Integrations** (92): Discord, Gmail, Reddit, Browserbase

#### In-Memory Storage Backend
- Full `MemoryStorageBackend` for testing and ephemeral workloads

#### Example Testing CI
- GitHub Actions workflow to validate all examples

#### AGENT.md
- Machine-readable agent instructions for LLM-powered development tools

#### llms.txt
- Standardized LLM context file for the project

#### USE_CASES.md
- Dedicated use case documentation

### Changed

- **README completely rewritten** — skimmable, use-case-led, targets AI-literate readers
- **License changed** to MIT
- **Version badge** updated across all files
- **Examples reorganized** into numbered categories with READMEs and style guide
- **Legacy examples** (agno_agents, ai/, web_browsing) cleaned up and modernized

### Fixed

- SAO plugin import cleanup
- PostgreSQL storage backend corrections
- CLI module path fixes

---

## [0.1.0] - 2025-10-15

### 🎉 Initial Release

Armature is an API optimization framework that finds optimal configurations through evolutionary algorithms, multi-armed bandits, and agent societies.

### Added

#### Core Framework

- **Optimization Engine** - Complete MAB + Evolution + RL optimization pipeline
- **Multi-Armed Bandits** - Thompson Sampling for intelligent exploration
- **Genetic Algorithms** - Mutation, crossover, and elite selection
- **RL Meta-Optimizer** - Learn from optimization history
- **Agent Society** (Optional) - RLP + SAO + Memory systems for advanced learning

#### Storage & Persistence

- **Multi-Backend Storage** - SQLite + File + Memory with redundancy
- **Legacy System** - Track optimization history across runs
- **Warm-Start** - Resume from previous winners
- **Session Management** - Organize related optimization runs
- **Export Formats** - JSON, CSV, Markdown reports

#### Evaluation System

- **Custom Evaluators** - Write Python functions for domain-specific scoring
- **Built-in Metrics** - Latency, cost, quality, exact match, similarity
- **Multi-Objective** - Optimize multiple metrics simultaneously
- **Test Case Evolution** - Auto-generate test variants (experimental)

#### Provider Support

- **API Adapters** - OpenAI, Azure OpenAI, Gemini, Groq, BrowserBase
- **Universal Adapter** - Works with any REST API
- **LiteLLM Integration** - Support for 100+ LLM providers
- **Authentication** - Bearer, API Key, Basic Auth, OAuth

#### CLI & UX

- **Interactive CLI** - Rich terminal UI with Typer
- **Progress Tracking** - Real-time optimization progress
- **Result Reports** - Human-readable Markdown + CSV + JSON
- **Error Handling** - Clear error messages and recovery
- **Environment Loading** - Auto-load .env files

#### Observability

- **Weave Integration** - Full observability with W&B Weave
- **LLM Tracing** - Track all API calls and costs
- **Experiment Tracking** - Compare optimization runs
- **Metrics Dashboard** - Visualize armature

#### Documentation

- **Comprehensive README** - Quick start and overview
- **User Guide** - Detailed SYSTEM_CONVERGENCE_USER_GUIDE_EXPERIENCE.md
- **Examples** - 15+ ready-to-run optimization examples
  - OpenAI chat completions
  - Azure O4-Mini reasoning
  - Gemini task decomposition
  - Groq fast inference
  - BrowserBase web automation
- **Contributing Guide** - How to contribute
- **Security Policy** - Security best practices

#### Developer Features

- **Protocol-Based Design** - Easy to extend with custom implementations
- **Plugin System** - Pluggy-based extensibility
- **Type Safety** - Full type hints with Pydantic
- **Async/Await** - Performant async implementation
- **Configuration** - Flexible YAML/JSON configuration
- **OpenAPI Generation** (Experimental) - Auto-generate configs from OpenAPI specs

#### Agent Society (Advanced)

- **RLP (Reinforcement Learning Pretraining)** - NVIDIA research implementation
- **SAO (Self-Alignment Optimization)** - Hugging Face research implementation
- **Memory Systems** - Procedural, semantic, and episodic memory
- **Collaboration** - Multi-agent optimization strategies

### Technical Details

#### Dependencies

- Python 3.11+
- Core: Pydantic, Typer, Rich, HTTPX, Tenacity
- Optimization: NumPy, SciPy
- Storage: aiosqlite, aiofiles
- LLM: LiteLLM, Weave
- Optional: transformers, torch, trl (for agent society)

#### Architecture

- Modular plugin-based design
- Protocol-oriented abstractions
- Multi-backend storage with redundancy
- Async-first implementation
- Type-safe configuration with Pydantic

#### Performance

- Parallel execution with configurable workers
- Smart caching to reduce API calls
- Early stopping to prevent over-optimization
- Efficient storage with SQLite + file system

### Known Limitations

- No automated test suite yet (coming in 0.2.0)
- OpenAPI auto-generation is experimental
- Test case evolution is experimental
- Large result sets may consume memory
- SQLite may not scale to massive datasets (use PostgreSQL backend for scale)

### Breaking Changes from Pre-Release

This is the first public release, so there are no breaking changes. Future releases will document breaking changes here.

### Migration Guide

Not applicable for initial release.

## Release Notes

### What's New in 0.1.0

**Armature** makes API optimization accessible to everyone:

- **Zero ML Expertise Required:** Just provide your API and test cases
- **Automated Discovery:** Find optimal configs through evolution
- **Multi-Objective:** Balance quality, speed, and cost simultaneously
- **Production-Ready:** Full observability and audit trails
- **Open Source:** MIT licensed, community-driven

### Quick Start

```bash
# Install
pip install -e .

# Run optimization
armature optimize examples/ai/openai/openai_responses_optimization.yaml

# View results
cat results/optimization_run/best_config.json
```

### Use Cases

- **LLM Parameter Tuning:** Find optimal temperature, top_p, max_tokens
- **API Cost Reduction:** Reduce costs while maintaining quality
- **A/B Testing at Scale:** Test hundreds of configurations automatically
- **Reasoning Model Optimization:** Tune reasoning chains and completion tokens
- **Browser Automation:** Optimize web scraping parameters

### Example Results

From real optimizations:

**OpenAI Chat (v0.1.0):**

- Cost reduced by 60% (using gpt-3.5-turbo over gpt-4)
- Quality maintained at 85%+ score
- Speed improved 40%

**Azure O4-Mini Reasoning (v0.1.0):**

- Latency reduced 70% (2000 tokens vs 10000)
- Reasoning accuracy improved 15%
- Found optimal `presence_penalty=-0.5`

**Groq Fast Inference (v0.1.0):**

- Optimal model: `llama-3.1-8b-instant`
- Temperature: 1.2 for creative tasks
- Score: 0.93 (excellent rating)

## Future Roadmap

### v0.2.0 (Planned - Q4 2025)

- [ ] Automated test suite with pytest
- [ ] Architecture documentation
- [ ] Plugin development guide
- [ ] Performance tuning guide
- [ ] Distributed optimization (multi-machine)

### v0.3.0 (Planned - Q1 2026)

- [ ] Web UI dashboard
- [ ] Real-time optimization streaming
- [ ] Cost prediction models
- [ ] Auto-scaling workers
- [ ] PostgreSQL backend

### v1.0.0 (Planned - Q2 2026)

- [ ] Production stability guarantees
- [ ] Enterprise support
- [ ] Cloud-hosted service
- [ ] Advanced analytics
- [ ] Multi-organization support

## Community

### Contributors

Thank you to everyone who contributed to this release!

- Aria Han - Creator & Maintainer

### How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Feedback

We'd love to hear from you:

- 🐛 [Report bugs](https://github.com/ariaxhan/armature-ai/issues)
- 💡 [Request features](https://github.com/ariaxhan/armature-ai/issues)
- 💬 [Join discussions](https://github.com/ariaxhan/armature-ai/discussions)
- ⭐ [Star on GitHub](https://github.com/ariaxhan/armature-ai)

## Support

- Documentation: [README.md](README.md)
- Issues: [GitHub Issues](https://github.com/ariaxhan/armature-ai/issues)
- Discussions: [GitHub Discussions](https://github.com/ariaxhan/armature-ai/discussions)

## License

[MIT License](LICENSE) - See LICENSE file for details

---

**Release Date:** October 15, 2025  
**Maintained by:** Aria Han  
**Repository:** <https://github.com/ariaxhan/armature-ai>
