# Self-Learning Production Readiness — Quick Reference

**One-Page Decision Guide for Your Codebase**

---

## What's Production-Ready NOW?

| Method | Min Data | Status | Your Code | Action |
|--------|----------|--------|-----------|--------|
| **Thompson Sampling** | 15-30 | ✅ Battle-tested | Implemented | Deploy immediately |
| **A/B Testing** | 100-500 | ✅ Standard | Use as foundation | Wrap metrics collection |
| **Contextual Bandits** | 20-50/context | ✅ Proven | Add if needed | Not urgent |

---

## What Needs Staging?

| Method | Min Data | Stability | Your Code | Action |
|--------|----------|-----------|-----------|--------|
| **RLP** | 500-1000+ | ⚠️ Emerging | 80% done | Add: entropy monitor, KL constraints, kill switch |
| **SAO** | 1000-5000+ | ⚠️ Volatile | Implemented | Research only; add external validation if used |

---

## What's Not Ready?

| Method | Why Not | Status |
|--------|--------|--------|
| **Meta-MAB** | Unknown stability, 2000+ data, no production proof | Skip for now |

---

## Deployment Sequence (Recommended)

```
Week 1:  Thompson Sampling + basic metrics
Week 2:  Add automated monitoring (regret, arm distribution)
Week 3:  RLP to 5% traffic with kill switches + entropy alerts
Week 4:  Harden RLP: add entropy monitoring, KL enforcement
Month 2: SAO in staging (fine-tuning only, non-critical)
Month 3+: Mature ensemble (TS + RLP + SAO with fallbacks)
```

---

## Critical Convergence Data

### Thompson Sampling
- **15 interactions**: Clear learning pattern emerges
- **20-30 interactions**: Near-optimal performance
- **50 interactions**: Stable, low variance
- **How it beats A/B**: 26.3% better regret, 43.8% faster convergence

### RLP
- **<500 interactions**: Unstable (use heuristic only)
- **500-1000**: Monitor reward signal (std < 0.3 required)
- **1000-2000**: Safe to deploy at <10% influence
- **2000+**: Can increase influence to 50%

### SAO
- **1000+**: Minimum for meaningful training
- **5000+**: Production confidence (for in-distribution only)
- **Risk**: Works for fine-tuning, fails for out-of-distribution tasks

---

## Cold Start: Hours 1-10

1. **Use heuristic reasoning** (implemented in RLP: `_generate_heuristic_reasoning()`)
2. **Collect feedback** but don't learn yet
3. **After 30 interactions**: Switch to Thompson Sampling
4. **Bootstrap options:**
   - Self-talk (LLM agents converse): ~$0.50-$2, 100-200 conversations
   - Transfer priors from related task: ~2x faster convergence
   - None (just wait): Safe, but slower

---

## Failure Recovery (Add These)

| Signal | Diagnosis | Fix |
|--------|-----------|-----|
| TS regret increasing | Arm rewards changed | Soften priors (α *= 0.8, β *= 0.8) |
| RLP reward collapse | Reward signal dead | Revert to heuristic, collect 50 fresh interactions |
| SAO quality drops >50% fail | Generator mode collapse | Clear history, increase temperature 0.6→0.8 |

---

## Hardening Checklist

**Before Production:**
- [ ] Thompson Sampling: Basic ✓
- [ ] Metrics: Regret, arm distribution, reward variance
- [ ] A/B Testing: Kill switches, harm detection
- [ ] RLP: Entropy monitoring, KL constraints, automated fallback
- [ ] SAO: External validation hooks, distribution shift detection

**Optional (Nice to Have):**
- [ ] Contextual bandits for prompt optimization
- [ ] Meta-monitoring (cross-validate TS vs RLP predictions)
- [ ] Automated re-tuning pipelines

---

## Key Numbers to Remember

| Metric | Value | Implication |
|--------|-------|-------------|
| Thompson convergence | 15-30 interactions | Deploy fast, no analysis paralysis |
| RLP minimum | 500 interactions | 2-3 weeks of typical usage |
| SAO minimum | 1000 interactions | 4-6 weeks of typical usage |
| A/B test samples | 100-500 | High variance needs larger N than traditional ML |
| Policy gradient data | 3-4x Thompson | GRPO/RLP more expensive than bandits |
| Cold start buffer | First 50 interactions | Heuristic only, collect feedback |

---

## One Question to Ask Yourself

**"How much data do I have on this task?"**

- **Zero?** → Heuristic + collect (hours to days)
- **<100?** → Thompson Sampling NOW
- **100-500?** → Thompson + context (if context matters)
- **500-2000?** → Add RLP to 10% influence, monitor
- **2000+?** → Ensemble (TS + RLP + SAO)

---

## Sources

Core:
- [Thompson Sampling 2025 Guide](https://www.shadecoder.com/topics/thompson-sampling-for-bandits-a-comprehensive-guide-for-2025)
- [Multi-Armed Bandits Meet LLMs](https://arxiv.org/abs/2505.13355)
- [Statsig LLM Optimization](https://www.statsig.com/blog/llm-optimization-online-experimentation)

Emerging:
- [RLP (NVIDIA/ICLR 2026)](https://github.com/NVlabs/RLP)
- [CAPO: Stabilizing Policy Gradients](https://openreview.net/forum?id=iIvPuXoDs1)

Experimental:
- [SAO: Fully Self-Synthetic Data](https://arxiv.org/abs/2510.06652)

---

**Last Updated:** March 12, 2026  
**Read First:** `self-learning-production-readiness.md` (full analysis)  
**Use This For:** Quick decisions in meetings/standups
