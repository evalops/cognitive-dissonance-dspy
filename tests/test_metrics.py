"""Tests for metrics module."""

import dspy
from cognitive_dissonance.metrics import (
    dissonance_detection_accuracy,
    reconciliation_quality,
    combined_metric,
    agreement_metric_factory,
    blended_metric_factory,
    confidence_weighted_accuracy
)


class TestDissonanceDetectionAccuracy:
    """Test dissonance detection accuracy metric."""

    def test_correct_detection_yes(self):
        """Test correct detection of dissonance."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"

        score = dissonance_detection_accuracy(example, prediction)
        assert score == 1.0

    def test_correct_detection_no(self):
        """Test correct detection of no dissonance."""
        example = dspy.Example(has_dissonance="no")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "no"

        score = dissonance_detection_accuracy(example, prediction)
        assert score == 1.0

    def test_incorrect_detection(self):
        """Test incorrect detection."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "no"

        score = dissonance_detection_accuracy(example, prediction)
        assert score == 0.0

    def test_handles_missing_fields(self):
        """Test handling of missing fields."""
        example = dspy.Example()  # No has_dissonance field
        prediction = dspy.Prediction()
        prediction.has_dissonance = "no"  # Set explicit value

        score = dissonance_detection_accuracy(example, prediction)
        assert score == 1.0  # Defaults match (both "no")

    def test_normalizes_values(self):
        """Test normalization of yes/no values."""
        example = dspy.Example(has_dissonance="YES")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes, definitely"

        score = dissonance_detection_accuracy(example, prediction)
        assert score == 1.0

    def test_handles_exception(self):
        """Test exception handling."""
        example = None
        prediction = dspy.Prediction()

        score = dissonance_detection_accuracy(example, prediction)
        assert score == 0.0


class TestReconciliationQuality:
    """Test reconciliation quality metric."""

    def test_exact_match(self):
        """Test exact match reconciliation."""
        example = dspy.Example(reconciled="The Earth is round")
        prediction = dspy.Prediction()
        prediction.reconciled = "The Earth is round"

        score = reconciliation_quality(example, prediction)
        assert score == 1.0

    def test_partial_overlap(self):
        """Test partial overlap in reconciliation."""
        example = dspy.Example(reconciled="The Earth is round and orbits the Sun")
        prediction = dspy.Prediction()
        prediction.reconciled = "The Earth is round"

        score = reconciliation_quality(example, prediction)
        assert 0.0 < score < 1.0

    def test_no_overlap(self):
        """Test no overlap in reconciliation."""
        example = dspy.Example(reconciled="The Earth is round")
        prediction = dspy.Prediction()
        prediction.reconciled = "Mars has two moons"

        score = reconciliation_quality(example, prediction)
        assert score == 0.0

    def test_empty_reconciliation(self):
        """Test empty reconciliation."""
        example = dspy.Example(reconciled="")
        prediction = dspy.Prediction()
        prediction.reconciled = "Some text"

        score = reconciliation_quality(example, prediction)
        assert score == 0.0

    def test_missing_field(self):
        """Test missing reconciliation field."""
        example = dspy.Example()  # No reconciled field
        prediction = dspy.Prediction()

        score = reconciliation_quality(example, prediction)
        assert score == 0.0

    def test_handles_exception(self):
        """Test exception handling."""
        example = None
        prediction = dspy.Prediction()

        score = reconciliation_quality(example, prediction)
        assert score == 0.0


class TestCombinedMetric:
    """Test combined metric."""

    def test_combined_scoring(self):
        """Test combined detection and reconciliation scoring."""
        example = dspy.Example(
            has_dissonance="yes",
            reconciled="The correct answer"
        )
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "The correct answer"

        score = combined_metric(example, prediction)
        assert score == 1.0  # Both components perfect

    def test_weighted_combination(self):
        """Test weighted combination of metrics."""
        example = dspy.Example(
            has_dissonance="yes",
            reconciled="The correct answer"
        )
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"  # Correct detection (weight 0.7)
        prediction.reconciled = "Wrong"  # Wrong reconciliation (weight 0.3)

        score = combined_metric(example, prediction)
        assert 0.7 <= score < 1.0  # Should be at least 0.7 from detection

    def test_partial_failure(self):
        """Test partial failure in combined metric."""
        example = dspy.Example(
            has_dissonance="yes",
            reconciled="The correct answer"
        )
        prediction = dspy.Prediction()
        prediction.has_dissonance = "no"  # Wrong detection
        prediction.reconciled = "The correct answer"  # Correct reconciliation

        score = combined_metric(example, prediction)
        assert 0.0 < score < 0.5  # Should be less than 0.5


class TestAgreementMetric:
    """Test agreement metric factory."""

    def test_agreement_when_agents_agree(self):
        """Test agreement when agents agree."""
        # Create mock agents
        class MockAgent:
            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "yes"
                return pred

        agent2 = MockAgent()

        metric = agreement_metric_factory(agent2)

        example = dspy.Example(text1="Text 1", text2="Text 2")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"

        score = metric(example, prediction)
        assert score == 1.0

    def test_disagreement_when_agents_disagree(self):
        """Test disagreement when agents disagree."""
        class MockAgent:
            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "no"
                return pred

        agent = MockAgent()
        metric = agreement_metric_factory(agent)

        example = dspy.Example(text1="Text 1", text2="Text 2")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"

        score = metric(example, prediction)
        assert score == 0.0

    def test_handles_exception(self):
        """Test exception handling in agreement metric."""
        class BrokenAgent:
            def __call__(self, text1, text2):
                raise ValueError("Agent error")

        agent = BrokenAgent()
        metric = agreement_metric_factory(agent)

        example = dspy.Example(text1="Text 1", text2="Text 2")
        prediction = dspy.Prediction()

        score = metric(example, prediction)
        assert score == 0.0


class TestBlendedMetric:
    """Test blended metric factory."""

    def test_blending_with_labels(self):
        """Test blending when labels are available."""
        class MockAgent:
            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "yes"
                return pred

        agent = MockAgent()
        metric = blended_metric_factory(agent, alpha=0.5)

        example = dspy.Example(
            text1="Text 1",
            text2="Text 2",
            has_dissonance="yes"
        )
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"

        score = metric(example, prediction)
        assert score == 1.0  # Both truth and agreement are perfect

    def test_blending_without_labels(self):
        """Test blending when labels are not available."""
        class MockAgent:
            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "yes"
                return pred

        agent = MockAgent()
        metric = blended_metric_factory(agent, alpha=0.5)

        example = dspy.Example(text1="Text 1", text2="Text 2")  # No labels
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"

        score = metric(example, prediction)
        assert score == 1.0  # Only agreement matters without labels

    def test_alpha_weighting(self):
        """Test alpha weighting in blended metric."""
        class MockAgent:
            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "no"  # Disagrees
                return pred

        agent = MockAgent()

        # Test with high alpha (truth-weighted)
        metric_high = blended_metric_factory(agent, alpha=0.9)

        example = dspy.Example(
            text1="Text 1",
            text2="Text 2",
            has_dissonance="yes"
        )
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"  # Correct truth

        score_high = metric_high(example, prediction)
        assert score_high >= 0.9  # Should be close to truth score (1.0)

        # Test with low alpha (agreement-weighted)
        metric_low = blended_metric_factory(agent, alpha=0.1)
        score_low = metric_low(example, prediction)
        assert score_low <= 0.2  # Should be close to agreement score (0.0)


class TestConfidenceWeightedAccuracy:
    """Test confidence weighted accuracy metric."""

    def test_high_confidence_correct(self):
        """Test high confidence with correct prediction."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.confidence1 = "high"
        prediction.confidence2 = "high"

        score = confidence_weighted_accuracy(example, prediction)
        assert score == 1.0

    def test_low_confidence_correct(self):
        """Test low confidence with correct prediction."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.confidence1 = "low"
        prediction.confidence2 = "low"

        score = confidence_weighted_accuracy(example, prediction)
        assert score == 0.4  # 1.0 * 0.4 (low confidence weight)

    def test_mixed_confidence(self):
        """Test mixed confidence levels."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.confidence1 = "high"
        prediction.confidence2 = "low"

        score = confidence_weighted_accuracy(example, prediction)
        expected = 1.0 * ((1.0 + 0.4) / 2)  # Average of high and low
        assert abs(score - expected) < 0.01

    def test_incorrect_with_high_confidence(self):
        """Test incorrect prediction with high confidence."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "no"
        prediction.confidence1 = "high"
        prediction.confidence2 = "high"

        score = confidence_weighted_accuracy(example, prediction)
        assert score == 0.0  # Wrong prediction gets 0 regardless of confidence

    def test_missing_confidence(self):
        """Test with missing confidence values."""
        example = dspy.Example(has_dissonance="yes")
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        # No confidence fields

        score = confidence_weighted_accuracy(example, prediction)
        assert score == 0.7  # Defaults to medium confidence (0.7)
