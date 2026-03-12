# CONTEXT HANDOFF
Generated: 2026-03-12

**Summary**: Designed adaptive learning system where methods (RLP, SAO, MemRL, Constitutional AI) are selected via meta-MAB based on use case.

---

## Goal

Build The Convergence as the enterprise self-evolving agent framework where:
1. Learning methods are NOT all used at once
2. A **meta-learner** selects which methods work best for each use case
3. The system self-learns which methods help which tasks
4. Prefer open source packages (trl, transformers) over NIH
5. Test-first implementation

---

## Current State

| Layer | Status |
|-------|--------|
| Runtime API | ✓ Works (configure, select, update) |
| Thompson Sampling MAB | ✓ Works |
| Storage (SQLite, PostgreSQL) | ✓ Works |
| Evaluators | ✓ Works (confidence bugs fixed) |
| RLP Plugin | ⚠️ Exists, not connected to MAB |
| SAO Plugin | ⚠️ Exists, no DPO integration |
| Pattern System | ✗ Static, needs evolution |
| Observability | ✗ Weave-locked, needs native |
| Meta-Learner | ✗ Not built |

**Branch:** codex/auto-commit-20260202 (dirty - uncommitted research artifacts)

---

## Decisions Made

### 1. Progressive Method Selection (Meta-MAB)
**Choice:** Don't use all learning methods at once. Build meta-MAB that selects methods.
**Rationale:** Different tasks need different methods. RLP helps reasoning tasks. SAO helps alignment. MemRL helps memory-heavy tasks. Let the system learn.

### 2. Methods as Arms
**Choice:** Treat each learning method as an arm in a meta-level Thompson Sampling.
**Rationale:** Reuse existing MAB infrastructure. Same exploration-exploitation tradeoff applies.

### 3. Open Source First
**Choice:** Use trl (Hugging Face), transformers, sentence-transformers instead of writing from scratch.
**Rationale:** Battle-tested. DPO, PPO, RLHF already implemented. Don't reinvent.

**Packages to use:**
| Need | Package |
|------|---------|
| DPO training | `trl.DPOTrainer` |
| Embeddings | `sentence-transformers` |
| Memory | `chromadb` or `qdrant-client` |
| Uncertainty | `torch.nn.functional.softmax` + entropy |

### 4. Test-First
**Choice:** Write tests before implementation for learning plugins.
**Rationale:** Methods interact. Need regression tests.

---

## Artifacts Created This Session

| Path | Purpose |
|------|---------|
| `_meta/CONVERGENCE-MEMO.md` | What we have vs what we're building |
| `_meta/docs/RLP-SAO-DEEP-DIVE.md` | How RLP/SAO work + novel methods |
| `_meta/plans/pattern-system-v2.md` | Architecture for self-evolving patterns |
| `_meta/research/novel-approaches-2026.md` | EvolveR, MAE, Constitutional AI research |
| `_meta/research/funjoin-failure-patterns.md` | Failure taxonomy from FunJoin |
| `_meta/research/funjoin-integration-needs.md` | What FunJoin needs |
| `_meta/research/collabvault-learnings.md` | 47 patterns from CollabVault |
| `_meta/handoffs/pattern-system-handoff.md` | Updated contract status |

---

## Open Threads

### BLOCKERS
- None

### TODOs
- [ ] Implement meta-MAB for method selection
- [ ] Connect RLP to runtime MAB (thoughts as arms)
- [ ] Integrate SAO with `trl.DPOTrainer`
- [ ] Add MemRL plugin (episodic memory)
- [ ] Add Constitutional AI plugin (principles in YAML)
- [ ] Native observability (watch learning, not just outputs)
- [ ] Pattern evolution via Thompson Sampling

### CONTRACTS READY
| Contract | Scope | Dependencies |
|----------|-------|--------------|
| CR-010 | Principle tracking | None |
| CR-005-v2 | Native observability | None |
| CR-006-v2 | Constitutional YAML | None |
| CR-007-v2 | Unified classifier | CR-010, CR-005-v2, CR-006-v2 |
| CR-008-v2 | Thompson on patterns | CR-010, CR-007-v2 |

---

## Next Steps

### Immediate (This Session or Next)
1. **Design meta-MAB schema** — How to track method performance per task type
2. **Survey open source packages** — Confirm trl, sentence-transformers, chromadb fit
3. **Write tests for RLP-MAB connection** — Test-first

### Implementation Order
```
Phase 1: Meta-MAB infrastructure (method selection)
Phase 2: Connect RLP to MAB (thoughts as arms)
Phase 3: Add MemRL via chromadb (episodic memory)
Phase 4: Integrate SAO with trl.DPOTrainer
Phase 5: Add Constitutional AI (YAML principles)
Phase 6: Pattern evolution (CR-008-v2)
```

### Package Investigation Needed
```python
# Verify these work for our use case
from trl import DPOTrainer, DPOConfig  # For SAO
from sentence_transformers import SentenceTransformer  # For MemRL embeddings
import chromadb  # For episodic memory
```

---

## Warnings (Failed Approaches to Avoid)

1. **Don't write DPO from scratch** — trl already has it
2. **Don't use all methods simultaneously** — meta-learner selects
3. **Don't deploy arbitrary thresholds** — need 500+ interactions to calibrate
4. **Don't trust self-generated data blindly** — model collapse is real
5. **Don't skip tests** — methods interact in subtle ways

---

## Key Learnings (Saved to AgentDB)

1. **adaptive-method-selection** — Progressive learning, methods selected by meta-MAB
2. **prefer-open-source** — trl, transformers, sentence-transformers
3. **test-first-implementation** — Define behavior, test, then implement
4. **meta-mab-for-methods** — Thompson Sampling over methods themselves
5. **method-compatibility-matrix** — RLP+MemRL complement, SAO+CAI complement

---

## Architecture Vision: Adaptive Learning Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                     META-MAB (Method Selector)                  │
│  Thompson Sampling over: [RLP, SAO, MemRL, CAI, SELAUR, MAE]   │
│  Context: task_type, user_history, domain                       │
│  Reward: downstream task success                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │   RLP   │  │   SAO   │  │  MemRL  │  │   CAI   │           │
│  │(reason) │  │ (data)  │  │(memory) │  │(align)  │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │            │            │            │                  │
│       └────────────┴────────────┴────────────┘                  │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │   EXPERIENCE BUFFER  │                           │
│              │  (unified storage)   │                           │
│              └──────────┬──────────┘                           │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │   RUNTIME MAB       │                           │
│              │  (arm selection)    │                           │
│              └─────────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Continuation Prompt

> /kernel:ingest Implement adaptive learning method selection (meta-MAB). Methods (RLP, SAO, MemRL, Constitutional AI) are arms. System learns which methods work for which task types. Test-first, prefer open source (trl, sentence-transformers, chromadb). Read _meta/handoffs/learning-system-2026-03-12.md and _meta/docs/RLP-SAO-DEEP-DIVE.md for context.

---

*Handoff generated: 2026-03-12*
