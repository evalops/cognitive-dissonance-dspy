"""Evaluation utilities for cognitive dissonance experiments."""

import logging
from collections.abc import Callable

import dspy

logger = logging.getLogger(__name__)


def _normalize_dissonance_label(label: str | None) -> str:
    """Normalize free-form dissonance labels into yes/no."""
    normalized = (label or "no").strip().lower()
    if "yes" in normalized and "no" not in normalized:
        return "yes"
    if "no" in normalized:
        return "no"
    return "no"


def evaluate(
    module: dspy.Module,
    dataset: list[dspy.Example],
    metric: Callable | None = None,
    display_progress: bool = True,
    return_outputs: bool = False
) -> float:
    """Evaluate a module on a dataset.

    Args:
        module: DSPy module to evaluate
        dataset: List of examples to evaluate on
        metric: Optional metric function (defaults to dissonance_detection_accuracy)
        display_progress: Whether to show progress
        return_outputs: Whether to return predictions along with score

    Returns:
        Average score across dataset (and optionally predictions)
    """
    from .metrics import dissonance_detection_accuracy

    if metric is None:
        metric = dissonance_detection_accuracy

    if not dataset:
        logger.warning("Empty dataset provided for evaluation")
        return 0.0 if not return_outputs else (0.0, [])

    scores = []
    outputs = []

    for i, example in enumerate(dataset):
        if display_progress and i % 10 == 0:
            logger.info(f"Evaluating example {i+1}/{len(dataset)}")

        try:
            # Get prediction
            prediction = module(text1=example.text1, text2=example.text2)

            # Calculate score
            score = metric(example, prediction)
            scores.append(score)

            if return_outputs:
                outputs.append(prediction)

            logger.debug(f"Example {i}: score={score:.3f}")

        except Exception as e:
            logger.warning(f"Failed to evaluate example {i}: {e}")
            scores.append(0.0)
            if return_outputs:
                outputs.append(None)

    avg_score = sum(scores) / len(scores) if scores else 0.0

    logger.info(f"Evaluation complete: avg_score={avg_score:.3f} over {len(dataset)} examples")

    if return_outputs:
        return avg_score, outputs
    return avg_score


def agreement_rate(
    agent1: dspy.Module,
    agent2: dspy.Module,
    dataset: list[dspy.Example]
) -> float:
    """Calculate agreement rate between two agents.

    Args:
        agent1: First agent
        agent2: Second agent
        dataset: Examples to evaluate on

    Returns:
        Agreement rate (0.0 to 1.0)
    """
    if not dataset:
        logger.warning("Empty dataset for agreement rate")
        return 0.0

    agreements = 0
    total = 0

    for example in dataset:
        try:
            # Get predictions from both agents
            pred1 = agent1(text1=example.text1, text2=example.text2)
            pred2 = agent2(text1=example.text1, text2=example.text2)

            # Compare dissonance detection
            dissonance1 = _normalize_dissonance_label(getattr(pred1, "has_dissonance", "no"))
            dissonance2 = _normalize_dissonance_label(getattr(pred2, "has_dissonance", "no"))

            if dissonance1 == dissonance2:
                agreements += 1

            total += 1

        except Exception as e:
            logger.warning(f"Failed to compute agreement for example: {e}")
            continue

    rate = agreements / total if total > 0 else 0.0
    logger.info(f"Agreement rate: {rate:.3f} ({agreements}/{total})")

    return rate


def cross_validate(
    module_class: type,
    dataset: list[dspy.Example],
    k_folds: int = 5,
    metric: Callable | None = None,
    **module_kwargs
) -> dict:
    """Perform k-fold cross-validation.

    Args:
        module_class: Class of module to instantiate
        dataset: Full dataset to cross-validate on
        k_folds: Number of folds
        metric: Evaluation metric
        **module_kwargs: Arguments to pass to module constructor

    Returns:
        Dictionary with validation results
    """
    from .metrics import combined_metric

    if metric is None:
        metric = combined_metric

    if len(dataset) < k_folds:
        logger.warning(f"Dataset too small for {k_folds}-fold CV, using leave-one-out")
        k_folds = len(dataset)

    fold_size = len(dataset) // k_folds
    scores = []

    for fold in range(k_folds):
        logger.info(f"Cross-validation fold {fold+1}/{k_folds}")

        # Split data
        val_start = fold * fold_size
        val_end = val_start + fold_size if fold < k_folds - 1 else len(dataset)

        val_data = dataset[val_start:val_end]
        train_data = dataset[:val_start] + dataset[val_end:]

        # Create and train module
        module = module_class(**module_kwargs)

        # Simple training: just warm up with training examples
        for example in train_data[:5]:  # Use first 5 for warmup
            try:
                _ = module(text1=example.text1, text2=example.text2)
            except:
                pass

        # Evaluate on validation set
        fold_score = evaluate(module, val_data, metric=metric, display_progress=False)
        scores.append(fold_score)

        logger.info(f"Fold {fold+1} score: {fold_score:.3f}")

    avg_score = sum(scores) / len(scores)
    std_score = (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5

    results = {
        "avg_score": avg_score,
        "std_score": std_score,
        "fold_scores": scores,
        "k_folds": k_folds
    }

    logger.info(f"Cross-validation complete: {avg_score:.3f} ± {std_score:.3f}")

    return results


def analyze_errors(
    module: dspy.Module,
    dataset: list[dspy.Example],
    metric: Callable | None = None
) -> dict:
    """Analyze errors made by the module.

    Args:
        module: Module to analyze
        dataset: Dataset to evaluate on
        metric: Metric to use

    Returns:
        Dictionary with error analysis
    """
    from .metrics import dissonance_detection_accuracy

    if metric is None:
        metric = dissonance_detection_accuracy

    errors = {
        "false_positives": [],  # Predicted dissonance when there isn't
        "false_negatives": [],  # Missed dissonance
        "reconciliation_failures": [],  # Poor reconciliation
        "total_errors": 0
    }

    for example in dataset:
        try:
            prediction = module(text1=example.text1, text2=example.text2)
            score = metric(example, prediction)

            if score < 1.0 and hasattr(example, "has_dissonance"):
                errors["total_errors"] += 1

                truth_dissonance = _normalize_dissonance_label(example.has_dissonance)
                pred_dissonance = _normalize_dissonance_label(
                    getattr(prediction, "has_dissonance", "no")
                )

                if truth_dissonance == "no" and pred_dissonance == "yes":
                    errors["false_positives"].append({
                        "claim1": example.text1[:100],
                        "claim2": example.text2[:100],
                        "predicted": pred_dissonance
                    })
                elif truth_dissonance == "yes" and pred_dissonance == "no":
                    errors["false_negatives"].append({
                        "claim1": example.text1[:100],
                        "claim2": example.text2[:100],
                        "predicted": pred_dissonance
                    })

                # Check reconciliation quality
                if hasattr(example, "reconciled") and hasattr(prediction, "reconciled"):
                    truth_rec = example.reconciled.lower()
                    pred_rec = (prediction.reconciled or "").lower()

                    # Simple check: very different lengths or no overlap
                    if abs(len(truth_rec) - len(pred_rec)) > len(truth_rec) * 0.5:
                        errors["reconciliation_failures"].append({
                            "expected": truth_rec[:100],
                            "predicted": pred_rec[:100]
                        })

        except Exception as e:
            logger.warning(f"Error analyzing example: {e}")
            errors["total_errors"] += 1

    # Calculate error rates
    total = len(dataset)
    errors["error_rate"] = errors["total_errors"] / total if total > 0 else 0.0
    errors["false_positive_rate"] = len(errors["false_positives"]) / total if total > 0 else 0.0
    errors["false_negative_rate"] = len(errors["false_negatives"]) / total if total > 0 else 0.0

    logger.info(f"Error analysis: {errors['total_errors']} errors, "
               f"FP rate: {errors['false_positive_rate']:.3f}, "
               f"FN rate: {errors['false_negative_rate']:.3f}")

    return errors
