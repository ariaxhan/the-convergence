"""Tests for confidence extraction evaluator.

Defines expected behavior for extracting confidence scores from LLM response text.
"""

import pytest


class TestExplicitConfidenceExtraction:
    """Test extraction of explicit confidence markers."""

    def test_extract_percentage_format(self):
        """Extract 'confidence: X%' format."""
        from convergence.evaluators.confidence import extract_confidence

        text = "The answer is X. Confidence: 85%"
        result = extract_confidence(text, method="explicit")

        assert result == pytest.approx(0.85, abs=0.01)

    def test_extract_decimal_format(self):
        """Extract 'confidence: 0.X' format."""
        from convergence.evaluators.confidence import extract_confidence

        text = "Based on the data, Y is correct. Confidence: 0.92"
        result = extract_confidence(text, method="explicit")

        assert result == pytest.approx(0.92, abs=0.01)

    def test_extract_with_colon_space(self):
        """Handle variations in spacing."""
        from convergence.evaluators.confidence import extract_confidence

        # With space
        assert extract_confidence("Confidence: 80%", method="explicit") == pytest.approx(0.80, abs=0.01)

        # Without space
        assert extract_confidence("Confidence:80%", method="explicit") == pytest.approx(0.80, abs=0.01)

        # Multiple spaces
        assert extract_confidence("Confidence:  80%", method="explicit") == pytest.approx(0.80, abs=0.01)

    def test_extract_case_insensitive(self):
        """Extraction should be case insensitive."""
        from convergence.evaluators.confidence import extract_confidence

        assert extract_confidence("CONFIDENCE: 75%", method="explicit") == pytest.approx(0.75, abs=0.01)
        assert extract_confidence("confidence: 75%", method="explicit") == pytest.approx(0.75, abs=0.01)
        assert extract_confidence("Confidence: 75%", method="explicit") == pytest.approx(0.75, abs=0.01)

    def test_no_explicit_marker_returns_none(self):
        """Return None when no explicit marker found."""
        from convergence.evaluators.confidence import extract_confidence

        text = "The answer is definitely X."
        result = extract_confidence(text, method="explicit")

        assert result is None

    def test_extract_from_middle_of_text(self):
        """Extract confidence marker from anywhere in text."""
        from convergence.evaluators.confidence import extract_confidence

        text = """
        Based on my analysis, the root cause is a memory leak.
        The leak originates from the connection pool. Confidence: 78%
        I recommend implementing connection timeouts.
        """
        result = extract_confidence(text, method="explicit")

        assert result == pytest.approx(0.78, abs=0.01)

    def test_first_marker_wins(self):
        """If multiple markers, use the first one."""
        from convergence.evaluators.confidence import extract_confidence

        text = "First answer (Confidence: 60%). Second answer (Confidence: 90%)."
        result = extract_confidence(text, method="explicit")

        assert result == pytest.approx(0.60, abs=0.01)


class TestHedgingDetection:
    """Test detection of hedging language that indicates uncertainty."""

    def test_single_hedging_word(self):
        """Single hedging word should lower confidence."""
        from convergence.evaluators.confidence import extract_confidence

        text = "I think the answer is X."
        result = extract_confidence(text, method="hedging")

        # Hedging should result in lower confidence
        assert result < 0.8
        assert result >= 0.0

    def test_multiple_hedging_words(self):
        """Multiple hedging words should lower confidence more."""
        from convergence.evaluators.confidence import extract_confidence

        single = "I think the answer is X."
        multiple = "I think maybe the answer might possibly be X."

        single_conf = extract_confidence(single, method="hedging")
        multiple_conf = extract_confidence(multiple, method="hedging")

        assert multiple_conf < single_conf

    def test_no_hedging_high_confidence(self):
        """No hedging words should result in high confidence."""
        from convergence.evaluators.confidence import extract_confidence

        text = "The answer is X. This is correct."
        result = extract_confidence(text, method="hedging")

        assert result >= 0.8

    def test_hedging_words_recognized(self):
        """Common hedging words should be detected."""
        from convergence.evaluators.confidence import extract_confidence

        hedging_phrases = [
            "I think",
            "I believe",
            "maybe",
            "perhaps",
            "possibly",
            "might",
            "could be",
            "not sure",
            "not certain",
            "uncertain",
            "I'm not entirely sure",
            "it seems like",
            "it appears",
            "probably",
        ]

        for phrase in hedging_phrases:
            text = f"{phrase} the answer is X."
            result = extract_confidence(text, method="hedging")
            assert result < 0.9, f"Hedging phrase '{phrase}' should lower confidence"

    def test_negated_hedging_not_counted(self):
        """'I am sure' should not be counted as hedging."""
        from convergence.evaluators.confidence import extract_confidence

        # "not sure" is hedging
        uncertain = "I'm not sure about this."
        # "I am sure" is not hedging
        certain = "I am sure about this."

        uncertain_conf = extract_confidence(uncertain, method="hedging")
        certain_conf = extract_confidence(certain, method="hedging")

        assert certain_conf > uncertain_conf


class TestCertaintyDetection:
    """Test detection of certainty markers that indicate high confidence."""

    def test_certainty_words_boost_confidence(self):
        """Certainty markers should increase confidence."""
        from convergence.evaluators.confidence import extract_confidence

        text = "This is definitely the correct answer."
        result = extract_confidence(text, method="certainty")

        assert result >= 0.8

    def test_no_certainty_markers_neutral(self):
        """No certainty markers should return neutral confidence."""
        from convergence.evaluators.confidence import extract_confidence

        text = "The answer is X."
        result = extract_confidence(text, method="certainty")

        # Neutral, neither high nor low
        assert 0.5 <= result <= 0.8

    def test_certainty_words_recognized(self):
        """Common certainty words should be detected."""
        from convergence.evaluators.confidence import extract_confidence

        certainty_phrases = [
            "definitely",
            "certainly",
            "absolutely",
            "always",
            "guaranteed",
            "without a doubt",
            "100%",
            "for sure",
            "clearly",
            "obviously",
        ]

        for phrase in certainty_phrases:
            text = f"The answer is {phrase} X."
            result = extract_confidence(text, method="certainty")
            assert result >= 0.7, f"Certainty phrase '{phrase}' should boost confidence"

    def test_multiple_certainty_markers(self):
        """Multiple certainty markers should boost more."""
        from convergence.evaluators.confidence import extract_confidence

        single = "This is definitely correct."
        multiple = "This is definitely, absolutely, certainly correct."

        single_conf = extract_confidence(single, method="certainty")
        multiple_conf = extract_confidence(multiple, method="certainty")

        assert multiple_conf >= single_conf


class TestAutoMethod:
    """Test the 'auto' method that combines all extraction methods."""

    def test_auto_uses_explicit_when_present(self):
        """Auto should use explicit confidence when available."""
        from convergence.evaluators.confidence import extract_confidence

        text = "I think this is right. Confidence: 90%"
        result = extract_confidence(text, method="auto")

        # Explicit marker should take precedence
        assert result == pytest.approx(0.90, abs=0.01)

    def test_auto_falls_back_to_linguistic(self):
        """Auto should use linguistic analysis when no explicit marker."""
        from convergence.evaluators.confidence import extract_confidence

        text = "I think maybe this could be the answer."
        result = extract_confidence(text, method="auto")

        # Should detect hedging
        assert result < 0.7

    def test_auto_takes_conservative_estimate(self):
        """Auto should be conservative when methods disagree."""
        from convergence.evaluators.confidence import extract_confidence

        # Hedging AND certainty in same text
        text = "I think this is definitely the answer."
        result = extract_confidence(text, method="auto")

        # Should be somewhere in middle, leaning conservative
        assert 0.3 <= result <= 0.8

    def test_default_method_is_auto(self):
        """Default method should be 'auto'."""
        from convergence.evaluators.confidence import extract_confidence

        text = "Confidence: 85%"

        explicit_result = extract_confidence(text, method="auto")
        default_result = extract_confidence(text)

        assert explicit_result == default_result


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        """Empty string should return neutral/low confidence."""
        from convergence.evaluators.confidence import extract_confidence

        result = extract_confidence("", method="auto")

        # Empty = uncertain
        assert result is not None
        assert 0.0 <= result <= 0.5

    def test_whitespace_only(self):
        """Whitespace-only string should return low confidence."""
        from convergence.evaluators.confidence import extract_confidence

        result = extract_confidence("   \n\t  ", method="auto")

        assert result is not None
        assert 0.0 <= result <= 0.5

    def test_very_long_text(self):
        """Long text should not cause issues."""
        from convergence.evaluators.confidence import extract_confidence

        text = "The answer is X. " * 1000 + "Confidence: 75%"
        result = extract_confidence(text, method="explicit")

        assert result == pytest.approx(0.75, abs=0.01)

    def test_special_characters(self):
        """Special characters should not break extraction."""
        from convergence.evaluators.confidence import extract_confidence

        text = "Answer: <code>X</code> 🎉 Confidence: 80%"
        result = extract_confidence(text, method="explicit")

        assert result == pytest.approx(0.80, abs=0.01)

    def test_invalid_percentage(self):
        """Invalid percentage values should be handled gracefully."""
        from convergence.evaluators.confidence import extract_confidence

        # Over 100%
        text = "Confidence: 150%"
        result = extract_confidence(text, method="explicit")
        # Should either be None or clamped to 1.0
        assert result is None or result == 1.0

        # Negative
        text = "Confidence: -50%"
        result = extract_confidence(text, method="explicit")
        assert result is None or result == 0.0

    def test_returns_float(self):
        """Result should always be a float or None."""
        from convergence.evaluators.confidence import extract_confidence

        result = extract_confidence("Confidence: 85%", method="explicit")
        assert isinstance(result, float)

        result = extract_confidence("No confidence marker", method="explicit")
        assert result is None or isinstance(result, float)


class TestMethodParameter:
    """Test the method parameter behavior."""

    def test_invalid_method_raises(self):
        """Invalid method should raise ValueError."""
        from convergence.evaluators.confidence import extract_confidence

        with pytest.raises(ValueError):
            extract_confidence("test", method="invalid_method")

    def test_all_methods_available(self):
        """All documented methods should work."""
        from convergence.evaluators.confidence import extract_confidence

        text = "I think the answer is X. Confidence: 70%"

        for method in ["explicit", "hedging", "certainty", "auto"]:
            result = extract_confidence(text, method=method)
            assert result is None or isinstance(result, float)
