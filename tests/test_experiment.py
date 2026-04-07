"""Tests for experiment module."""

import pytest
from unittest.mock import Mock, patch
import dspy
from cognitive_dissonance.experiment import (
    ExperimentResults,
    cognitive_dissonance_experiment,
    run_ablation_study,
    run_confidence_analysis
)


class TestExperimentResults:
    """Test ExperimentResults class."""
    
    def test_initialization(self):
        """Test initialization of results container."""
        results = ExperimentResults()
        
        assert results.rounds == []
        assert results.agent_a is None
        assert results.agent_b is None
        assert results.error_analysis == {}
    
    def test_add_round(self):
        """Test adding round results."""
        results = ExperimentResults()
        
        results.add_round(
            round_num=1,
            acc_a=0.8,
            acc_b=0.75,
            agree_dev=0.9,
            agree_train=0.85,
            reconciliation_quality=0.7
        )
        
        assert len(results.rounds) == 1
        assert results.rounds[0]["round"] == 1
        assert results.rounds[0]["accuracy_a"] == 0.8
        assert results.rounds[0]["accuracy_b"] == 0.75
        assert results.rounds[0]["agreement_dev"] == 0.9
        assert results.rounds[0]["agreement_train"] == 0.85
        assert results.rounds[0]["reconciliation_quality"] == 0.7
    
    def test_get_final_accuracies(self):
        """Test getting final accuracies."""
        results = ExperimentResults()
        
        # Empty results
        acc_a, acc_b = results.get_final_accuracies()
        assert acc_a == 0.0
        assert acc_b == 0.0
        
        # Add rounds
        results.add_round(1, 0.6, 0.5, 0.7, 0.65)
        results.add_round(2, 0.8, 0.75, 0.85, 0.8)
        
        acc_a, acc_b = results.get_final_accuracies()
        assert acc_a == 0.8
        assert acc_b == 0.75
    
    def test_get_final_agreement(self):
        """Test getting final agreement."""
        results = ExperimentResults()
        
        # Empty results
        assert results.get_final_agreement() == 0.0
        
        # Add rounds
        results.add_round(1, 0.6, 0.5, 0.7, 0.65)
        results.add_round(2, 0.8, 0.75, 0.85, 0.8)
        
        assert results.get_final_agreement() == 0.85
    
    def test_get_final_reconciliation(self):
        """Test getting final reconciliation quality."""
        results = ExperimentResults()
        
        # Empty results
        assert results.get_final_reconciliation() == 0.0
        
        # Add rounds
        results.add_round(1, 0.6, 0.5, 0.7, 0.65, reconciliation_quality=0.6)
        results.add_round(2, 0.8, 0.75, 0.85, 0.8, reconciliation_quality=0.9)
        
        assert results.get_final_reconciliation() == 0.9
    
    def test_summary(self):
        """Test generating summary."""
        results = ExperimentResults()
        
        # Empty summary
        summary = results.summary()
        assert summary["total_rounds"] == 0
        
        # Add data
        results.add_round(1, 0.6, 0.5, 0.7, 0.65, 0.55)
        results.add_round(2, 0.8, 0.75, 0.85, 0.8, 0.7)
        results.add_round(3, 0.75, 0.8, 0.9, 0.85, 0.8)
        results.error_analysis = {"error_rate": 0.1}
        
        summary = results.summary()
        
        assert summary["total_rounds"] == 3
        assert summary["final_accuracy_a"] == 0.75
        assert summary["final_accuracy_b"] == 0.8
        assert summary["final_agreement"] == 0.9
        assert summary["final_reconciliation"] == 0.8
        assert summary["max_accuracy_a"] == 0.8
        assert summary["max_accuracy_b"] == 0.8
        assert summary["max_agreement"] == 0.9
        assert summary["error_analysis"]["error_rate"] == 0.1


class TestCognitiveDissonanceExperiment:
    """Test main experiment function."""
    
    @patch('cognitive_dissonance.experiment.get_dev_labeled')
    @patch('cognitive_dissonance.experiment.get_train_unlabeled')
    @patch('cognitive_dissonance.experiment.GEPAOptimizer')
    def test_basic_experiment(self, mock_gepa, mock_train, mock_dev, mock_config):
        """Test basic experiment execution."""
        # Setup mock data
        mock_dev.return_value = [
            dspy.Example(
                text1="t1", text2="t2",
                has_dissonance="yes",
                reconciled="r1"
            ).with_inputs("text1", "text2")
        ]
        mock_train.return_value = [
            dspy.Example(text1="t3", text2="t4").with_inputs("text1", "text2")
        ]
        
        # Setup mock optimizer
        mock_optimizer = Mock()
        mock_optimizer.compile = Mock(return_value=Mock())
        mock_gepa.return_value = mock_optimizer
        
        # Configure for minimal rounds
        mock_config.rounds = 1
        mock_config.validate = Mock()
        mock_config.setup_dspy = Mock()
        
        # Run experiment
        with patch('cognitive_dissonance.experiment.evaluate', return_value=0.8):
            with patch('cognitive_dissonance.experiment.agreement_rate', return_value=0.9):
                with patch('cognitive_dissonance.experiment.analyze_errors', return_value={}):
                    results = cognitive_dissonance_experiment(mock_config)
        
        assert isinstance(results, ExperimentResults)
        assert len(results.rounds) == 1
        assert results.agent_a is not None
        assert results.agent_b is not None
    
    @patch('cognitive_dissonance.experiment.ExperimentConfig')
    def test_experiment_from_env(self, mock_config_class):
        """Test experiment loading config from environment."""
        mock_config = Mock()
        mock_config.rounds = 0  # Will cause early exit
        mock_config.validate = Mock()
        mock_config.setup_dspy = Mock()
        mock_config_class.from_env.return_value = mock_config
        
        with patch('cognitive_dissonance.experiment.get_dev_labeled', return_value=[]):
            with patch('cognitive_dissonance.experiment.get_train_unlabeled', return_value=[]):
                with pytest.raises(ValueError):  # Empty dataset should raise
                    cognitive_dissonance_experiment()
    
    def test_experiment_with_overrides(self, mock_config):
        """Test experiment with parameter overrides."""
        mock_config.validate = Mock()
        mock_config.setup_dspy = Mock()
        
        with patch('cognitive_dissonance.experiment.get_dev_labeled', return_value=[]):
            with patch('cognitive_dissonance.experiment.get_train_unlabeled', return_value=[]):
                with pytest.raises(ValueError):  # Empty dataset
                    cognitive_dissonance_experiment(
                        config=mock_config,
                        rounds=3,
                        use_cot=True,
                        alpha_anchor=0.5
                    )
        
        assert mock_config.rounds == 3
        assert mock_config.use_cot is True
        assert mock_config.alpha == 0.5


class TestAblationStudy:
    """Test ablation study function."""
    
    @patch('cognitive_dissonance.experiment.cognitive_dissonance_experiment')
    def test_run_ablation_study(self, mock_experiment, mock_config):
        """Test running ablation study."""
        # Setup mock experiment results
        mock_results = ExperimentResults()
        mock_results.add_round(1, 0.8, 0.75, 0.85, 0.8, 0.7)
        mock_experiment.return_value = mock_results
        
        results = run_ablation_study(mock_config)
        
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # Check that different configurations were tested
        assert "baseline" in results
        assert "with_cot" in results
        assert "alpha_0.1" in results
        assert "alpha_0.5" in results
        
        # Verify experiment was called multiple times
        assert mock_experiment.call_count == len(results)
    
    @patch('cognitive_dissonance.experiment.cognitive_dissonance_experiment')
    def test_ablation_study_handles_failures(self, mock_experiment, mock_config):
        """Test ablation study handles experiment failures."""
        # Make some experiments fail
        mock_experiment.side_effect = [
            ExperimentResults(),  # Success
            ValueError("Failed"),  # Failure
            ExperimentResults(),  # Success
        ]
        
        results = run_ablation_study(mock_config)
        
        # Should still return results, with None for failures
        assert any(r is None for r in results.values())
        assert any(r is not None for r in results.values())


class TestConfidenceAnalysis:
    """Test confidence analysis function."""
    
    @patch('cognitive_dissonance.experiment.get_dev_labeled')
    @patch('cognitive_dissonance.experiment.BootstrapFewShot')
    @patch('cognitive_dissonance.experiment.evaluate')
    def test_run_confidence_analysis(
        self, mock_evaluate, mock_bootstrap, mock_dev, mock_config
    ):
        """Test running confidence analysis."""
        # Setup mock data
        mock_dev.return_value = [
            dspy.Example(
                text1="t1", text2="t2",
                has_dissonance="yes",
                reconciled="r1"
            ).with_inputs("text1", "text2")
        ]
        
        # Setup mock optimizer
        mock_optimizer = Mock()
        mock_optimizer.compile = Mock(return_value=Mock())
        mock_bootstrap.return_value = mock_optimizer
        
        # Setup mock evaluation
        mock_evaluate.side_effect = [0.7, 0.8, 0.75]
        
        mock_config.validate = Mock()
        mock_config.setup_dspy = Mock()
        
        results = run_confidence_analysis(mock_config)
        
        assert isinstance(results, dict)
        assert "accuracy_without_confidence" in results
        assert "accuracy_with_confidence" in results
        assert "confidence_weighted_accuracy" in results
        assert "improvement" in results
        
        assert results["accuracy_without_confidence"] == 0.7
        assert results["accuracy_with_confidence"] == 0.8
        assert results["confidence_weighted_accuracy"] == 0.75
        assert abs(results["improvement"] - 0.1) < 0.0001  # Use approximate equality
    
    @patch('cognitive_dissonance.experiment.ExperimentConfig')
    def test_confidence_analysis_from_env(self, mock_config_class):
        """Test confidence analysis loading config from environment."""
        mock_config = Mock()
        mock_config.validate = Mock()
        mock_config.setup_dspy = Mock()
        mock_config_class.from_env.return_value = mock_config
        
        with patch('cognitive_dissonance.experiment.get_dev_labeled', return_value=[]):
            with patch('cognitive_dissonance.experiment.BootstrapFewShot'):
                with patch('cognitive_dissonance.experiment.evaluate', return_value=0.5):
                    results = run_confidence_analysis()
        
        assert isinstance(results, dict)