"""
Prompt injection detection for The Convergence framework.

OWASP LLM Top 10 #1: Prompt Injection
- Rule-based detection for known patterns
- Semantic detection for paraphrased attacks
- Unicode normalization for evasion detection
"""

import base64
import re
import unicodedata
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class InjectionSeverity(str, Enum):
    """Severity levels for injection detection."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, InjectionSeverity):
            return NotImplemented
        order = [InjectionSeverity.NONE, InjectionSeverity.LOW, InjectionSeverity.MEDIUM, InjectionSeverity.HIGH, InjectionSeverity.CRITICAL]
        return order.index(self) >= order.index(other)

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, InjectionSeverity):
            return NotImplemented
        order = [InjectionSeverity.NONE, InjectionSeverity.LOW, InjectionSeverity.MEDIUM, InjectionSeverity.HIGH, InjectionSeverity.CRITICAL]
        return order.index(self) > order.index(other)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, InjectionSeverity):
            return NotImplemented
        order = [InjectionSeverity.NONE, InjectionSeverity.LOW, InjectionSeverity.MEDIUM, InjectionSeverity.HIGH, InjectionSeverity.CRITICAL]
        return order.index(self) <= order.index(other)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, InjectionSeverity):
            return NotImplemented
        order = [InjectionSeverity.NONE, InjectionSeverity.LOW, InjectionSeverity.MEDIUM, InjectionSeverity.HIGH, InjectionSeverity.CRITICAL]
        return order.index(self) < order.index(other)


class DetectionMethod(str, Enum):
    """Detection methods available."""
    RULE_BASED = "rule_based"
    SEMANTIC = "semantic"


class InjectionResult(BaseModel):
    """Result of injection detection."""
    is_injection: bool = False
    severity: InjectionSeverity = InjectionSeverity.NONE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_patterns: List[str] = Field(default_factory=list)
    methods_triggered: List[DetectionMethod] = Field(default_factory=list)
    explanation: str = ""
    action: str = "allow"


# Injection patterns organized by severity and category
INSTRUCTION_OVERRIDE_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|guidelines?)", "ignore"),
    (r"disregard\s+(all\s+)?(previous|prior|above|everything)", "ignore"),
    (r"forget\s+(all\s+)?(previous|prior|above|everything)", "ignore"),
    (r"override\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?)", "ignore"),
    (r"new\s+instructions?[:\s]", "ignore"),
    (r"from\s+now\s+on[,\s]", "ignore"),
]

SYSTEM_PROMPT_EXTRACTION_PATTERNS = [
    (r"(what|show|reveal|print|display|tell)\s+(is|are|me)?\s*(your|the)\s+(system\s+)?(prompt|instructions?|rules?|guidelines?|configuration)", "extraction"),
    (r"(initial|original|hidden|secret)\s+(prompt|instructions?)", "extraction"),
    (r"what\s+(were\s+you|are\s+you)\s+(told|instructed)\s+to\s+do", "extraction"),
    (r"(reveal|show|print|display)\s+(your|the)\s+(configuration|setup)", "extraction"),
]

ROLE_HIJACKING_PATTERNS = [
    (r"you\s+are\s+now\s+\w+", "role"),
    (r"pretend\s+(you\s+are|to\s+be)\s+", "role"),
    (r"act\s+(as\s+if|like)\s+", "role"),
    (r"respond\s+as\s+\w+", "role"),
    (r"from\s+now\s+on[,\s]+(you\s+)?(will\s+)?respond\s+as", "role"),
    (r"you\s+(will|must|should)\s+respond\s+as", "role"),
    (r"(no|without|ignore)\s+(safety|restrictions?|guidelines?|rules?|limitations?)", "role"),
    (r"(be|act)\s+(evil|harmful|unrestricted|unfiltered)", "role"),
]

DELIMITER_INJECTION_PATTERNS = [
    (r"```\s*(?:SYSTEM|system)\s*[\n:]", "delimiter"),
    (r"###\s*(?:SYSTEM|system)\s*###", "delimiter"),
    (r"\[INST\]", "delimiter"),
    (r"\[/INST\]", "delimiter"),
    (r"<\|im_start\|>", "delimiter"),
    (r"<\|im_end\|>", "delimiter"),
    (r"<\|system\|>", "delimiter"),
    (r"<\|user\|>", "delimiter"),
    (r"<\|assistant\|>", "delimiter"),
]

DATA_EXFILTRATION_PATTERNS = [
    (r"(send|post|email|transmit|upload)\s+.*(data|secrets?|credentials?|passwords?|keys?)\s+to\s+", "exfil"),
    (r"(send|post|email|transmit|upload)\s+.*\s+to\s+\w+\.(com|net|org|io)", "exfil"),
    (r"(curl|wget|fetch|http|post)\s+.*(evil|attacker|collect)", "exfil"),
    (r"email\s+(the|all)?\s*(database|db|contents?|data)", "exfil"),
    (r"(send|transmit|post)\s+(to|all)\s+.*(evil|attacker)", "exfil"),
]

# Base64 pattern for detecting encoded payloads
BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

# Suspicious but not conclusive patterns (educational context)
SUSPICIOUS_PATTERNS = [
    (r"(how\s+(does|do)\s+)?(prompt\s+)?injection\s+(work|attack)", "educational"),
    (r"explain\s+(prompt\s+)?injection", "educational"),
]

# Semantic keywords that indicate malicious intent
SEMANTIC_KEYWORDS = {
    "ignore": ["disregard", "forget", "override", "bypass", "skip", "dismiss", "neglect"],
    "instructions": ["rules", "guidelines", "constraints", "limitations", "restrictions", "directives"],
    "previous": ["prior", "above", "earlier", "original", "initial", "before"],
    "reveal": ["show", "display", "print", "output", "expose", "disclose", "tell"],
    "pretend": ["act", "roleplay", "simulate", "impersonate", "behave"],
    "game": ["play", "let's", "imagine", "scenario", "hypothetical"],
}


def _normalize_unicode(text: str) -> str:
    """Normalize unicode to detect obfuscation attacks."""
    # Normalize to NFKC (compatibility decomposition then composition)
    normalized = unicodedata.normalize("NFKC", text)

    # Remove zero-width characters
    zero_width_chars = [
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\ufeff",  # Zero-width no-break space
        "\u00ad",  # Soft hyphen
    ]
    for char in zero_width_chars:
        normalized = normalized.replace(char, "")

    return normalized


def _decode_leetspeak(text: str) -> str:
    """Decode common leetspeak substitutions."""
    leet_map = {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "8": "b",
        "!": "i",
        "@": "a",
        "$": "s",
    }
    result = text.lower()
    for leet, char in leet_map.items():
        result = result.replace(leet, char)
    return result


def _check_base64_payload(text: str) -> Optional[str]:
    """Check for base64 encoded payloads and decode them."""
    matches = BASE64_PATTERN.findall(text)
    for match in matches:
        try:
            # Try to decode and check if result is ASCII text
            decoded = base64.b64decode(match).decode("utf-8", errors="strict")
            if decoded.isprintable() and len(decoded) > 5:
                return decoded
        except Exception:
            pass
    return None


class InjectionDetector:
    """
    Detect prompt injection attacks.

    Implements multi-layer detection:
    1. Rule-based: Fast pattern matching for known attacks
    2. Semantic: Paraphrase-aware detection for novel attacks
    3. Unicode normalization: Detect obfuscation attempts
    4. Base64 decoding: Detect encoded payloads
    """

    def __init__(
        self,
        additional_patterns: Optional[List[str]] = None,
        sensitivity: str = "medium",
        mode: str = "block",
    ):
        """
        Initialize injection detector.

        Args:
            additional_patterns: Additional regex patterns to detect
            sensitivity: Detection sensitivity ("low", "medium", "high")
            mode: Action mode ("block" or "audit")
        """
        self.additional_patterns = additional_patterns or []
        self.sensitivity = sensitivity
        self.mode = mode

        # Compile all patterns for efficiency
        self._compiled_patterns: List[tuple[re.Pattern, str, InjectionSeverity]] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile all regex patterns."""
        # Critical patterns (data exfil)
        for pattern, tag in DATA_EXFILTRATION_PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), tag, InjectionSeverity.CRITICAL)
            )

        # High severity (instruction override)
        for pattern, tag in INSTRUCTION_OVERRIDE_PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), tag, InjectionSeverity.HIGH)
            )

        # High severity (system prompt extraction)
        for pattern, tag in SYSTEM_PROMPT_EXTRACTION_PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), tag, InjectionSeverity.HIGH)
            )

        # High severity (role hijacking)
        for pattern, tag in ROLE_HIJACKING_PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), tag, InjectionSeverity.HIGH)
            )

        # Medium severity (delimiter injection)
        for pattern, tag in DELIMITER_INJECTION_PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), tag, InjectionSeverity.MEDIUM)
            )

        # Low severity (suspicious but educational)
        for pattern, tag in SUSPICIOUS_PATTERNS:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), tag, InjectionSeverity.LOW)
            )

        # Add custom patterns as HIGH severity
        for pattern in self.additional_patterns:
            self._compiled_patterns.append(
                (re.compile(pattern, re.IGNORECASE), "custom", InjectionSeverity.HIGH)
            )

    def _rule_based_detect(self, text: str) -> tuple[List[str], InjectionSeverity]:
        """
        Rule-based detection using compiled patterns.

        Returns:
            Tuple of (matched_patterns, max_severity)
        """
        matched = []
        max_severity = InjectionSeverity.NONE

        # Normalize text for detection
        normalized = _normalize_unicode(text)
        leet_decoded = _decode_leetspeak(normalized)

        # Check both normalized and leetspeak-decoded versions
        texts_to_check = [normalized, leet_decoded]

        for check_text in texts_to_check:
            for pattern, tag, severity in self._compiled_patterns:
                if pattern.search(check_text):
                    if tag not in matched:
                        matched.append(tag)
                    if severity > max_severity:
                        max_severity = severity

        return matched, max_severity

    def _semantic_detect(self, text: str) -> tuple[bool, float]:
        """
        Semantic detection for paraphrased attacks.

        Returns:
            Tuple of (is_suspicious, confidence)
        """
        normalized = _normalize_unicode(text).lower()
        leet_decoded = _decode_leetspeak(normalized)

        # Check for semantic patterns
        found_categories: set[str] = set()
        for category, synonyms in SEMANTIC_KEYWORDS.items():
            if category in leet_decoded:
                found_categories.add(category)
            for synonym in synonyms:
                if synonym in leet_decoded:
                    found_categories.add(category)

        # Suspicious if multiple categories present
        # e.g., "ignore" + "instructions" + "previous"
        suspicious_combos = [
            {"ignore", "instructions"},
            {"ignore", "previous"},
            {"reveal", "instructions"},
            {"game", "pretend"},
            {"pretend", "instructions"},
        ]

        for combo in suspicious_combos:
            if combo.issubset(found_categories):
                confidence = min(0.9, 0.5 + 0.2 * len(found_categories))
                return True, confidence

        # Lower confidence if only partial match
        if len(found_categories) >= 2:
            return True, 0.3 + 0.1 * len(found_categories)

        return False, 0.0

    def _check_base64_injection(self, text: str) -> tuple[bool, InjectionSeverity]:
        """Check for injection in base64 encoded content."""
        decoded = _check_base64_payload(text)
        if decoded:
            # Run detection on decoded content
            matched, severity = self._rule_based_detect(decoded)
            if matched:
                return True, max(severity, InjectionSeverity.MEDIUM)
        return False, InjectionSeverity.NONE

    def detect(
        self,
        text: Optional[str],
        methods: Optional[List[DetectionMethod]] = None,
    ) -> InjectionResult:
        """
        Detect injection in input text.

        Args:
            text: Input text to analyze
            methods: Detection methods to use (default: all)

        Returns:
            InjectionResult with detection details
        """
        # Handle empty/None input
        if not text:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.NONE,
                confidence=1.0,
                explanation="Empty input",
                action="allow",
            )

        # Default to all methods
        if methods is None:
            methods = [DetectionMethod.RULE_BASED, DetectionMethod.SEMANTIC]

        matched_patterns: List[str] = []
        methods_triggered: List[DetectionMethod] = []
        max_severity = InjectionSeverity.NONE
        confidence = 0.0

        # Rule-based detection
        if DetectionMethod.RULE_BASED in methods:
            rule_matched, rule_severity = self._rule_based_detect(text)
            if rule_matched:
                matched_patterns.extend(rule_matched)
                methods_triggered.append(DetectionMethod.RULE_BASED)
                if rule_severity > max_severity:
                    max_severity = rule_severity
                    confidence = max(confidence, 0.9 if rule_severity >= InjectionSeverity.HIGH else 0.7)

        # Semantic detection
        if DetectionMethod.SEMANTIC in methods:
            is_suspicious, sem_confidence = self._semantic_detect(text)
            if is_suspicious:
                if "semantic" not in matched_patterns:
                    matched_patterns.append("semantic")
                methods_triggered.append(DetectionMethod.SEMANTIC)
                if sem_confidence > confidence:
                    confidence = sem_confidence
                # Semantic alone is MEDIUM unless rule-based already higher
                if max_severity < InjectionSeverity.MEDIUM and sem_confidence > 0.5:
                    max_severity = InjectionSeverity.MEDIUM

        # Base64 detection (always run)
        b64_detected, b64_severity = self._check_base64_injection(text)
        if b64_detected:
            if "base64" not in matched_patterns:
                matched_patterns.append("base64")
            if b64_severity > max_severity:
                max_severity = b64_severity
                confidence = max(confidence, 0.7)

        # Adjust based on sensitivity
        if self.sensitivity == "high":
            # More aggressive - bump up severity for borderline cases
            if max_severity == InjectionSeverity.LOW:
                max_severity = InjectionSeverity.MEDIUM
            confidence = min(1.0, confidence * 1.2)
        elif self.sensitivity == "low":
            # Less aggressive - only flag clear attacks
            if max_severity == InjectionSeverity.LOW:
                max_severity = InjectionSeverity.NONE
                matched_patterns = []
            confidence = confidence * 0.8

        is_injection = max_severity >= InjectionSeverity.MEDIUM or (
            max_severity == InjectionSeverity.LOW and self.sensitivity == "high"
        )

        # Generate explanation
        explanation = ""
        if is_injection:
            explanation = f"Detected {len(matched_patterns)} suspicious pattern(s): {', '.join(matched_patterns)}"
            if max_severity == InjectionSeverity.CRITICAL:
                explanation += ". CRITICAL: Possible data exfiltration attempt."
            elif max_severity == InjectionSeverity.HIGH:
                explanation += ". HIGH: Instruction override or extraction attempt."

        # Confidence represents certainty in the detection result
        # For detections: higher = more sure it's an injection
        # For non-detections: confidence represents how sure we are it's safe
        # If nothing detected, confidence is proportional to thoroughness
        if is_injection:
            final_confidence = confidence
        else:
            # If no patterns matched at all, base confidence on what we checked
            # More methods = more confident in "safe" result
            base_safe_confidence = 0.5 + 0.2 * len(methods)
            final_confidence = min(1.0, base_safe_confidence)

        return InjectionResult(
            is_injection=is_injection,
            severity=max_severity,
            confidence=final_confidence,
            matched_patterns=matched_patterns,
            methods_triggered=methods_triggered,
            explanation=explanation,
            action=self.mode if is_injection else "allow",
        )

    def detect_with_context(self, messages: List[str]) -> InjectionResult:
        """
        Detect injection across multiple messages (context-aware).

        Catches split payloads where attack is distributed across messages.

        Args:
            messages: List of message texts in conversation order

        Returns:
            InjectionResult for the entire conversation
        """
        if not messages:
            return InjectionResult(
                is_injection=False,
                severity=InjectionSeverity.NONE,
                explanation="No messages",
            )

        # Check each message individually
        individual_results = [self.detect(msg) for msg in messages]

        # Check combined text (catches split payloads)
        combined_text = " ".join(messages)
        combined_result = self.detect(combined_text)

        # Return worst result
        all_results = individual_results + [combined_result]
        worst = max(all_results, key=lambda r: (r.severity, r.confidence))

        # If combined found something individuals didn't, note split payload
        if combined_result.is_injection and not any(r.is_injection for r in individual_results):
            worst.explanation = "Split payload detected across messages. " + worst.explanation
            worst.matched_patterns = list(set(worst.matched_patterns + ["split_payload"]))

        return worst
