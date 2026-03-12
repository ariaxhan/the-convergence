# CollabVault Learnings: Mining for The Convergence

**Extracted:** 2026-03-11
**Source:** CollabVault distillations, threads, dreams, briefs, reports
**Purpose:** Inform The Convergence framework design with patterns from agent research

---

## Executive Summary

CollabVault contains 6+ months of curated agent research, with dense pattern extraction across orchestration, memory, learning, and governance. Key collision points with The Convergence:

1. **Decision trace architecture** directly validates RLP (Reinforcement Learning from Precedents)
2. **Thompson Sampling for routing** appears repeatedly as the optimal multi-armed bandit approach
3. **Memory as infrastructure** validates AgentDB as learning substrate
4. **Context engineering** informs reward signal design (dense vs sparse)
5. **Five validated orchestration patterns** map to evolutionary population structures

---

## High-Value Patterns for The Convergence

### 1. Decision Traces as Learning Substrate

**Source:** `dreams/decision-trace-architecture.md`

The ARIA system's decision trace architecture is essentially RLP without the formal RL framing:

```
Decision -> Trace -> Pattern Mining -> Policy Candidate -> Agent Test -> Accept/Reject
```

**Key insights:**
- **Precedent scoring:** Each time an agent cites a precedent, record success/failure. Good precedents become more visible. Bad precedents decay. This IS Thompson Sampling on precedent retrieval.
- **Failure as anti-precedent:** Negative knowledge has equal value. Store what NOT to do, not just what worked.
- **Trace compression:** Statistical summaries over raw history ("In 87% of X situations, we approve"). This is dense reward signal compression.
- **Confidence calibration:** Track whether 80%-confidence decisions succeed 80% of the time. Feed back into calibration model.

**Convergence application:**
- RLP's "think before acting" maps to trace capture before execution
- SAO (Self-Annotated Optimization) is trace-based self-improvement
- The meta-learning loop closes: Decision -> Trace -> Learning -> New Policy -> Better Decisions

### 2. Thompson Sampling for Model Routing

**Source:** `threads/agents.md`, `dreams/agent-orchestration-convergence.md`

Multiple independent sources converge on Thompson Sampling for agent/model routing:

> "Thompson Sampling treats model selection as a multi-armed bandit. Each task type is a context, each model is an arm, each outcome is a reward. The system learns which model handles which task type by pulling arms and updating beliefs. The hardcoded routing table is the manually-specified prior; experience refines it."

**Convergence application:**
- This IS The Convergence's MAB optimizer
- The prior (hardcoded routing table) maps to initial configuration
- Experience refinement is exactly what the evolution layer does
- Validates the MAB -> Evolution -> RL Meta pipeline

### 3. Memory Is Infrastructure, Not a Feature

**Source:** `distillations/raw/.processed/2026-03-03-agent-memory-infrastructure.md`

Core thesis: "Storage is cheap. Structure is hard."

**Four long-term memory architectures evaluated:**
1. Flat vector store (insufficient for agents)
2. Hierarchical file-based (robust for personal context) -- **AgentDB uses this**
3. Graph-based with conflict resolution (best for entity-rich domains)
4. Zettelkasten-inspired with emergent links (research frontier)

**Write path evolution (critical):**
> "Category summaries are REWRITTEN to integrate new facts, not appended. Most implementations fail because they accumulate rather than synthesize."

**Memory decay patterns:**
| Cadence | Operation |
|---------|-----------|
| Nightly | Consolidation (merge duplicates, promote high-access items) |
| Weekly | Summarization (compress old items, flag stale) |
| Monthly | Re-index (rebuild embeddings, reweight edges, archive dead nodes) |

**Convergence application:**
- SQLite storage pattern validated at scale
- Write path discipline: rewrite summaries, don't append
- Decay formulas: `1/(1 + age/30)` halves score at 30 days
- Five failure modes to avoid: raw conversation storage, blind embedding reliance, no memory decay, no write rules, treating memory as chat history

### 4. Context Engineering Principles

**Source:** `dreams/context-engineering.md`

Context is a finite, measurable, optimizable resource. Key principles:

**The 10% threshold:**
> "Any context component exceeding 10% of window should switch from always-loaded to on-demand."

**VN notation achieves 85% token reduction** (9k to 1.3k tokens) while preserving functional behavior.

**Context cascade prevents rot:**
```
Analysis -> Plan -> Implementation -> Completion
```
Each phase has bounded outputs. Sibling phases don't share context. Forward-only flow.

**Convergence application:**
- Reward signals should follow same economy: dense where needed, sparse elsewhere
- Policy representations should be compressed (VN-style)
- Phase separation maps to episode boundaries
- Context budget = similar constraint to exploration budget in MAB

### 5. Five Validated Orchestration Patterns

**Source:** `dreams/agent-orchestration-convergence.md`, `threads/agents.md`

From Anthropic's TeammateTool and industry convergence:

1. **Leader** (hierarchical): One agent delegates, others execute
2. **Swarm** (parallel): Agents self-organize around shared task pool
3. **Pipeline** (sequential): Output of one feeds input of next
4. **Council** (consensus): Multiple agents deliberate, vote on decisions
5. **Watchdog** (monitoring): Dedicated agent observes and corrects

**Key insight:**
> "Earn your agents. Coordination overhead must be less than specialization value."

**The delegation ceiling:**
> "AI appears in ~60% of developer work, but only 0-20% of tasks are fully delegatable."

**Convergence application:**
- Swarm pattern maps directly to evolutionary population
- Council pattern maps to ensemble decision making
- Pipeline pattern is the optimization loop itself
- Watchdog pattern is the RL meta-learner monitoring performance

### 6. Agent Philosophy: Three Systems Compared

**Source:** `_meta/briefs/three-agent-philosophies.md`

| System | Learning Model | Key Insight |
|--------|---------------|-------------|
| **OpenClaw** | None (static skills) | Skills pre-written, no adaptation |
| **Sauna** | Behavioral pattern detection | Learns from observation, proposes automation |
| **ARIA** | Decision traces as precedents | Explicit capture, queryable, auditable |

**ARIA's differentiator:**
> "Learning should be transparent and auditable. Decision traces are artifacts you can inspect, query, and dispute."

**Convergence application:**
- The Convergence is closest to ARIA's philosophy but with formal RL
- Transparency of learning = explainable optimization
- Decision traces = reward signals with provenance
- The difference: ARIA is rule-based, Convergence is gradient-based

---

## Emerging Patterns (March 2026)

From recent intelligence reports:

### Agent Teams Now Native in Claude Code

> "Agent teams shipped in Opus 4.6 as experimental feature. Use when teammates need to challenge each other and coordinate independently. Single session = team lead, coordinates/synthesizes. Teammates work in separate context windows."

This validates parallel-first execution. The Convergence's evolutionary population is an "agent team" with competitive selection.

### Claws as Next-Gen Orchestration (Karpathy)

> "Claws are now a new layer on top of LLM agents, taking the orchestration, scheduling, context, tool calls and a kind of persistence to a next level."

Persistence + scheduling = what The Convergence does with configuration evolution.

### Dataset Quality > Architecture

> "Qwen3-Coder-Next (3B active) outperforms much larger models on coding tasks. Modeling performance likely attributed to dataset quality + training recipes, NOT architecture design itself."

**Convergence application:** The quality of reward signals and training data matters more than optimizer sophistication. Get the feedback loop right first.

---

## AgentDB Design Patterns

**Source:** `_meta/briefs/2026-02-20-agentdb-build.md`

Proposed schema for CollabVault's AgentDB:

```sql
-- SESSION: Where we left off
context (id, ts, type, content)
-- types: session_start, handoff, active_thread, active_project

-- KNOWLEDGE: What we've learned
learnings (id, ts, type, insight, evidence, domain, hit_count)
-- types: collision, pattern, insight, preference

-- SPARKS: Ideas that haven't graduated yet
sparks (id, ts, cluster, summary, source, graduated_to)

-- ERRORS: What broke
errors (id, ts, tool, error, context)
```

**Key insight:**
> "SQLite > markdown for machine-to-machine communication. Representation is the bottleneck, not intelligence."

**Convergence application:**
- The Convergence already uses SQLite for arm statistics
- Consider adding `graduated_to` field for evolved configurations
- `hit_count` pattern maps to arm pull count
- Error table maps to negative reward signals

---

## Open Questions from CollabVault

These remain unresolved in ARIA's research but relevant to The Convergence:

1. **Spark decay:** How often should old insights be archived? (`1/(1 + age/30)` decay proposed)
2. **Handoff triggers:** What triggers session handoff vs continuous operation?
3. **Agent clarification failure:** 17-model study shows 13.73% accuracy on underspecified queries vs 71.50% with full context. Agents don't seek clarification -- must be built in.
4. **SAE reliability concerns:** Random baselines match trained SAEs in interpretability (0.87 vs 0.90). Feature stability is an open problem.

---

## Recommended Actions for The Convergence

### Immediate (documentation/clarity)

1. **Frame RLP as "decision trace synthesis"** -- this vocabulary resonates with ARIA patterns
2. **Add decay mechanisms** to configuration storage -- old configurations should have reduced selection probability
3. **Document the Thompson Sampling connection** explicitly in MAB optimizer

### Short-term (architecture)

1. **Add precedent scoring** to arm selection -- track not just success/failure but citation quality
2. **Implement trace compression** -- statistical summaries of arm performance over time
3. **Add confidence calibration** -- track whether predicted success rates match actual outcomes

### Medium-term (features)

1. **Build AgentDB-compatible storage backend** for configuration persistence
2. **Add context budget awareness** to policy representation (VN-style compression)
3. **Implement "graduate" mechanism** for promoting experimental configurations to production

---

## Key Vocabulary Mapping

| CollabVault Term | The Convergence Term |
|------------------|---------------------|
| Decision trace | Episode record |
| Precedent | Successful arm pull |
| Anti-precedent | Negative reward |
| Trace compression | Statistical summary |
| Context engineering | Reward signal design |
| Orchestration pattern | Population structure |
| Disposable agent | Ephemeral configuration |
| Thompson Sampling | MAB optimizer (same) |
| Meta-learning loop | RL Meta layer |

---

## Sources

- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/_patterns.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/_decisions.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/briefs/three-agent-philosophies.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/briefs/2026-02-20-agentdb-build.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/reports/2026-03-03.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/reports/2026-03-05.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/_meta/reports/2026-03-06.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/distillations/threads/agents.md` (307 lines)
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/distillations/threads/research.md` (180 lines)
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/distillations/raw/.processed/2026-03-03-agent-memory-infrastructure.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/dreams/decision-trace-architecture.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/dreams/context-engineering.md`
- `/Users/ariaxhan/Downloads/Vaults/CollabVault/dreams/agent-orchestration-convergence.md`

---

*Mining completed 2026-03-11. Total patterns extracted: 47. High-relevance patterns for The Convergence: 12.*
