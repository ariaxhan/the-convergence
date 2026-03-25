# Dream: Local Simulation Harness

## Context

Aria wants to run a **real customer support bot simulation** locally using Ollama, watching The Convergence's learning loop in action. The goal is both a demo and a reusable simulation system.

**Existing state:**
- `examples/01_apps/customer_support_bot/app.py` — simulates rewards with random numbers, never calls an actual LLM
- `examples/90_models/local/ollama.py` — calls Ollama but with trivial "what's the capital of France" task
- Runtime API (`configure_runtime`, `runtime_select`, `runtime_update`) is production-ready
- Thompson Sampling converges in 15-30 interactions
- `RuntimeRewardEvaluator` supports multi-metric weighted aggregation
- No existing simulation framework — each example is standalone

**The gap:** Nothing actually runs a realistic workload through the full loop: real queries → real LLM responses → real evaluation → real learning. And there's no way to replay, compare, or visualize simulation runs.

---

## 🔻 Minimalist

You already have the runtime API and Ollama works. You don't need a "simulation harness." You need **one script** that:

1. Defines 3 arms (different system prompts + temperatures for support styles)
2. Loads 20 canned support tickets from a JSON file
3. Calls Ollama for each, selects arm via Thompson Sampling
4. Scores responses with a simple rubric (length, keyword presence, tone match)
5. Prints a table at the end showing arm convergence

That's `sim.py` + `tickets.json`. Two files. ~150 lines. Run it, watch Thompson Sampling learn which prompt style works best for support tickets. Done.

No framework. No visualizer. No replay system. If you want to change the scenario, edit the file.

**Effort:** 2-3 hours
**Coverage:** 70% — proves the learning loop works end-to-end with a real LLM. Doesn't generalize to other scenarios without copy-paste.

— minimalist

---

## 🔺 Maximalist

Build a **simulation engine** that's a first-class feature of The Convergence — not an example, but a tool for anyone to stress-test their agent configurations before deploying.

### Architecture

```
convergence/
  simulation/
    __init__.py
    engine.py          # SimulationEngine: orchestrates runs
    scenarios.py       # Scenario protocol + built-in scenarios
    evaluators.py      # LLM-as-judge + heuristic evaluators
    synthetic.py       # Synthetic data generation (ticket templates + variation)
    recorder.py        # Records every decision, response, reward for replay
    reporter.py        # Rich terminal dashboard + markdown report + JSON export

examples/
  simulations/
    customer_support/
      scenario.yaml    # Scenario definition
      tickets.json     # Seed data
      run.py           # Entry point
    content_generation/
      scenario.yaml
      prompts.json
      run.py
```

### SimulationEngine

```python
engine = SimulationEngine(
    scenario="customer_support",
    arms=[
        Arm("empathetic", system_prompt="...", temperature=0.7),
        Arm("efficient", system_prompt="...", temperature=0.3),
        Arm("technical", system_prompt="...", temperature=0.5),
    ],
    evaluator=LLMJudgeEvaluator(model="ollama/llama3.2"),  # LLM grades LLM
    provider="ollama/llama3.2",
    episodes=100,
    storage="sqlite",
)

results = await engine.run()
engine.report()  # Rich terminal dashboard
engine.export("results/run_001.json")
```

### Features
- **Scenario protocol**: Define any simulation via YAML (queries, evaluation criteria, expected behaviors)
- **Synthetic data generation**: Generate ticket variations from templates so you're not just looping 20 queries
- **LLM-as-judge evaluation**: Use a second Ollama model (or the same one) to grade responses on multiple dimensions
- **Live dashboard**: Rich terminal showing arm distributions updating in real-time
- **Recording + replay**: Every decision recorded. Replay with different strategies to compare.
- **Regression testing**: Save a "golden run" and detect when changes degrade performance
- **CLI integration**: `convergence simulate customer_support --episodes 100 --provider ollama/llama3.2`

### What this enables beyond the immediate need
- **Anyone** can validate their agent config before deploying
- **Regression suite** for the framework itself — run simulations as CI tests
- **Demo tool** for showing The Convergence to potential users
- **Research tool** for comparing MAB strategies, reward shaping, exploration parameters

**Effort:** 2-3 weeks
**Enables:** Simulation as a product feature, CI regression testing, demo/sales tool, research infrastructure

— maximalist

---

## ⚖️ Pragmatist

Take the maximalist vision but ship in two phases. Phase 1 this week, phase 2 when you need it.

### Phase 1: Working simulation (ship now)

```
examples/
  simulations/
    engine.py              # Lightweight SimulationEngine (~200 lines)
    evaluators.py          # Heuristic + LLM-as-judge evaluators
    reporter.py            # Terminal output with Rich tables
    customer_support/
      scenario.py          # Scenario config + ticket data
      run.py               # Entry point: python run.py
```

**What `engine.py` does:**
- Takes a list of arms (system prompt + params), a provider (Ollama model name), a list of queries, and an evaluator
- Runs N episodes: select arm → call Ollama via LiteLLM → evaluate → update
- Tracks per-arm stats (pulls, mean reward, alpha/beta evolution)
- Prints summary table + per-episode log

**What `evaluators.py` does:**
- `HeuristicEvaluator`: scores on response length, keyword coverage, tone (fast, no extra LLM call)
- `LLMJudgeEvaluator`: sends response to Ollama with a grading prompt, extracts 0-1 score (slower, more accurate)
- Both implement a simple `evaluate(query, response, context) → Dict[str, float]` interface

**What `reporter.py` does:**
- Rich table showing arm convergence after each batch of 10
- Final summary: winner, confidence interval, total episodes, cost estimate
- Markdown export for sharing

**What the customer support scenario includes:**
- 30 realistic support tickets (billing, technical, account, feature request categories)
- 3 arms: empathetic (warm, detailed), efficient (brief, action-oriented), technical (precise, reference-heavy)
- Evaluation on: helpfulness, relevance, tone-appropriateness, completeness

### Phase 2: Generalize later (defer)

- Move engine into `convergence/simulation/` as a package feature
- Add YAML scenario format
- Add CLI command `convergence simulate`
- Add synthetic data generation
- Add recording/replay
- Add regression testing

**Skip for now because:** You have one scenario. Generalizing before you have two is premature. The Phase 1 structure is clean enough to refactor into Phase 2 without rewriting.

**Effort:** 1-2 days (Phase 1), 1 week (Phase 2 when needed)
**Tradeoffs:** No CLI integration, no YAML scenarios, no replay — all deferrable. Hardcoded scenario structure, but clean interfaces make Phase 2 a refactor not a rewrite.
**Upgrade path:** Phase 1 evaluator/engine interfaces become the protocol for Phase 2. Scenario data moves into YAML. Engine moves into package. No throwaway code.

— pragmatist

---

**Which timeline?** Reply with your choice, argue for a hybrid, or ask for more detail on any perspective.
