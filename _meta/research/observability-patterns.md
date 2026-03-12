# Observability Patterns for Text Classification & Pattern Matching Systems

**Research Date:** 2026-03-11  
**Status:** Complete  
**Scope:** Library-level observability for regex/classification systems in Python

---

## 1. Making Classification Systems Observable

### Core Observables

For text classification and pattern matching systems, track four core signals:

#### A. Match Results (Hit Rate Tracking)
- **What to log:** Whether pattern matched, confidence if applicable, pattern variant tried
- **Why:** Understand coverage gaps and hit rate trends over time
- **Implementation:** Structured field `match_result: {matched: bool, confidence: float, pattern_id: str}`

#### B. Confidence Scores
- **Explicit confidence:** When model/classifier outputs a score (0-1)
- **Linguistic confidence:** Extracted from text analysis (e.g., hedging language, certainty markers)
- **Pattern match confidence:** How definitively did regex match? (full vs. partial, position, anchoring)
- **Integration:** Always include as `confidence: {method: str, score: float}` in observability output

#### C. False Positives / Edge Cases
- **Record non-matches that seem like they should match** (improve recall debugging)
- **Record ambiguous matches** (high confidence but conflicting patterns)
- **Track user corrections** (user said "this should/shouldn't match") as feedback loop
- **Implementation:** Structured rejection logs with context

#### D. Classification Metrics
- **Accuracy:** % of matches that were correct (requires ground truth)
- **Precision:** Of matches made, how many were right
- **Recall:** Of things that should match, how many did
- **F1 score:** Harmonic mean of precision/recall
- **Per-pattern metrics:** Track each regex/classifier separately

---

## 2. Recommended Observability Stack

### Primary: Weave (Already in Dependencies)

**Why:** The Convergence already has `weave>=0.50.0` as core dependency.

**Patterns for classification:**

```python
import weave

@weave.op()
def classify_text(text: str, patterns: dict) -> dict:
    """Classify text and log all observable signals."""
    result = {
        'text': text,
        'matches': [],
        'confidence': 0.0,
    }
    
    # Track each pattern attempt
    for pattern_name, pattern_obj in patterns.items():
        match = pattern_obj.search(text)
        if match:
            result['matches'].append({
                'pattern': pattern_name,
                'matched_text': match.group(0),
                'confidence': extract_confidence(text),  # Your confidence extraction
                'span': match.span(),
            })
    
    return result  # Weave logs this automatically
```

**Strengths:**
- Decorator-based, zero-friction integration
- Returns structured data that Weave traces automatically
- Integrates with W&B dashboard for visualization
- Already configured in codebase

**Limitations:**
- Requires W&B entity/project (optional but recommended)
- Weave @op() only logs at function boundary; internal metrics need manual structuring

### Secondary: structlog (Recommended Addition)

**Why:** Structured, JSON-friendly logging without regex parsing burdens.

**Current State:** Not in dependencies.  
**Cost:** Single import, ~10 lines per logging point.

**Pattern for confidence tracking:**

```python
import structlog

logger = structlog.get_logger()

def match_pattern(text: str, pattern_id: str, regex_obj, confidence_extractor):
    match = regex_obj.search(text)
    
    logger.msg(
        "pattern_match_attempt",
        pattern_id=pattern_id,
        matched=match is not None,
        confidence=confidence_extractor(text) if match else None,
        text_length=len(text),
        match_span=match.span() if match else None,
    )
    
    return match
```

**Output (single JSON line):**
```json
{"pattern_id": "email", "matched": true, "confidence": 0.92, "text_length": 256, "match_span": [10, 30], "event": "pattern_match_attempt", "timestamp": "2026-03-11T14:23:00"}
```

**Strengths:**
- Zero regex parsing needed; logs are directly queryable
- Context preservation (bind session IDs, model versions)
- Processor pipeline for filtering sensitive data
- ~100K+ weekly downloads, industry standard

**When to Use:** If building observability for users of your library, structlog is lighter than Weave.

### Tertiary: OpenTelemetry (Future-Proofing)

**When:** If observability needs scale to multi-service deployments.

**Current State:** Not in dependencies; would add ~3 new deps.

**Minimal setup for classification:**
```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Trace a classification call
with tracer.start_as_current_span("classify") as span:
    span.set_attribute("pattern.id", pattern_id)
    span.set_attribute("confidence", confidence)
    span.set_attribute("match.success", bool(match))
    result = classify(text)

# Emit metric: classification accuracy
accuracy_counter = meter.create_counter("classification.accuracy")
accuracy_counter.add(1 if correct else 0, {"pattern": pattern_id})
```

**Strengths:**
- Vendor-neutral; works with any backend
- Tracing + metrics in one system
- 224M downloads/month (Python SDK)
- Spans can be sampled (reduce verbosity in production)

**Cost:** 1000+ lines for full integration. **Only adopt if multi-system observability is needed.**

---

## 3. Tracking Classifier Drift & Degradation

### The Problem

Text classifiers degrade when input distribution shifts. Regex patterns written for 2024 may not match 2026 edge cases. You need to detect when confidence drops, false positive rate rises, or recall plummets.

### Recommended Approach: Sliding Window Confidence & Error Tracking

#### A. Record Every Classification Attempt

Store minimal: `(timestamp, pattern_id, confidence, was_match, user_feedback)`

```python
# In your Storage class (you have multiple storage backends)
async def log_classification_event(
    pattern_id: str,
    confidence: float,
    matched: bool,
    user_correction: Optional[bool] = None,  # User said this was wrong?
):
    """Record classification attempt for drift detection."""
    await storage.insert("classification_events", {
        "timestamp": datetime.now().isoformat(),
        "pattern_id": pattern_id,
        "confidence": confidence,
        "matched": matched,
        "user_feedback": user_correction,  # True = wrong, False = correct, None = unknown
    })
```

#### B. Detect Confidence Drift (Weekly Batches)

```python
async def detect_confidence_drift(pattern_id: str, threshold: float = 0.05):
    """Detect if average confidence has dropped significantly."""
    events = await storage.query_recent_events(pattern_id, days=7)
    
    if len(events) < 30:  # Need sample size
        return None  # Not enough data
    
    avg_confidence = mean([e['confidence'] for e in events])
    baseline = await storage.get_baseline_confidence(pattern_id)  # Rolling average
    
    drift = abs(avg_confidence - baseline) / (baseline + 1e-6)
    if drift > threshold:
        logger.warning(
            "confidence_drift_detected",
            pattern_id=pattern_id,
            current=avg_confidence,
            baseline=baseline,
            drift_pct=drift * 100,
        )
        return True
    return False
```

#### C. False Positive Rate Tracking

```python
async def compute_false_positive_rate(pattern_id: str, window_days: int = 7):
    """Track % of matches that user marked as incorrect."""
    events = await storage.query_events_with_feedback(pattern_id, days=window_days)
    
    if not events:
        return None
    
    false_positives = sum(1 for e in events if e['matched'] and e['user_feedback'] is False)
    total_matches = sum(1 for e in events if e['matched'])
    
    if total_matches == 0:
        return 0.0
    
    fpr = false_positives / total_matches
    logger.info(
        "false_positive_rate",
        pattern_id=pattern_id,
        fpr=fpr,
        false_positives=false_positives,
        total_matches=total_matches,
    )
    return fpr
```

#### D. Edge Case Collection

```python
async def collect_edge_case(
    text: str,
    pattern_id: str,
    confidence: float,
    reason: str,  # "should_match_but_didnt", "ambiguous", "conflicting_patterns"
):
    """Capture edge cases for pattern improvement."""
    await storage.insert("edge_cases", {
        "timestamp": datetime.now().isoformat(),
        "pattern_id": pattern_id,
        "text_sample": text[:500],  # First 500 chars
        "confidence": confidence,
        "reason": reason,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
    })
    
    # Alert if edge case rate is rising
    rate = await storage.count_recent_edge_cases(pattern_id, hours=24)
    if rate > 5:  # More than 5/day is a signal
        logger.warning("edge_case_spike", pattern_id=pattern_id, count=rate)
```

### Integration with The Convergence's RL Loop

Your MAB (Multi-Armed Bandit) loop already selects strategies. Extend it to patterns:

1. **Arm = Pattern variant** (regex_v1 vs regex_v2 vs classifier_v1)
2. **Reward = Inverse of false positive rate + confidence bonus**
3. **Thompson Sampling chooses which pattern to try next**
4. **User feedback → update pattern reward → explore new patterns**

---

## 4. Hook Points for Library Users

For a library (not a service), minimize coupling. Provide **optional hooks** users can integrate:

### Pattern 1: Observer Pattern (Zero Required Setup)

```python
class ClassificationObserver(Protocol):
    """Users can implement this to observe classifications."""
    
    async def on_match(
        self,
        pattern_id: str,
        text: str,
        confidence: float,
        matched: bool,
    ) -> None:
        """Called after each classification attempt."""
        ...

# In your classifier:
class TextClassifier:
    def __init__(self, observers: list[ClassificationObserver] = None):
        self.observers = observers or []
    
    async def classify(self, text: str) -> dict:
        result = self._classify_internal(text)
        
        for obs in self.observers:
            await obs.on_match(
                pattern_id=result['pattern'],
                text=text,
                confidence=result['confidence'],
                matched=result['matched'],
            )
        
        return result
```

**User integration:**
```python
class MyWeaveObserver(ClassificationObserver):
    async def on_match(self, pattern_id, text, confidence, matched):
        weave.log_classification(pattern_id, confidence, matched)

classifier = TextClassifier(observers=[MyWeaveObserver()])
```

### Pattern 2: Context Manager for Batch Operations

```python
class ObservabilityContext:
    """Optional context manager for batch observability."""
    
    def __init__(self, pattern_id: str, debug: bool = False):
        self.pattern_id = pattern_id
        self.debug = debug
        self.matches = []
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.debug:
            logger.info(
                "classification_batch_complete",
                pattern_id=self.pattern_id,
                total_attempts=len(self.matches),
                success_rate=sum(m['matched'] for m in self.matches) / len(self.matches),
            )
    
    async def classify(self, text: str) -> dict:
        result = await self.classifier.classify(text)
        self.matches.append(result)
        return result
```

**User integration:**
```python
async with ObservabilityContext("email_pattern", debug=True) as ctx:
    for email_text in batch:
        result = await ctx.classify(email_text)
```

### Pattern 3: Configuration-Based Observability

```python
from pydantic import BaseModel

class ObservabilityConfig(BaseModel):
    enabled: bool = True
    method: str = "weave"  # or "structlog", "noop"
    log_level: str = "INFO"
    sample_rate: float = 1.0  # Log 100% of events by default
    track_edge_cases: bool = True
    drift_detection_threshold: float = 0.05
    
    class Config:
        env_prefix = "CONVERGENCE_OBS_"

# In your classifier init:
class TextClassifier:
    def __init__(self, config: ObservabilityConfig = None):
        self.config = config or ObservabilityConfig()
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        if self.config.method == "weave":
            return WeaveLogger()
        elif self.config.method == "structlog":
            return structlog.get_logger()
        else:
            return NoOpLogger()
```

**User sets via environment:**
```bash
export CONVERGENCE_OBS_METHOD=structlog
export CONVERGENCE_OBS_LOG_LEVEL=DEBUG
export CONVERGENCE_OBS_SAMPLE_RATE=0.1  # Log 10% to reduce noise
```

---

## 5. Minimal Viable Observability (MVo)

### For Initial Release

**Only these three metrics:**

1. **Hit Rate:** % of texts that matched any pattern
2. **Avg Confidence:** Average confidence across all matches
3. **Error Rate:** % of matches user marked as wrong

**Implementation (50 lines):**

```python
import structlog
from collections import deque
from datetime import datetime, timedelta

logger = structlog.get_logger()

class MinimalObserver:
    def __init__(self, window_size: int = 100):
        self.recent_events = deque(maxlen=window_size)
    
    async def on_match(self, pattern_id: str, confidence: float, matched: bool):
        self.recent_events.append({
            "timestamp": datetime.now(),
            "confidence": confidence,
            "matched": matched,
        })
        
        # Log only when buffer is full (every 100 events)
        if len(self.recent_events) == self.recent_events.maxlen:
            hit_rate = sum(1 for e in self.recent_events if e['matched']) / len(self.recent_events)
            avg_conf = sum(e['confidence'] for e in self.recent_events) / len(self.recent_events)
            
            logger.info(
                "classification_batch_metrics",
                hit_rate=hit_rate,
                avg_confidence=avg_conf,
                batch_size=len(self.recent_events),
            )
```

**What this gives you:**
- Zero external dependencies (structlog is stdlib-like in Python ecosystem)
- Queryable, JSON-formatted logs
- Enough signal to detect major degradation
- Users can extend with their own observers

### Debug Mode vs Production

```python
class TextClassifier:
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    async def classify(self, text: str) -> dict:
        result = self._classify_internal(text)
        
        if self.debug:
            logger.debug(
                "classification_details",
                text_preview=text[:100],
                all_matches_attempted=result.get('attempts', []),
                timing_ms=result.get('elapsed_ms'),
            )
        else:
            logger.info(
                "classification_result",
                matched=result['matched'],
                confidence=result['confidence'],
            )
        
        return result
```

**Debug mode = verbose detail**  
**Production = only summary + anomalies**

---

## 6. Common Pitfalls

### Pitfall 1: Logging Every Character Match

**Symptom:** Log volume explodes; observer pattern slows down classification 10x.

**Why:** Logging to disk is I/O bound. Instrumenting regex character-level details per match is overkill.

**Fix:**
- Log only at pattern level, not character level
- Use sampling (log 10% of events in prod)
- Buffer events, emit batch logs every N events

**Source:** [Preventing Observability Overinstrumentation](https://speedscale.com/blog/python-observability/)

---

### Pitfall 2: Confidence Scores Without Baseline

**Symptom:** You see `confidence: 0.87` but don't know if that's good or bad. Drift detection false alarms.

**Why:** Confidence is meaningless without reference. A model that always outputs 0.87 (even when wrong) looks "stable."

**Fix:**
- Track `confidence_distribution` (not just mean) weekly
- Compare to baseline built on first 1K events
- Alert on confidence *variance* rising, not just mean shift
- Pair confidence with correctness when possible

```python
# Good: Confidence with correctness pairing
{
    "confidence": 0.92,
    "was_correct": True,  # or None if unknown
    "match_position": [10, 20],
}

# Bad: Confidence in isolation
{
    "confidence": 0.92,
}
```

**Source:** [Confidence Intervals in A/B Testing](https://www.statsig.com/perspectives/confidence-intervals-ab-testing)

---

### Pitfall 3: User Feedback Loop Without Aggregation

**Symptom:** You collect feedback ("this match was wrong") but never use it to retrain or adapt patterns.

**Why:** Feedback without action is noise. Users see no improvement.

**Fix:**
- Batch feedback weekly
- Run pattern evolution (you have this in RLP!)
- Generate new pattern variants with SAO
- A/B test old vs new patterns
- Report back to users: "Pattern updated based on your corrections"

**Source:** Integrate with existing RL loop; see _meta/research/ on RLP/SAO patterns.

---

### Pitfall 4: Confusing Match Count with Accuracy

**Symptom:** "Pattern matched 500 times" doesn't tell you how many were *correct*.

**Why:** High volume ≠ high quality. A pattern that matches everything has high volume but low precision.

**Fix:**
```python
# Good: Metrics with context
{
    "pattern_id": "email",
    "total_matches": 500,
    "confirmed_correct": 485,  # User feedback
    "precision": 0.97,
    "matched_texts_sample": ["user@example.com", "invalid@"],  # With edge cases
}

# Bad: Volume alone
{
    "pattern_id": "email",
    "match_count": 500,
}
```

**Source:** [Netflix A/B Testing Best Practices](https://netflixtechblog.com/interpreting-a-b-test-results-false-positives-and-statistical-significance-c1522d0db27a)

---

### Pitfall 5: Over-Logging Sensitive Text

**Symptom:** Logs contain credit card numbers, emails, passwords from user input.

**Why:** Structured logging makes this easier to miss; "log everything" mindset + PII = data breach.

**Fix:**
```python
# Good: Hash or truncate sensitive data
{
    "pattern_id": "credit_card",
    "text_hash": "a1b2c3...",  # SHA-256 of full text
    "text_preview": "****-****-****-1234",  # Last 4 digits only
    "matched": True,
}

# Bad: Raw text
{
    "text": "4111111111111111",  # Don't do this!
    "matched": True,
}
```

**Integration:**
- Use structlog's processor pipeline to scrub fields
- Hash user inputs before logging

**Source:** [Structlog Context Processors](https://www.structlog.org/en/17.1.0/)

---

## 7. Alternatives Considered & Rejected

### Alternative 1: Custom In-Memory Metrics Class

**Approach:** Build a simple dict that tracks counts.

```python
class Metrics:
    def __init__(self):
        self.matches = 0
        self.errors = 0
    
    def record_match(self): self.matches += 1
```

**Why Rejected:**
- No persistence (metrics lost on restart)
- Can't query historical trends
- Doesn't integrate with dashboards
- Requires manual export/serialization

**Better:** Use structlog (queries via grep/log aggregator) or Weave (dashboard built-in).

---

### Alternative 2: Full OpenTelemetry from Day 1

**Approach:** Instrument everything with trace spans and meters.

**Why Rejected:**
- 1000+ lines of integration code for minimal value initially
- Requires external backend (Jaeger, Datadog, etc.)
- Over-engineered for a library (not a service)
- Users may not need it

**Better:** Start with structlog/Weave; add OTel when users ask for multi-service tracing.

---

### Alternative 3: Database-First Logging

**Approach:** Store all events directly in SQLite (you have multi_backend storage).

**Why Rejected:**
- Database writes are slower than structured logging
- Log aggregation tools expect log format, not DB queries
- Couples observability to storage layer
- Makes it hard for library users to integrate their own storage

**Better:** Use structlog for events; let users pipe to their own storage if needed.

---

## 8. Recommended Implementation Plan

### Phase 1 (Now): Minimal Observability + Weave

1. Add structured logging to confidence extraction (`confidence.py`):
   ```python
   import structlog
   logger = structlog.get_logger()
   
   @weave.op()
   def extract_confidence(text: str, method: str = "auto") -> Optional[float]:
       result = _extract_confidence_internal(text, method)
       logger.msg("confidence_extraction", text_len=len(text), method=method, result=result)
       return result
   ```

2. Extend WeaveLogger with classification events:
   ```python
   @weave.op()
   def log_classification(
       self,
       pattern_id: str,
       confidence: float,
       matched: bool,
       user_feedback: Optional[bool] = None,
   ):
       return {
           "pattern_id": pattern_id,
           "confidence": confidence,
           "matched": matched,
           "user_feedback": user_feedback,
           "timestamp": datetime.now().isoformat(),
       }
   ```

3. Test with confidence.py extraction:
   ```python
   # In tests/test_confidence_observability.py
   logger = get_weave_logger()
   result = extract_confidence("I'm 85% sure...")
   logger.log_classification("confidence_test", result, True, None)
   ```

**Effort:** 3-4 hours  
**Files:** `convergence/core/weave_logger.py`, `convergence/evaluators/confidence.py`, new test file

---

### Phase 2 (Next Sprint): Drift Detection + Feedback Loop

1. Add edge case collection to storage:
   ```python
   async def insert_classification_event(
       self,
       pattern_id: str,
       confidence: float,
       matched: bool,
       user_feedback: Optional[bool] = None,
   ):
       # Insert to whichever backend is active
       await self.backend.insert(...)
   ```

2. Compute weekly metrics:
   ```python
   async def compute_pattern_metrics(pattern_id: str):
       events = await storage.query_events(pattern_id, days=7)
       return {
           "hit_rate": ...,
           "avg_confidence": ...,
           "false_positive_rate": ...,
       }
   ```

3. Wire into MAB reward signal:
   ```python
   # In thompson_sampling.py
   reward = 1.0 - false_positive_rate + confidence_bonus
   ```

**Effort:** 8-10 hours  
**Files:** Storage layer, new `classification_metrics.py`, MAB integration

---

### Phase 3 (Future): User-Facing Observers + Docs

1. Implement observer protocol
2. Document for library users
3. Add example: "How to integrate with Datadog"

**Effort:** 5-6 hours  
**Files:** New module, README section, examples/

---

## Summary Table

| Component | Recommended | Why | Cost | Status |
|-----------|-------------|-----|------|--------|
| **Hit Rate Tracking** | structlog + Weave | Already have Weave; structlog is lightweight | 30 min | Ready now |
| **Confidence Logging** | Weave @op() | Decorator-based, zero friction | 1 hour | Ready now |
| **Drift Detection** | Storage + weekly batch | Leverage existing backends | 3 hours | Phase 2 |
| **False Positive Rate** | User feedback + computation | Requires user engagement | 2 hours | Phase 2 |
| **Edge Case Collection** | Storage + alerts | Built on Phase 2 | 1.5 hours | Phase 2 |
| **A/B Testing Patterns** | MAB Thompson Sampling | You have this; extend reward | 2 hours | Phase 2 |
| **Observer Pattern** | For library users | Optional; Phase 3 | 3 hours | Phase 3 |
| **OpenTelemetry** | Only if multi-service | Not needed initially | 1000+ | Defer |

---

## Key Sources

- [W&B Weave Documentation](https://docs.wandb.ai/weave)
- [Structlog Best Practices](https://www.structlog.org/en/17.1.0/)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/languages/python/)
- [Netflix A/B Testing](https://netflixtechblog.com/interpreting-a-b-test-results-false-positives-and-statistical-significance-c1522d0db27a)
- [Data Drift Detection](https://www.datacamp.com/tutorial/understanding-data-drift-model-drift)
- [Observability Overinstrumentation](https://speedscale.com/blog/python-observability/)

