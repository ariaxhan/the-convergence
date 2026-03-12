"""
Output validation for The Convergence framework.

Validates LLM outputs before returning to users:
- PII detection and redaction
- Secret/credential detection
- Toxicity scoring
- Hallucination risk assessment
- Schema validation (JSON Schema + Pydantic)
"""

import hashlib
import json
import re
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field


class PIIType(str, Enum):
    """Types of PII that can be detected."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "date_of_birth"
    CUSTOM = "custom"


class ValidationResult(BaseModel):
    """Result of output validation."""
    is_valid: bool = True
    issues: List[str] = Field(default_factory=list)
    contains_pii: bool = False
    pii_types: List[PIIType] = Field(default_factory=list)
    contains_secrets: bool = False
    toxicity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    contains_contradiction: bool = False
    action: str = "allow"
    output: Optional[str] = None
    redacted_output: Optional[str] = None
    audit_log: Optional[Dict[str, Any]] = None
    validation_time_ms: float = 0.0
    parsed_data: Optional[Any] = None


class ValidationConfig(BaseModel):
    """Configuration for output validator."""
    custom_pii_patterns: List[str] = Field(default_factory=list)
    sensitivity: str = "medium"


# PII detection patterns
PII_PATTERNS = {
    PIIType.EMAIL: re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ),
    PIIType.PHONE: re.compile(
        r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b"
    ),
    PIIType.SSN: re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
    ),
    PIIType.CREDIT_CARD: re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    ),
    PIIType.IP_ADDRESS: re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    ),
}

# Secret detection patterns
SECRET_PATTERNS = [
    # API keys - use shorter minimum lengths for better detection
    (re.compile(r"sk-proj-[A-Za-z0-9]{10,}"), "openai_api_key"),
    (re.compile(r"sk-[A-Za-z0-9]{10,}"), "openai_api_key"),
    (re.compile(r"ghp_[A-Za-z0-9]{10,}"), "github_token"),
    (re.compile(r"gho_[A-Za-z0-9]{10,}"), "github_oauth"),
    (re.compile(r"Bearer\s+eyJ[A-Za-z0-9_-]+"), "jwt_token"),
    # Connection strings - detect actual credentials in URLs (word:word@)
    (re.compile(r"postgresql://[^:]+:[^@]+@"), "postgres_connection"),
    (re.compile(r"mongodb\+srv://[^:]+:[^@]+@"), "mongodb_connection"),
    (re.compile(r"redis://:[^@]+@"), "redis_connection"),
    # Generic password patterns - actual values not placeholders
    (re.compile(r"password\s+is[:\s]+\S+", re.IGNORECASE), "password"),
    (re.compile(r"your\s+password\s+is[:\s]+\S+", re.IGNORECASE), "password"),
    # AWS
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key"),
]

# Placeholder patterns (should NOT be flagged as secrets)
# These indicate example/template text, not actual secrets
PLACEHOLDER_PATTERNS = [
    re.compile(r"your[_\s]?key[_\s]?here", re.IGNORECASE),
    re.compile(r"your[_\s]?password[_\s]?here", re.IGNORECASE),  # Only "your password here", not "your password is:"
    re.compile(r"YOUR[_A-Z]{3,}", re.IGNORECASE),  # YOUR_API_KEY etc
    re.compile(r"<your[^>]+>", re.IGNORECASE),  # <your_key_here>
    re.compile(r"\[your[^\]]+\]", re.IGNORECASE),  # [your_key]
    re.compile(r"username:password\b", re.IGNORECASE),  # exact placeholder
    re.compile(r"user:pass\b", re.IGNORECASE),  # exact placeholder
    re.compile(r"replace\s+with", re.IGNORECASE),  # "replace with your key"
]

# Toxicity keywords (simplified for demo - production would use ML model)
TOXIC_PATTERNS = [
    (re.compile(r"\b(idiot|stupid|dumb|moron)\b", re.IGNORECASE), 0.5),
    (re.compile(r"\b(hate|despise)\s+all\s+\[?\w+\]?", re.IGNORECASE), 0.9),
    (re.compile(r"\bdeserve\s+(bad|harm|death|pain)", re.IGNORECASE), 0.8),
    (re.compile(r"\bkill\s+(yourself|them|all)", re.IGNORECASE), 1.0),
    (re.compile(r"\b(worthless|pathetic|disgusting)\s+(person|people|human)", re.IGNORECASE), 0.7),
]

# Hallucination indicators
OVERCONFIDENCE_PATTERNS = [
    re.compile(r"\b(100%|absolutely|definitely|certainly|guaranteed)\s+(certain|sure|correct|true)", re.IGNORECASE),
    re.compile(r"\bthere\s+is\s+no\s+doubt\s+that", re.IGNORECASE),
    re.compile(r"\bI\s+am\s+(100%|completely|absolutely)\s+(certain|sure)", re.IGNORECASE),
    re.compile(r"\bIt\s+is\s+(absolutely|definitely)\s+guaranteed", re.IGNORECASE),
]

CITATION_PATTERN = re.compile(
    r"(?:According to|As stated by|Based on)\s+[A-Z][a-z]+(?:\s+et\s+al\.?)?\s*\(\d{4}\)",
    re.IGNORECASE
)


def _is_placeholder(text: str) -> bool:
    """Check if text contains placeholder patterns."""
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _redact_pattern(text: str, pattern: re.Pattern, replacement: str = "[REDACTED]") -> str:
    """Redact matches of a pattern in text."""
    return pattern.sub(replacement, text)


T = TypeVar("T", bound=BaseModel)


class OutputValidator:
    """
    Validate and sanitize LLM outputs.

    Implements defense-in-depth validation:
    1. PII detection (emails, phones, SSN, credit cards)
    2. Secret detection (API keys, connection strings)
    3. Toxicity scoring
    4. Hallucination risk assessment
    5. Schema validation (JSON Schema + Pydantic)
    """

    def __init__(
        self,
        detect_pii: bool = True,
        detect_secrets: bool = True,
        detect_toxicity: bool = True,
        detect_hallucination: bool = True,
        mode: str = "block",
        sensitivity: str = "medium",
        config: Optional[ValidationConfig] = None,
    ):
        """
        Initialize output validator.

        Args:
            detect_pii: Enable PII detection
            detect_secrets: Enable secret detection
            detect_toxicity: Enable toxicity scoring
            detect_hallucination: Enable hallucination detection
            mode: Action mode ("block", "redact", or "audit")
            sensitivity: Detection sensitivity ("relaxed", "medium", "strict")
            config: Additional configuration
        """
        self.detect_pii = detect_pii
        self.detect_secrets = detect_secrets
        self.detect_toxicity = detect_toxicity
        self.detect_hallucination = detect_hallucination
        self.mode = mode
        self.sensitivity = sensitivity
        self.config = config or ValidationConfig()

        # Compile custom PII patterns
        self._custom_pii_patterns: List[re.Pattern] = []
        for pattern in self.config.custom_pii_patterns:
            self._custom_pii_patterns.append(re.compile(pattern))

    def _detect_pii(self, text: str) -> tuple[bool, List[PIIType], str]:
        """
        Detect PII in text.

        Returns:
            Tuple of (contains_pii, pii_types, redacted_text)
        """
        found_types: List[PIIType] = []
        redacted = text

        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                found_types.append(pii_type)
                redacted = _redact_pattern(redacted, pattern, f"[{pii_type.value.upper()}_REDACTED]")

        # Check custom patterns
        for pattern in self._custom_pii_patterns:
            if pattern.search(text):
                found_types.append(PIIType.CUSTOM)
                redacted = _redact_pattern(redacted, pattern, "[CUSTOM_REDACTED]")
                break  # Only add CUSTOM once

        return len(found_types) > 0, found_types, redacted

    def _detect_secrets(self, text: str) -> bool:
        """Detect secrets/credentials in text."""
        # Check if this is a placeholder example
        if _is_placeholder(text):
            return False

        for pattern, _ in SECRET_PATTERNS:
            if pattern.search(text):
                return True

        return False

    def _calculate_toxicity(self, text: str) -> float:
        """Calculate toxicity score."""
        max_score = 0.0

        for pattern, score in TOXIC_PATTERNS:
            if pattern.search(text):
                max_score = max(max_score, score)

        return max_score

    def _calculate_hallucination_risk(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, bool]:
        """
        Calculate hallucination risk.

        Returns:
            Tuple of (risk_score, contains_contradiction)
        """
        risk = 0.0
        context = context or {}

        # Check for overconfidence patterns
        for pattern in OVERCONFIDENCE_PATTERNS:
            if pattern.search(text):
                risk = max(risk, 0.3)
                break

        # Check for fabricated citations
        if CITATION_PATTERN.search(text):
            known_sources = context.get("known_sources", [])
            if not known_sources:
                # Citation without provided sources = high risk
                risk = max(risk, 0.5)

        # Check for self-contradictions (simplified)
        contains_contradiction = False
        sentences = text.split(".")
        for i, sent1 in enumerate(sentences):
            for sent2 in sentences[i+1:]:
                # Very simple contradiction detection
                # Check if same subject has opposite predicates
                sent1_lower = sent1.lower().strip()
                sent2_lower = sent2.lower().strip()

                # Look for "X is Y" and "X is not Y" pattern
                # Pattern 1: "X is Y" followed by "X is not Y"
                is_match = re.search(r"(\w+)\s+is\s+(?:a\s+)?(\w+)", sent1_lower)
                is_not_match = re.search(r"(\w+)\s+is\s+not\s+(\w+)", sent2_lower)

                if is_match and is_not_match:
                    if is_match.group(1) == is_not_match.group(1) and is_match.group(2) == is_not_match.group(2):
                        contains_contradiction = True
                        risk = max(risk, 0.7)

                # Pattern 2: "X is Y" and later "not Y" in same context (e.g., "compiled" and "not compiled")
                # Look for same subject and contradicting predicate
                if is_match:
                    subj = is_match.group(1)
                    pred = is_match.group(2)
                    if subj in sent2_lower and f"not {pred}" in sent2_lower:
                        contains_contradiction = True
                        risk = max(risk, 0.7)

        return risk, contains_contradiction

    def validate(
        self,
        text: Optional[str],
        context: Optional[Dict[str, Any]] = None,
        redact: bool = False,
    ) -> ValidationResult:
        """
        Validate output text.

        Args:
            text: Output text to validate
            context: Optional context for validation
            redact: If True, generate redacted version

        Returns:
            ValidationResult with validation details
        """
        start_time = time.perf_counter()

        # Handle empty/None input
        if text is None:
            return ValidationResult(
                is_valid=False,
                issues=["Output is None"],
                action="block",
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        if text == "":
            return ValidationResult(
                is_valid=False,
                issues=["Empty output"],
                action="block",
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        issues: List[str] = []
        contains_pii = False
        pii_types: List[PIIType] = []
        redacted_output = text
        contains_secrets = False
        toxicity_score = 0.0
        hallucination_risk = 0.0
        contains_contradiction = False

        # PII detection
        if self.detect_pii:
            contains_pii, pii_types, redacted_output = self._detect_pii(text)
            if contains_pii:
                issues.append(f"Contains PII: {', '.join(t.value for t in pii_types)}")

        # Secret detection
        if self.detect_secrets:
            contains_secrets = self._detect_secrets(text)
            if contains_secrets:
                issues.append("Contains secrets or credentials")

        # Toxicity detection
        if self.detect_toxicity:
            toxicity_score = self._calculate_toxicity(text)
            if toxicity_score >= 0.7:
                issues.append(f"High toxicity score: {toxicity_score:.2f}")

        # Hallucination detection
        if self.detect_hallucination:
            hallucination_risk, contains_contradiction = self._calculate_hallucination_risk(
                text, context
            )
            if contains_contradiction:
                issues.append("Contains self-contradiction")

        # Apply sensitivity adjustments
        if self.sensitivity == "strict":
            # More issues in strict mode
            if toxicity_score >= 0.3:
                if "toxicity" not in str(issues):
                    issues.append(f"Elevated toxicity score: {toxicity_score:.2f}")
        elif self.sensitivity == "relaxed":
            # Filter out minor issues
            issues = [i for i in issues if "elevated" not in i.lower()]

        # Determine validity and action
        is_valid = True
        action = "allow"
        output: Optional[str] = text
        audit_log: Optional[Dict[str, Any]] = None

        if self.mode == "block":
            if contains_pii or contains_secrets or toxicity_score >= 0.7:
                is_valid = False
                action = "block"
                output = None
        elif self.mode == "redact":
            action = "redact"
            output = redacted_output
            is_valid = True
        elif self.mode == "audit":
            action = "audit"
            output = text
            is_valid = True
            audit_log = {
                "contains_pii": contains_pii,
                "pii_types": [t.value for t in pii_types],
                "contains_secrets": contains_secrets,
                "toxicity_score": toxicity_score,
                "hallucination_risk": hallucination_risk,
                "issues": issues,
                "text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
            }

        validation_time_ms = (time.perf_counter() - start_time) * 1000

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            contains_pii=contains_pii,
            pii_types=pii_types,
            contains_secrets=contains_secrets,
            toxicity_score=toxicity_score,
            hallucination_risk=hallucination_risk,
            contains_contradiction=contains_contradiction,
            action=action,
            output=output,
            redacted_output=redacted_output if redact or self.mode == "redact" else None,
            audit_log=audit_log,
            validation_time_ms=validation_time_ms,
        )

    def validate_schema(
        self,
        text: str,
        schema: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate text against JSON schema.

        Args:
            text: JSON text to validate
            schema: JSON Schema to validate against

        Returns:
            ValidationResult with validation details
        """
        start_time = time.perf_counter()

        try:
            import jsonschema
        except ImportError:
            # Fall back to basic validation without jsonschema
            return self._validate_schema_basic(text, schema, start_time)

        try:
            data = json.loads(text)
            jsonschema.validate(data, schema)

            return ValidationResult(
                is_valid=True,
                issues=[],
                output=text,
                parsed_data=data,
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                issues=[f"Invalid JSON: {e}"],
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        except jsonschema.ValidationError as e:
            return ValidationResult(
                is_valid=False,
                issues=[f"Schema validation failed: {e.message}"],
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _validate_schema_basic(
        self,
        text: str,
        schema: Dict[str, Any],
        start_time: float,
    ) -> ValidationResult:
        """Basic schema validation without jsonschema library."""
        try:
            data = json.loads(text)

            # Basic type checking
            schema_type = schema.get("type")
            if schema_type == "object" and not isinstance(data, dict):
                return ValidationResult(
                    is_valid=False,
                    issues=["Expected object, got " + type(data).__name__],
                    validation_time_ms=(time.perf_counter() - start_time) * 1000,
                )

            # Check required fields
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            for field in required:
                if field not in data:
                    return ValidationResult(
                        is_valid=False,
                        issues=[f"Missing required field: {field}"],
                        validation_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

            # Check property types and constraints
            for field, value in data.items():
                if field in properties:
                    prop_schema = properties[field]
                    prop_type = prop_schema.get("type")

                    # Type check
                    type_map: Dict[str, type | tuple[type, ...]] = {
                        "string": str,
                        "integer": int,
                        "number": (int, float),
                        "boolean": bool,
                        "array": list,
                        "object": dict,
                    }

                    if prop_type in type_map:
                        expected = type_map[prop_type]
                        if not isinstance(value, expected):  # type: ignore[arg-type]
                            return ValidationResult(
                                is_valid=False,
                                issues=[f"Field {field}: expected {prop_type}, got {type(value).__name__}"],
                                validation_time_ms=(time.perf_counter() - start_time) * 1000,
                            )

                    # Minimum constraint
                    if "minimum" in prop_schema and isinstance(value, (int, float)):
                        if value < prop_schema["minimum"]:
                            return ValidationResult(
                                is_valid=False,
                                issues=[f"Field {field}: value {value} below minimum {prop_schema['minimum']}"],
                                validation_time_ms=(time.perf_counter() - start_time) * 1000,
                            )

            return ValidationResult(
                is_valid=True,
                issues=[],
                output=text,
                parsed_data=data,
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                issues=[f"Invalid JSON: {e}"],
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def validate_pydantic(
        self,
        text: str,
        model: Type[T],
    ) -> ValidationResult:
        """
        Validate text against a Pydantic model.

        Args:
            text: JSON text to validate
            model: Pydantic model class to validate against

        Returns:
            ValidationResult with parsed_data if valid
        """
        start_time = time.perf_counter()

        try:
            data = json.loads(text)
            parsed = model.model_validate(data)

            return ValidationResult(
                is_valid=True,
                issues=[],
                output=text,
                parsed_data=parsed,
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        except json.JSONDecodeError as e:
            return ValidationResult(
                is_valid=False,
                issues=[f"Invalid JSON: {e}"],
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                issues=[f"Pydantic validation failed: {e}"],
                validation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
