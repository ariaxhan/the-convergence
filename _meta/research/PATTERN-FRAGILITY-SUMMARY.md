# Pattern Fragility Research - Quick Reference

## The Problem
Hardcoded patterns (HEDGING_PHRASES, CERTAINTY_PHRASES, regex) break as requirements evolve:
- No versioning when patterns change
- No regression testing
- No graceful fallback when patterns don't match
- Code redeployment required for every pattern tweak

## Solution in 4 Phases

### 1. Configuration-Driven (Week 1)
Move patterns to YAML with hot-reload:
```yaml
# convergence/patterns/v1.yaml
patterns:
  hedging:
    - pattern: "i'm not sure"
      weight: 1.0
```
- 20 lines Python (PatternLoader)
- Users can extend without code changes
- Patterns versioned independently

### 2. Regression Testing (Week 2)
Golden test set prevents breakage:
```yaml
# tests/patterns/golden/confidence_v1.yaml
test_cases:
  - id: "hedging_single"
    input: "I think maybe..."
    expected_score: 0.55
```
- 50+ hand-verified test cases
- Automated CI/CD checks
- Catches 95%+ of regressions

### 3. Graceful Degradation (Week 3)
Three-tier fallback when patterns fail:
- Tier 1: Explicit markers (Confidence: 85%)
- Tier 2: Pattern matching (linguistic analysis)
- Tier 3: Heuristic fallback (text length)

Track which tier is used → alerts when patterns degrading

### 4. Property-Based Testing (Week 4)
Hypothesis finds edge cases patterns miss:
```python
@given(st.text(min_size=1))
def test_confidence_bounded(text):
    score, _ = extract_confidence(text)
    assert 0.0 <= score <= 1.0
```

## Key Metrics

| What | Before | After |
|------|--------|-------|
| Pattern change cycle | 2-4 hours | 5 minutes |
| Regression detection | Manual | Automated |
| Tier 3 fallback rate | Unknown | <10% (alerted) |

## Implementation Cost
- Total code: ~120 lines (mostly YAML)
- Test overhead: ~100 lines
- No breaking changes to existing API
- Can run in parallel with current system

## Why This Works

1. **Configuration separates concerns** - Patterns evolve independently of code
2. **Golden datasets ensure stability** - Any regression caught immediately
3. **Graceful degradation** - System never fails, just gets less confident
4. **Property testing** - Automation finds human-miss edge cases

## Files to Create
```
convergence/
├── confidence/
│   └── pattern_loader.py      (20 lines)
├── patterns/
│   └── v1.yaml                (~100 lines)

tests/
├── patterns/
│   ├── golden/
│   │   └── confidence_v1.yaml (50 test cases)
│   └── test_confidence_regression.py (50 lines)
```

## Success Criteria
- [ ] Pattern changes don't require code review
- [ ] All regressions caught by CI/CD
- [ ] <10% traffic hits Tier 3 fallback
- [ ] Pattern tests run in <200ms

See full research: `/Users/ariaxhan/Downloads/Vaults/CodingVault/the-convergence/_meta/research/pattern-fragility.md`
