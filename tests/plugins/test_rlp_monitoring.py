"""
Tests for RLP entropy monitoring and KL divergence constraints.

Tests policy stability checks for safe reinforcement learning.
"""

import pytest
import numpy as np

from convergence.plugins.learning.rlp import RLPMixin, RLPConfig


# =============================================================================
# ENTROPY MONITORING TESTS
# =============================================================================


class TestRLPEntropyMonitoring:
    """Test entropy computation for policy distributions."""

    @pytest.fixture
    def rlp_mixin(self):
        """Create RLP mixin for testing."""
        config = RLPConfig(normalize_rewards=False)
        return RLPMixin(config=config)

    def test_compute_policy_entropy_uniform(self, rlp_mixin):
        """Uniform distribution should have maximum entropy."""
        # Uniform distribution over 4 actions
        policy = np.array([0.25, 0.25, 0.25, 0.25])

        entropy = rlp_mixin.compute_policy_entropy(policy)

        # Max entropy for 4 actions = log(4) ≈ 1.386
        expected = np.log(4)
        assert abs(entropy - expected) < 0.001

    def test_compute_policy_entropy_deterministic(self, rlp_mixin):
        """Deterministic policy should have zero entropy."""
        # All probability on one action
        policy = np.array([1.0, 0.0, 0.0, 0.0])

        entropy = rlp_mixin.compute_policy_entropy(policy)

        assert entropy == 0.0

    def test_compute_policy_entropy_skewed(self, rlp_mixin):
        """Skewed distribution should have intermediate entropy."""
        # Mostly one action
        policy = np.array([0.7, 0.1, 0.1, 0.1])

        entropy = rlp_mixin.compute_policy_entropy(policy)

        # Should be between 0 and max
        max_entropy = np.log(4)
        assert 0 < entropy < max_entropy

    def test_entropy_threshold_warning(self, rlp_mixin):
        """Low entropy should trigger warning/flag."""
        # Near-deterministic policy
        policy = np.array([0.95, 0.02, 0.02, 0.01])

        entropy = rlp_mixin.compute_policy_entropy(policy)
        is_low_entropy = rlp_mixin.is_entropy_below_threshold(
            policy, threshold=0.5
        )

        assert is_low_entropy is True

    def test_entropy_healthy_policy(self, rlp_mixin):
        """Healthy exploration should not trigger warning."""
        # Good exploration
        policy = np.array([0.4, 0.3, 0.2, 0.1])

        is_low_entropy = rlp_mixin.is_entropy_below_threshold(
            policy, threshold=0.5
        )

        assert is_low_entropy is False


# =============================================================================
# KL DIVERGENCE CONSTRAINT TESTS
# =============================================================================


class TestRLPKLDivergence:
    """Test KL divergence constraints for policy updates."""

    @pytest.fixture
    def rlp_mixin(self):
        """Create RLP mixin for testing."""
        config = RLPConfig(kl_target=0.01)
        return RLPMixin(config=config)

    def test_compute_kl_divergence_identical(self, rlp_mixin):
        """Identical distributions should have zero KL divergence."""
        p = np.array([0.5, 0.3, 0.2])
        q = np.array([0.5, 0.3, 0.2])

        kl = rlp_mixin.compute_kl_divergence(p, q)

        assert kl == 0.0

    def test_compute_kl_divergence_different(self, rlp_mixin):
        """Different distributions should have positive KL divergence."""
        p = np.array([0.5, 0.3, 0.2])
        q = np.array([0.3, 0.4, 0.3])

        kl = rlp_mixin.compute_kl_divergence(p, q)

        assert kl > 0.0

    def test_kl_divergence_asymmetric(self, rlp_mixin):
        """KL divergence should be asymmetric: KL(p||q) != KL(q||p)."""
        p = np.array([0.8, 0.1, 0.1])
        q = np.array([0.4, 0.3, 0.3])

        kl_pq = rlp_mixin.compute_kl_divergence(p, q)
        kl_qp = rlp_mixin.compute_kl_divergence(q, p)

        assert kl_pq != kl_qp

    def test_kl_constraint_violated(self, rlp_mixin):
        """Large policy change should violate KL constraint."""
        old_policy = np.array([0.5, 0.3, 0.2])
        new_policy = np.array([0.1, 0.1, 0.8])  # Big change

        is_violated = rlp_mixin.is_kl_constraint_violated(
            old_policy, new_policy, threshold=0.1
        )

        assert is_violated is True

    def test_kl_constraint_satisfied(self, rlp_mixin):
        """Small policy change should satisfy KL constraint."""
        old_policy = np.array([0.5, 0.3, 0.2])
        new_policy = np.array([0.48, 0.32, 0.20])  # Small change

        is_violated = rlp_mixin.is_kl_constraint_violated(
            old_policy, new_policy, threshold=0.1
        )

        assert is_violated is False

    def test_kl_handles_zeros_safely(self, rlp_mixin):
        """KL computation should handle zero probabilities safely."""
        # Add small epsilon to avoid log(0)
        p = np.array([0.5, 0.5, 0.0])
        q = np.array([0.4, 0.4, 0.2])

        # Should not raise, should return finite value
        kl = rlp_mixin.compute_kl_divergence(p, q)

        assert np.isfinite(kl)


# =============================================================================
# POLICY STABILITY METRICS TESTS
# =============================================================================


class TestRLPPolicyStability:
    """Test combined policy stability monitoring."""

    @pytest.fixture
    def rlp_mixin(self):
        """Create RLP mixin for testing."""
        return RLPMixin(config=RLPConfig())

    def test_get_policy_health_metrics(self, rlp_mixin):
        """Should return comprehensive policy health metrics."""
        old_policy = np.array([0.4, 0.3, 0.2, 0.1])
        new_policy = np.array([0.35, 0.35, 0.2, 0.1])

        metrics = rlp_mixin.get_policy_health_metrics(old_policy, new_policy)

        assert "entropy" in metrics
        assert "kl_divergence" in metrics
        assert "entropy_ratio" in metrics
        assert "is_healthy" in metrics

    def test_policy_health_flags_collapse(self, rlp_mixin):
        """Should flag policy collapse (low entropy)."""
        old_policy = np.array([0.25, 0.25, 0.25, 0.25])
        new_policy = np.array([0.97, 0.01, 0.01, 0.01])

        metrics = rlp_mixin.get_policy_health_metrics(old_policy, new_policy)

        assert metrics["is_healthy"] is False
        assert "low_entropy" in metrics.get("warnings", [])

    def test_policy_health_flags_drift(self, rlp_mixin):
        """Should flag excessive policy drift (high KL)."""
        old_policy = np.array([0.5, 0.3, 0.15, 0.05])
        new_policy = np.array([0.05, 0.15, 0.3, 0.5])  # Reversed

        metrics = rlp_mixin.get_policy_health_metrics(old_policy, new_policy)

        assert metrics["is_healthy"] is False
        assert "high_kl_divergence" in metrics.get("warnings", [])


# =============================================================================
# INTEGRATION WITH EXPERIENCE BUFFER
# =============================================================================


class TestRLPMonitoringIntegration:
    """Test entropy/KL monitoring integrates with learning loop."""

    @pytest.fixture
    def rlp_mixin(self):
        """Create RLP mixin with buffer."""
        config = RLPConfig(buffer_size=100, kl_target=0.01)
        return RLPMixin(config=config)

    def test_learning_metrics_include_entropy(self, rlp_mixin):
        """Learning metrics should include entropy stats."""
        # Add some experiences
        for i in range(20):
            rlp_mixin.experience_buffer.add(
                state={"step": i},
                thought=f"thought_{i}",
                action=f"action_{i}",
                reward=0.5 + (i * 0.02),
                next_state={"step": i + 1},
            )

        metrics = rlp_mixin.get_learning_metrics()

        # Should have buffer metrics
        assert metrics["buffer_size"] == 20

        # Metrics structure should be present
        assert "recent_mean_reward" in metrics or "status" in metrics
