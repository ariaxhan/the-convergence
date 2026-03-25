# Use Case Decision Matrix

Find the right Convergence modules for your goal.

## "I want to..."

| Goal | Modules | Example | Complexity |
|------|---------|---------|------------|
| **Reduce API costs** | Semantic Cache | [`00_quickstart/04_semantic_cache.py`](examples/00_quickstart/04_semantic_cache.py) | Low |
| **Make my agent learn over time** | Runtime + Thompson Sampling | [`00_quickstart/06_thompson_sampling_loop.py`](examples/00_quickstart/06_thompson_sampling_loop.py) | Low |
| **Extract confidence from responses** | Confidence Evaluator | [`00_quickstart/02_confidence_extraction.py`](examples/00_quickstart/02_confidence_extraction.py) | Low |
| **Persist agent state across restarts** | Storage (SQLite/PostgreSQL) | [`00_quickstart/05_runtime_with_storage.py`](examples/00_quickstart/05_runtime_with_storage.py) | Low |
| **Add safety guardrails** | Safety module | [`04_safety/input_validation.py`](examples/04_safety/input_validation.py) | Low |
| **Build a knowledge base** | Context Graph | [`03_knowledge/basic_graph.py`](examples/03_knowledge/basic_graph.py) | Medium |
| **Combine multiple reward signals** | Reward Evaluator | [`02_optimization/reward_evaluation.py`](examples/02_optimization/reward_evaluation.py) | Medium |
| **Monitor for drift** | Observability | [`05_observability/drift_detection.py`](examples/05_observability/drift_detection.py) | Medium |
| **Track API costs** | Observability | [`05_observability/cost_tracking.py`](examples/05_observability/cost_tracking.py) | Low |
| **Calibrate confidence accuracy** | Observability | [`05_observability/confidence_calibration.py`](examples/05_observability/confidence_calibration.py) | Medium |
| **Use with Claude** | ClaudeClient | [`90_models/claude/basic.py`](examples/90_models/claude/basic.py) | Low |
| **Use with OpenAI** | Runtime + OpenAI SDK | [`90_models/openai/basic.py`](examples/90_models/openai/basic.py) | Low |
| **Use with local models** | Runtime + Ollama | [`90_models/local/ollama.py`](examples/90_models/local/ollama.py) | Low |
| **Optimize API parameters at scale** | SDK run_optimization | [`00_quickstart/09_optimization_local.py`](examples/00_quickstart/09_optimization_local.py) | High |
| **Build a self-evolving support bot** | All modules | [`01_apps/customer_support_bot/`](examples/01_apps/customer_support_bot/) | High |
| **Build a research assistant** | Graph + Runtime | [`01_apps/research_assistant/`](examples/01_apps/research_assistant/) | High |
| **Build a self-improving classifier** | Runtime + Confidence | [`01_apps/self_improving_classifier/`](examples/01_apps/self_improving_classifier/) | High |
| **Run multi-agent teams** | CivilizationRuntime | [`06_teams/basic_team.py`](examples/06_teams/basic_team.py) | Medium |
| **Build a multi-step pipeline** | Multiple Runtimes | [`07_workflows/sequential_pipeline.py`](examples/07_workflows/sequential_pipeline.py) | Medium |
| **Add human-in-the-loop escalation** | Runtime + Confidence | [`07_workflows/human_in_the_loop.py`](examples/07_workflows/human_in_the_loop.py) | Medium |
| **Persist cache across restarts** | SemanticCache (SQLite) | [`08_caching/sqlite_cache.py`](examples/08_caching/sqlite_cache.py) | Low |
| **Run A/B tests** | Runtime + Statistics | [`09_production/ab_testing.py`](examples/09_production/ab_testing.py) | Medium |
| **Deploy with canary rollout** | Runtime + SelectionStrategy | [`09_production/gradual_rollout.py`](examples/09_production/gradual_rollout.py) | Medium |
| **Use YAML config (CLI workflow)** | ConfigLoader | [`94_yaml_configs/`](examples/94_yaml_configs/) | Low |

## When NOT to Use Convergence

| Scenario | Why | Use Instead |
|----------|-----|-------------|
| Simple one-shot LLM calls | No learning loop needed | Call the LLM API directly |
| Batch processing with no feedback | No reward signals to learn from | A pipeline tool (Airflow, Prefect) |
| Real-time chat with no evolution | You don't need MAB optimization | A simpler framework (LangChain, etc.) |
| Static, deterministic workflows | No exploration/exploitation tradeoff | Standard application code |

## Module Compatibility Matrix

| | Runtime | Cache | Graph | Safety | Observability | ClaudeClient |
|---|---|---|---|---|---|---|
| **Runtime** | - | Works together | Independent | Independent | Works together | Built-in |
| **Cache** | Works together | - | Independent | Independent | Works together | Separate |
| **Graph** | Independent | Independent | - | Independent | Independent | Independent |
| **Safety** | Independent | Independent | Independent | - | Works together | Separate |
| **Observability** | Works together | Works together | Independent | Works together | - | Works together |
| **ClaudeClient** | Built-in | Separate | Independent | Separate | Works together | - |
