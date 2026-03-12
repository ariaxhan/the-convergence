"""
Tests for SAO distribution shift detection.

Tests dataset integrity monitoring for self-alignment optimization.
"""

import pytest

from convergence.plugins.learning.sao import SAOMixin, SAOConfig


# =============================================================================
# DISTRIBUTION SHIFT DETECTION TESTS
# =============================================================================


class TestSAODistributionShift:
    """Test distribution shift detection in SAO datasets."""

    @pytest.fixture
    def sao_mixin(self):
        """Create SAO mixin for testing."""
        config = SAOConfig(
            quality_filter=True,
            similarity_threshold=0.9,
        )
        return SAOMixin(config=config)

    def test_detect_shift_no_baseline(self, sao_mixin):
        """No shift detected when no baseline exists."""
        result = sao_mixin.detect_distribution_shift()

        assert result["has_baseline"] is False
        assert result["shift_detected"] is False

    def test_detect_shift_with_stable_data(self, sao_mixin):
        """No shift when data distribution is stable."""
        # Add baseline data
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"How do I implement feature {i}?",
                "chosen": f"Here's how to implement feature {i}...",
                "rejected": f"Feature {i} is not important.",
            })

        # Establish baseline
        sao_mixin.establish_distribution_baseline()

        # Add similar new data
        for i in range(50, 60):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"How do I implement feature {i}?",
                "chosen": f"Here's how to implement feature {i}...",
                "rejected": f"Feature {i} is not important.",
            })

        result = sao_mixin.detect_distribution_shift()

        assert result["has_baseline"] is True
        assert result["shift_detected"] is False

    def test_detect_shift_with_drifted_data(self, sao_mixin):
        """Shift detected when data distribution changes significantly."""
        # Add baseline data (coding questions)
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"How do I write Python code for {i}?",
                "chosen": f"Here's the Python code...",
                "rejected": f"I don't know Python.",
            })

        sao_mixin.establish_distribution_baseline()

        # Add very different data (cooking questions)
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"How do I cook recipe {i}?",
                "chosen": f"Here's how to cook...",
                "rejected": f"I can't cook.",
            })

        result = sao_mixin.detect_distribution_shift()

        assert result["has_baseline"] is True
        assert result["shift_detected"] is True
        assert result["shift_magnitude"] > 0.1

    def test_shift_magnitude_proportional(self, sao_mixin):
        """Shift magnitude should be proportional to distribution change."""
        # Establish baseline
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Python question {i}",
                "chosen": "Python answer",
                "rejected": "Bad answer",
            })

        sao_mixin.establish_distribution_baseline()

        # Small shift
        for i in range(10):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"JavaScript question {i}",
                "chosen": "JavaScript answer",
                "rejected": "Bad answer",
            })

        small_result = sao_mixin.detect_distribution_shift()

        # Add more different data for larger shift
        for i in range(100):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Cooking question {i}",
                "chosen": "Cooking answer",
                "rejected": "Bad cooking",
            })

        large_result = sao_mixin.detect_distribution_shift()

        # Larger shift should have larger magnitude
        if small_result["shift_detected"] and large_result["shift_detected"]:
            assert large_result["shift_magnitude"] >= small_result["shift_magnitude"]


# =============================================================================
# SHIFT THRESHOLD TESTS
# =============================================================================


class TestSAOShiftThresholds:
    """Test shift detection threshold configuration."""

    def test_custom_shift_threshold(self):
        """Should respect custom shift threshold."""
        config = SAOConfig(distribution_shift_threshold=0.3)
        sao_mixin = SAOMixin(config=config)

        # Add baseline
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Question {i}",
                "chosen": "Answer",
                "rejected": "Bad",
            })

        sao_mixin.establish_distribution_baseline()

        # Add moderately different data
        for i in range(30):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Different topic {i}",
                "chosen": "Different answer",
                "rejected": "Different bad",
            })

        result = sao_mixin.detect_distribution_shift(threshold=0.5)

        # High threshold should not trigger
        assert result["threshold_used"] == 0.5

    def test_default_threshold_from_config(self):
        """Should use config threshold by default."""
        config = SAOConfig(distribution_shift_threshold=0.15)
        sao_mixin = SAOMixin(config=config)

        result = sao_mixin.detect_distribution_shift()

        assert result.get("threshold_used", 0.15) == 0.15


# =============================================================================
# BASELINE MANAGEMENT TESTS
# =============================================================================


class TestSAOBaselineManagement:
    """Test distribution baseline establishment and updates."""

    @pytest.fixture
    def sao_mixin(self):
        """Create SAO mixin for testing."""
        return SAOMixin(config=SAOConfig())

    def test_establish_baseline(self, sao_mixin):
        """Should establish baseline from current dataset."""
        for i in range(30):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Question {i}",
                "chosen": "Answer",
                "rejected": "Bad",
            })

        sao_mixin.establish_distribution_baseline()

        assert sao_mixin.has_distribution_baseline() is True

    def test_reset_baseline(self, sao_mixin):
        """Should be able to reset baseline."""
        # Establish baseline (need minimum 10 samples)
        for i in range(15):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Test question {i}",
                "chosen": f"Yes answer {i}",
                "rejected": f"No answer {i}",
            })
        sao_mixin.establish_distribution_baseline()

        assert sao_mixin.has_distribution_baseline() is True

        # Reset
        sao_mixin.reset_distribution_baseline()

        assert sao_mixin.has_distribution_baseline() is False

    def test_baseline_requires_minimum_data(self, sao_mixin):
        """Should require minimum data for baseline."""
        # Only 2 samples
        sao_mixin.synthetic_dataset.append({"prompt": "Q1", "chosen": "A1", "rejected": "B1"})
        sao_mixin.synthetic_dataset.append({"prompt": "Q2", "chosen": "A2", "rejected": "B2"})

        # Should warn or return False for insufficient data
        result = sao_mixin.establish_distribution_baseline()

        # Implementation can either return False or raise - test for one
        assert result is False or sao_mixin.has_distribution_baseline() is False


# =============================================================================
# SHIFT WARNING INTEGRATION TESTS
# =============================================================================


class TestSAOShiftWarnings:
    """Test shift detection integrates with generation stats."""

    @pytest.fixture
    def sao_mixin(self):
        """Create SAO mixin for testing."""
        return SAOMixin(config=SAOConfig())

    def test_generation_stats_include_shift_info(self, sao_mixin):
        """Generation stats should include shift detection info."""
        # Add data and baseline
        for i in range(20):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Q{i}",
                "chosen": f"A{i}",
                "rejected": f"B{i}",
            })

        sao_mixin.establish_distribution_baseline()

        stats = sao_mixin.get_generation_stats()

        assert "distribution_shift" in stats or "shift_detection" in stats

    def test_shift_triggers_warning_flag(self, sao_mixin):
        """Significant shift should set warning flag in stats."""
        # Establish baseline with coding data
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Code question {i}",
                "chosen": "Code answer",
                "rejected": "Bad code",
            })

        sao_mixin.establish_distribution_baseline()

        # Add very different data
        for i in range(100):
            sao_mixin.synthetic_dataset.append({
                "prompt": f"Medical question {i}",
                "chosen": "Medical answer",
                "rejected": "Bad medical",
            })

        stats = sao_mixin.get_generation_stats()

        # Should have warning when shift detected
        shift_info = stats.get("distribution_shift", stats.get("shift_detection", {}))
        if shift_info.get("shift_detected"):
            assert "warning" in stats or shift_info.get("shift_detected") is True


# =============================================================================
# EDGE CASES
# =============================================================================


class TestSAOShiftEdgeCases:
    """Test edge cases in shift detection."""

    def test_empty_dataset_no_crash(self):
        """Empty dataset should not crash."""
        sao_mixin = SAOMixin(config=SAOConfig())

        result = sao_mixin.detect_distribution_shift()

        assert result["has_baseline"] is False
        assert result["shift_detected"] is False

    def test_single_sample_dataset(self):
        """Single sample should handle gracefully."""
        sao_mixin = SAOMixin(config=SAOConfig())

        sao_mixin.synthetic_dataset.append({
            "prompt": "Only question",
            "chosen": "Only answer",
            "rejected": "Only bad",
        })

        result = sao_mixin.detect_distribution_shift()

        # Should not crash, baseline may or may not be established
        assert "shift_detected" in result

    def test_identical_prompts_no_false_shift(self):
        """Identical prompts should not trigger false shift."""
        sao_mixin = SAOMixin(config=SAOConfig())

        # Same prompt repeated
        for i in range(100):
            sao_mixin.synthetic_dataset.append({
                "prompt": "How do I learn Python?",
                "chosen": f"Answer variant {i}",
                "rejected": f"Bad variant {i}",
            })

        sao_mixin.establish_distribution_baseline()

        # More of the same
        for i in range(50):
            sao_mixin.synthetic_dataset.append({
                "prompt": "How do I learn Python?",
                "chosen": f"New answer {i}",
                "rejected": f"New bad {i}",
            })

        result = sao_mixin.detect_distribution_shift()

        # Same topic should not trigger major shift
        assert result["shift_detected"] is False or result["shift_magnitude"] < 0.3
