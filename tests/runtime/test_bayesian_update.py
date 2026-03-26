"""Tests for Bayesian update computation.

This is critical math - must be correct for Thompson Sampling to work.
"""

import pytest
import math

from armature.types.runtime import RuntimeArm
from armature.runtime.bayesian_update import compute_bayesian_update


class TestBayesianUpdateBasics:
    """Test basic Bayesian update behavior."""

    def test_update_with_full_reward(self):
        """Full reward (1.0) should increase alpha."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=1.0)

        assert result["alpha"] == 2.0  # alpha + 1.0
        assert result["beta"] == 1.0   # beta + 0.0
        assert result["total_pulls"] == 1
        assert result["total_reward"] == 1.0

    def test_update_with_zero_reward(self):
        """Zero reward should increase beta."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=0.0)

        assert result["alpha"] == 1.0  # alpha + 0.0
        assert result["beta"] == 2.0   # beta + 1.0
        assert result["total_pulls"] == 1
        assert result["total_reward"] == 0.0

    def test_update_with_partial_reward(self):
        """Partial reward should split between alpha and beta."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=0.7)

        assert result["alpha"] == pytest.approx(1.7, abs=0.01)  # alpha + 0.7
        assert result["beta"] == pytest.approx(1.3, abs=0.01)   # beta + 0.3
        assert result["total_pulls"] == 1
        assert result["total_reward"] == pytest.approx(0.7, abs=0.01)


class TestRewardClamping:
    """Test that rewards are clamped to [0, 1]."""

    def test_reward_above_one_clamped(self):
        """Reward > 1.0 should be clamped to 1.0."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=1.5)

        # Should be treated as reward=1.0
        assert result["alpha"] == 2.0
        assert result["beta"] == 1.0

    def test_reward_below_zero_clamped(self):
        """Reward < 0.0 should be clamped to 0.0."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=-0.5)

        # Should be treated as reward=0.0
        assert result["alpha"] == 1.0
        assert result["beta"] == 2.0


class TestMeanEstimate:
    """Test mean estimate computation."""

    def test_uniform_prior_mean(self):
        """Uniform prior (1, 1) should have mean 0.5."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=0.5)

        # After (1, 1) -> (1.5, 1.5): mean = 1.5/3.0 = 0.5
        assert result["mean_estimate"] == pytest.approx(0.5, abs=0.01)

    def test_mean_increases_with_rewards(self):
        """Mean should increase as we observe more rewards."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        # Simulate multiple positive rewards
        for _ in range(10):
            result = compute_bayesian_update(arm, reward=1.0)
            arm = RuntimeArm(
                arm_id="test",
                alpha=result["alpha"],
                beta=result["beta"],
                total_pulls=result["total_pulls"],
                total_reward=result["total_reward"],
            )

        # After 10 successes: alpha=11, beta=1, mean=11/12 ≈ 0.917
        assert result["mean_estimate"] > 0.9

    def test_mean_decreases_with_failures(self):
        """Mean should decrease as we observe failures."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        # Simulate multiple failures
        for _ in range(10):
            result = compute_bayesian_update(arm, reward=0.0)
            arm = RuntimeArm(
                arm_id="test",
                alpha=result["alpha"],
                beta=result["beta"],
                total_pulls=result["total_pulls"],
                total_reward=result["total_reward"],
            )

        # After 10 failures: alpha=1, beta=11, mean=1/12 ≈ 0.083
        assert result["mean_estimate"] < 0.1


class TestConfidenceInterval:
    """Test confidence interval computation."""

    def test_ci_bounds_valid(self):
        """CI bounds should be in [0, 1]."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=0.5)

        ci = result["confidence_interval"]
        assert ci["lower"] >= 0.0
        assert ci["upper"] <= 1.0
        assert ci["lower"] <= ci["upper"]

    def test_ci_narrows_with_samples(self):
        """CI should narrow as we get more samples."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        # First sample
        result1 = compute_bayesian_update(arm, reward=0.5)
        ci1_width = result1["confidence_interval"]["upper"] - result1["confidence_interval"]["lower"]

        # Update arm and get more samples
        arm = RuntimeArm(
            arm_id="test",
            alpha=result1["alpha"],
            beta=result1["beta"],
            total_pulls=result1["total_pulls"],
            total_reward=result1["total_reward"],
        )

        for _ in range(50):
            result = compute_bayesian_update(arm, reward=0.5)
            arm = RuntimeArm(
                arm_id="test",
                alpha=result["alpha"],
                beta=result["beta"],
                total_pulls=result["total_pulls"],
                total_reward=result["total_reward"],
            )

        ci2_width = result["confidence_interval"]["upper"] - result["confidence_interval"]["lower"]

        # CI should be narrower after more samples
        assert ci2_width < ci1_width

    def test_ci_contains_mean(self):
        """CI should contain the mean estimate."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=5.0,
            beta=5.0,
            total_pulls=8,
            total_reward=4.0,
        )

        result = compute_bayesian_update(arm, reward=0.6)

        ci = result["confidence_interval"]
        mean = result["mean_estimate"]

        assert ci["lower"] <= mean <= ci["upper"]


class TestAverageReward:
    """Test average reward tracking."""

    def test_avg_reward_computed(self):
        """Average reward should be total_reward / total_pulls."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        # First pull: reward=0.8
        result = compute_bayesian_update(arm, reward=0.8)
        assert result["avg_reward"] == pytest.approx(0.8, abs=0.01)

        # Second pull: reward=0.6
        arm = RuntimeArm(
            arm_id="test",
            alpha=result["alpha"],
            beta=result["beta"],
            total_pulls=result["total_pulls"],
            total_reward=result["total_reward"],
        )
        result = compute_bayesian_update(arm, reward=0.6)

        # avg = (0.8 + 0.6) / 2 = 0.7
        assert result["avg_reward"] == pytest.approx(0.7, abs=0.01)


class TestEdgeCases:
    """Test edge cases."""

    def test_large_alpha_beta(self):
        """Should handle large alpha/beta values."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1000.0,
            beta=1000.0,
            total_pulls=1998,
            total_reward=1000.0,
        )

        result = compute_bayesian_update(arm, reward=0.5)

        # Should not overflow or produce invalid values
        assert 0.0 <= result["mean_estimate"] <= 1.0
        assert result["alpha"] > 1000.0
        assert result["beta"] > 1000.0

    def test_very_small_beta(self):
        """Should handle very small beta (highly successful arm)."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=100.0,
            beta=0.1,
            total_pulls=99,
            total_reward=99.0,
        )

        result = compute_bayesian_update(arm, reward=1.0)

        # Mean should be very high
        assert result["mean_estimate"] > 0.99

    def test_result_structure(self):
        """Result should have all required fields."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=1.0,
            beta=1.0,
            total_pulls=0,
            total_reward=0.0,
        )

        result = compute_bayesian_update(arm, reward=0.5)

        # Check all required fields
        assert "alpha" in result
        assert "beta" in result
        assert "total_pulls" in result
        assert "total_reward" in result
        assert "avg_reward" in result
        assert "mean_estimate" in result
        assert "confidence_interval" in result
        assert "lower" in result["confidence_interval"]
        assert "upper" in result["confidence_interval"]

        # Check types
        assert isinstance(result["alpha"], float)
        assert isinstance(result["beta"], float)
        assert isinstance(result["total_pulls"], int)
        assert isinstance(result["total_reward"], float)
        assert isinstance(result["avg_reward"], float)
        assert isinstance(result["mean_estimate"], float)


class TestMathematicalCorrectness:
    """Test mathematical correctness of the implementation."""

    def test_beta_distribution_formula(self):
        """Verify the Beta distribution update formula."""
        # Beta(alpha, beta) + observation(reward) -> Beta(alpha + reward, beta + 1 - reward)
        arm = RuntimeArm(
            arm_id="test",
            alpha=3.0,
            beta=7.0,
            total_pulls=8,
            total_reward=3.0,
        )

        reward = 0.4
        result = compute_bayesian_update(arm, reward=reward)

        # Manual calculation
        expected_alpha = 3.0 + 0.4
        expected_beta = 7.0 + 0.6

        assert result["alpha"] == pytest.approx(expected_alpha, abs=0.001)
        assert result["beta"] == pytest.approx(expected_beta, abs=0.001)

    def test_variance_formula(self):
        """Verify variance calculation is correct."""
        arm = RuntimeArm(
            arm_id="test",
            alpha=10.0,
            beta=10.0,
            total_pulls=18,
            total_reward=9.0,
        )

        result = compute_bayesian_update(arm, reward=0.5)

        # Manual variance calculation
        alpha = result["alpha"]
        beta = result["beta"]
        expected_variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
        expected_std = math.sqrt(expected_variance)

        # CI width should be approximately 2 * 1.96 * std_dev
        ci_width = result["confidence_interval"]["upper"] - result["confidence_interval"]["lower"]
        expected_ci_width = 2 * 1.96 * expected_std

        # Allow for clamping at 0 and 1
        assert ci_width <= expected_ci_width + 0.01
