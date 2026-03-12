# Tear Down: Architecture v3 (Research-Informed)

**Reviewed:** 2026-03-12
**Reviewer:** kernel:tearitapart
**Subject:** ARCHITECTURE-v3-RESEARCH-INFORMED.md + context-graphs-architecture.md

---

## Critical Issues

### CRITICAL-1: Context Graph Layer Missing from Architecture v3

**Severity:** Critical (blocks implementation coherence)

Architecture v3 does NOT include the Context Graph layer documented in `context-graphs-architecture.md`. The README has been updated to include it, but the implementation plan doesn't reflect it.

**Evidence:**
- Architecture v3 has 5 layers: Safety → Observability → Optimization → Experimental → Storage
- Context graph research shows KNOWLEDGE should be the **foundation layer** everything operates on
- README now shows KNOWLEDGE as the first layer, but plan doesn't include implementation phases for it

**Impact:**
- Implementation will be incoherent (plan says one thing, README says another)
- Context graph is labeled "Beta" in README but has zero implementation plan

**Fix:**
1. Update Architecture v3 to include KNOWLEDGE layer as Layer 0
2. Add Phase 0.5 for Context Graph MVP (schema + basic operations)
3. Reconcile README architecture diagram with implementation plan

---

### CRITICAL-2: No Persistence for Thompson Sampling State

**Severity:** Critical (data loss on restart)

Thompson Sampling implementation (`thompson_sampling.py:46`) stores `arm_stats` in memory only:
```python
self.arm_stats: Dict[str, Dict[str, float]] = {}
```

**Impact:**
- All learning is lost on process restart
- Agent restarts cold every time
- Defeats the purpose of "self-evolving"

**Current code has no:**
- Save/load methods
- Integration with storage backends
- State restoration logic

**Fix:**
Add to Phase 0 (Foundation Hardening):
- [ ] Add `save_state()` / `load_state()` methods to Thompson Sampling
- [ ] Integrate with existing storage backends (SQLite, PostgreSQL)
- [ ] Load state on initialization

---

### CRITICAL-3: Semantic Cache Linear Scan

**Severity:** Critical (performance bottleneck)

`semantic.py:143-152` scans ALL entries for every cache lookup:
```python
# Get all entries from backend
entries = await self._backend.get_all_entries()

for entry in entries:
    similarity = cosine_similarity(query_embedding, entry.embedding)
```

**Impact:**
- O(n) lookup time
- At 10K entries, every cache check becomes expensive
- Defeats the purpose of caching for latency reduction

**Fix:**
- Use approximate nearest neighbor (ANN) search
- Add to Phase 3 (Semantic Cache):
  - [ ] Integrate Qdrant/FAISS for vector search
  - [ ] Or add SQLite FTS5 with pgvector for PostgreSQL

---

## Security Review

### SEC-1: No Input Validation on NeMo Guardrails Integration

**Severity:** Medium

Plan shows NeMo integration but doesn't specify:
- What config files will be used
- How injection attacks will be detected
- Colang rules for the use case

**Research says:** "Prompt injection is OWASP LLM#1 for 2025. 73% of production deployments vulnerable."

**Fix:**
- [ ] Define default Colang rules for FunJoin use case
- [ ] Add unit tests for injection attempts
- [ ] Document config structure in Phase 1

### SEC-2: Budget Enforcement Has No Persistence

**Severity:** Medium

`budget.py` example shows in-memory tracking only:
```python
self.spent_today: float = 0.0
```

**Impact:**
- Process restart resets daily budget
- Could allow overspend across restarts

**Fix:**
- [ ] Persist budget state to storage
- [ ] Add date-based reset logic
- [ ] Include in Phase 1 implementation

### SEC-3: RLP Experience Buffer Has No Size Limit Enforcement

**Severity:** Low

`rlp.py` uses `deque(maxlen=...)` but stores full dicts with state objects.

**Impact:**
- Large state objects could cause memory issues
- No sanitization of what goes in buffer

**Fix:**
- [ ] Add size limits to state objects before buffering
- [ ] Document memory requirements for RLP

---

## Concerns

### CONCERN-1: Missing Integration Tests Between Layers

Plan specifies unit tests but no integration tests showing:
- Safety layer rejecting → Observability records it → MAB gets negative signal
- Cache hit → Observability records latency → Cost tracking shows $0

**Fix:** Add integration test examples to each phase.

### CONCERN-2: PostgreSQL Storage Not in Files List

Architecture mentions "SQLite (dev) | PostgreSQL (prod)" but:
- `postgresql.py` exists but not in Phase files
- No verification that PostgreSQL backend works with new components

**Fix:** Add PostgreSQL integration verification to Phase 0.

### CONCERN-3: Weave Dependency for Basic Operation

`thompson_sampling.py` and `rlp.py` both use `@weave.op()` decorator:
```python
@weave.op()
def select_arm(self, arms: List[str], state: Dict[str, Any]) -> str:
```

**Impact:**
- Weave import required even if user doesn't want observability
- Could fail if Weave not installed

**Fix:**
- Make Weave optional (graceful fallback if not installed)
- Or require Weave in core dependencies

### CONCERN-4: No Error Recovery for Learning Methods

RLP and SAO don't have:
- Checkpoint/recovery mechanisms
- Graceful degradation when buffer is corrupt
- Kill switches mentioned in plan but not in existing code

**Fix:** Add to Phase 0 hardening checklist.

### CONCERN-5: Semantic Cache Threshold Validation Missing

Plan says: "Validate threshold empirically. 0.7 → 99% false positives."

But there's no:
- Validation tooling to test threshold
- Metrics to track false positive rate
- Automated threshold tuning

**Fix:** Add threshold validation utility to Phase 3.

---

## Questions

### Q1: Context Graph Implementation Scope

The context-graphs-architecture.md shows extensive features:
- Traverse, extract, merge, evolve
- Graph learning with Thompson Sampling
- Progressive disclosure (Campaign → Objective)

**Question:** Which subset is MVP? What's actually needed for FunJoin?

**Suggested answer:** Phase 1 of context graph doc (schema + basic traverse + extract) is MVP. Learning and merge are future.

### Q2: NeMo vs Guardrails AI Overlap

Plan shows both:
- NeMo Guardrails (input/output/execution rails)
- Guardrails AI (schema validation)

**Question:** Is this redundant? Can we use just one?

**Evidence from research:** They serve different purposes:
- NeMo: Conversation flow, Colang rules, tool authorization
- Guardrails AI: Output schema validation, structured extraction

**Suggested answer:** Keep both. Different concerns.

### Q3: Experimental Methods Location

Plan says: "Move from plugins, add monitoring"

**Question:** Are we moving `convergence/plugins/learning/rlp.py` to `convergence/experimental/rlp.py`? Or keeping in both places?

**Suggested answer:** Move entirely. Avoid duplicate code.

### Q4: Meta-MAB Contract in AgentDB

AgentDB shows active contract for Meta-MAB:
```json
{"id":"META-001","goal":"Meta-MAB Method Selection",...}
```

But Architecture v3 says: "Meta-MAB — No production proof, unknown stability. Skip for now."

**Question:** Should we close this contract?

**Suggested answer:** Yes, close META-001. Reopen when data supports.

---

## Architecture Review

### Separation of Concerns: GOOD

Each layer has clear responsibility:
- Safety: Validation, authorization, budget
- Observability: Metrics, tracking, drift
- Optimization: Learning, caching, evolution
- Experimental: Data-gated advanced methods
- Storage: Persistence backends

### Coupling: MEDIUM CONCERN

- Thompson Sampling depends on Weave (should be optional)
- RLP depends on numpy and optionally torch (documented)
- Semantic Cache depends on sentence-transformers (documented as optional)

**Fix:** Clear optional dependency structure in pyproject.toml.

### Interface Stability: GOOD

- Storage uses StorageProtocol
- Observability plan uses Observer Protocol
- Safety layer uses ValidationResult

### Pattern Consistency: MEDIUM CONCERN

- Some classes use mixins (RLPMixin)
- Some use plugins (ThompsonSamplingPlugin)
- Some are direct implementations (SemanticCache)

**Question:** Should there be a unified plugin architecture?

**Suggested answer:** Not for MVP. Document the patterns used.

### Missing from Architecture: Context Graph

As noted in CRITICAL-1, the context graph layer that's documented in README is not in the implementation plan.

---

## Verdict: REVISE

**Reason:** 3 critical issues that must be addressed before implementation.

### Required Changes Before Implementation

1. **CRITICAL-1:** Add Context Graph Layer to Architecture v3
   - Add as Layer 0 (KNOWLEDGE)
   - Add Phase 0.5 for MVP implementation
   - Reconcile with README

2. **CRITICAL-2:** Add State Persistence to Thompson Sampling
   - Add to Phase 0 (Foundation Hardening)
   - save_state() / load_state() methods
   - Integration test with storage backends

3. **CRITICAL-3:** Fix Semantic Cache O(n) Lookup
   - Add vector index (ANN search)
   - Or document scaling limits clearly
   - Add to Phase 3 scope

### Recommended Changes

4. **SEC-1, SEC-2:** Persist safety state (budget, audit logs)
5. **CONCERN-2:** Verify PostgreSQL backend compatibility
6. **CONCERN-3:** Make Weave optional
7. **Q4:** Close META-001 contract

---

## Implementation Readiness Checklist

After REVISE:

- [ ] Context Graph Layer added to architecture
- [ ] Thompson Sampling persistence added to Phase 0
- [ ] Semantic Cache ANN search added to Phase 3
- [ ] PostgreSQL verification added to Phase 0
- [ ] META-001 contract closed or updated
- [ ] Weave made optional in MAB/RLP code

---

*Teardown complete. Address REVISE items before implementation.*
