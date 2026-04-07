"""Tests for uncertainty module."""

import dspy
from cognitive_dissonance.uncertainty import (
    UncertaintyQuantifier,
    EnhancedConfidenceScorer
)


class TestUncertaintyQuantifier:
    """Test uncertainty quantifier."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        quantifier = UncertaintyQuantifier()
        assert quantifier.calibration_samples == 100
        assert quantifier.confidence_bins == 10
        assert quantifier.calibration_data == []
        assert quantifier.is_calibrated is False
    
    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        quantifier = UncertaintyQuantifier(calibration_samples=50, confidence_bins=5)
        assert quantifier.calibration_samples == 50
        assert quantifier.confidence_bins == 5
    
    def test_compute_uncertainty(self):
        """Test uncertainty computation."""
        quantifier = UncertaintyQuantifier()
        
        # Create mock prediction
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "This is a reconciliation"
        prediction.confidence1 = "high"
        prediction.confidence2 = "medium"
        
        uncertainty = quantifier.compute_uncertainty(prediction)
        
        assert isinstance(uncertainty, dict)
        assert 'epistemic' in uncertainty
        assert 'aleatoric' in uncertainty
        assert 'total' in uncertainty
        assert 'confidence_score' in uncertainty
        assert 'calibrated_confidence' in uncertainty
        
        # Check value ranges
        assert 0.0 <= uncertainty['epistemic'] <= 1.0
        assert 0.0 <= uncertainty['aleatoric'] <= 1.0
        assert 0.0 <= uncertainty['total'] <= 1.0
        assert 0.0 <= uncertainty['confidence_score'] <= 1.0
        assert 0.0 <= uncertainty['calibrated_confidence'] <= 1.0
    
    def test_compute_uncertainty_with_context(self):
        """Test uncertainty computation with context."""
        quantifier = UncertaintyQuantifier()
        
        prediction = dspy.Prediction()
        prediction.has_dissonance = "no"
        prediction.reconciled = ""
        
        context = {
            'domain_familiarity': 0.9,
            'input_complexity': 0.3,
            'ambiguity_score': 0.1
        }
        
        uncertainty = quantifier.compute_uncertainty(prediction, context)
        
        assert isinstance(uncertainty, dict)
        assert all(key in uncertainty for key in ['epistemic', 'aleatoric', 'total', 'confidence_score', 'calibrated_confidence'])
    
    def test_compute_epistemic_uncertainty(self):
        """Test epistemic uncertainty computation."""
        quantifier = UncertaintyQuantifier()
        
        # High uncertainty case
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = ""  # No reconciliation
        
        epistemic = quantifier._compute_epistemic_uncertainty(prediction)
        assert epistemic > 0.0
        
        # Low uncertainty case
        prediction2 = dspy.Prediction()
        prediction2.has_dissonance = "no"
        prediction2.reconciled = "A good reconciliation here"
        
        epistemic2 = quantifier._compute_epistemic_uncertainty(prediction2)
        assert epistemic2 < epistemic  # Should be lower uncertainty
    
    def test_compute_aleatoric_uncertainty(self):
        """Test aleatoric uncertainty computation."""
        quantifier = UncertaintyQuantifier()
        
        # High uncertainty case
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "This might be unclear and possibly wrong"
        
        aleatoric = quantifier._compute_aleatoric_uncertainty(prediction)
        assert aleatoric > 0.0
        
        # Low uncertainty case
        prediction2 = dspy.Prediction()
        prediction2.has_dissonance = "no"
        prediction2.reconciled = "Clear and definitive answer"
        
        aleatoric2 = quantifier._compute_aleatoric_uncertainty(prediction2)
        assert aleatoric2 <= aleatoric
    
    def test_normalize_confidence(self):
        """Test confidence normalization."""
        quantifier = UncertaintyQuantifier()
        
        assert quantifier._normalize_confidence("high") == 0.9
        assert quantifier._normalize_confidence("medium") == 0.6
        assert quantifier._normalize_confidence("low") == 0.3
        assert quantifier._normalize_confidence("very_high") == 0.95
        assert quantifier._normalize_confidence("very_low") == 0.1
        assert quantifier._normalize_confidence("unknown") == 0.5
    
    def test_compute_confidence_score(self):
        """Test confidence score computation."""
        quantifier = UncertaintyQuantifier()
        
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "Good reconciliation"
        prediction.confidence1 = "high"
        prediction.confidence2 = "high"
        
        confidence = quantifier._compute_confidence_score(prediction)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be high with high confidence inputs
    
    def test_calibrate(self):
        """Test calibration process."""
        quantifier = UncertaintyQuantifier()
        
        # Create mock predictions and ground truth
        predictions = []
        ground_truth = []
        
        for i in range(10):
            pred = dspy.Prediction()
            pred.has_dissonance = "yes" if i % 2 == 0 else "no"
            pred.reconciled = f"Reconciliation {i}"
            pred.confidence1 = "high" if i < 5 else "low"
            pred.confidence2 = "medium"
            predictions.append(pred)
            ground_truth.append(i % 2 == 0)  # True for even indices
        
        quantifier.calibrate(predictions, ground_truth)
        
        assert quantifier.is_calibrated is True
        assert len(quantifier.calibration_data) == 10
        assert hasattr(quantifier, 'calibration_curve')
    
    def test_calibrate_mismatched_lengths(self):
        """Test calibration with mismatched lengths."""
        quantifier = UncertaintyQuantifier()
        
        predictions = [dspy.Prediction()]
        ground_truth = [True, False]  # Different length
        
        quantifier.calibrate(predictions, ground_truth)
        
        assert quantifier.is_calibrated is False  # Should not calibrate
    
    def test_get_calibration_metrics_uncalibrated(self):
        """Test calibration metrics for uncalibrated quantifier."""
        quantifier = UncertaintyQuantifier()
        
        metrics = quantifier.get_calibration_metrics()
        
        assert 'calibration_error' in metrics
        assert metrics['calibration_error'] == float('inf')
    
    def test_get_calibration_metrics_calibrated(self):
        """Test calibration metrics for calibrated quantifier."""
        quantifier = UncertaintyQuantifier()
        
        # Simple calibration
        predictions = [dspy.Prediction() for _ in range(5)]
        for pred in predictions:
            pred.confidence1 = "high"
            pred.confidence2 = "high"
            pred.has_dissonance = "no"
            pred.reconciled = "Good"
        
        ground_truth = [True] * 5
        
        quantifier.calibrate(predictions, ground_truth)
        metrics = quantifier.get_calibration_metrics()
        
        assert 'calibration_error' in metrics
        assert 'num_calibration_samples' in metrics
        assert isinstance(metrics['calibration_error'], float)
        assert metrics['num_calibration_samples'] == 5


class TestEnhancedConfidenceScorer:
    """Test enhanced confidence scorer."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        scorer = EnhancedConfidenceScorer()
        assert hasattr(scorer, 'uncertainty_quantifier')
        assert isinstance(scorer.uncertainty_quantifier, UncertaintyQuantifier)
    
    def test_initialization_custom(self):
        """Test initialization with custom quantifier."""
        quantifier = UncertaintyQuantifier(calibration_samples=50)
        scorer = EnhancedConfidenceScorer(quantifier)
        assert scorer.uncertainty_quantifier == quantifier
    
    def test_score_prediction(self):
        """Test prediction scoring."""
        scorer = EnhancedConfidenceScorer()
        
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "Reconciliation text"
        prediction.confidence1 = "high"
        prediction.confidence2 = "medium"
        
        scores = scorer.score_prediction(prediction)
        
        assert isinstance(scores, dict)
        expected_keys = [
            'raw_confidence', 'calibrated_confidence', 'uncertainty_adjusted_confidence',
            'epistemic_uncertainty', 'aleatoric_uncertainty', 'total_uncertainty',
            'confidence_category', 'reliability_score'
        ]
        
        for key in expected_keys:
            assert key in scores
        
        # Check value ranges
        assert 0.0 <= scores['raw_confidence'] <= 1.0
        assert 0.0 <= scores['calibrated_confidence'] <= 1.0
        assert 0.0 <= scores['uncertainty_adjusted_confidence'] <= 1.0
        assert scores['confidence_category'] in ['very_low', 'low', 'medium', 'high', 'very_high']
    
    def test_categorize_confidence(self):
        """Test confidence categorization."""
        scorer = EnhancedConfidenceScorer()
        
        assert scorer._categorize_confidence(0.95) == 'very_high'
        assert scorer._categorize_confidence(0.8) == 'high'
        assert scorer._categorize_confidence(0.6) == 'medium'
        assert scorer._categorize_confidence(0.4) == 'low'
        assert scorer._categorize_confidence(0.1) == 'very_low'
    
    def test_compute_reliability_score(self):
        """Test reliability score computation."""
        scorer = EnhancedConfidenceScorer()
        
        prediction = dspy.Prediction()
        prediction.has_dissonance = "yes"
        prediction.reconciled = "Good reconciliation"
        
        uncertainty = {
            'calibrated_confidence': 0.8,
            'total': 0.2
        }
        
        reliability = scorer._compute_reliability_score(prediction, uncertainty)
        
        assert 0.0 <= reliability <= 1.0
        assert isinstance(reliability, float)
    
    def test_calibrate_scorer(self):
        """Test scorer calibration."""
        scorer = EnhancedConfidenceScorer()
        
        predictions = []
        ground_truth = []
        
        for i in range(5):
            pred = dspy.Prediction()
            pred.has_dissonance = "yes" if i % 2 == 0 else "no"
            pred.confidence1 = "high"
            pred.confidence2 = "medium"
            predictions.append(pred)
            ground_truth.append(i % 2 == 0)
        
        scorer.calibrate_scorer(predictions, ground_truth)
        
        assert scorer.uncertainty_quantifier.is_calibrated is True
    
    def test_get_scoring_summary_empty(self):
        """Test scoring summary with empty predictions."""
        scorer = EnhancedConfidenceScorer()
        
        summary = scorer.get_scoring_summary([])
        
        assert summary == {}
    
    def test_get_scoring_summary(self):
        """Test scoring summary with predictions."""
        scorer = EnhancedConfidenceScorer()
        
        predictions = []
        for i in range(5):
            pred = dspy.Prediction()
            pred.has_dissonance = "yes" if i % 2 == 0 else "no"
            pred.reconciled = f"Reconciliation {i}"
            pred.confidence1 = "high" if i < 3 else "low"
            pred.confidence2 = "medium"
            predictions.append(pred)
        
        summary = scorer.get_scoring_summary(predictions)
        
        assert isinstance(summary, dict)
        expected_keys = [
            'num_predictions', 'avg_confidence', 'avg_uncertainty', 'avg_reliability',
            'confidence_distribution', 'high_confidence_predictions', 'low_confidence_predictions'
        ]
        
        for key in expected_keys:
            assert key in summary
        
        assert summary['num_predictions'] == 5
        assert isinstance(summary['confidence_distribution'], dict)
    
    def test_compute_confidence_distribution(self):
        """Test confidence distribution computation."""
        scorer = EnhancedConfidenceScorer()
        
        scores = [
            {'confidence_category': 'high'},
            {'confidence_category': 'high'},
            {'confidence_category': 'medium'},
            {'confidence_category': 'low'},
            {'confidence_category': 'very_low'}
        ]
        
        distribution = scorer._compute_confidence_distribution(scores)
        
        assert isinstance(distribution, dict)
        assert distribution['high'] == 2
        assert distribution['medium'] == 1
        assert distribution['low'] == 1
        assert distribution['very_low'] == 1
        assert distribution['very_high'] == 0