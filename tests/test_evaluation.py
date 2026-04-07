"""Tests for evaluation module."""

import dspy
from unittest.mock import Mock
from cognitive_dissonance.evaluation import (
    evaluate,
    agreement_rate,
    cross_validate,
    analyze_errors
)
class TestEvaluate:
    """Test evaluate function."""

    def test_evaluate_with_default_metric(self, sample_examples):
        """Test evaluation with default metric."""
        # Create mock module
        mock_module = Mock()
        mock_pred = dspy.Prediction()
        mock_pred.has_dissonance = "yes"
        mock_module.return_value = mock_pred

        score = evaluate(mock_module, sample_examples, display_progress=False)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        assert mock_module.call_count == len(sample_examples)

    def test_evaluate_with_custom_metric(self, sample_examples):
        """Test evaluation with custom metric."""
        def custom_metric(example, prediction):
            return 0.5  # Always return 0.5

        mock_module = Mock()
        mock_pred = dspy.Prediction()
        mock_module.return_value = mock_pred

        score = evaluate(
            mock_module,
            sample_examples,
            metric=custom_metric,
            display_progress=False
        )

        assert score == 0.5

    def test_evaluate_empty_dataset(self):
        """Test evaluation with empty dataset."""
        mock_module = Mock()

        score = evaluate(mock_module, [], display_progress=False)
        assert score == 0.0

    def test_evaluate_with_return_outputs(self, sample_examples):
        """Test evaluation returning outputs."""
        mock_module = Mock()
        mock_pred = dspy.Prediction()
        mock_pred.has_dissonance = "yes"
        mock_module.return_value = mock_pred

        score, outputs = evaluate(
            mock_module,
            sample_examples,
            display_progress=False,
            return_outputs=True
        )

        assert isinstance(score, float)
        assert len(outputs) == len(sample_examples)
        assert all(isinstance(o, dspy.Prediction) for o in outputs)

    def test_evaluate_handles_exceptions(self, sample_examples):
        """Test evaluation handles module exceptions."""
        mock_module = Mock(side_effect=ValueError("Test error"))

        score = evaluate(mock_module, sample_examples, display_progress=False)

        assert score == 0.0  # Should handle errors gracefully


class TestAgreementRate:
    """Test agreement rate calculation."""

    def test_perfect_agreement(self, sample_examples):
        """Test perfect agreement between agents."""
        # Create agents that always agree
        agent1 = Mock()
        agent2 = Mock()

        pred = dspy.Prediction()
        pred.has_dissonance = "yes"

        agent1.return_value = pred
        agent2.return_value = pred

        rate = agreement_rate(agent1, agent2, sample_examples)
        assert rate == 1.0

    def test_no_agreement(self, sample_examples):
        """Test no agreement between agents."""
        # Create agents that always disagree
        agent1 = Mock()
        agent2 = Mock()

        pred1 = dspy.Prediction()
        pred1.has_dissonance = "yes"

        pred2 = dspy.Prediction()
        pred2.has_dissonance = "no"

        agent1.return_value = pred1
        agent2.return_value = pred2

        rate = agreement_rate(agent1, agent2, sample_examples)
        assert rate == 0.0

    def test_partial_agreement(self, sample_examples):
        """Test partial agreement between agents."""
        agent1 = Mock()
        agent2 = Mock()

        # Alternate between agree and disagree
        predictions = []
        for i in range(len(sample_examples)):
            pred1 = dspy.Prediction()
            pred2 = dspy.Prediction()

            if i % 2 == 0:
                pred1.has_dissonance = "yes"
                pred2.has_dissonance = "yes"
            else:
                pred1.has_dissonance = "yes"
                pred2.has_dissonance = "no"

            predictions.append((pred1, pred2))

        agent1.side_effect = [p[0] for p in predictions]
        agent2.side_effect = [p[1] for p in predictions]

        rate = agreement_rate(agent1, agent2, sample_examples)
        assert 0.0 < rate < 1.0

    def test_normalizes_free_form_verdicts(self, sample_examples):
        """Free-form labels should normalize before agreement is computed."""
        agent1 = Mock()
        agent2 = Mock()

        pred1 = dspy.Prediction()
        pred1.has_dissonance = "Yes, definitely contradictory"

        pred2 = dspy.Prediction()
        pred2.has_dissonance = "yes"

        agent1.return_value = pred1
        agent2.return_value = pred2

        rate = agreement_rate(agent1, agent2, sample_examples)
        assert rate == 1.0

    def test_empty_dataset(self):
        """Test agreement rate with empty dataset."""
        agent1 = Mock()
        agent2 = Mock()

        rate = agreement_rate(agent1, agent2, [])
        assert rate == 0.0

    def test_handles_exceptions(self, sample_examples):
        """Test agreement rate handles exceptions."""
        agent1 = Mock(side_effect=ValueError("Error"))
        agent2 = Mock()

        rate = agreement_rate(agent1, agent2, sample_examples)
        assert rate == 0.0  # Should handle errors gracefully


class TestCrossValidate:
    """Test cross-validation."""

    def test_cross_validate_basic(self, sample_examples):
        """Test basic cross-validation."""
        # Create a mock module class
        class MockModule:
            def __init__(self, **kwargs):
                pass

            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "yes"
                pred.reconciled = "test"
                return pred

        results = cross_validate(
            MockModule,
            sample_examples,
            k_folds=2,
            display_progress=False
        )

        assert "avg_score" in results
        assert "std_score" in results
        assert "fold_scores" in results
        assert "k_folds" in results
        assert results["k_folds"] == 2
        assert len(results["fold_scores"]) == 2

    def test_cross_validate_with_module_kwargs(self, sample_examples):
        """Test cross-validation with module kwargs."""
        class MockModule:
            def __init__(self, use_cot=False):
                self.use_cot = use_cot

            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "yes" if self.use_cot else "no"
                return pred

        results = cross_validate(
            MockModule,
            sample_examples,
            k_folds=2,
            use_cot=True
        )

        assert results["avg_score"] >= 0.0

    def test_cross_validate_small_dataset(self):
        """Test cross-validation with dataset smaller than k."""
        small_dataset = [
            dspy.Example(text1="t1", text2="t2", has_dissonance="yes").with_inputs("text1", "text2"),
            dspy.Example(text1="t3", text2="t4", has_dissonance="no").with_inputs("text1", "text2"),
        ]

        class MockModule:
            def __init__(self, **kwargs):
                pass

            def __call__(self, text1, text2):
                pred = dspy.Prediction()
                pred.has_dissonance = "yes"
                return pred

        results = cross_validate(
            MockModule,
            small_dataset,
            k_folds=5  # More folds than data
        )

        # Should use leave-one-out
        assert results["k_folds"] == len(small_dataset)


class TestAnalyzeErrors:
    """Test error analysis."""

    def test_analyze_errors_no_errors(self, sample_examples):
        """Test error analysis with no errors."""
        # Create perfect module
        mock_module = Mock()

        def perfect_predict(text1, text2):
            # Find the example and return correct prediction
            for ex in sample_examples:
                if ex.text1 == text1 and ex.text2 == text2:
                    pred = dspy.Prediction()
                    pred.has_dissonance = ex.has_dissonance
                    pred.reconciled = ex.reconciled
                    return pred
            return dspy.Prediction()

        mock_module.side_effect = perfect_predict

        errors = analyze_errors(mock_module, sample_examples)

        assert errors["total_errors"] == 0
        assert errors["error_rate"] == 0.0
        assert len(errors["false_positives"]) == 0
        assert len(errors["false_negatives"]) == 0

    def test_analyze_errors_false_positives(self, sample_examples):
        """Test error analysis with false positives."""
        mock_module = Mock()

        # Always predict "yes" for dissonance
        pred = dspy.Prediction()
        pred.has_dissonance = "yes"
        pred.reconciled = "test"
        mock_module.return_value = pred

        errors = analyze_errors(mock_module, sample_examples)

        # Should have false positives for examples with has_dissonance="no"
        assert len(errors["false_positives"]) > 0
        assert errors["false_positive_rate"] > 0.0

    def test_analyze_errors_false_negatives(self, sample_examples):
        """Test error analysis with false negatives."""
        mock_module = Mock()

        # Always predict "no" for dissonance
        pred = dspy.Prediction()
        pred.has_dissonance = "no"
        pred.reconciled = "test"
        mock_module.return_value = pred

        errors = analyze_errors(mock_module, sample_examples)

        # Should have false negatives for examples with has_dissonance="yes"
        assert len(errors["false_negatives"]) > 0
        assert errors["false_negative_rate"] > 0.0

    def test_analyze_errors_reconciliation_failures(self, sample_examples):
        """Test error analysis with reconciliation failures."""
        mock_module = Mock()

        def bad_reconcile(text1, text2):
            pred = dspy.Prediction()
            pred.has_dissonance = "yes"
            pred.reconciled = "x"  # Very short/different reconciliation
            return pred

        mock_module.side_effect = bad_reconcile

        errors = analyze_errors(mock_module, sample_examples)

        # Should detect reconciliation failures
        assert len(errors["reconciliation_failures"]) > 0

    def test_analyze_errors_handles_exceptions(self, sample_examples):
        """Test error analysis handles exceptions."""
        mock_module = Mock(side_effect=ValueError("Error"))

        errors = analyze_errors(mock_module, sample_examples)

        assert errors["total_errors"] == len(sample_examples)
        assert errors["error_rate"] == 1.0
