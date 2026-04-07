"""Integration tests for cognitive dissonance system."""

import pytest
from unittest.mock import patch, Mock
import dspy
from cognitive_dissonance import (
    ExperimentConfig,
    BeliefAgent,
    DissonanceDetector,
    ReconciliationAgent,
    CognitiveDissonanceResolver,
    cognitive_dissonance_experiment,
    evaluate,
    agreement_rate
)
from cognitive_dissonance.data import get_dev_labeled, get_train_unlabeled


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline."""

    def test_full_resolver_pipeline(self):
        """Test complete resolver pipeline with real components."""
        # Setup configuration
        config = ExperimentConfig(
            model="mock_model",
            api_base="http://localhost:11434",
            temperature=0.5,
            max_tokens=100
        )

        # Mock DSPy configuration
        with patch('dspy.configure'):
            with patch('dspy.configure_cache', create=True):
                with patch('dspy.LM'):
                    config.setup_dspy()

        # Create resolver
        resolver = CognitiveDissonanceResolver(use_cot=False)

        # Mock the underlying DSPy operations
        def mock_extract(text):
            pred = dspy.Prediction()
            if "Paris" in text and "not" not in text:
                pred.claim = "Paris is the capital of France"
                pred.confidence = "high"
            else:
                pred.claim = "Paris is not the capital"
                pred.confidence = "medium"
            return pred

        def mock_detect(claim1, claim2):
            pred = dspy.Prediction()
            if "not" in claim2 and "not" not in claim1:
                pred.are_contradictory = "yes"
                pred.reason = "Contradictory statements about Paris"
            else:
                pred.are_contradictory = "no"
                pred.reason = "Compatible statements"
            return pred

        def mock_reconcile(**kwargs):
            pred = dspy.Prediction()
            if kwargs.get("has_conflict") == "yes":
                pred.reconciled_claim = "Paris is the capital of France"
            else:
                pred.reconciled_claim = f"{kwargs['claim1']}. {kwargs['claim2']}"
            return pred

        resolver.belief_agent.extract = mock_extract
        resolver.dissonance_detector.detect = mock_detect
        resolver.reconciliation_agent.reconcile = mock_reconcile

        # Test with conflicting texts
        text1 = "The capital of France is Paris. It is a beautiful city."
        text2 = "Paris is not the capital of France. London holds that title."

        result = resolver(text1, text2)

        assert result.has_dissonance == "yes"
        assert "Paris" in result.reconciled
        assert result.confidence1 in ["high", "medium", "low"]
        assert result.confidence2 in ["high", "medium", "low"]

    def test_agents_interaction(self):
        """Test interaction between different agents."""
        # Create agents
        belief = BeliefAgent()
        dissonance = DissonanceDetector()
        reconciliation = ReconciliationAgent()

        # Mock their core functions
        belief.extract = lambda text: dspy.Prediction(
            claim="Test claim",
            confidence="medium"
        )

        dissonance.detect = lambda c1, c2: dspy.Prediction(
            are_contradictory="yes",
            reason="Test reason"
        )

        reconciliation.reconcile = lambda **kwargs: dspy.Prediction(
            reconciled_claim="Reconciled test claim"
        )

        # Test pipeline
        text1 = "First text"
        text2 = "Second text"

        belief1 = belief(text1)
        belief2 = belief(text2)

        conflict = dissonance(belief1.claim, belief2.claim)

        if conflict.are_contradictory == "yes":
            reconciled = reconciliation(
                belief1.claim,
                belief2.claim,
                has_conflict="yes"
            )
            assert reconciled.reconciled_claim == "Reconciled test claim"


class TestDataIntegration:
    """Test data loading and processing integration."""

    def test_data_pipeline(self):
        """Test complete data pipeline."""
        # Load data
        dev_data = get_dev_labeled()
        train_data = get_train_unlabeled()

        assert len(dev_data) > 0
        assert len(train_data) > 0

        # Create a simple resolver
        resolver = CognitiveDissonanceResolver()

        # Mock the underlying operations
        resolver.belief_agent.extract = lambda text: dspy.Prediction(
            claim="test", confidence="medium"
        )
        resolver.dissonance_detector.detect = lambda c1, c2: dspy.Prediction(
            are_contradictory="no", reason="test"
        )
        resolver.reconciliation_agent.reconcile = lambda **kw: dspy.Prediction(
            reconciled_claim="test reconciled"
        )

        # Process some examples
        for example in dev_data[:2]:
            result = resolver(example.text1, example.text2)
            assert hasattr(result, "has_dissonance")
            assert hasattr(result, "reconciled")

    def test_evaluation_on_data(self):
        """Test evaluation on real data."""
        # Get data
        dev_data = get_dev_labeled()[:3]  # Use small subset

        # Create mock module
        mock_module = Mock()
        mock_module.return_value = dspy.Prediction(
            has_dissonance="yes",
            reconciled="test"
        )

        # Run evaluation
        score = evaluate(mock_module, dev_data, display_progress=False)

        assert 0.0 <= score <= 1.0
        assert mock_module.call_count == len(dev_data)


class TestExperimentIntegration:
    """Test experiment integration."""

    @patch('cognitive_dissonance.experiment.GEPAOptimizer')
    def test_mini_experiment(self, mock_gepa):
        """Test minimal experiment execution."""
        # Setup minimal config
        config = ExperimentConfig(
            rounds=1,
            temperature=0.5,
            max_tokens=100
        )

        # Mock optimizer
        mock_optimizer = Mock()
        mock_compiled = Mock()
        mock_compiled.return_value = dspy.Prediction(
            has_dissonance="yes",
            reconciled="test",
            claim1="c1",
            claim2="c2",
            confidence1="high",
            confidence2="low"
        )
        mock_optimizer.compile = Mock(return_value=mock_compiled)
        mock_gepa.return_value = mock_optimizer

        # Mock DSPy setup
        with patch('dspy.configure'):
            with patch('dspy.configure_cache', create=True):
                with patch('dspy.LM'):
                    results = cognitive_dissonance_experiment(config)

        from cognitive_dissonance.experiment import ExperimentResults
        assert isinstance(results, ExperimentResults)
        assert len(results.rounds) == 1

    def test_agreement_between_agents(self):
        """Test agreement calculation between agents."""
        # Create two mock agents
        agent1 = Mock()
        agent2 = Mock()

        # Make them agree sometimes
        predictions = [
            (dspy.Prediction(has_dissonance="yes"), dspy.Prediction(has_dissonance="yes")),
            (dspy.Prediction(has_dissonance="no"), dspy.Prediction(has_dissonance="yes")),
            (dspy.Prediction(has_dissonance="no"), dspy.Prediction(has_dissonance="no")),
        ]

        agent1.side_effect = [p[0] for p in predictions]
        agent2.side_effect = [p[1] for p in predictions]

        # Create test data
        test_data = [
            dspy.Example(text1=f"t{i}1", text2=f"t{i}2").with_inputs("text1", "text2")
            for i in range(3)
        ]

        rate = agreement_rate(agent1, agent2, test_data)

        # Should have 2/3 agreement
        assert abs(rate - 2/3) < 0.01


class TestMetricsIntegration:
    """Test metrics integration."""

    def test_metrics_with_real_predictions(self):
        """Test metrics with realistic predictions."""
        from cognitive_dissonance.metrics import (
            dissonance_detection_accuracy,
            reconciliation_quality,
            combined_metric
        )

        # Create realistic example and prediction
        example = dspy.Example(
            text1="The Earth is round",
            text2="The Earth is flat",
            has_dissonance="yes",
            reconciled="The Earth is round, not flat"
        )

        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "The Earth is round"

        # Test metrics
        detection_score = dissonance_detection_accuracy(example, prediction)
        assert detection_score == 1.0  # Correct detection

        recon_score = reconciliation_quality(example, prediction)
        assert 0.0 < recon_score < 1.0  # Partial match

        combined = combined_metric(example, prediction)
        assert 0.7 <= combined <= 1.0  # Weighted combination


class TestConfigurationIntegration:
    """Test configuration integration."""

    def test_config_affects_behavior(self):
        """Test that configuration changes affect behavior."""
        # Test with Chain of Thought
        resolver_cot = CognitiveDissonanceResolver(use_cot=True)
        assert resolver_cot.belief_agent.use_cot is True
        assert resolver_cot.dissonance_detector.use_cot is True
        assert resolver_cot.reconciliation_agent.use_cot is True

        # Test without Chain of Thought
        resolver_no_cot = CognitiveDissonanceResolver(use_cot=False)
        assert resolver_no_cot.belief_agent.use_cot is False
        assert resolver_no_cot.dissonance_detector.use_cot is False
        assert resolver_no_cot.reconciliation_agent.use_cot is False

    def test_environment_config_loading(self, monkeypatch):
        """Test loading configuration from environment."""
        # Set environment variables
        monkeypatch.setenv("MODEL", "test_model")
        monkeypatch.setenv("ALPHA", "0.3")
        monkeypatch.setenv("ROUNDS", "5")
        monkeypatch.setenv("USE_COT", "true")
        monkeypatch.setenv("DISSONANCE_THRESHOLD", "0.8")

        config = ExperimentConfig.from_env()

        assert config.model == "test_model"
        assert config.alpha == 0.3
        assert config.rounds == 5
        assert config.use_cot is True
        assert config.dissonance_threshold == 0.8


@pytest.mark.slow
class TestLongRunningIntegration:
    """Long-running integration tests (marked as slow)."""

    @patch('cognitive_dissonance.experiment.GEPAOptimizer')
    def test_multi_round_experiment(self, mock_gepa):
        """Test multi-round experiment."""
        config = ExperimentConfig(rounds=3)

        # Setup mock optimizer
        mock_optimizer = Mock()
        mock_compiled = Mock()
        mock_compiled.return_value = dspy.Prediction(
            has_dissonance="yes",
            reconciled="test",
            claim1="c1",
            claim2="c2",
            confidence1="high",
            confidence2="low"
        )
        mock_optimizer.compile = Mock(return_value=mock_compiled)
        mock_gepa.return_value = mock_optimizer

        with patch('dspy.configure'):
            with patch('dspy.configure_cache', create=True):
                with patch('dspy.LM'):
                    results = cognitive_dissonance_experiment(config)

        assert len(results.rounds) == 3

        # Check progression
        for i in range(1, 3):
            assert results.rounds[i]["round"] == i + 1
