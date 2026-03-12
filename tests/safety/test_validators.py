"""
Tests for output validation using Guardrails AI patterns.

Validates LLM outputs before returning to users.
Defense-in-depth layer 4: catch hallucinations & leaks.
"""

import pytest

from convergence.safety.validators import (
    OutputValidator,
    ValidationResult,
    ValidationConfig,
    PIIType,
)


# =============================================================================
# BASIC OUTPUT VALIDATION
# =============================================================================


class TestBasicOutputValidation:
    """Test basic output validation."""

    @pytest.fixture
    def validator(self):
        """Create output validator."""
        return OutputValidator()

    def test_valid_output_passes(self, validator):
        """Valid output should pass validation."""
        result = validator.validate("Here is the information you requested about Python.")

        assert result.is_valid is True
        assert len(result.issues) == 0

    def test_empty_output_handled(self, validator):
        """Empty output should be flagged."""
        result = validator.validate("")

        assert result.is_valid is False
        assert "empty" in result.issues[0].lower()

    def test_none_output_handled(self, validator):
        """None output should be handled."""
        result = validator.validate(None)

        assert result.is_valid is False


# =============================================================================
# PII DETECTION
# =============================================================================


class TestPIIDetection:
    """Test PII (Personally Identifiable Information) detection."""

    @pytest.fixture
    def validator(self):
        return OutputValidator(detect_pii=True)

    def test_detect_email(self, validator):
        """Should detect email addresses."""
        result = validator.validate("Contact john.doe@example.com for details")

        assert result.contains_pii is True
        assert PIIType.EMAIL in result.pii_types

    def test_detect_phone_number(self, validator):
        """Should detect phone numbers."""
        result = validator.validate("Call me at 555-123-4567")

        assert result.contains_pii is True
        assert PIIType.PHONE in result.pii_types

    def test_detect_ssn(self, validator):
        """Should detect SSN patterns."""
        result = validator.validate("SSN: 123-45-6789")

        assert result.contains_pii is True
        assert PIIType.SSN in result.pii_types

    def test_detect_credit_card(self, validator):
        """Should detect credit card numbers."""
        result = validator.validate("Card: 4111-1111-1111-1111")

        assert result.contains_pii is True
        assert PIIType.CREDIT_CARD in result.pii_types

    def test_no_false_positive_on_numbers(self, validator):
        """Should not flag arbitrary numbers as PII."""
        result = validator.validate("The year is 2026 and version 3.14.159")

        assert result.contains_pii is False

    def test_redact_pii(self, validator):
        """Should be able to redact detected PII."""
        output = "Email: user@example.com and phone: 555-123-4567"

        result = validator.validate(output, redact=True)

        assert result.contains_pii is True
        assert "user@example.com" not in result.redacted_output
        assert "555-123-4567" not in result.redacted_output


# =============================================================================
# SECRET DETECTION
# =============================================================================


class TestSecretDetection:
    """Test detection of secrets and credentials."""

    @pytest.fixture
    def validator(self):
        return OutputValidator(detect_secrets=True)

    def test_detect_api_key_patterns(self, validator):
        """Should detect API key patterns."""
        outputs = [
            "Use this key: sk-proj-abc123xyz789",
            "API_KEY=ghp_xxxxxxxxxxxx",
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        ]

        for output in outputs:
            result = validator.validate(output)
            assert result.contains_secrets is True, f"Missed secret in: {output}"

    def test_detect_password_in_output(self, validator):
        """Should detect password patterns."""
        result = validator.validate("Your password is: MyS3cr3tP@ss!")

        assert result.contains_secrets is True

    def test_detect_connection_strings(self, validator):
        """Should detect database connection strings."""
        outputs = [
            "postgresql://user:password@localhost:5432/db",
            "mongodb+srv://admin:secret@cluster.mongodb.net",
            "redis://:mypassword@redis-server:6379",
        ]

        for output in outputs:
            result = validator.validate(output)
            assert result.contains_secrets is True, f"Missed secret in: {output}"

    def test_no_false_positive_on_examples(self, validator):
        """Should not flag placeholder examples."""
        outputs = [
            "Set your API key like: API_KEY=your_key_here",
            "Replace YOUR_PASSWORD with actual password",
            "Use format: postgres://username:password@host/db",
        ]

        for output in outputs:
            result = validator.validate(output)
            # These are instructional, not actual secrets
            assert result.contains_secrets is False, f"False positive: {output}"


# =============================================================================
# HALLUCINATION DETECTION
# =============================================================================


class TestHallucinationDetection:
    """Test detection of potential hallucinations."""

    @pytest.fixture
    def validator(self):
        return OutputValidator(detect_hallucination=True)

    def test_detect_fabricated_citations(self, validator):
        """Should flag suspicious citations."""
        output = "According to Smith et al. (2024) in Nature, quantum computers can..."

        result = validator.validate(
            output,
            context={"known_sources": []},  # No sources provided
        )

        assert result.hallucination_risk >= 0.5

    def test_detect_confident_uncertainty(self, validator):
        """Should flag overly confident uncertain claims."""
        outputs = [
            "I am 100% certain that...",
            "It is absolutely guaranteed that...",
            "There is no doubt that the future will...",
        ]

        for output in outputs:
            result = validator.validate(output)
            assert result.hallucination_risk >= 0.3, f"Should flag: {output}"

    def test_detect_contradictions(self, validator):
        """Should detect self-contradictions."""
        output = "Python is a compiled language. Python is interpreted, not compiled."

        result = validator.validate(output)

        assert result.contains_contradiction is True


# =============================================================================
# TOXICITY DETECTION
# =============================================================================


class TestToxicityDetection:
    """Test detection of toxic or harmful content."""

    @pytest.fixture
    def validator(self):
        return OutputValidator(detect_toxicity=True)

    def test_detect_explicit_toxicity(self, validator):
        """Should detect explicitly harmful content."""
        # Using mild examples for testing
        outputs = [
            "You are an idiot and deserve bad things",
            "I hate all [group] and they should...",
        ]

        for output in outputs:
            result = validator.validate(output)
            assert result.toxicity_score >= 0.7, f"Should flag: {output}"

    def test_benign_negative_sentiment_ok(self, validator):
        """Should not flag legitimate negative sentiment."""
        outputs = [
            "I'm disappointed with the service quality",
            "This product has serious flaws",
            "The experience was frustrating",
        ]

        for output in outputs:
            result = validator.validate(output)
            assert result.toxicity_score < 0.5, f"False positive: {output}"


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================


class TestSchemaValidation:
    """Test structured output schema validation."""

    @pytest.fixture
    def validator(self):
        return OutputValidator()

    def test_validate_json_schema(self, validator):
        """Should validate against JSON schema."""
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
        }

        valid_output = '{"name": "Alice", "age": 30}'
        invalid_output = '{"name": "Alice", "age": -5}'

        valid_result = validator.validate_schema(valid_output, schema)
        invalid_result = validator.validate_schema(invalid_output, schema)

        assert valid_result.is_valid is True
        assert invalid_result.is_valid is False

    def test_validate_with_pydantic(self, validator):
        """Should validate using Pydantic models."""
        from pydantic import BaseModel

        class UserResponse(BaseModel):
            name: str
            email: str

        output = '{"name": "Alice", "email": "alice@example.com"}'

        result = validator.validate_pydantic(output, UserResponse)

        assert result.is_valid is True
        assert result.parsed_data.name == "Alice"


# =============================================================================
# VALIDATION ACTIONS
# =============================================================================


class TestValidationActions:
    """Test validation action modes."""

    def test_block_mode(self):
        """Block mode should prevent output."""
        validator = OutputValidator(
            mode="block",
            detect_pii=True,
        )

        result = validator.validate("Contact me at secret@email.com")

        assert result.is_valid is False
        assert result.action == "block"
        assert result.output is None  # Output blocked

    def test_redact_mode(self):
        """Redact mode should clean output."""
        validator = OutputValidator(
            mode="redact",
            detect_pii=True,
        )

        result = validator.validate("Contact me at secret@email.com")

        assert result.is_valid is True  # Allowed after redaction
        assert result.action == "redact"
        assert "secret@email.com" not in result.output

    def test_audit_mode(self):
        """Audit mode should log but allow."""
        validator = OutputValidator(
            mode="audit",
            detect_pii=True,
        )

        result = validator.validate("Contact me at secret@email.com")

        assert result.is_valid is True
        assert result.action == "audit"
        assert "secret@email.com" in result.output  # Original preserved
        assert result.audit_log is not None


# =============================================================================
# CONFIGURATION
# =============================================================================


class TestValidatorConfig:
    """Test validator configuration."""

    def test_custom_pii_patterns(self):
        """Should accept custom PII patterns."""
        config = ValidationConfig(
            custom_pii_patterns=[
                r"INTERNAL-\d{6}",  # Internal ID format
            ]
        )
        validator = OutputValidator(config=config, detect_pii=True)

        result = validator.validate("Reference: INTERNAL-123456")

        assert result.contains_pii is True

    def test_sensitivity_levels(self):
        """Should support different sensitivity levels."""
        strict = OutputValidator(sensitivity="strict")
        relaxed = OutputValidator(sensitivity="relaxed")

        borderline = "The result is approximately 95% accurate"

        strict_result = strict.validate(borderline)
        relaxed_result = relaxed.validate(borderline)

        # Strict should flag more things
        assert len(strict_result.issues) >= len(relaxed_result.issues)

    def test_disable_specific_checks(self):
        """Should allow disabling specific checks."""
        validator = OutputValidator(
            detect_pii=False,
            detect_secrets=True,
        )

        # Contains email but PII check disabled
        result = validator.validate("Email: test@example.com")

        assert result.contains_pii is False  # Check disabled


# =============================================================================
# RESULT STRUCTURE
# =============================================================================


class TestValidationResult:
    """Test ValidationResult structure."""

    @pytest.fixture
    def validator(self):
        return OutputValidator(
            detect_pii=True,
            detect_secrets=True,
            detect_toxicity=True,
        )

    def test_result_has_required_fields(self, validator):
        """Result should have all required fields."""
        result = validator.validate("test output")

        assert hasattr(result, "is_valid")
        assert hasattr(result, "issues")
        assert hasattr(result, "contains_pii")
        assert hasattr(result, "contains_secrets")
        assert hasattr(result, "toxicity_score")
        assert hasattr(result, "action")
        assert hasattr(result, "output")

    def test_result_serializable(self, validator):
        """Result should be JSON serializable."""
        import json

        result = validator.validate("test output")
        data = result.model_dump()

        # Should not raise
        json.dumps(data)

    def test_result_includes_timing(self, validator):
        """Result should include validation timing."""
        result = validator.validate("test output")

        assert hasattr(result, "validation_time_ms")
        assert result.validation_time_ms >= 0


# =============================================================================
# EDGE CASES
# =============================================================================


class TestValidatorEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def validator(self):
        return OutputValidator()

    def test_very_long_output(self, validator):
        """Should handle very long outputs."""
        long_output = "word " * 100000  # 100k words

        result = validator.validate(long_output)

        # Should complete without error
        assert result is not None

    def test_unicode_output(self, validator):
        """Should handle unicode properly."""
        outputs = [
            "こんにちは世界",
            "مرحبا بالعالم",
            "🎉 Success! 🎉",
        ]

        for output in outputs:
            result = validator.validate(output)
            assert result.is_valid is True

    def test_malformed_json_in_output(self, validator):
        """Should handle malformed JSON gracefully."""
        result = validator.validate('{"broken": json')

        # Should not crash
        assert result is not None

    def test_binary_looking_content(self, validator):
        """Should handle binary-looking content."""
        result = validator.validate("\\x00\\x01\\x02 binary data")

        # Should not crash
        assert result is not None
