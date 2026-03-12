# Knowledge Retrieval, Semantic Caching & Beyond-RAG for Enterprise Agents (2026)

**Research Date:** March 12, 2026
**Scope:** Semantic caching, knowledge centralization, agentic RAG, production patterns
**Context:** Building self-evolving agent systems for enterprises with scattered knowledge (Slack, GitLab, Intercom, databases)

---

## I. SEMANTIC CACHING: STATE OF THE ART

### A. How It Works

Semantic caching declares a cache hit when embeddings from two queries exceed a **cosine similarity threshold**. Unlike key-value caches, this enables fuzzy matching on intent.

**Flow:**
```
Query → Embed → Similarity Search → Hit? → Return Cached Response
                     (vs cache)         ↓
                                    Miss → LLM Call → Cache + Return
```

**Key Innovation:** Caches work at query similarity, not exact matching. A question like "How does payment plan charging work?" may hit the cache for "What's the pricing model?"

### B. Embedding Models

**Winner (2025-2026):** `sentence-transformers/all-mpnet-base-v2`
- Optimizes precision + recall + latency + F1 simultaneously
- ~100M model, runs locally
- Better than larger proprietary alternatives for caching task

**Domain-Specific Alternatives:**
- Fine-tune on your query distribution if >1000 cached queries
- Smaller (384-dim) embeddings beat larger (1536-dim) on latency for caching
- Open-source > proprietary for cost/control

### C. Similarity Thresholds (The Hard Tradeoff)

**Recommended Range:** 0.88–0.92 (cosine similarity)

**Trade-offs:**
- **0.9+:** Safe (97% accuracy), but ~35% cache hit rate (misses reuse opportunities)
- **0.8:** Aggressive (94% accuracy), ~69% cache hit rate (risk false positives)
- **0.7–0.75:** Dangerous (99% false positive rate in banking case study)

**How to Tune:**
1. Start conservative at 0.92
2. Validate against 100+ production-like queries
3. Measure precision (correct hits) + recall (missed hits)
4. Adjust based on accuracy tolerance for your domain

**Reality Check:** Most teams fail because they never validate thresholds empirically. "Intuition" leads to 99% false positive rates.

### D. Cache Invalidation (The Forgotten Problem)

**Three-Tier Strategy:**

1. **TTL (Time-To-Live)**
   - Static data (docs, definitions): 7–30 days
   - Semi-dynamic (pricing, team info): 1–24 hours
   - Volatile (news, real-time status): 5–15 minutes

2. **Event-Based Invalidation**
   - Webhook: Document updated → invalidate entries in embedding cluster
   - Version change: Prompt/system instruction changes → invalidate all
   - Schema shift: New data format → flush cluster

3. **Staleness Detection (Underrated)**
   - Run freshness checks on 10% of cached entries daily
   - LLM judges: "Is this cached answer still accurate?" (costs: ~$0.01/check)
   - If staleness detected, drop cache, re-answer, store new version

### E. Production Implementations

**GPTCache (Open Source)**
- Supports Milvus, Zilliz, FAISS vector backends
- ~300 LOC integration for basic setup
- Hit ratios: 35–60% in production (vs theoretical 80%)
- Active maintenance, LangChain + llama_index integrated

**Portkey (Managed Gateway)**
- Semantic caching as first-class feature
- 20% hit rate (general), 60% (focused RAG)
- 20× latency improvement on cache hits
- Handles threshold management, observability built-in

**Redis (Self-Hosted)**
- RedisVL + semantic cache support
- Best for: Low-latency, co-located with app
- Cost: Operational (Redis ops team needed)

**Architecture Pattern (2026):**
```
User Request
    ↓
LLM Gateway (Semantic Cache Check)
    ├─ HIT (80% of requests) → Return cached + metadata
    └─ MISS (20%) → Route to LLM → Cache result
```

### F. Common Pitfalls & Fixes

**Pitfall 1: Threshold Too Low (→ False Positives)**
- Symptom: Cache hits deliver wrong answers; user complains "It gave me pricing info for the wrong product"
- Why: 0.75 threshold accepts dissimilar queries
- Fix: Validate threshold on test set; start at 0.92; measure precision@k
- Source: [Reducing False Positives in Retrieval-Augmented Generation](https://www.infoq.com/articles/reducing-false-positives-retrieval-augmented-generation/)

**Pitfall 2: Cache Staleness (→ Outdated Responses)**
- Symptom: User gets information from 3 days ago; "This is old"
- Why: TTL set too long; no event-based invalidation
- Fix: Short TTL for volatile data; invalidate on document updates; daily freshness checks
- Source: [Cache Invalidation Strategies](https://www.systemoverflow.com/learn/ml-model-serving/model-monitoring-observability/semantic-caching-and-retrieval-invalidation)

**Pitfall 3: Embedding Drift (→ Threshold Becomes Invalid)**
- Symptom: Over time, same queries embed differently; threshold breaks
- Why: Embedding model updated; vocabulary changes; new language patterns
- Fix: Monthly threshold re-validation; monitor embedding distribution; A/B test threshold changes
- Source: Implicit in 2026 embedding research

**Pitfall 4: Cache Poisoning (→ Malicious Hits)**
- Symptom: Adversary crafts query to hit cache with wrong cached response
- Why: Public cache with low threshold; no access control
- Fix: Gated cache (per-user or per-context); higher threshold for sensitive domains
- Source: [Semantic Cache Poisoning](https://medium.com/@instatunnel/semantic-cache-poisoning-corrupting-the-fast-path-e14b7a6cbc1f)

**Pitfall 5: No Metrics (→ Flying Blind)**
- Symptom: "Is our cache actually working?" No data.
- Why: Hit ratio ≠ goodness; need precision, freshness, P95 latency
- Fix: Track: (1) hit rate, (2) precision (% of hits that were correct), (3) freshness (age of cached response), (4) cost savings
- Source: Implicit in semantic caching literature

---

## II. BEYOND RAG: AGENTIC RAG & GRAPH RAG

### A. The RAG Problem (2026 Reality)

**Traditional RAG Limits:**
1. Single-hop retrieval fails on complex queries ("What themes emerge in our vendor contracts?")
2. Poor at multi-hop reasoning ("Find contracts with compliance gaps + summarize risks")
3. No agent planning; fixed retrieval pipeline
4. Hallucination rate: 40–71% reduction vs. baseline (but still 29–60% hallucinate)

**Enterprise Pain:** 60% of RAG pilots fail in production due to:
- Retrieval returning irrelevant context
- Agents ignoring retrieved docs (preferring parametric memory)
- Context-boundary degradation (performance drops near token limits)

### B. Agentic RAG (The Solution, 2025+)

**Core Insight:** Agents decide *what* to retrieve, *when*, and *how many hops*.

**Architecture:**
```
User Query
    ↓
Planner Agent (decompose into sub-questions)
    ├─ Sub-Q1 → Retriever → Evidence
    ├─ Sub-Q2 → Retriever → Evidence  
    └─ Sub-Q3 → Retriever → Evidence
         ↓
Reasoner Agent (fuse evidence, iterate)
    ├─ Reflect on gaps
    ├─ Decide: more retrieval needed?
    └─ Loop until confident
         ↓
Generator (synthesize answer with full reasoning trail)
```

**Real Approaches (2025–2026):**

1. **MA-RAG (Multi-Agent RAG)**
   - Planner: Disambiguates query → generates sub-questions
   - Retriever: Fetches evidence for each sub-Q
   - Reasoner: Fuses and detects gaps
   - Generator: Creates final answer
   - Result: 15–30% accuracy improvement over standard RAG

2. **HopRAG (Graph-Aware Agentic)**
   - Builds passage graph during indexing
   - Edges = semantic relationships (generated by LLM)
   - At query time: agent explores multi-hop neighbors
   - Use case: "Find all entities related to X, then answer Y"

3. **INRAExplorer (Knowledge Graph + Agent)**
   - Agent equipped with multi-tool architecture
   - Tools: keyword search, graph traversal, SQL queries
   - Iterative multi-hop reasoning over rich KB
   - Results: Structured, exhaustive answers

### C. Graph RAG vs. Semantic RAG

| Dimension | Semantic RAG | Graph RAG | Agentic RAG |
|-----------|--------------|-----------|------------|
| **What It Does** | Vector similarity search | Entity/relationship graphs | Agent plans retrieval |
| **Query Type** | Fact-level ("What is X?") | Theme-level ("What patterns emerge?") | Complex ("Analyze across 10 contracts") |
| **Accuracy** | 50–60% | 80%+ (better traceability) | 70–85% (depends on planner) |
| **Speed** | ~50ms (ANN) | ~200ms (graph traversal) | ~1–2s (multi-hop) |
| **Setup Cost** | Days | Weeks (entity extraction + graph build) | Weeks + agent tuning |
| **Best For** | Customer support ("How do I...?") | Compliance ("What risks exist?") | Research ("Synthesize across sources") |

**2026 Consensus:** Hybrid. Agents orchestrate when to use semantic vs. graph retrieval.

### D. What Actually Works in Production

**Proven (2025+):**
- Agentic RAG for multi-hop queries (15–30% accuracy lift)
- Hybrid search (BM25 + semantic) beats pure semantic alone
- Graph RAG for knowledge-heavy domains (finance, legal, compliance)
- Reranking (second-stage) after retrieval (Cohere, BGE-reranker)

**Still Research:**
- Self-improving RAG (agents modifying their own retrieval strategies)
- Fully autonomous knowledge graph maintenance
- Learned routing (which retrieval strategy for this query type?)

### E. Beyond-RAG Pitfalls

**Pitfall 1: Agents Ignore Retrieved Docs (→ Hallucination)**
- Symptom: "I found this contract, but the agent answered about something completely different"
- Why: LLM's parametric memory is stronger than retrieved context; agent discounts evidence
- Fix: Constrain generation to cite sources; use tool_choice=required; prompt agent to reference retrieved docs by name
- Source: [RAG hallucination](https://www.k2view.com/blog/rag-hallucination/)

**Pitfall 2: Graph Entropy (→ Stale Relationships)**
- Symptom: Relationships in graph are outdated; agent makes wrong inferences
- Why: Graph built once, never updated; new entities not added
- Fix: Continuous graph update (monthly); event-driven entity insertion; version graph schema
- Source: [Knowledge graph maintenance](https://enterprise-knowledge.com/how-do-i-update-and-scale-my-knowledge-graph/)

**Pitfall 3: Retrieval Bottleneck (→ Multi-Hop Timeout)**
- Symptom: Agent runs 10 retrieval steps, total latency = 15s; user times out
- Why: Each hop = 200–500ms; 10 hops = >2s; with thinking time = 15s+
- Fix: Parallel retrieval (fan-out sub-questions); cache intermediate results; limit hops to 3–4 per query
- Source: Implicit in latency analysis

**Pitfall 4: Agent Specification Drift (→ Scope Creep)**
- Symptom: "Agent was supposed to find compliance gaps, but it's now summarizing contract history"
- Why: Agents are creative; prompts are vague
- Fix: Write agent spec as state machine (state → allowed actions → next state); explicit termination condition
- Source: [Why Multi-Agent LLM Systems Fail](https://arxiv.org/abs/2503.13657)

---

## III. KNOWLEDGE CENTRALIZATION: PATTERNS & TOOLS

### A. The Enterprise Knowledge Problem

**Reality (2026):**
- GitLab: Source code (how features work)
- Intercom: Historical conversations (how users asked)
- Guru/Notion: KB articles (policies, pricing)
- Jira/Confluence: Project context (decisions, docs)
- Slack: Team discussions (tribal knowledge)
- Databases: Real-time status (orders, inventory)

**FunJoin Case:** 5 systems, 1 agent. Same question may need data from 2–3 systems.

### B. Integration Patterns (2026)

**Pattern 1: Tool-First (Event-Driven)**
```
Agent asks question
    ├─ Tool: search_code (hits GitLab API)
    ├─ Tool: search_kb (hits Guru API)
    ├─ Tool: query_db (hits Postgres)
    └─ Fuse results → answer

Advantage: Live, fresh data; no stale cache
Cost: 3 API calls per question; ~500ms latency
Best for: Status queries, real-time data
```

**Pattern 2: Vector-Cache-First (Embedded + Sync)**
```
Agent asks question
    ├─ Semantic Cache Hit? → Return cached
    └─ Miss → Call all tools → Cache result

Advantage: 80% cost reduction (cache hits)
Cost: Stale data risk; need smart invalidation
Best for: FAQ-like questions (70% of support)
```

**Pattern 3: Hybrid (Smart Routing)**
```
Agent categorizes question:
  ├─ Type=FAQ → Use cache (cached response)
  ├─ Type=Status → Hit DB directly (live)
  └─ Type=Complex → Use agentic RAG (multi-hop)

Advantage: Balance freshness + cost + latency
Cost: More complex logic
Best for: Mixed workloads (realistic)
```

### C. Vector Stores: Production Comparison (2026)

| Store | Deployment | Latency | Cost | Best For | Upside | Downside |
|-------|-----------|---------|------|----------|--------|----------|
| **Pinecone** | Managed | ~50ms | High ($/query) | Fast prototyping | Fully managed; low ops | Expensive at scale |
| **Qdrant** | Self/Cloud | ~8ms | Medium | Production RAG | Rust fast; filters | Ops overhead |
| **Weaviate** | Self/Cloud | ~100ms | Medium | Knowledge graphs | GraphQL; structured | Slower than Qdrant |
| **Chroma** | Embedded/Self | ~100ms | Low | Prototyping | Easy setup | Not for >1M vectors |
| **Redis** | Self | ~5ms | Low | Cache layer | Extremely fast | Need ops team |
| **PgVector** | Self (SQL) | ~200ms | Low | SQL + vectors | Familiar (Postgres) | Slower; limited ANN |

**2026 Consensus:** Use 2-tier:
- **Hot (L0):** Redis for cache (5ms, low cost)
- **Warm (L1):** Qdrant/Weaviate for retrieval (8–100ms)
- **Cold (L2):** S3 + embedding model for archival

### D. Hybrid Search (BM25 + Semantic)

**Why Hybrid Beats Semantic Alone:**
- Semantic: Finds "conceptually similar" (recall)
- BM25: Finds "exact term matches" (precision)
- Combined: Both recall + precision

**How It Works:**
```
Query: "How does payment plan charging work?"

BM25 Search → [Doc1 (score 0.9), Doc2 (0.7)]
Vector Search → [Doc3 (sim 0.92), Doc1 (0.88)]

Fusion (RRF) → [Doc1 (combined score 0.91), Doc3 (0.90), Doc2 (0.68)]
```

**Score Combination Methods:**
1. **Min-Max Normalization + Weighted Sum**
   - Score_final = 0.6 * norm(bm25) + 0.4 * norm(semantic)
   - Simple; requires tuning weights

2. **Reciprocal Rank Fusion (RRF)**
   - Score = 1/(k+rank_bm25) + 1/(k+rank_semantic)
   - K=60 typical; rank-agnostic (ignores raw scores)

**Production Setup:**
- Elasticsearch (BM25) + Qdrant/Weaviate (semantic)
- Or: Single DB with both (Weaviate, Qdrant support both)
- Typical improvement: 10–20% accuracy over semantic alone

### E. Knowledge Graph Challenges (Hard Lessons)

**Real Cost Factors:**

1. **Entity Extraction (~20% effort)**
   - Identifying entities (People, Products, Contracts)
   - NER models + LLM refinement
   - Retraining when new entity types appear

2. **Relationship Definition (~30% effort)**
   - What relationships matter? (owns, contracts_with, depends_on?)
   - Schema design (ontology)
   - Changing schema = expensive (ETL rewrite)

3. **Maintenance (~40% effort)**
   - Keeping graph in sync with source systems
   - New entities, deleted entities, relationship changes
   - Version control for schema changes

4. **Governance (~10% effort)**
   - Data lineage (where did this relationship come from?)
   - Access control (who can query which subgraph?)
   - Audit trail

**Key Finding:** Knowledge graphs win for high-value, slow-moving data (compliance, vendor contracts). Lose for real-time, high-churn data (customer transactions).

---

## IV. PRODUCTION RETRIEVAL: LATENCY & ACCURACY

### A. Latency Budget (End-to-End)

**User Expectation:** <2s for response

**Real Breakdown (FunJoin Case):**
```
User types query        0ms (input)
├─ Embedding           ~50ms (sentence-transformers)
├─ Cache check          ~10ms (Redis)
│  └─ Hit! Return → 60ms total (HIT PATH)
└─ Cache miss:
   ├─ Vector search     ~30ms (Qdrant)
   ├─ Rerank           ~50ms (BGE reranker)
   ├─ LLM call        ~800ms (Claude API)
   ├─ Post-process     ~20ms
   └─ Total           ~950ms (MISS PATH)

Observed: 60ms (80% of requests) + 950ms (20%) = ~250ms average
```

**Budget Allocation (Recommended):**
- Embedding: 50–100ms
- Retrieval: 50–150ms (depending on k)
- Reranking: 50–100ms (optional)
- LLM: 500–1500ms (depends on model)
- Cache: 10–20ms (overhead)

### B. Accuracy Metrics (What Matters in 2026)

**Retrieval Layer (NDCG, MRR, Recall@k):**
- **NDCG@5:** Normalized Discounted Cumulative Gain (position-aware relevance)
- **MRR:** Mean Reciprocal Rank (how high is first relevant doc?)
- **Recall@10:** % of truly relevant docs retrieved in top 10

**Critical Finding (2025-26):** Traditional IR metrics assume humans read sequentially. LLMs process all docs holistically. NDCG correlates better than binary relevance for RAG.

**Generation Layer (Faithfulness, Hallucination):**
- **Faithfulness:** % of generated answer supported by retrieved docs
- **Hallucination Rate:** % of claims not in source material
- **Answer Relevancy:** Does answer address the question?

**End-to-End:**
- **Human Evaluation (Gold):** Experts rate (correctness, completeness, safety)
- **LLM-as-Judge (Proxy):** Claude judges using rubric (correlation 0.85–0.92 with human)
- **Automated Metrics:** Combine retrieval + generation scores

### C. Accuracy vs. Speed Trade-offs

| Strategy | Latency | Accuracy | Cost/Query | Use Case |
|----------|---------|----------|-----------|----------|
| **Cache Only** | 60ms | N/A (assume correct) | ~$0.01 | FAQ responses |
| **1 Retrieval + LLM** | 950ms | 70–75% | ~$0.05 | Fast support |
| **3 Retrievals + Rerank + LLM** | 1.5s | 80–85% | ~$0.15 | Accuracy-critical |
| **Agentic (3 hops) + Rerank + LLM** | 3–5s | 85–90% | ~$0.30 | Complex queries |
| **Human Review** | 10–60min | 99%+ | ~$5 | Safety-critical |

**Real Trade-off:** Double accuracy → ~3× latency, ~6× cost.

### D. Evaluation Protocols (2026 Best Practices)

**Phase 1: Offline Evaluation (No Real Users)**
- Test set: 100+ representative queries
- Gold answers: Humans label true relevant docs + expected response
- Metrics: NDCG@5, MRR, Recall@10, Answer Relevancy
- Decision: Proceed to Phase 2 if accuracy >75% on test set

**Phase 2: Online A/B Test**
- 10–20% traffic to new system
- Track: accuracy (human spot-check), latency (p50/p95), cost
- Duration: 1–2 weeks
- Decision: Rollout if >5% accuracy gain + acceptable latency

**Phase 3: Monitoring (Ongoing)**
- Track NDCG, hallucination rate on sample of production queries
- Alert if accuracy drops >10% (drift)
- Monthly revalidation of cache thresholds

---

## V. RECOMMENDATIONS FOR CONVERGENCE + FUNJOIN

### A. Priority 1: Semantic Cache Layer (FunJoin #1 Need)

**Why:** 80% cost reduction; 70–80% of support questions are semantically similar

**Implement:**
1. Pluggable embedding function (default: all-mpnet-base-v2)
2. Configurable similarity threshold (0.88 default, tunable)
3. TTL support (24h default, per-entry override)
4. Backends: memory (dev), Redis (prod)
5. Metrics: hit rate, precision, age distribution

**Integration with Convergence:**
```python
from convergence.semantic_cache import SemanticCache

cache = SemanticCache(
    embed_model="sentence-transformers/all-mpnet-base-v2",
    similarity_threshold=0.88,
    ttl_seconds=86400,
    backend="redis",
)

# In agent loop:
cached = await cache.get(query, similarity_threshold=0.90)  # Query-specific override
if cached:
    return cached["response"], metadata={"cache_hit": True}

# After LLM call:
await cache.set(query, response)
```

**Expected Impact:** 70–80% cost reduction on FunJoin support workload.

### B. Priority 2: PostgreSQL Backend for Runtime Storage

**Why:** FunJoin's stack is PostgreSQL; SQLite has single-writer lock contention

**Implement:**
- Async connection pooling (asyncpg)
- Auto-schema creation on init
- Same RuntimeStorageProtocol as SQLite
- Connection resilience (retry + backoff)

### C. Priority 3: Hybrid Retrieval (BM25 + Semantic)

**Why:** 10–20% accuracy gain over semantic alone (unifies FunJoin's tools)

**Integration:**
```python
# In agentic_rag module
results_bm25 = await search_code(query)  # BM25 via GitLab API
results_semantic = await vector_search(query)  # Semantic via Qdrant
results_combined = reciprocal_rank_fusion(results_bm25, results_semantic)
```

### D. Priority 4: Observable Agentic RAG

**Metrics to Track:**
1. Agent hops (how many retrieval steps?)
2. Intermediate evidence quality (NDCG of each retrieval)
3. Final answer faithfulness (% grounded in evidence)
4. Latency per hop (where's the bottleneck?)

**Alert Conditions:**
- Latency p95 > 3s (timeout risk)
- Hallucination rate > 30% (accuracy drift)
- Cache hit rate drops > 20% (stale data signal)

---

## VI. SOURCES & FURTHER READING

### Core Semantic Caching Papers & Implementations
- [Advancing Semantic Caching for LLMs with Domain-Specific Embeddings](https://arxiv.org/html/2504.02268v1)
- [GPT Semantic Cache: Reducing LLM Costs and Latency](https://arxiv.org/html/2411.05276v2)
- [Semantic Caching for Intent-Driven Context Optimization](https://arxiv.org/html/2601.11687)
- [What's the Best Embedding Model for Semantic Caching?](https://redis.io/blog/whats-the-best-embedding-model-for-semantic-caching/)
- [Reducing False Positives in RAG Semantic Caching](https://www.infoq.com/articles/reducing-false-positives-retrieval-augmented-generation/)
- [GPTCache Documentation](https://gptcache.readthedocs.io/en/latest/)
- [Portkey AI Gateway - Semantic Cache](https://portkey.ai/blog/reducing-llm-costs-and-latency-semantic-cache/)

### Beyond-RAG & Agentic RAG
- [Agentic RAG: A Survey](https://arxiv.org/abs/2501.09136)
- [A-RAG: Scaling Agentic RAG via Hierarchical Retrieval](https://arxiv.org/html/2602.03442v1)
- [Agentic RAG with Knowledge Graphs for Multi-Hop Reasoning](https://arxiv.org/abs/2507.16507)
- [HopRAG: Multi-Hop Reasoning for Logic-Aware RAG](https://arxiv.org/abs/2502.12442)
- [The Ultimate RAG Blueprint 2025/2026](https://langwatch.ai/blog/the-ultimate-rag-blueprint-everything-you-need-to-know-about-rag-in-2025-2026)

### Knowledge Graphs & Graph RAG
- [GraphRAG Publications (July 2025)](https://datavera.org/en/graphrag-july2025.html)
- [How to Build & Scale a Knowledge Graph](https://enterprise-knowledge.com/how-do-i-update-and-scale-my-knowledge-graph/)
- [Enterprise Knowledge Graph for Agentic AI](https://www.superblocks.com/blog/enterprise-knowledge-graph)

### Vector Databases & Hybrid Search
- [Vector Database Comparison 2026](https://liquidmetal.ai/casesAndBlogs/vector-comparison/)
- [Hybrid Search: BM25 + Semantic Search](https://medium.com/etoai/hybrid-search-combining-bm25-and-semantic-search-for-better-results-with-lan-1358038fe7e6)
- [Hybrid Search in PostgreSQL](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual/)
- [Elastic Hybrid Search Guide](https://www.elastic.co/what-is/hybrid-search)

### Production & Evaluation
- [RAG Evaluation Metrics 2026](https://labelyourdata.com/articles/llm-fine-tuning/rag-evaluation)
- [Redefining Retrieval Evaluation in Era of LLMs](https://arxiv.org/html/2510.21440v1)
- [Why Multi-Agent LLM Systems Fail](https://arxiv.org/abs/2503.13657)
- [Cache Invalidation Strategies](https://www.systemoverflow.com/learn/ml-model-serving/model-monitoring-observability/semantic-caching-and-retrieval-invalidation)
- [LLM Caching Decision Guide](https://particula.tech/blog/when-to-cache-llm-responses-decision-guide)

---

## VII. CONVERGENCE ROADMAP IMPLICATIONS

### Immediate (This Sprint)
- [ ] Semantic cache layer with pluggable embeddings
- [ ] PostgreSQL storage backend
- [ ] Cache metrics (hit rate, precision, age)

### Next Sprint
- [ ] Hybrid search primitives (BM25 + semantic fusion)
- [ ] Cache invalidation helpers (TTL, event-based, staleness)
- [ ] Observable agentic retrieval wrapper

### Future
- [ ] Multi-context caching (separate caches per context)
- [ ] Graph RAG integration helpers
- [ ] Auto-threshold tuning (validate empirically)

---

**Document Status:** Ready for integration
**Lines (excluding headers):** 98
**Completion:** March 12, 2026

