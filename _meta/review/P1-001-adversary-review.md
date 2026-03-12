# P1-001 Adversary Review: Safety & Guardrails

**Date:** 2026-03-12  
**Reviewer:** Adversary Agent (Haiku 4.5)  
**Contract:** P1-001 Safety Integration  
**Files Reviewed:** injection.py, validators.py, budget.py, audit.py  
**Test Coverage:** 108 tests (ALL PASSING)  

---

## EXECUTIVE SUMMARY

**VERDICT: FAIL** - Critical vulnerabilities in injection detection allow common evasion techniques to bypass all detection layers. Feature-complete but NOT production-ready.

**Critical Issues Found:** 2  
**High Issues Found:** 3  
**Medium Issues Found:** 4  
**Low Issues Found:** 2  

Recommendation: Block merge until CRITICAL issues resolved.

---

## CRITICAL ISSUES (MUST FIX)

### Issue 1: Unicode Normalization Bypass in Injection Detection

**Severity:** CRITICAL  
**Impact:** Attackers can bypass prompt injection detection using unicode combining characters

**Description:**

The `_normalize_unicode()` function in `injection.py` uses `unicodedata.normalize("NFKC", text)` which decomposes and recomposes characters, but **does not handle all forms of unicode obfuscation**. Specifically:

1. **Combining diacritical marks** - Characters with combining marks (U+0300–U+036F) survive normalization
2. **Lookalike character substitution** - Characters that look identical after normalization but aren't caught
3. **Character composition variations** - Some characters have multiple valid NFKC representations

**Proof of Concept:**

```python
from convergence.safety.injection import InjectionDetector

detector = InjectionDetector()

# These SHOULD be detected as injections but are NOT:
test_cases = [
    "Ign͡ore previous",        # macron combining mark
    "ĭğñőŕé previous",        # combining marks on each letter  
    "Ⅰgnore",                  # uppercase roman numeral (U+2160)
    "ignοre",                  # omicron (U+03BF) instead of 'o' (U+006F)
    "ignore\u0301",            # combining acute accent
]

for text in test_cases:
    result = detector.detect(text)
    print(f"{text}: is_injection={result.is_injection}")
    # Output: All False - VULNERABLE
```

**Evidence from Adversary Testing:**

```
[TEST 1] Unicode Normalization Bypass
  MISSED   | combining macron               | 'Ign͡ore previous'
  MISSED   | combining marks                | 'ĭğñőŕé previous'
  MISSED   | uppercase roman numeral I      | 'Ⅰgnore'
  MISSED   | omicron instead of o           | 'ignοre'
  MISSED   | combining acute accent on 'e'  | 'ignoré'
```

**Root Cause:**

In `injection.py` lines 137-153, the normalization process:
1. Uses NFKC normalization (good, but not sufficient)
2. Removes some zero-width characters (good, but incomplete)
3. **DOES NOT** remove combining marks or handle lookalike character substitution

```python
def _normalize_unicode(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    # ... removes zero-width chars ...
    return normalized
    # MISSING: removal of combining marks (category Mn)
    # MISSING: detection of lookalike substitutions (omicron vs o)
```

**Recommended Fix:**

```python
def _normalize_unicode(text: str) -> str:
    # NFKC first
    normalized = unicodedata.normalize("NFKC", text)
    
    # Remove zero-width characters
    zero_width_chars = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u00ad"]
    for char in zero_width_chars:
        normalized = normalized.replace(char, "")
    
    # CRITICAL: Remove combining marks (diacritical marks)
    normalized = ''.join(
        char for char in normalized 
        if unicodedata.category(char) != 'Mn'
    )
    
    # CRITICAL: Replace common lookalike substitutions
    lookalike_map = {
        'ο': 'o',   # U+03BF omicron -> 'o'
        'Ο': 'O',   # U+039F omicron -> 'O'
        'ν': 'v',   # U+03BD nu -> 'v'
        'Ⅰ': 'I',   # U+2160 Roman I -> 'I'
        'Ⅴ': 'V',   # U+2164 Roman V -> 'V'
    }
    for lookalike, replacement in lookalike_map.items():
        normalized = normalized.replace(lookalike, replacement)
    
    return normalized
```

**Implementation Effort:** Trivial (modify single function)  
**Risk:** Low (only affects injection detection, not other subsystems)  
**Priority:** P0 - Block merge without this fix

---

### Issue 2: Incomplete Secret Detection Pattern Coverage

**Severity:** CRITICAL  
**Impact:** API keys and credentials in non-standard formats silently leak in output validation

**Description:**

The secret detection patterns in `validators.py` (lines 79-95) are too narrow. Missing common credential formats that appear in production systems:

1. **Password assignment patterns** - `password=value` with special characters (MISSED)
2. **Key-value pairs without specific prefix** - `api_key:token123` format (MISSED)
3. **Connection strings with varied syntax** - some formats not matched
4. **Custom credential naming** - systems using `secret`, `token`, `credential` variables

**Proof of Concept:**

```python
from convergence.safety.validators import OutputValidator

validator = OutputValidator(detect_secrets=True)

# These contain secrets but are NOT detected:
test_cases = [
    "password=MyS3cr3t!",              # Password with special chars - MISSED
    "api_key:xyzabc123def456ghi789",   # Custom key format - MISSED
]

for text in test_cases:
    result = validator.validate(text)
    print(f"{text}: contains_secrets={result.contains_secrets}")
    # Output: Both False - VULNERABLE
```

**Evidence from Adversary Testing:**

```
[MEDIUM] Secret Pattern Coverage:
  MISSED   | Password with special chars         | 'password=MyS3cr3t!'
  MISSED   | API key alternate format            | 'api_key:xyzabc123def456ghi789'
```

**Root Cause:**

In `validators.py` lines 79-95:
- Regex patterns are very specific (e.g., `r"password\s+is[:\s]+\S+"`)
- They miss variations like `password=value` (uses `=` instead of `is`)
- Generic patterns like `api_key:...` are not covered

```python
SECRET_PATTERNS = [
    # ... existing patterns ...
    (re.compile(r"password\s+is[:\s]+\S+", re.IGNORECASE), "password"),  # ONLY matches "is" not "="
    # MISSING: password=value pattern
    # MISSING: generic key:value patterns
]
```

**Recommended Fix:**

Add patterns in `SECRET_PATTERNS`:

```python
SECRET_PATTERNS = [
    # ... existing patterns ...
    # Password assignment (various formats)
    (re.compile(r"password\s*[=:]\s*[\w!@#$%^&*()_+\-=\[\]{}|;:'\",./<>?]{6,}", re.IGNORECASE), "password"),
    # Generic key:value patterns (api_key:, secret:, token:, credential:)
    (re.compile(r"(api_key|secret|token|credential)\s*[:=]\s*[\w\-_+/]{10,}", re.IGNORECASE), "generic_credential"),
    # AWS keys with optional spaces
    (re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE), "aws_access_key"),
]
```

**Implementation Effort:** Trivial (add 2-3 regex patterns)  
**Risk:** Low (only affects secret detection)  
**Priority:** P0 - Block merge without this fix

---

## HIGH SEVERITY ISSUES

### Issue 3: Hallucination Detection Fails on Common Patterns

**Severity:** HIGH  
**Impact:** LLM hallucinations pass through validation layer undetected

**Description:**

The `_calculate_hallucination_risk()` function in `validators.py` (lines 242-298) has significant coverage gaps:

1. **Future citations not flagged** - "According to recent research (2025)" produces risk=0.0
2. **Absolute claims not flagged** - "100% accuracy in all cases" produces risk=0.0
3. **Contradiction detection fails** - Self-contradictions don't trigger detection

**Proof of Concept:**

```python
from convergence.safety.validators import OutputValidator

validator = OutputValidator(detect_hallucination=True)

tests = [
    "According to recent research (2025), quantum computers...",  # Future citation
    "This method has 100% accuracy in all cases",               # Absolute claim
    "Python is compiled. Actually, Python is interpreted.",     # Contradiction
]

for text in tests:
    result = validator.validate(text)
    print(f"Text: {text[:50]}...")
    print(f"  Risk: {result.hallucination_risk}")
    print(f"  Contradiction: {result.contains_contradiction}")
```

**Evidence from Adversary Testing:**

```
[MEDIUM] Hallucination Coverage:
  Risk=0.00 | Contradiction=    0 | Future citation
  Risk=0.00 | Contradiction=    0 | Absolute claim
  Risk=0.00 | Contradiction=    0 | Self contradiction
```

**Root Cause:**

1. Citation pattern (line 127-130) only flags if `known_sources` is empty - doesn't check if year is future
2. Overconfidence patterns (lines 120-125) miss "100%" without "certain/sure" follow-up
3. Contradiction detection (lines 281-296) requires exact matching of subject and predicate - fragile

**Recommended Fix:**

Add year-aware citation checking and improve pattern matching:

```python
def _calculate_hallucination_risk(self, text: str, context: Optional[Dict[str, Any]] = None) -> tuple[float, bool]:
    risk = 0.0
    context = context or {}
    
    # ... existing checks ...
    
    # Check for future citations
    import re
    from datetime import datetime
    future_year_pattern = re.compile(r'(\d{4})')
    for match in future_year_pattern.finditer(text):
        year = int(match.group(1))
        if year > datetime.now().year:
            risk = max(risk, 0.4)  # Flag future year citations
    
    # Check for absolute claims (100%, 100% accuracy, etc)
    if re.search(r'100%\s+(accurate|correct|sure|certain|true)', text, re.IGNORECASE):
        risk = max(risk, 0.5)
```

**Implementation Effort:** Moderate  
**Risk:** Low  
**Priority:** P1 - Fix before release

---

### Issue 4: Budget Daily Reset Not Timezone-Aware

**Severity:** HIGH  
**Impact:** Budget limits can be circumvented by crossing midnight boundary with ambiguous timezone handling

**Description:**

Budget manager uses `datetime.utcnow()` for timestamps but the daily reset logic (line 278 in `budget.py`) checks:

```python
if today == datetime.utcnow().date():
```

This creates a race condition near midnight UTC. If records are stored with a timestamp in one timezone but checked against UTC midnight, budget enforcement becomes inconsistent.

**Root Cause:**

In `budget.py` lines 126-132 and line 278:
- Date keys use UTC-based strings: `dt.strftime("%Y-%m-%d")`
- But comparison uses current UTC time, which may not match stored record timezone
- No timezone documentation in code

**Recommended Fix:**

Add explicit timezone handling:

```python
def _get_date_key(self, dt: datetime) -> str:
    """Get storage key for a date (UTC)."""
    # Ensure we're using UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d")

async def record_cost(self, ...):
    # Ensure timestamp is UTC
    if timestamp and timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
```

**Implementation Effort:** Moderate  
**Risk:** Medium (affects budget logic)  
**Priority:** P1 - Fix before release

---

### Issue 5: Audit Log Does Not Sanitize Input for JSONL Injection

**Severity:** HIGH  
**Impact:** Malicious messages could corrupt audit logs if they contain newlines or JSONL-breaking content

**Description:**

The `_write_event()` method in `audit.py` (lines 210-220) trusts the event message without sanitization:

```python
def _write_event(self, event: AuditEvent) -> None:
    line = json.dumps(event.model_dump(), default=str) + "\n"
    with open(self.log_path, "a") as f:
        f.write(line)
```

While `json.dumps()` does escape newlines, it's relying on Python's JSON implementation. Better to be explicit.

**Root Cause:**

No explicit sanitization of message field before creating JSON. While the test passes (because `json.dumps` handles it), this is fragile:

```python
event = AuditEvent(
    level=AuditLevel.INFO,
    message='Normal\n{"injected": "event"}',  # Will be escaped by json.dumps
    # ... but relies on implementation detail
)
```

**Recommended Fix:**

Explicitly sanitize before serialization:

```python
def _write_event(self, event: AuditEvent) -> None:
    # Sanitize message field explicitly
    if event.message:
        event.message = event.message.replace('\n', '\\n').replace('\r', '\\r')
    
    line = json.dumps(event.model_dump(), default=str) + "\n"
    try:
        with open(self.log_path, "a") as f:
            f.write(line)
    except Exception:
        pass
```

**Implementation Effort:** Trivial  
**Risk:** Low  
**Priority:** P2 - Fix in next PR

---

## MEDIUM SEVERITY ISSUES

### Issue 6: Semantic Injection Detection Confidence Calculation Unclear

**Severity:** MEDIUM  
**Impact:** Users cannot trust confidence scores for borderline cases

**Description:**

In `injection.py` lines 315-332, the semantic detection confidence formula is ad-hoc:

```python
confidence = min(0.9, 0.5 + 0.2 * len(found_categories))
```

This means:
- 2 categories found = 0.9 confidence (high)
- But these might be legitimate words in normal text

No justification for the constants 0.5 and 0.2.

**Recommended Fix:**

Document the calculation and consider a Bayesian approach:

```python
# Confidence represents how sure we are this is an attack
# More categories = higher confidence (multiplicative)
# Max confidence = 0.9 for semantic detection alone
if len(found_categories) >= 3:
    confidence = 0.8
elif len(found_categories) == 2:
    confidence = 0.6
else:
    confidence = 0.3
```

**Implementation Effort:** Trivial  
**Risk:** Low  
**Priority:** P3 - Nice to have

---

### Issue 7: PII Detection Regex Patterns Missing Edge Cases

**Severity:** MEDIUM  
**Impact:** Valid PII patterns in edge cases may not be detected

**Description:**

Email regex in `validators.py` line 61-62:
```python
r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
```

This DOES catch `john+spam@example.com` but the `|` character is unnecessary (inside `[...]` it's literal, not alternation).

Phone regex line 64-65 is complex and might miss:
- Parentheses-only format: `(555) 123-4567`
- International formats with multiple spaces

**Recommended Fix:**

Improve regex patterns for robustness:

```python
PIIType.EMAIL: re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}\b"
),
PIIType.PHONE: re.compile(
    r"\b(?:\+?1\s*)?(?:\(\d{3}\)|\d{3})\s*[-.\s]?\d{3}\s*[-.\s]?\d{4}\b"
),
```

**Implementation Effort:** Trivial  
**Risk:** Low  
**Priority:** P3 - Nice to have

---

### Issue 8: Budget Manager Error Messaging Could Leak Information

**Severity:** MEDIUM  
**Impact:** Error messages might expose budget details to users

**Description:**

In `budget.py` lines 265-266:

```python
raise BudgetExceededError(
    f"Session limit exceeded: ${session_spent + amount:.2f} > ${self.config.per_session_limit:.2f}"
)
```

This error message reveals:
- Current session spending
- Total limit
- Exactly how much would be exceeded

An attacker could probe to determine budget structure.

**Recommended Fix:**

Sanitize error messages for external consumption:

```python
# Internal logging (detailed)
self._logger.warning(f"Session limit: ${session_spent:.2f} + ${amount:.2f} > ${limit:.2f}")

# User-facing error (generic)
raise BudgetExceededError("Session budget limit exceeded. Request cannot be processed.")
```

**Implementation Effort:** Trivial  
**Risk:** Low  
**Priority:** P3 - Nice to have

---

## LOW SEVERITY ISSUES

### Issue 9: Missing Input Validation on Custom Patterns

**Severity:** LOW  
**Impact:** Invalid regex patterns could cause DoS via ReDoS

**Description:**

In `injection.py` lines 262-265, custom patterns are compiled without validation:

```python
for pattern in self.additional_patterns:
    self._compiled_patterns.append(
        (re.compile(pattern, re.IGNORECASE), "custom", InjectionSeverity.HIGH)
    )
```

If a user provides a ReDoS (Regular Expression Denial of Service) pattern, it could hang.

**Recommended Fix:**

Add regex validation:

```python
for pattern in self.additional_patterns:
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        # Test with timeout to catch ReDoS
        # (would need to add timeout logic)
        self._compiled_patterns.append((compiled, "custom", InjectionSeverity.HIGH))
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}")
```

**Implementation Effort:** Trivial  
**Risk:** Low  
**Priority:** P3 - Nice to have

---

### Issue 10: Type Hints Missing in Some Function Signatures

**Severity:** LOW  
**Impact:** Code is less maintainable, mypy --strict may fail

**Description:**

Several functions missing return type hints:
- `injection.py` line 267: `_rule_based_detect()` missing return type hint on tuple
- `validators.py` line 196: `_detect_pii()` return type could be more precise

**Fix:** Add explicit return types

```python
def _rule_based_detect(self, text: str) -> tuple[list[str], InjectionSeverity]:
def _detect_pii(self, text: str) -> tuple[bool, list[PIIType], str]:
```

**Implementation Effort:** Trivial  
**Priority:** P3 - Code quality only

---

## VERIFIED WORKING (PASSED ADVERSARY TESTS)

- [x] **Concurrent request safety** - Budget limits properly enforced under concurrency
- [x] **Fail-closed mode** - Storage failures properly reject requests when fail_open=False
- [x] **Leetspeak detection** - Numeric substitutions caught
- [x] **Semantic injection detection** - Paraphrased attacks detected with good confidence
- [x] **Audit log JSONL format** - Newlines properly escaped, no corruption
- [x] **Base64 encoding detection** - Encoded payloads detected and decoded
- [x] **PII edge cases** - Phone with country codes, emails with plus addressing all detected
- [x] **Rate limiting** - Requests per minute limit enforced correctly
- [x] **Daily budget limits** - Transition across dates handled correctly
- [x] **Team budget rollup** - Team-level aggregation works as designed

---

## RECOMMENDATIONS FOR TESTING

Before marking this as production-ready, add:

1. **Fuzz testing for injection patterns** - Use property-based testing (Hypothesis) to generate attack variations
2. **Penetration testing on secrets** - Test with real production API key formats from major cloud providers
3. **Timezone edge case tests** - Test budget reset near midnight UTC in all timezones
4. **Load testing** - Verify audit logging doesn't bottleneck under high concurrency
5. **OWASP Top 10 coverage** - Map detection to specific OWASP LLM Top 10 attacks

---

## SUMMARY OF FIXES REQUIRED

| Issue | Severity | Files | LOC | Priority |
|-------|----------|-------|-----|----------|
| Unicode bypass | CRITICAL | injection.py | ~10 | P0 |
| Secret patterns | CRITICAL | validators.py | ~5 | P0 |
| Hallucination detection | HIGH | validators.py | ~10 | P1 |
| Timezone handling | HIGH | budget.py | ~5 | P1 |
| Audit sanitization | HIGH | audit.py | ~3 | P2 |
| Semantic confidence | MEDIUM | injection.py | ~5 | P3 |
| PII regex | MEDIUM | validators.py | ~3 | P3 |
| Error messages | MEDIUM | budget.py | ~10 | P3 |
| Regex validation | LOW | injection.py | ~5 | P3 |
| Type hints | LOW | multiple | ~10 | P3 |

---

## VERDICT

**FAIL** - Do not merge to main.

The safety layer is feature-complete and handles common cases well (108 tests pass), but the two CRITICAL vulnerabilities in injection detection and secret detection expose the system to known attacks. These must be fixed before production use.

Estimated fix time: 4-6 hours for all critical issues, 2-3 days for full hardening.

---

**Reviewed by:** Adversary Agent  
**Date:** 2026-03-12  
**Confidence:** HIGH (actual attack scenarios tested, not theoretical)
