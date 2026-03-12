# RLP + SAO: Deep Dive

**What they are, how they work, improvements, and novel methods to add**

---

## TL;DR

| Plugin | Core Idea | Source Paper |
|--------|-----------|--------------|
| **RLP** | Think before acting. Reward = did the thought improve prediction? | [NVIDIA RLP](https://arxiv.org/abs/2510.01265) |
| **SAO** | Generate your own training data. No external labels needed. | [Hugging Face SAO](https://arxiv.org/abs/2510.06652) |

Both are **self-improvement** methods. No human labelers. No GPT-4 as judge. The model improves itself.

---

## Part 1: RLP (Reinforcement Learning on Policy)

### What It Is

RLP makes agents **think before acting**. The key insight: internal reasoning improves predictions, and we can reward the agent for *useful* thoughts.

### How It Works

```
1. Receive state/context
2. Generate internal thought (chain-of-thought)
3. Make prediction based on thought
4. Calculate reward: Did the thought help?
5. Update policy to generate better thoughts
```

### The Reward Function

The core of RLP is **information gain**:

```python
reward = log P(outcome | context + thought) - log P(outcome | context)
```

**Translation:** How much did the thought improve our prediction?

- Positive reward → Thought helped
- Negative reward → Thought hurt (or was useless)
- Zero → No difference

### Current Implementation (`convergence/plugins/learning/rlp.py`)

**What exists:**

```python
class RLPMixin:
    async def generate_internal_reasoning(self, state, context):
        """Generate chain-of-thought before prediction."""
        # Constructs reasoning prompt
        # Calls LLM to generate thought
        # Returns thought + optional log-probs

    def information_gain_reward(self, thought, prediction, outcome, context):
        """Calculate information gain reward."""
        # Baseline: prediction without thought
        # With thought: prediction conditioned on thought
        # Reward = improvement

    def update_rlp_policy(self, thought, reward, state, action):
        """Update policy based on reward."""
        # Normalize reward
        # Store in experience buffer
        # Track statistics
```

**Key components:**

| Component | Purpose | Status |
|-----------|---------|--------|
| `ExperienceBuffer` | Store (state, thought, action, reward) tuples | ✓ Works |
| `normalize_reward()` | Keep rewards in stable range | ✓ Works |
| `compute_gae_advantages()` | GAE for variance reduction | ✓ Exists, not used |
| `extract_logprobs_from_response()` | Get real log-probs from LLM | ✓ Exists |
| `_compute_accuracy()` | Proxy for log-likelihood | ⚠️ Heuristic |

### Limitations

1. **No actual policy gradient training** — The mixin tracks rewards but doesn't do gradient updates
2. **Proxy reward** — Uses text similarity instead of real log-probabilities (most APIs don't expose them)
3. **Not connected to MAB** — Thoughts aren't selected via Thompson Sampling
4. **Weave-locked** — All observability requires Weave

---

## Part 2: SAO (Self-Alignment Optimization)

### What It Is

SAO generates **fully synthetic training data**. The model creates prompts, responses, and preference labels — all without human involvement.

### How It Works

```
1. Generate diverse prompts via persona role-play
2. Generate 2 responses per prompt (different temperatures)
3. Self-judge: which response is better?
4. Create preference pair: (prompt, chosen, rejected)
5. Train with DPO on the synthetic dataset
```

### The Key Insight

From the paper: **Persona role-play acts as a compress-and-decompress mechanism for world knowledge.**

By pretending to be diverse personas, the model generates diverse prompts that cover its knowledge space.

### Current Implementation (`convergence/plugins/learning/sao.py`)

**What exists:**

```python
class SAOMixin:
    async def generate_synthetic_prompts(self, n_samples):
        """Generate diverse prompts via persona role-play."""
        # Uses PERSONA_TEMPLATES and PERSONA_ATTRIBUTES
        # Creates personas like "A 35 year old software engineer from Tokyo..."
        # LLM generates question this persona would ask

    async def generate_response_pairs(self, prompt):
        """Generate two responses for comparison."""
        # Temperature 0.6 for first response
        # Temperature 0.8 for second response
        # Returns (response_a, response_b)

    async def self_judge(self, prompt, response_a, response_b):
        """Self-evaluate to create preference labels."""
        # Constructs judgment prompt
        # Model chooses A or B
        # Returns (chosen, rejected)

    async def iterative_sao_refinement(self, n_samples_per_round):
        """Multi-round refinement with quality filtering."""
        # Generate → Filter → Repeat
```

**Quality controls:**

| Control | Purpose | Status |
|---------|---------|--------|
| `is_duplicate()` | Reject similar prompts | ✓ Works |
| `passes_quality_filter()` | Check length, diversity, substance | ✓ Works |
| `compute_dataset_diversity()` | Track dataset diversity score | ✓ Works |
| `export_dataset()` / `import_dataset()` | Persist synthetic data | ✓ Works |

### Limitations

1. **No actual DPO training** — Generates data but doesn't train on it
2. **Basic similarity detection** — Uses Jaccard, not embeddings
3. **No model collapse prevention** — Small models can collapse on self-generated data
4. **Not connected to runtime** — Dataset isn't used by the optimization loop

---

## Part 3: How They Complement Each Other

```
┌─────────────────────────────────────────────────────┐
│                  THE LEARNING LOOP                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│   ┌───────────┐                   ┌───────────┐    │
│   │    RLP    │                   │    SAO    │    │
│   │           │                   │           │    │
│   │  THINK    │◄─────────────────►│  TRAIN    │    │
│   │  (online) │                   │  (offline)│    │
│   │           │                   │           │    │
│   └─────┬─────┘                   └─────┬─────┘    │
│         │                               │          │
│         ▼                               ▼          │
│   Generate thought              Generate data      │
│   for THIS request              for FUTURE training│
│         │                               │          │
│         ▼                               ▼          │
│   Information gain              Preference pairs   │
│   reward signal                 (chosen/rejected)  │
│         │                               │          │
│         └───────────────┬───────────────┘          │
│                         │                          │
│                         ▼                          │
│              EXPERIENCE BUFFER                     │
│              (thoughts + rewards +                 │
│               synthetic pairs)                     │
│                         │                          │
│                         ▼                          │
│              Thompson Sampling                     │
│              selects best strategies               │
│                                                    │
└────────────────────────────────────────────────────┘
```

**RLP is online:** It improves the current request by thinking first.

**SAO is offline:** It generates training data for future model updates.

**Together:** RLP explores strategies in production. SAO captures successful strategies as training data. The model continuously improves.

---

## Part 4: Improvements to Current Implementation

### Improvement 1: Connect to MAB

**Problem:** Thoughts aren't selected via Thompson Sampling.

**Solution:** Treat thought strategies as arms.

```python
# Example thought strategies (arms)
THOUGHT_STRATEGIES = {
    "step_by_step": "Let me think through this step by step...",
    "pros_cons": "Let me weigh the pros and cons...",
    "analogies": "This is similar to...",
    "first_principles": "Breaking this down to first principles...",
}

# Thompson Sampling selects strategy
async def generate_internal_reasoning(self, state, context):
    strategy = await self.sampler.select_strategy()  # MAB selection
    thought = await self.llm_provider.generate(
        prompt=THOUGHT_STRATEGIES[strategy.id] + context
    )
    return thought, strategy.id
```

### Improvement 2: Use Real Log-Probabilities

**Problem:** Current reward uses text similarity as proxy.

**Solution:** Use actual log-probs when available.

```python
def information_gain_reward_v2(self, thought, prediction, outcome, context):
    # Get log-probs from model (if available)
    logprob_with_thought = self.get_logprob(outcome, context + thought)
    logprob_without_thought = self.get_logprob(outcome, context)

    if logprob_with_thought is not None:
        # Real information gain
        return logprob_with_thought - logprob_without_thought
    else:
        # Fall back to proxy
        return self._compute_accuracy_proxy(...)
```

### Improvement 3: Integrate SAO with Runtime

**Problem:** SAO generates data but doesn't feed it into training.

**Solution:** Connect SAO to DPO training loop.

```python
# After each batch of production interactions
if len(experience_buffer) > BATCH_SIZE:
    # Generate SAO training data from successful interactions
    dataset = await sao.generate_from_experiences(experience_buffer.get_recent(100))

    # Export for DPO training
    sao.export_dataset("training/batch_{timestamp}.jsonl")

    # Trigger async training job
    await trigger_dpo_training(dataset)
```

### Improvement 4: Add Model Collapse Prevention

**Problem:** Self-training can cause model collapse.

**Solution:** Diversity enforcement + reference model anchoring.

```python
# From Constitutional AI research
def prevent_collapse(self, chosen, rejected, reference_response):
    # KL divergence penalty to reference model
    kl_penalty = compute_kl(chosen, reference_response)

    if kl_penalty > KL_THRESHOLD:
        # Too different from reference, likely collapsing
        return False, "kl_divergence_exceeded"

    return True, "ok"
```

### Improvement 5: Add Quality Metrics for RLP

**Problem:** No way to track if thoughts are actually helping.

**Solution:** Track thought quality metrics.

```python
class RLPMetrics:
    thought_usage_rate: Counter      # How often thoughts are generated
    positive_reward_rate: Gauge      # % of thoughts that helped
    avg_information_gain: Histogram  # Distribution of rewards
    thought_strategy_performance: Dict[str, float]  # Per-strategy success
```

---

## Part 5: Novel Methods to Add

Based on research synthesis, here are methods that would enhance The Convergence:

### 1. MemRL (Episodic Memory RL)

**Paper:** [MemRL: Self-Evolving Agents via Runtime Reinforcement Learning on Episodic Memory](https://arxiv.org/html/2601.03192v1)

**What it is:** Agents learn from episodic memory without retraining the LLM.

**How it works:**
- Freeze the LLM (no gradient updates)
- Store experiences in episodic memory
- Learn Q-values for memory retrieval
- Two-phase retrieval: semantic similarity → Q-value ranking

**Why add it:**
- No model retraining needed
- Memory evolves, model stays stable
- Works with any frozen LLM

```python
class MemRLPlugin:
    """Memory-based RL without model updates."""

    def __init__(self, llm_provider):
        self.memory = EpisodicMemory()
        self.q_network = QNetwork()  # Small, trainable
        self.llm = llm_provider  # Frozen

    async def retrieve(self, query):
        # Phase 1: Semantic similarity
        candidates = self.memory.semantic_search(query, k=100)

        # Phase 2: Q-value ranking
        q_values = self.q_network.predict(candidates)
        return candidates[np.argmax(q_values)]

    def update(self, experience, reward):
        # Update Q-network, not LLM
        self.q_network.train(experience, reward)
        self.memory.add(experience)
```

### 2. SELAUR (Uncertainty-Aware Rewards)

**Paper:** Self-Evolving LLM Agent via Uncertainty-aware Rewards

**What it is:** Use LLM uncertainty to shape rewards, especially for failed trajectories.

**How it works:**
- Compute token-level uncertainty (entropy, margin, confidence)
- Aggregate to step/trajectory level
- Reshape rewards for failed trajectories using uncertainty signals
- High uncertainty = valuable exploration, not just failure

**Why add it:**
- Extracts learning signal from failures
- Improves exploration efficiency
- Dense supervision (every token)

```python
class SELAURPlugin:
    """Uncertainty-aware reward shaping."""

    def compute_uncertainty(self, logprobs):
        # Entropy-based uncertainty
        entropy = -np.sum(np.exp(logprobs) * logprobs)

        # Margin-based uncertainty
        sorted_probs = np.sort(np.exp(logprobs))[::-1]
        margin = sorted_probs[0] - sorted_probs[1]

        # Combined uncertainty
        return (entropy + (1 - margin)) / 2

    def reshape_reward(self, base_reward, uncertainty, success):
        if success:
            return base_reward
        else:
            # Failed trajectory, but was it valuable exploration?
            exploration_bonus = uncertainty * EXPLORATION_WEIGHT
            return base_reward + exploration_bonus
```

### 3. Multi-Agent Evolve (MAE)

**Paper:** [Multi-Agent Evolve: LLM Self-Improve through Co-evolution](https://arxiv.org/abs/2510.23595)

**What it is:** Three agents (Proposer, Solver, Judge) co-evolve through mutual feedback.

**How it works:**
- Proposer generates questions
- Solver attempts answers
- Judge evaluates both
- All three improve simultaneously
- No external grounding needed

**Why add it:**
- Self-contained improvement loop
- No human labels or external verifiers
- Domain-agnostic

```python
class MAEPlugin:
    """Multi-agent co-evolution."""

    def __init__(self, base_llm):
        self.proposer = Role(base_llm, "proposer")
        self.solver = Role(base_llm, "solver")
        self.judge = Role(base_llm, "judge")

    async def evolve_round(self):
        # Proposer generates challenge
        question = await self.proposer.generate_question()

        # Solver attempts
        answer = await self.solver.solve(question)

        # Judge evaluates
        evaluation = await self.judge.evaluate(question, answer)

        # All three learn from the interaction
        await self.proposer.update(evaluation.question_quality)
        await self.solver.update(evaluation.answer_quality)
        await self.judge.update(evaluation.judgment_quality)
```

### 4. Constitutional AI / RLAIF

**Paper:** [Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/abs/2212.08073)

**What it is:** Define principles (a constitution), use AI feedback instead of human feedback.

**How it works:**
- Define high-level principles ("be helpful", "avoid harm")
- Model critiques its own outputs against principles
- Model revises based on critique
- Train on (original, revised) preference pairs

**Why add it:**
- No human labelers needed
- Explicit, auditable principles
- Update constitution without retraining

```python
class ConstitutionalAIPlugin:
    """Principle-based self-improvement."""

    def __init__(self, constitution):
        self.constitution = constitution  # YAML principles

    async def critique_and_revise(self, response):
        # Critique against each principle
        critiques = []
        for principle in self.constitution.principles:
            critique = await self.llm.generate(
                f"Does this response violate '{principle}'? {response}"
            )
            critiques.append(critique)

        # Revise based on critiques
        revision_prompt = f"Original: {response}\nCritiques: {critiques}\nRevised:"
        revised = await self.llm.generate(revision_prompt)

        return response, revised  # (rejected, chosen) pair
```

### 5. OAIF (Online AI Feedback)

**Paper:** Online AI Feedback for Direct Alignment

**What it is:** Generate preference pairs online during training, not from static dataset.

**How it works:**
- Each training iteration: sample 2 responses from current model
- LLM annotator chooses preferred response (online)
- Train on the fresh preference pair
- Model and data co-evolve

**Why add it:**
- Fresh data every iteration
- Avoids distribution shift
- Self-correcting (model improves, data improves)

```python
class OAIFPlugin:
    """Online AI feedback for DPO."""

    async def get_online_preference(self, prompt):
        # Sample 2 responses from CURRENT model
        response_a = await self.model.generate(prompt, temperature=0.7)
        response_b = await self.model.generate(prompt, temperature=0.9)

        # Get online AI feedback
        judgment = await self.annotator.compare(prompt, response_a, response_b)

        if judgment == "A":
            return (response_a, response_b)  # (chosen, rejected)
        else:
            return (response_b, response_a)
```

### 6. Tool-R0 (Zero-Data Tool Learning)

**Paper:** Tool-R0: Zero-Data Self-Play RL

**What it is:** Generator and Solver co-evolve for tool learning without human data.

**How it works:**
- Generator creates tool-use tasks
- Solver attempts to solve them
- Difficulty-guided reward targets Solver's competence frontier
- Both improve through complementary rewards

**Why add it:**
- Zero human-annotated data
- Learns complex tool-calling autonomously
- Targets the edge of capability (efficient exploration)

```python
class ToolR0Plugin:
    """Zero-data tool learning via self-play."""

    async def self_play_round(self):
        # Generator creates task at Solver's frontier
        task = await self.generator.create_task(
            difficulty=self.solver.estimated_capability + FRONTIER_OFFSET
        )

        # Solver attempts
        solution = await self.solver.solve(task)
        success = await self.verify(task, solution)

        # Difficulty-guided rewards
        generator_reward = self._generator_reward(task, success)
        solver_reward = self._solver_reward(success, task.difficulty)

        # Both learn
        await self.generator.update(generator_reward)
        await self.solver.update(solver_reward)
```

---

## Part 6: Recommended Stack

Based on research and The Convergence's architecture, here's the recommended plugin stack:

### Tier 1: Core (Keep)
- **RLP** — Think before acting (needs connection to MAB)
- **SAO** — Self-generated training data (needs DPO integration)

### Tier 2: Add Now
- **MemRL** — Episodic memory without model updates (complements RLP)
- **Constitutional AI** — Principle-based alignment (complements SAO)

### Tier 3: Add Later
- **SELAUR** — Uncertainty-aware rewards (enhances exploration)
- **MAE** — Multi-agent co-evolution (for complex tasks)
- **OAIF** — Online preference generation (replaces static SAO)

### Integration Map

```
┌─────────────────────────────────────────────────────────────────┐
│                   THE CONVERGENCE LEARNING STACK                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────┐   │
│  │    RLP      │   │    SAO      │   │  Constitutional AI  │   │
│  │ (reasoning) │   │ (data gen)  │   │   (alignment)       │   │
│  └──────┬──────┘   └──────┬──────┘   └──────────┬──────────┘   │
│         │                 │                      │              │
│         ▼                 ▼                      ▼              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    EXPERIENCE BUFFER                     │   │
│  │  (thoughts, rewards, preferences, principles)            │   │
│  └────────────────────────┬────────────────────────────────┘   │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                  │
│         ▼                 ▼                 ▼                  │
│  ┌───────────┐     ┌───────────┐     ┌───────────┐            │
│  │  MemRL    │     │ Thompson  │     │  SELAUR   │            │
│  │ (memory)  │     │ Sampling  │     │(uncertty) │            │
│  └─────┬─────┘     └─────┬─────┘     └─────┬─────┘            │
│        │                 │                 │                   │
│        └─────────────────┼─────────────────┘                   │
│                          │                                      │
│                          ▼                                      │
│               ┌─────────────────────┐                          │
│               │   POLICY UPDATE     │                          │
│               │  (DPO / PPO / GAE)  │                          │
│               └─────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 7: Implementation Priorities

| Priority | Method | Files | Effort | Impact |
|----------|--------|-------|--------|--------|
| 1 | Connect RLP to MAB | 2 | Low | High |
| 2 | Add Constitutional YAML | 3 | Medium | High |
| 3 | Integrate SAO with DPO | 4 | Medium | High |
| 4 | Add MemRL plugin | 3 | Medium | High |
| 5 | Add SELAUR uncertainty | 2 | Low | Medium |
| 6 | Add MAE co-evolution | 4 | High | High |

---

## Sources

### Original Papers (Already Implemented)
- [RLP: Reinforcement as a Pretraining Objective (NVIDIA)](https://arxiv.org/abs/2510.01265)
- [SAO: Aligning LLMs via Fully Self-Synthetic Data](https://arxiv.org/abs/2510.06652)

### Novel Methods to Add
- [EvolveR: Self-Evolving LLM Agents through Experience-Driven Lifecycle](https://arxiv.org/abs/2510.16079)
- [Multi-Agent Evolve: LLM Self-Improve through Co-evolution](https://arxiv.org/abs/2510.23595)
- [MemRL: Self-Evolving Agents via Runtime RL on Episodic Memory](https://arxiv.org/html/2601.03192v1)
- [Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/abs/2212.08073)
- [Survey of Self-Evolving Agents](https://arxiv.org/abs/2507.21046)

### Resources
- [Awesome RLAIF (GitHub)](https://github.com/mengdi-li/awesome-RLAIF)
- [Awesome Self-Evolving Agents (GitHub)](https://github.com/EvoAgentX/Awesome-Self-Evolving-Agents)
- [Constitutional AI & AI Feedback (RLHF Book)](https://rlhfbook.com/c/13-cai)

---

*Deep dive generated: 2026-03-12*
*For: The Convergence learning plugin enhancement*
