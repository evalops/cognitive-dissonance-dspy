"""Cognitive Dissonance Detection and Resolution Framework using DSPy."""

from .config import ExperimentConfig, setup_logging
from .data import (
    get_belief_conflicts,
    get_dev_labeled,
    get_external_knowledge,
    get_train_unlabeled,
    validate_dataset,
)
from .evaluation import agreement_rate, analyze_errors, cross_validate, evaluate
from .experiment import (
    ExperimentResults,
    advanced_cognitive_dissonance_experiment,
    cognitive_dissonance_experiment,
    run_ablation_study,
    run_confidence_analysis,
)
from .metrics import (
    agreement_metric_factory,
    blended_metric_factory,
    combined_metric,
    confidence_weighted_accuracy,
    dissonance_detection_accuracy,
    reconciliation_quality,
)
from .verifier import (
    BeliefAgent,
    CognitiveDissonanceResolver,
    DissonanceDetector,
    ReconciliationAgent,
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
