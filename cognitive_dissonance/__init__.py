"""Cognitive Dissonance Detection and Resolution Framework using DSPy."""

from .config import ExperimentConfig, setup_logging
from .verifier import (
    BeliefAgent,
    DissonanceDetector,
    ReconciliationAgent,
    CognitiveDissonanceResolver
)
from .experiment import (
    cognitive_dissonance_experiment,
    advanced_cognitive_dissonance_experiment,
    run_ablation_study,
    run_confidence_analysis,
    ExperimentResults
)
from .metrics import (
    dissonance_detection_accuracy,
    reconciliation_quality,
    combined_metric,
    agreement_metric_factory,
    blended_metric_factory,
    confidence_weighted_accuracy
)
from .evaluation import (
    evaluate,
    agreement_rate,
    cross_validate,
    analyze_errors
)
from .data import (
    get_belief_conflicts,
    get_dev_labeled,
    get_train_unlabeled,
    validate_dataset,
    get_external_knowledge
)

__version__ = "0.1.0"

__all__ = [
    # Config
    "ExperimentConfig",
    "setup_logging",

    # Verifiers/Agents
    "BeliefAgent",
    "DissonanceDetector",
    "ReconciliationAgent",
    "CognitiveDissonanceResolver",

    # Experiments
    "cognitive_dissonance_experiment",
    "advanced_cognitive_dissonance_experiment",
    "run_ablation_study",
    "run_confidence_analysis",
    "ExperimentResults",

    # Metrics
    "dissonance_detection_accuracy",
    "reconciliation_quality",
    "combined_metric",
    "agreement_metric_factory",
    "blended_metric_factory",
    "confidence_weighted_accuracy",

    # Evaluation
    "evaluate",
    "agreement_rate",
    "cross_validate",
    "analyze_errors",

    # Data
    "get_belief_conflicts",
    "get_dev_labeled",
    "get_train_unlabeled",
    "validate_dataset",
    "get_external_knowledge",
]
