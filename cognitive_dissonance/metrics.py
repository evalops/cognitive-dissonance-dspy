"""Metrics for evaluating cognitive dissonance detection and resolution."""

import logging
from collections.abc import Callable

import dspy

logger = logging.getLogger(__name__)


def dissonance_detection_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Measure accuracy of dissonance detection.

    Args:
        example: Ground truth example
        prediction: Model prediction

    Returns:
        1.0 if correct, 0.0 otherwise
    """
    try:
        ground_truth = getattr(example, "has_dissonance", "no").strip().lower()
        predicted = (prediction.has_dissonance or "no").strip().lower()

        # Normalize to yes/no
        if "yes" in predicted and "no" not in predicted:
            predicted = "yes"
        elif "no" in predicted:
            predicted = "no"

        score = 1.0 if ground_truth == predicted else 0.0
        logger.debug(f"Dissonance accuracy: truth={ground_truth}, pred={predicted}, score={score}")
        return score

    except Exception as e:
        logger.warning(f"Error in dissonance_detection_accuracy: {e}")
        return 0.0


def reconciliation_quality(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Measure quality of belief reconciliation.

    Args:
        example: Ground truth example with reconciled claim
        prediction: Model prediction

    Returns:
        Score between 0.0 and 1.0 based on similarity
    """
    try:
        ground_truth = getattr(example, "reconciled", "").strip().lower()
        predicted = (prediction.reconciled or "").strip().lower()

        if not ground_truth or not predicted:
            return 0.0

        # Simple overlap-based scoring
        truth_words = set(ground_truth.split())
        pred_words = set(predicted.split())

        if not truth_words or not pred_words:
            return 0.0

        overlap = len(truth_words & pred_words)
        union = len(truth_words | pred_words)

        score = overlap / union if union > 0 else 0.0
        logger.debug(f"Reconciliation quality: score={score:.3f}")
        return score

    except Exception as e:
        logger.warning(f"Error in reconciliation_quality: {e}")
        return 0.0


def combined_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Combined metric for both detection and reconciliation.

    Args:
        example: Ground truth example
        prediction: Model prediction

    Returns:
        Weighted average of detection and reconciliation scores
    """
    detection_score = dissonance_detection_accuracy(example, prediction)
    reconciliation_score = reconciliation_quality(example, prediction)

    # Weight detection more heavily since it's primary task
    combined = 0.7 * detection_score + 0.3 * reconciliation_score

    logger.debug(f"Combined metric: detection={detection_score:.3f}, "
                f"reconciliation={reconciliation_score:.3f}, combined={combined:.3f}")

    return combined


def agreement_metric_factory(other_agent: dspy.Module) -> Callable:
    """Create a metric that measures agreement with another agent.

    Args:
        other_agent: The other agent to agree with

    Returns:
        Metric function for agreement
    """
    def agreement_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
        """Measure agreement between two agents."""
        try:
            # Get the other agent's prediction
            other_pred = other_agent(text1=example.text1, text2=example.text2)

            # Compare dissonance detection
            this_dissonance = (prediction.has_dissonance or "no").strip().lower()
            other_dissonance = (other_pred.has_dissonance or "no").strip().lower()

            # Normalize
            for pred in [this_dissonance, other_dissonance]:
                if "yes" in pred and "no" not in pred:
                    pred = "yes"
                elif "no" in pred:
                    pred = "no"

            score = 1.0 if this_dissonance == other_dissonance else 0.0
            logger.debug(f"Agreement score: {score} (this={this_dissonance}, other={other_dissonance})")

            return score

        except Exception as e:
            logger.warning(f"Error in agreement_metric: {e}")
            return 0.0

    return agreement_metric


def blended_metric_factory(other_agent: dspy.Module, alpha: float = 0.5) -> Callable:
    """Create a blended metric combining truth and agreement.

    Args:
        other_agent: The other agent for agreement
        alpha: Weight for truth component (1-alpha for agreement)

    Returns:
        Blended metric function
    """
    agreement_fn = agreement_metric_factory(other_agent)

    def blended_metric(example: dspy.Example, prediction: dspy.Prediction) -> float:
        """Blend truth accuracy with agreement."""
        try:
            # Only use truth metric if we have labels
            if hasattr(example, "has_dissonance"):
                truth_score = dissonance_detection_accuracy(example, prediction)
            else:
                # No labels, full weight to agreement
                truth_score = 0.0
                alpha_adj = 0.0

            agreement_score = agreement_fn(example, prediction)

            # Adjust alpha if no labels
            alpha_adj = alpha if hasattr(example, "has_dissonance") else 0.0

            score = alpha_adj * truth_score + (1 - alpha_adj) * agreement_score

            logger.debug(f"Blended metric: truth={truth_score:.3f}, "
                        f"agreement={agreement_score:.3f}, "
                        f"blended={score:.3f} (alpha={alpha_adj})")

            return score

        except Exception as e:
            logger.warning(f"Error in blended_metric: {e}")
            return 0.0

    return blended_metric


def confidence_weighted_accuracy(example: dspy.Example, prediction: dspy.Prediction) -> float:
    """Accuracy weighted by confidence scores.

    Args:
        example: Ground truth example
        prediction: Model prediction with confidence

    Returns:
        Confidence-weighted accuracy score
    """
    try:
        base_accuracy = dissonance_detection_accuracy(example, prediction)

        # Get confidence scores
        conf1 = getattr(prediction, "confidence1", "medium").lower()
        conf2 = getattr(prediction, "confidence2", "medium").lower()

        # Map confidence to weights
        conf_weights = {"high": 1.0, "medium": 0.7, "low": 0.4}

        weight1 = conf_weights.get(conf1, 0.7)
        weight2 = conf_weights.get(conf2, 0.7)

        # Average confidence weight
        avg_confidence = (weight1 + weight2) / 2

        # Apply confidence weighting
        weighted_score = base_accuracy * avg_confidence

        logger.debug(f"Confidence weighted: base={base_accuracy:.3f}, "
                    f"conf={avg_confidence:.3f}, weighted={weighted_score:.3f}")

        return weighted_score

    except Exception as e:
        logger.warning(f"Error in confidence_weighted_accuracy: {e}")
        return 0.0
