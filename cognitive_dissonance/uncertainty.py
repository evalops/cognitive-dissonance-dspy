"""Advanced uncertainty quantification and confidence scoring for cognitive dissonance detection."""

import logging
import math
from typing import Any

import dspy
import numpy as np

logger = logging.getLogger(__name__)


class UncertaintyQuantifier:
    """
    Advanced uncertainty quantification for belief and dissonance detection.
    Separates epistemic (model) uncertainty from aleatoric (data) uncertainty.
    """

    def __init__(self,
                 calibration_samples: int = 100,
                 confidence_bins: int = 10):
        """
        Initialize uncertainty quantifier.

        Args:
            calibration_samples: Number of samples for calibration
            confidence_bins: Number of bins for confidence calibration
        """
        self.calibration_samples = calibration_samples
        self.confidence_bins = confidence_bins
        self.calibration_data = []
        self.is_calibrated = False
        logger.debug(f"Initialized uncertainty quantifier with {confidence_bins} bins")

    def compute_uncertainty(self,
                          prediction: dspy.Prediction,
                          context: dict | None = None) -> dict[str, float]:
        """
        Compute multiple types of uncertainty for a prediction.

        Args:
            prediction: DSPy prediction to analyze
            context: Additional context for uncertainty computation

        Returns:
            Dictionary with different uncertainty measures
        """
        uncertainty = {
            'epistemic': self._compute_epistemic_uncertainty(prediction, context),
            'aleatoric': self._compute_aleatoric_uncertainty(prediction, context),
            'total': 0.0,
            'confidence_score': self._compute_confidence_score(prediction),
            'calibrated_confidence': 0.0
        }

        # Total uncertainty (combine epistemic and aleatoric)
        uncertainty['total'] = math.sqrt(
            uncertainty['epistemic']**2 + uncertainty['aleatoric']**2
        )

        # Apply calibration if available
        if self.is_calibrated:
            uncertainty['calibrated_confidence'] = self._apply_calibration(
                uncertainty['confidence_score']
            )
        else:
            uncertainty['calibrated_confidence'] = uncertainty['confidence_score']

        return uncertainty

    def _compute_epistemic_uncertainty(self,
                                     prediction: dspy.Prediction,
                                     context: dict | None = None) -> float:
        """
        Compute epistemic (model) uncertainty.
        This represents uncertainty about the model's knowledge.
        """
        # Factors that increase epistemic uncertainty
        factors = []

        # 1. Prediction consistency
        has_dissonance = getattr(prediction, 'has_dissonance', 'no')
        reconciled = getattr(prediction, 'reconciled', '')

        # Check for contradictory outputs
        if has_dissonance == 'yes' and not reconciled:
            factors.append(0.3)  # High uncertainty if dissonance detected but no reconciliation

        # 2. Response length and detail
        reconciliation_length = len(reconciled.split()) if reconciled else 0
        if reconciliation_length < 3:
            factors.append(0.2)  # Higher uncertainty for very short responses
        elif reconciliation_length > 50:
            factors.append(0.1)  # Slight uncertainty for very long responses

        # 3. Ensemble disagreement (if available)
        if hasattr(prediction, 'ensemble_confidence'):
            ensemble_disagreement = 1.0 - prediction.ensemble_confidence
            factors.append(ensemble_disagreement * 0.4)

        # 4. Context-based uncertainty
        if context:
            domain_familiarity = context.get('domain_familiarity', 0.8)
            factors.append((1.0 - domain_familiarity) * 0.2)

        # Combine factors (max to avoid over-accumulation)
        epistemic = min(sum(factors), 0.9)
        return epistemic

    def _compute_aleatoric_uncertainty(self,
                                     prediction: dspy.Prediction,
                                     context: dict | None = None) -> float:
        """
        Compute aleatoric (data) uncertainty.
        This represents inherent uncertainty in the data/task.
        """
        factors = []

        # 1. Task complexity indicators
        has_dissonance = getattr(prediction, 'has_dissonance', 'no')
        if has_dissonance == 'yes':
            factors.append(0.2)  # Dissonance cases are inherently more uncertain

        # 2. Input complexity (if available in context)
        if context:
            input_complexity = context.get('input_complexity', 0.5)
            factors.append(input_complexity * 0.3)

            # Ambiguous or contradictory inputs
            ambiguity_score = context.get('ambiguity_score', 0.0)
            factors.append(ambiguity_score * 0.4)

        # 3. Domain-specific uncertainty
        reconciled = getattr(prediction, 'reconciled', '')
        if reconciled:
            # Check for hedge words that indicate inherent uncertainty
            hedge_words = ['might', 'could', 'possibly', 'perhaps', 'may be', 'unclear']
            hedge_count = sum(1 for word in hedge_words if word in reconciled.lower())
            if hedge_count > 0:
                factors.append(min(hedge_count * 0.1, 0.3))

        aleatoric = min(sum(factors), 0.8)
        return aleatoric

    def _compute_confidence_score(self, prediction: dspy.Prediction) -> float:
        """
        Compute overall confidence score for the prediction.

        Args:
            prediction: DSPy prediction

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence_factors = []

        # 1. Basic confidence from prediction
        if hasattr(prediction, 'confidence1') and hasattr(prediction, 'confidence2'):
            conf1 = self._normalize_confidence(prediction.confidence1)
            conf2 = self._normalize_confidence(prediction.confidence2)
            confidence_factors.append((conf1 + conf2) / 2)

        # 2. Consistency indicators
        has_dissonance = getattr(prediction, 'has_dissonance', 'no')
        reconciled = getattr(prediction, 'reconciled', '')

        if has_dissonance == 'yes' and reconciled:
            confidence_factors.append(0.7)  # Good consistency
        elif has_dissonance == 'no':
            confidence_factors.append(0.8)  # No dissonance detected
        else:
            confidence_factors.append(0.4)  # Inconsistent state

        # 3. Ensemble agreement (if available)
        if hasattr(prediction, 'ensemble_confidence'):
            confidence_factors.append(prediction.ensemble_confidence)

        # 4. Response quality indicators
        if reconciled:
            # Length-based heuristic (not too short, not too long)
            length = len(reconciled.split())
            if 5 <= length <= 30:
                confidence_factors.append(0.8)
            elif 3 <= length <= 50:
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.4)

        # Weighted average (recent factors get higher weight)
        if confidence_factors:
            weights = [1.2**i for i in range(len(confidence_factors))]
            weighted_sum = sum(
                cf * w
                for cf, w in zip(confidence_factors, weights, strict=True)
            )
            total_weight = sum(weights)
            return min(weighted_sum / total_weight, 1.0)

        return 0.5  # Default moderate confidence

    def _normalize_confidence(self, confidence: str) -> float:
        """Normalize string confidence to numeric value."""
        conf_map = {
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3,
            'very_high': 0.95,
            'very_low': 0.1
        }
        return conf_map.get(confidence.lower(), 0.5)

    def calibrate(self, predictions: list[dspy.Prediction], ground_truth: list[bool]):
        """
        Calibrate confidence scores using ground truth data.

        Args:
            predictions: List of predictions with confidence scores
            ground_truth: List of ground truth correctness (True/False)
        """
        if len(predictions) != len(ground_truth):
            logger.warning("Predictions and ground truth lengths don't match")
            return

        logger.info(f"Calibrating uncertainty quantifier with {len(predictions)} samples")

        # Collect calibration data
        self.calibration_data = []
        for pred, correct in zip(predictions, ground_truth, strict=True):
            uncertainty = self.compute_uncertainty(pred)
            self.calibration_data.append({
                'confidence': uncertainty['confidence_score'],
                'correct': correct
            })

        # Compute calibration curve
        self.calibration_curve = self._compute_calibration_curve()
        self.is_calibrated = True

        logger.info("Calibration complete")

    def _compute_calibration_curve(self) -> list[tuple[float, float]]:
        """Compute calibration curve from calibration data."""
        if not self.calibration_data:
            return []

        # Sort by confidence
        sorted_data = sorted(self.calibration_data, key=lambda x: x['confidence'])

        # Create bins
        bin_size = len(sorted_data) // self.confidence_bins
        calibration_curve = []

        for i in range(self.confidence_bins):
            start_idx = i * bin_size
            end_idx = start_idx + bin_size if i < self.confidence_bins - 1 else len(sorted_data)

            bin_data = sorted_data[start_idx:end_idx]
            if not bin_data:
                continue

            avg_confidence = sum(d['confidence'] for d in bin_data) / len(bin_data)
            accuracy = sum(d['correct'] for d in bin_data) / len(bin_data)

            calibration_curve.append((avg_confidence, accuracy))

        return calibration_curve

    def _apply_calibration(self, raw_confidence: float) -> float:
        """Apply calibration to raw confidence score."""
        if not hasattr(self, 'calibration_curve') or not self.calibration_curve:
            return raw_confidence

        # Find closest calibration point
        closest_point = min(self.calibration_curve,
                          key=lambda x: abs(x[0] - raw_confidence))

        # Simple linear interpolation (could be improved)
        return closest_point[1]

    def get_calibration_metrics(self) -> dict[str, float]:
        """Get calibration quality metrics."""
        if not self.is_calibrated:
            return {'calibration_error': float('inf')}

        # Expected Calibration Error (ECE)
        ece = 0.0
        total_samples = len(self.calibration_data)

        for conf, acc in self.calibration_curve:
            # Find samples in this bin
            bin_samples = [d for d in self.calibration_data
                          if abs(d['confidence'] - conf) < (1.0 / self.confidence_bins)]

            if bin_samples:
                weight = len(bin_samples) / total_samples
                ece += weight * abs(conf - acc)

        return {
            'calibration_error': ece,
            'num_calibration_samples': total_samples
        }


class EnhancedConfidenceScorer:
    """
    Enhanced confidence scoring system that integrates uncertainty quantification.
    """

    def __init__(self, uncertainty_quantifier: UncertaintyQuantifier | None = None):
        """
        Initialize enhanced confidence scorer.

        Args:
            uncertainty_quantifier: Optional uncertainty quantifier instance
        """
        self.uncertainty_quantifier = uncertainty_quantifier or UncertaintyQuantifier()
        logger.debug("Initialized enhanced confidence scorer")

    def score_prediction(self,
                        prediction: dspy.Prediction,
                        context: dict | None = None) -> dict[str, float]:
        """
        Compute comprehensive confidence scoring for a prediction.

        Args:
            prediction: DSPy prediction to score
            context: Additional context information

        Returns:
            Dictionary with various confidence measures
        """
        # Get uncertainty measures
        uncertainty = self.uncertainty_quantifier.compute_uncertainty(prediction, context)

        # Compute additional confidence measures
        confidence_scores = {
            'raw_confidence': uncertainty['confidence_score'],
            'calibrated_confidence': uncertainty['calibrated_confidence'],
            'uncertainty_adjusted_confidence': max(0.0, uncertainty['confidence_score'] - uncertainty['total']),
            'epistemic_uncertainty': uncertainty['epistemic'],
            'aleatoric_uncertainty': uncertainty['aleatoric'],
            'total_uncertainty': uncertainty['total'],
            'confidence_category': self._categorize_confidence(uncertainty['calibrated_confidence']),
            'reliability_score': self._compute_reliability_score(prediction, uncertainty)
        }

        return confidence_scores

    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize numeric confidence into descriptive categories."""
        if confidence >= 0.85:
            return 'very_high'
        elif confidence >= 0.7:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        elif confidence >= 0.3:
            return 'low'
        else:
            return 'very_low'

    def _compute_reliability_score(self,
                                 prediction: dspy.Prediction,
                                 uncertainty: dict[str, float]) -> float:
        """
        Compute overall reliability score combining confidence and uncertainty.

        Args:
            prediction: DSPy prediction
            uncertainty: Uncertainty measures

        Returns:
            Reliability score between 0.0 and 1.0
        """
        # Base reliability from calibrated confidence
        base_reliability = uncertainty['calibrated_confidence']

        # Reduce reliability based on total uncertainty
        uncertainty_penalty = uncertainty['total'] * 0.5

        # Boost reliability for consistent predictions
        consistency_bonus = 0.0
        has_dissonance = getattr(prediction, 'has_dissonance', 'no')
        reconciled = getattr(prediction, 'reconciled', '')

        if has_dissonance == 'yes' and reconciled:
            consistency_bonus = 0.1  # Bonus for consistent dissonance + reconciliation
        elif has_dissonance == 'no':
            consistency_bonus = 0.05  # Small bonus for clear no-dissonance

        # Ensemble agreement bonus (if available)
        ensemble_bonus = 0.0
        if hasattr(prediction, 'ensemble_confidence'):
            ensemble_bonus = (prediction.ensemble_confidence - 0.5) * 0.2

        reliability = base_reliability - uncertainty_penalty + consistency_bonus + ensemble_bonus
        return max(0.0, min(1.0, reliability))

    def calibrate_scorer(self, predictions: list[dspy.Prediction], ground_truth: list[bool]):
        """
        Calibrate the confidence scorer using ground truth data.

        Args:
            predictions: List of predictions
            ground_truth: List of ground truth correctness
        """
        self.uncertainty_quantifier.calibrate(predictions, ground_truth)
        logger.info("Confidence scorer calibration complete")

    def get_scoring_summary(self, predictions: list[dspy.Prediction]) -> dict[str, Any]:
        """
        Get summary statistics for a set of predictions.

        Args:
            predictions: List of predictions to analyze

        Returns:
            Summary statistics
        """
        if not predictions:
            return {}

        all_scores = [self.score_prediction(pred) for pred in predictions]

        # Aggregate statistics
        summary = {
            'num_predictions': len(predictions),
            'avg_confidence': np.mean([s['calibrated_confidence'] for s in all_scores]),
            'avg_uncertainty': np.mean([s['total_uncertainty'] for s in all_scores]),
            'avg_reliability': np.mean([s['reliability_score'] for s in all_scores]),
            'confidence_distribution': self._compute_confidence_distribution(all_scores),
            'high_confidence_predictions': sum(1 for s in all_scores if s['confidence_category'] in ['high', 'very_high']),
            'low_confidence_predictions': sum(1 for s in all_scores if s['confidence_category'] in ['low', 'very_low'])
        }

        return summary

    def _compute_confidence_distribution(self, scores: list[dict[str, float]]) -> dict[str, int]:
        """Compute distribution of confidence categories."""
        distribution = {
            'very_high': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'very_low': 0
        }

        for score in scores:
            category = score['confidence_category']
            distribution[category] += 1

        return distribution
