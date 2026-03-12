# Enterprise Agent Safety — Research Summary

**Status:** Complete. 662-line research document with 5 critical pitfalls, framework recommendations, and 25+ sources.

**File:** `_meta/research/enterprise-agent-foundations.md`

---

## TL;DR — What to Build

### Layer Stack (Recommended)

| Layer | Tool | Purpose | Integration |
|-------|------|---------|-------------|
| 1 | **NeMo Guardrails** | Input/output validation, execution rails | 30-50 lines config |
| 2 | **Guardrails AI** | Response schema validation | 15-20 lines |
| 3 | **CrewAI/Semantic Kernel** | Multi-agent validation (critic) | 50-100 lines per agent |
| 4 | **Weave + structlog** | Observability (already in use) | 30-40 lines |
| 5 | **AI Gateway (Portkey/Bifrost)** | Cost control + budget enforcement | 1-2 hours |

---

## Critical Pitfalls (Not Optional)

### 1. Overprivileged Access (Most Common)
- **Problem:** Agent given root access, hallucination causes data deletion
- **Real case:** Solana dev environment nearly deleted database
- **Fix:** Execution rails (NeMo) + least-privilege tools + human approval for mutations

### 2. Prompt Injection (OWASP #1)
- **Problem:** User input overrides system prompt
- **Reality:** 73% of production deployments vulnerable
- **Fix:** Defense-in-depth (input spotlighting + validation + output monitoring + human review)

### 3. Hallucination in Tool Calls (HIGH IMPACT)
- **Problem:** Agent fabricates database queries, API params, tool results
- **Fix:** Graph-RAG + semantic tool filtering + multi-agent validation
- **Impact:** 60-90% error reduction proven in trials

### 4. Runaway Costs (FINANCIAL DAMAGE)
- **Problem:** $10K+ overnight from infinite loops, excessive token usage
- **Fix:** Budget enforcement, timeouts, AI gateway cost tracking (2 hours to implement)

### 5. Data Exposure (COMPLIANCE RISK)
- **Problem:** Agent accesses/leaks PII, secrets, regulated information
- **Fix:** Context-aware data filtering + data classification + log scrubbing + audit trails

---

## What Already Exists (Don't Reinvent)

**Don't build:**
- Guardrail validators (use NeMo or Guardrails AI)
- Custom prompt injection detection (use NeMo input rails)
- Multi-agent orchestration (use CrewAI)
- Cost tracking (use Portkey, TrueFoundry, Bifrost)

**Build:**
- Integration layer that ties them together
- RL feedback loop: safety metrics → MAB reward → policy evolution
- Convergence-specific validators (e.g., pattern confidence guardrails)
- Custom execution rails for agent-specific tools

---

## Implementation Phases

**Phase 1 (Week 1-2):** NeMo + Guardrails AI + cost tracking
**Phase 2 (Week 3-4):** Observability + weave integration
**Phase 3 (Week 5-6):** Multi-agent validation for critical decisions
**Phase 4 (Ongoing):** RL integration (self-evolving safer policies)

---

## Key Insight

**Security is NOT a feature; it's an invariant.** Design agents to fail safely at the framework level (execution rails, budget limits, permission checks) not at the LLM level (trust the model to self-limit — it won't).

---

## Sources (25+)
All documented in `enterprise-agent-foundations.md`. Top references:
- NeMo Guardrails: https://docs.nvidia.com/nemo/guardrails/latest/index.html
- OWASP Prompt Injection: https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- State of Agent Security 2026: https://www.gravitee.io/blog/state-of-ai-agent-security-2026-report-when-adoption-outpaces-control
- Cerbos: Permission Management: https://www.cerbos.dev/blog/permission-management-for-ai-agents

