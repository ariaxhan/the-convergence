# Observability Patterns Research - Executive Summary

## Questions Answered

### 1. How to Make Regex/Classification Systems Observable?

**Track these four core signals:**
1. **Match Results** - Hit rate, which patterns matched
2. **Confidence Scores** - Explicit (model output) or linguistic (hedging detection)
3. **False Positives** - User feedback on wrong matches
4. **Classification Metrics** - Precision, recall, F1 per pattern

**Implementation:** Use `@weave.op()` decorators on classification functions. Return structured dicts with all observables. Weave logs everything automatically.

---

### 2. What Observability Libraries Integrate Well?

**Recommendation Hierarchy:**

| Tier | Library | When to Use | Effort | Download Volume |
|------|---------|-----------|--------|-----------------|
| 1 | **Weave** (already in deps) | Immediate - instrumentation at function boundary | Low (decorator) | 1M+/month |
| 2 | **structlog** (add to deps) | Detailed structured logging, JSON output | Low (~20 lines) | 100K+/week |
| 3 | **OpenTelemetry** | Multi-service tracing, enterprise | High (1000+ lines) | 224M/month |

**Your Stack:**
- Use **Weave @op() decorators** for high-level observables (What matched, confidence, reward)
- Use **structlog** for detailed event logging (JSON queryable, no regex parsing)
- Skip **OpenTelemetry** until you need cross-service tracing

---

### 3. How to Track Classifier Drift & Degradation?

**Three-layer approach:**

1. **Event Stream** - Log every classification attempt with confidence + user feedback
2. **Sliding Window Metrics** - Weekly batches: compute hit rate, FP rate, avg confidence
3. **Anomaly Detection** - Alert when confidence drops >5%, FP rate rises >10%, or edge cases spike

**Integration with RL Loop:**
- Store metrics in SQLite (you have multi_backend storage)
- Feed FP rate into MAB reward: `reward = 1.0 - fp_rate + confidence_bonus`
- Thompson Sampling explores new pattern variants
- SAO generates improved patterns from user feedback

**Code pattern:**
```python
# Every classification
logger.log_classification(pattern_id, confidence, matched, user_feedback)

# Weekly batch job
metrics = await compute_pattern_metrics(pattern_id, days=7)
await storage.update_baseline_metrics(pattern_id, metrics)

# Alert if drift
if metrics['confidence'] < baseline * 0.95:
    logger.warning("confidence_drift", pattern_id, current=metrics['confidence'])
```

---

### 4. What's the Minimal Viable Observability?

**For initial release, track only THREE metrics:**

1. **Hit Rate** - % of texts that matched any pattern
2. **Avg Confidence** - Average confidence across matches
3. **Error Rate** - % of matches user marked wrong

**Implementation: 50 lines with structlog:**

```python
class MinimalObserver:
    def __init__(self):
        self.buffer = []
    
    async def record(self, confidence, matched):
        self.buffer.append({"confidence": confidence, "matched": matched})
        if len(self.buffer) >= 100:  # Emit batch every 100
            hit_rate = sum(1 for e in self.buffer if e['matched']) / 100
            logger.info("batch_metrics", hit_rate=hit_rate, avg_conf=mean(...))
            self.buffer.clear()
```

**Debug Mode vs Production:**
- **Debug** (`debug=True`): Log everything - text previews, timing, all patterns attempted
- **Production** (`debug=False`): Log only summary + anomalies (matches + confidence + errors)

---

## What to Implement Now

### Phase 1 (3-4 hours, do this sprint)

1. Add structlog to `convergence/evaluators/confidence.py`:
   ```python
   logger.msg("confidence_extraction", text_len=len(text), method=method, result=result)
   ```

2. Extend `WeaveLogger` with classification event:
   ```python
   @weave.op()
   def log_classification(self, pattern_id, confidence, matched, user_feedback=None):
       return {"pattern_id": ..., "confidence": ..., "matched": ..., ...}
   ```

3. Wire into existing confidence extraction tests

**Deliverable:** Logs showing confidence + match status for all classifications

---

### Phase 2 (8-10 hours, next sprint)

1. Add edge case & event collection to storage layer
2. Compute weekly metrics (hit rate, FP rate, avg confidence)
3. Wire into Thompson Sampling reward signal
4. Set up weekly drift detection alerts

**Deliverable:** Automated drift detection; FP rate feeding into MAB

---

### Phase 3 (5-6 hours, future)

1. Observer pattern for library users
2. Documentation: "How to integrate with Datadog/Splunk"
3. Examples showing pattern evolution from user feedback

**Deliverable:** Library users can plug in their own observability

---

## Key Insights

1. **Confidence without correctness is noise.** Always pair `confidence` with `was_correct` (or `user_feedback`) when possible.

2. **Drift detection needs baseline.** Don't alert on absolute confidence values; alert on *change from baseline*.

3. **False positives are the primary risk.** Track FP rate obsessively. A pattern with 90% hit rate but 50% false positive rate is worse than 50% hit rate with 5% false positives.

4. **User feedback loop closes the loop.** Collecting feedback without using it to evolve patterns is waste. Wire feedback → metrics → MAB reward → new patterns.

5. **Avoid logging full text.** Hash or truncate. Use `text_preview[:100]` and `text_hash` instead of raw input.

---

## One-Pager for Implementation

```
START:
  - Add structlog import to confidence.py (20 lines)
  - Add @weave.op() log_classification method (15 lines)
  - Update existing tests to call log_classification (10 lines)

CONFIDENCE EXTRACTION:
  Extract from text using:
    - Explicit markers: "Confidence: 85%"
    - Linguistic cues: hedging ("maybe", "possibly") vs certainty ("definitely")
    - Pair with match result & user feedback

PHASE 2:
  - Store events (pattern_id, confidence, matched, user_feedback, timestamp) in SQLite
  - Weekly batch: compute hit_rate, fp_rate, avg_confidence
  - Alert on > 5% confidence drop or > 10% FP rate spike
  - Feed FP rate into MAB: reward = 1.0 - fp_rate + confidence_bonus

DONE:
  Classifier is observable. Drift is detected. Users can integrate custom loggers.
```

---

## References

- [Full Research Doc](observability-patterns.md) - 781 lines with code examples
- [Weave Docs](https://docs.wandb.ai/weave)
- [Structlog Docs](https://www.structlog.org/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [Netflix A/B Testing](https://netflixtechblog.com/interpreting-a-b-test-results-false-positives-and-statistical-significance-c1522d0db27a)
