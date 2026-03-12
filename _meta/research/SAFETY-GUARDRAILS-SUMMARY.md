# Safety & Guardrails Integration — Quick Summary

**Document:** `/Users/ariaxhan/Downloads/Vaults/CodingVault/the-convergence/_meta/research/safety-guardrails-research.md`

---

## Key Findings

### The Problem
73% of production agent deployments vulnerable to prompt injection. Current guardrail approaches fail because they're stateless and detect-based (filtering after generation), not structural (making attacks impossible).

### The Solution: Defense-in-Depth (5 Layers)

1. **Structural Validation** (Pydantic) — Make dangerous states impossible
2. **Input Validation** (Fast rules + rate limiting) — Block obvious attacks
3. **Semantic Injection Detection** (Small LLM classifier) — Catch reframed attacks
4. **Output Validation** (Guardrails AI) — Catch hallucinations & leaks
5. **Budget Enforcement** (LiteLLM) — Prevent runaway costs

### Recommended Stack

| Component | Tool | Why |
|-----------|------|-----|
| Structural validation | Pydantic | Already in The Convergence; makes preconditions enforced |
| Input/Output guards | Guardrails AI | Production-ready, Pydantic-native, stable API |
| Budget tracking | LiteLLM + custom | Hierarchical budgets, per-session limits, cost visibility |
| Injection detection | Custom classifier | Small model, fast, fits into agent loop |
| NeMo Guardrails | Skip for now | Beta version has critical bugs; use for non-critical output formatting only |

### What Fails (Anti-Patterns)

1. **Post-hoc filtering** → Use structural preconditions instead
2. **Stateless validators** → Track conversation context across turns
3. **Signature-based injection detection** → Multi-model ensemble (fast + semantic)
4. **Real-time budget queries** → Cache budget checks, update async
5. **No per-session limits** → Add max_iterations + max_budget_per_session

---

## Implementation Plan (4 Phases)

**Phase 1 (Weeks 1–2):** Pydantic structural validation  
**Phase 2 (Weeks 3–4):** Guardrails AI integration  
**Phase 3 (Weeks 5–6):** LiteLLM budget tracking  
**Phase 4 (Weeks 7–8):** Semantic injection detection  

Total effort: 8 weeks, medium complexity, high security impact.

---

## Critical Details

See full research document for:
- 5 detailed anti-patterns with examples
- NeMo Guardrails bugs (#1092, #1696, #1700, #1413, #1325, #1692)
- Guardrails AI integration examples
- Defense-in-depth code examples (all 5 layers)
- Budget tracking patterns (hierarchical, tiered enforcement)
- Source citations (25+ references)

---

## Next Steps

1. Review research document: `/Users/ariaxhan/Downloads/Vaults/CodingVault/the-convergence/_meta/research/safety-guardrails-research.md`
2. Confirm Phase 1 (Pydantic) is compatible with existing agent loop
3. Plan integration with optimization loop (Tier 2 scope: 1–2 week surgical change)
4. Add dependencies: `guardrails-ai` (production-ready)
5. Reject NeMo (beta; defer to future release)

