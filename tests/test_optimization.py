"""Tests for optimization module."""

import dspy

from cognitive_dissonance.metrics import combined_metric
from cognitive_dissonance.optimization import (
    EnsembleModule,
    EnsembleOptimizer,
    GEPAOptimizer,
    create_advanced_optimizer,
)
from cognitive_dissonance.verifier import CognitiveDissonanceResolver


class TestGEPAOptimizer:
    """Test GEPA optimizer."""

    def test_initialization(self):
        """Test GEPA optimizer initialization."""
        optimizer = GEPAOptimizer(metric=combined_metric)
        assert optimizer.metric == combined_metric
        assert optimizer.max_iterations == 3
        assert optimizer.improvement_threshold == 0.05
        assert optimizer.optimization_history == []

    def test_initialization_custom_params(self):
        """Test GEPA optimizer with custom parameters."""
        optimizer = GEPAOptimizer(
            metric=combined_metric,
            max_iterations=5,
            improvement_threshold=0.1
        )
        assert optimizer.max_iterations == 5
        assert optimizer.improvement_threshold == 0.1

    def test_reflect_on_trajectory(self):
        """Test reflection on trajectory."""
        optimizer = GEPAOptimizer(metric=combined_metric)
        module = CognitiveDissonanceResolver()

        # Create mock examples
        examples = [
            dspy.Example(text1="Text 1", text2="Text 2", has_dissonance="yes"),
            dspy.Example(text1="Text 3", text2="Text 4", has_dissonance="no")
        ]

        reflection = optimizer.reflect_on_trajectory(module, examples, 0.75)

        assert isinstance(reflection, str)
        assert len(reflection) > 0
        assert "Performance Analysis" in reflection

    def test_format_predictions(self):
        """Test prediction formatting for reflection."""
        optimizer = GEPAOptimizer(metric=combined_metric)

        predictions = [{
            'input': ("Text 1", "Text 2"),
            'output': {'has_dissonance': 'yes', 'reconciled': 'Test reconciliation'},
            'expected': {'has_dissonance': 'yes', 'reconciled': 'Expected reconciliation'}
        }]

        formatted = optimizer._format_predictions(predictions)

        assert isinstance(formatted, str)
        assert "Example 1" in formatted
        assert "Text 1" in formatted
        assert "yes" in formatted

    def test_analyze_predictions(self):
        """Test prediction analysis."""
        optimizer = GEPAOptimizer(metric=combined_metric)

        predictions = [
            {
                'output': {'has_dissonance': 'yes', 'reconciled': 'Good reconciliation'},
                'expected': {'has_dissonance': 'yes', 'reconciled': 'Expected reconciliation'}
            },
            {
                'output': {'has_dissonance': 'no', 'reconciled': ''},
                'expected': {'has_dissonance': 'no', 'reconciled': ''}
            }
        ]

        analysis = optimizer._analyze_predictions(predictions, 0.8)

        assert isinstance(analysis, str)
        assert "Performance Analysis" in analysis
        assert "0.800" in analysis


class TestEnsembleOptimizer:
    """Test ensemble optimizer."""

    def test_initialization(self):
        """Test ensemble optimizer initialization."""
        from dspy.teleprompt import BootstrapFewShot

        optimizers = [BootstrapFewShot(metric=combined_metric)]
        ensemble_optimizer = EnsembleOptimizer(optimizers)

        assert ensemble_optimizer.base_optimizers == optimizers
        assert ensemble_optimizer.ensemble_size == 5
        assert ensemble_optimizer.voting_strategy == "majority"

    def test_initialization_custom_params(self):
        """Test ensemble optimizer with custom parameters."""
        from dspy.teleprompt import BootstrapFewShot

        optimizers = [BootstrapFewShot(metric=combined_metric)]
        ensemble_optimizer = EnsembleOptimizer(
            optimizers,
            ensemble_size=3,
            voting_strategy="weighted"
        )

        assert ensemble_optimizer.ensemble_size == 3
        assert ensemble_optimizer.voting_strategy == "weighted"


class TestEnsembleModule:
    """Test ensemble module."""

    def test_initialization(self):
        """Test ensemble module initialization."""
        modules = [CognitiveDissonanceResolver(), CognitiveDissonanceResolver()]
        scores = [0.8, 0.9]

        ensemble = EnsembleModule(modules, scores)

        assert len(ensemble.modules) == 2
        assert ensemble.scores == scores
        assert ensemble.voting_strategy == "majority"
        assert len(ensemble.weights) == 2

    def test_compute_weights(self):
        """Test weight computation."""
        modules = [CognitiveDissonanceResolver()]
        scores = [0.8, 0.9]

        ensemble = EnsembleModule(modules, scores)
        weights = ensemble._compute_weights(scores)

        assert len(weights) == 2
        assert abs(sum(weights) - 1.0) < 0.01  # Weights should sum to 1
        assert weights[1] > weights[0]  # Higher score should get higher weight

    def test_compute_weights_zero_scores(self):
        """Test weight computation with zero scores."""
        modules = [CognitiveDissonanceResolver(), CognitiveDissonanceResolver()]
        scores = [0.0, 0.0]

        ensemble = EnsembleModule(modules, scores)
        weights = ensemble._compute_weights(scores)

        assert len(weights) == 2
        assert weights[0] == weights[1] == 0.5  # Equal weights for zero scores

    def test_forward_fallback(self):
        """Test forward with fallback prediction."""
        # Create a dummy module for the ensemble but make it fail
        class FailingModule:
            def __call__(self, **kwargs):
                raise ValueError("Module failure")

        modules = [FailingModule()]
        ensemble = EnsembleModule(modules, [1.0])

        result = ensemble.forward(text1="Test 1", text2="Test 2")

        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, 'has_dissonance')
        assert hasattr(result, 'reconciled')
        assert result.has_dissonance == "no"
        assert result.reconciled == "Unable to determine"

    def test_majority_vote(self):
        """Test majority voting."""
        modules = [CognitiveDissonanceResolver()]
        ensemble = EnsembleModule(modules, [1.0])

        # Create mock predictions
        pred1 = dspy.Prediction()
        pred1.has_dissonance = "yes"
        pred1.reconciled = "Reconciliation 1"

        pred2 = dspy.Prediction()
        pred2.has_dissonance = "no"
        pred2.reconciled = "Reconciliation 2"

        result = ensemble._majority_vote([pred1, pred2])

        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, 'has_dissonance')
        assert hasattr(result, 'reconciled')
        assert hasattr(result, 'ensemble_confidence')
        assert hasattr(result, 'ensemble_size')

    def test_weighted_vote(self):
        """Test weighted voting."""
        modules = [CognitiveDissonanceResolver()]
        ensemble = EnsembleModule(modules, [1.0], voting_strategy="weighted")

        # Create mock predictions
        pred1 = dspy.Prediction()
        pred1.has_dissonance = "yes"
        pred1.reconciled = "Reconciliation 1"

        pred2 = dspy.Prediction()
        pred2.has_dissonance = "no"
        pred2.reconciled = "Reconciliation 2"

        result = ensemble._weighted_vote([pred1, pred2])

        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, 'has_dissonance')
        assert hasattr(result, 'ensemble_confidence')

    def test_weighted_vote_fallback(self):
        """Test weighted vote fallback to majority vote."""
        modules = [CognitiveDissonanceResolver()]
        ensemble = EnsembleModule(modules, [1.0], voting_strategy="weighted")

        # Mismatch between predictions and weights
        pred1 = dspy.Prediction()
        pred1.has_dissonance = "yes"

        # This should fallback to majority vote
        result = ensemble._weighted_vote([pred1])

        assert isinstance(result, dspy.Prediction)


class TestAdvancedOptimizerFactory:
    """Test advanced optimizer factory."""

    def test_create_gepa_optimizer(self):
        """Test creating GEPA optimizer."""
        optimizer = create_advanced_optimizer("gepa")
        assert isinstance(optimizer, GEPAOptimizer)

    def test_create_ensemble_optimizer(self):
        """Test creating ensemble optimizer."""
        optimizer = create_advanced_optimizer("ensemble")
        assert isinstance(optimizer, EnsembleOptimizer)

    def test_create_combined_optimizer(self):
        """Test creating combined GEPA+ensemble optimizer."""
        optimizer = create_advanced_optimizer("gepa+ensemble")
        assert isinstance(optimizer, EnsembleOptimizer)

    def test_create_unknown_strategy(self):
        """Test creating optimizer with unknown strategy."""
        optimizer = create_advanced_optimizer("unknown_strategy")
        assert isinstance(optimizer, GEPAOptimizer)
