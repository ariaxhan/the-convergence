# Context Graphs: The Missing Layer

**Date:** 2026-03-12
**Source:** Conversation with Stanley (Lattice Protocol), aDNA architecture
**Status:** Research synthesis

---

## The Problem

Current AI agent architectures have a knowledge problem:

```
Traditional RAG:
  Query → Embed → Find similar chunks → Generate

The issue: No structure. No relationships. No context about context.
```

When agents "start every session cold," they lack:
- Project structure and architecture
- Prior decisions and their rationale
- Current state and active work
- Relationships between entities (who owns what, what depends on what)

Vector embeddings capture *similarity* but not *structure*. You can find similar text, but you can't answer "who made this decision and why?"

---

## What Context Graphs Add

A context graph is a **structured knowledge representation** that both humans and AI agents can navigate.

### The aDNA Triad (from Lattice Protocol)

Stanley's aDNA architecture organizes knowledge into three fundamental categories:

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

Every piece of project knowledge fits into exactly ONE category.
No ambiguity. Both humans and agents can navigate.
```

### Progressive Disclosure

Instead of loading everything into context, the graph enables **narrowing**:

```
Campaign (strategic, weeks)
    └── Phase (logical grouping)
            └── Mission (multi-session)
                    └── Objective (session-sized)

Each level narrows context:
- Fewer tokens
- Higher signal density
- Relevant to the current task
```

### Session Continuity

Agents don't start cold. They inherit:
- **STATE.md** — Current operational state
- **SITREPs** — Handoff documents from previous sessions
- **Coordination files** — What other agents are working on

### Graph Operations

| Operation | What It Does |
|-----------|--------------|
| **Traverse** | Follow relationships (who owns this? what depends on this?) |
| **Extract** | Build context payload from subgraph for current session |
| **Merge** | Combine graphs from different sources (graph product on ontologies) |
| **Evolve** | Graph structure improves over time (ties to self-learning!) |

---

## How This Fits The Convergence

### Current Architecture (What We Have)

```
┌─────────────────────────────────────────────────────────────┐
│  SAFETY → OBSERVABILITY → OPTIMIZATION → STORAGE            │
└─────────────────────────────────────────────────────────────┘
```

### Enhanced Architecture (With Context Graphs)

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  KNOWLEDGE LAYER (The Foundation of Everything)             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Context Graph                                       │    │
│  │  • Ontology: who/what/how triad                     │    │
│  │  • Relationships: edges with semantics              │    │
│  │  • Provenance: where did this knowledge come from?  │    │
│  │  • State: what's current? what's historical?        │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│  SAFETY LAYER            │                                  │
│  ┌───────────────────────┴─────────────────────────────┐    │
│  │  Guardrails informed by graph                       │    │
│  │  • WHO has permission to access WHAT?               │    │
│  │  • HOW should this knowledge be used?               │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│  OBSERVABILITY LAYER     │                                  │
│  ┌───────────────────────┴─────────────────────────────┐    │
│  │  Metrics connected to graph                         │    │
│  │  • Which knowledge is being accessed?               │    │
│  │  • Which relationships are traversed often?         │    │
│  │  • Where are gaps in the graph?                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│  OPTIMIZATION LAYER      │                                  │
│  ┌───────────────────────┴─────────────────────────────┐    │
│  │  Learning improves the graph                        │    │
│  │  • Thompson Sampling on retrieval strategies        │    │
│  │  • Graph structure evolves based on usage           │    │
│  │  • Context payloads optimized for task type         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### The Key Insight

**The context graph is not a feature. It's the substrate.**

Everything else operates ON the graph:
- Safety checks WHO has access to WHAT via HOW
- Observability tracks which parts of the graph are used
- Optimization learns which graph traversals work best
- Storage persists the graph across sessions

---

## Implementation Considerations

### Scaling: File → SQLite → PostgreSQL

Stanley's insight:

> "As nodes start growing, context/file-tree search starts to be a drag on perf... wanna figure out what a good SQLite solution could be, when would be the 'hand-off-point'"

**The Convergence already has this:**
- SQLite for development
- PostgreSQL for production
- Same API for both

**What we need to add:**
- Graph schema (nodes, edges, ontology types)
- Graph operations (traverse, extract, merge)
- Migration path from file-based to database-backed

### Schema Design

```sql
-- Nodes (the entities)
CREATE TABLE graph_nodes (
    id TEXT PRIMARY KEY,
    ontology_type TEXT NOT NULL,  -- 'who', 'what', 'how'
    entity_type TEXT NOT NULL,    -- 'person', 'decision', 'process', etc.
    content TEXT,                 -- The actual knowledge
    metadata JSONB,               -- Flexible metadata
    embedding VECTOR(768),        -- For hybrid search
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Edges (the relationships)
CREATE TABLE graph_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES graph_nodes(id),
    target_id TEXT REFERENCES graph_nodes(id),
    relationship_type TEXT,       -- 'owns', 'depends_on', 'created', etc.
    weight REAL DEFAULT 1.0,      -- For learning which edges matter
    metadata JSONB,
    created_at TIMESTAMP
);

-- Session context (what was loaded for this session)
CREATE TABLE session_context (
    session_id TEXT PRIMARY KEY,
    node_ids TEXT[],              -- Which nodes were in context
    edge_ids TEXT[],              -- Which edges were traversed
    task_type TEXT,               -- Campaign, mission, objective
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    sitrep TEXT                   -- Handoff document
);
```

### Graph Operations

```python
class ContextGraph:
    """The knowledge substrate."""

    async def traverse(
        self,
        start_node: str,
        relationship_types: list[str],
        max_depth: int = 3
    ) -> Subgraph:
        """Follow relationships from a starting point."""
        ...

    async def extract_context(
        self,
        task_type: str,
        focus_nodes: list[str],
        token_budget: int = 8000
    ) -> ContextPayload:
        """Build optimal context payload for current task."""
        # Progressive disclosure: narrow to what's relevant
        # Stay within token budget
        # Include provenance (where did this come from?)
        ...

    async def merge(
        self,
        other: "ContextGraph",
        conflict_resolution: Literal["ours", "theirs", "manual"] = "manual"
    ) -> "ContextGraph":
        """Combine two graphs via ontology product."""
        # Graph product on ontologies
        # Resolve conflicts
        # Return unified graph
        ...

    async def record_usage(
        self,
        session_id: str,
        nodes_accessed: list[str],
        edges_traversed: list[str],
        outcome: float
    ):
        """Feed back to optimization layer."""
        # Which traversals worked?
        # Update edge weights
        # Learn optimal context extraction
        ...
```

---

## Integration with Existing Components

### With Semantic Cache

```python
# Before: Pure similarity
cached = await cache.get(query)

# After: Graph-informed
subgraph = await graph.extract_context(task_type, focus_nodes)
cached = await cache.get(query, context=subgraph.summary)
```

The graph provides **context** for the cache. Similar queries might need different cached responses depending on *where in the graph* they originate.

### With Safety Guardrails

```python
# Before: Check permissions generically
if not rails.check_permission(user, action):
    deny()

# After: Graph-informed permissions
node = await graph.get_node(target_resource)
owner = await graph.traverse(node, ["owned_by"])
if not rails.check_permission(user, action, owner):
    deny()
```

The graph encodes WHO owns WHAT and HOW it should be accessed.

### With Thompson Sampling

```python
# Before: Learn which arms work
selection = await bandit.select(arms)

# After: Learn which graph traversals work
traversal_strategy = await bandit.select(traversal_arms)
context = await graph.extract_context(strategy=traversal_strategy)
# ... use context, get reward ...
await bandit.update(traversal_strategy, reward)
```

The optimization layer learns which parts of the graph are valuable for which tasks.

---

## The Vision: Mergeable Knowledge

Stanley's key insight:

> "You can simply 'merge' in the comic book generator and get it to make a comic from/about your context."

This is powerful for enterprise:
- **Company knowledge graph** (org structure, policies, history)
- **Project knowledge graph** (decisions, artifacts, state)
- **Domain knowledge graph** (industry, regulations, best practices)
- **Personal knowledge graph** (preferences, context, history)

Merge them for the current session. The agent has all relevant context without loading everything.

---

## Implementation Priority

### Phase 1: Core Graph (MVP)
- Node/edge schema in existing storage backends
- Basic traverse and extract operations
- Integration with session tracking

### Phase 2: Progressive Disclosure
- Execution hierarchy (campaign → objective)
- Token-budget-aware context extraction
- SITREP generation for handoffs

### Phase 3: Graph Learning
- Thompson Sampling on traversal strategies
- Edge weight learning based on usage
- Automatic ontology refinement

### Phase 4: Merge Operations
- Graph product on ontologies
- Conflict resolution strategies
- Cross-graph queries

---

## Questions for Stanley

1. **Handoff point:** At what node count does file-based become slow? 100? 1000? 10000?

2. **Ontology evolution:** How do you handle when the triad categories need to change? New entity types?

3. **Merge conflicts:** When two graphs have conflicting decisions, how does resolution work?

4. **Embedding + graph:** Do you use embeddings alongside the graph? Or is the graph structure sufficient for retrieval?

5. **Multi-tenant:** How would this work for an enterprise with multiple teams, each with their own graph that sometimes needs to merge?

---

## Key Takeaway

The context graph is not "another feature" — it's the **substrate** that makes everything else work better:

- Safety is graph-aware (who owns what)
- Observability tracks graph usage
- Optimization learns graph traversals
- Caching is context-aware

This is what separates "beyond RAG" from "slightly better RAG."

---

*Research synthesized from Stanley (Lattice Protocol) + aDNA architecture*
*For: The Convergence knowledge layer design*
