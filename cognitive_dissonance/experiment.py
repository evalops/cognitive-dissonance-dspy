"""Main experiment implementation for Cognitive Dissonance resolution."""

from typing import List, Dict, Tuple, Any
import logging
from dspy.teleprompt import BootstrapFewShot

from .config import ExperimentConfig
from .verifier import CognitiveDissonanceResolver
from .data import get_dev_labeled, get_train_unlabeled, validate_dataset
from .metrics import (
    dissonance_detection_accuracy,
    combined_metric,
    agreement_metric_factory,
    blended_metric_factory,
    confidence_weighted_accuracy
)
from .evaluation import evaluate, agreement_rate, analyze_errors
from .optimization import create_advanced_optimizer, GEPAOptimizer
from .uncertainty import UncertaintyQuantifier, EnhancedConfidenceScorer

logger = logging.getLogger(__name__)


class ExperimentResults:
    """Container for experiment results."""

    def __init__(self):
        self.rounds: List[Dict[str, Any]] = []
        self.agent_a = None
        self.agent_b = None
        self.error_analysis = {}
        self.optimization_history = []
        self.confidence_analysis = {}
        self.uncertainty_metrics = {}

    def add_round(
        self,
        round_num: int,
        acc_a: float,
        acc_b: float,
        agree_dev: float,
        agree_train: float,
        reconciliation_quality: float = 0.0
    ) -> None:
        """Add results for a training round."""
        self.rounds.append(
            {
                "round": round_num,
                "accuracy_a": acc_a,
                "accuracy_b": acc_b,
                "agreement_dev": agree_dev,
                "agreement_train": agree_train,
                "reconciliation_quality": reconciliation_quality,
            }
        )

    def get_final_accuracies(self) -> Tuple[float, float]:
        """Get final accuracies for both agents."""
        if not self.rounds:
            return 0.0, 0.0
        last_round = self.rounds[-1]
        return last_round["accuracy_a"], last_round["accuracy_b"]

    def get_final_agreement(self) -> float:
        """Get final agreement rate on dev set."""
        if not self.rounds:
            return 0.0
        return self.rounds[-1]["agreement_dev"]

    def get_final_reconciliation(self) -> float:
        """Get final reconciliation quality."""
        if not self.rounds:
            return 0.0
        return self.rounds[-1].get("reconciliation_quality", 0.0)

    def summary(self) -> Dict[str, Any]:
        """Get experiment summary."""
        if not self.rounds:
            return {"total_rounds": 0}

        acc_a, acc_b = self.get_final_accuracies()
        final_agreement = self.get_final_agreement()
        final_reconciliation = self.get_final_reconciliation()

        return {
            "total_rounds": len(self.rounds),
            "final_accuracy_a": acc_a,
            "final_accuracy_b": acc_b,
            "final_agreement": final_agreement,
            "final_reconciliation": final_reconciliation,
            "max_accuracy_a": max(r["accuracy_a"] for r in self.rounds),
            "max_accuracy_b": max(r["accuracy_b"] for r in self.rounds),
            "max_agreement": max(r["agreement_dev"] for r in self.rounds),
            "error_analysis": self.error_analysis,
        }


def cognitive_dissonance_experiment(
    config: ExperimentConfig = None,
    rounds: int = None,
    use_cot: bool = None,
    alpha_anchor: float = None,
) -> ExperimentResults:
    """
    Run the Cognitive Dissonance experiment.

    Args:
        config: Experiment configuration (if None, loads from environment)
        rounds: Override number of rounds
        use_cot: Override Chain of Thought setting
        alpha_anchor: Override truth anchoring weight

    Returns:
        ExperimentResults object containing all results
    """
    # Setup configuration
    if config is None:
        config = ExperimentConfig.from_env()

    # Apply overrides
    if rounds is not None:
        config.rounds = rounds
    if use_cot is not None:
        config.use_cot = use_cot
    if alpha_anchor is not None:
        config.alpha = alpha_anchor

    config.validate()
    config.setup_dspy()

    logger.info(f"Starting Cognitive Dissonance experiment with {config.rounds} rounds")
    logger.info(f"Alpha (truth anchoring): {config.alpha}")
    logger.info(f"Chain of Thought: {config.use_cot}")
    logger.info(f"Dissonance threshold: {config.dissonance_threshold}")

    # Load and validate datasets
    dev_labeled = get_dev_labeled()
    train_unlabeled = get_train_unlabeled()

    validate_dataset(dev_labeled, require_labels=True)
    validate_dataset(train_unlabeled, require_labels=False)

    logger.info(
        f"Loaded {len(dev_labeled)} labeled examples, {len(train_unlabeled)} unlabeled"
    )

    # Initialize agents
    agent_a = CognitiveDissonanceResolver(use_cot=config.use_cot)
    agent_b = CognitiveDissonanceResolver(use_cot=config.use_cot)

    results = ExperimentResults()

    def build_optimizer(metric):
        return GEPAOptimizer(metric=metric)

    try:
        # Baseline: truth-optimized agent A
        logger.info("Training baseline agent A on ground truth...")
        optimizer_a = build_optimizer(combined_metric)
        agent_a = optimizer_a.compile(agent_a, trainset=dev_labeled)

        # Initialize agent B with same baseline training
        logger.info("Training baseline agent B on ground truth...")
        optimizer_b = build_optimizer(combined_metric)
        agent_b = optimizer_b.compile(agent_b, trainset=dev_labeled)

        # Iterative co-training
        for round_num in range(1, config.rounds + 1):
            logger.info(f"Starting round {round_num}/{config.rounds}")

            # Choose metric based on alpha value
            if config.alpha > 0:
                metric_a = blended_metric_factory(agent_b, config.alpha)
                metric_b = blended_metric_factory(agent_a, config.alpha)
                logger.debug(f"Using blended metric with alpha={config.alpha}")
            else:
                metric_a = agreement_metric_factory(agent_b)
                metric_b = agreement_metric_factory(agent_a)
                logger.debug("Using pure agreement metric")

            # Train A to agree with B while detecting dissonance
            logger.debug("Training agent A...")
            optimizer_a = build_optimizer(metric_a)
            agent_a = optimizer_a.compile(agent_a, trainset=train_unlabeled)

            # Train B to agree with A while detecting dissonance
            logger.debug("Training agent B...")
            optimizer_b = build_optimizer(metric_b)
            agent_b = optimizer_b.compile(agent_b, trainset=train_unlabeled)

            # Evaluate both agents
            acc_a = evaluate(agent_a, dev_labeled, metric=dissonance_detection_accuracy, display_progress=False)
            acc_b = evaluate(agent_b, dev_labeled, metric=dissonance_detection_accuracy, display_progress=False)

            # Evaluate reconciliation quality
            recon_quality = evaluate(agent_a, dev_labeled, metric=combined_metric, display_progress=False)

            # Calculate agreement rates
            agree_dev = agreement_rate(agent_a, agent_b, dev_labeled)
            # Use min to avoid hardcoded slice that could fail with small datasets
            train_sample_size = min(60, len(train_unlabeled))
            agree_train = agreement_rate(
                agent_a, agent_b, train_unlabeled[:train_sample_size]
            )

            # Store results
            results.add_round(round_num, acc_a, acc_b, agree_dev, agree_train, recon_quality)

            # Log progress
            logger.info(
                f"[round {round_num}] accA={acc_a:.3f} accB={acc_b:.3f} "
                f"agree_dev={agree_dev:.3f} agree_train={agree_train:.3f} "
                f"reconciliation={recon_quality:.3f}"
            )

            print(
                f"[round {round_num}] accA={acc_a:.3f} accB={acc_b:.3f} "
                f"agree_dev={agree_dev:.3f} agree_train={agree_train:.3f} "
                f"reconciliation={recon_quality:.3f}"
            )

        # Store final agents
        results.agent_a = agent_a
        results.agent_b = agent_b

        # Perform error analysis
        logger.info("Performing error analysis...")
        results.error_analysis = analyze_errors(agent_a, dev_labeled, metric=dissonance_detection_accuracy)

        logger.info("Experiment completed successfully")
        logger.info(f"Final summary: {results.summary()}")

        return results

    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        raise


def advanced_cognitive_dissonance_experiment(
    config: ExperimentConfig = None,
    optimization_strategy: str = "gepa+ensemble",
    rounds: int = None,
    use_cot: bool = None,
    alpha_anchor: float = None,
) -> ExperimentResults:
    """
    Run advanced cognitive dissonance experiment with enhanced optimization.

    Args:
        config: Experiment configuration
        optimization_strategy: Advanced optimization strategy to use
        rounds: Override number of rounds
        use_cot: Override Chain of Thought setting
        alpha_anchor: Override truth anchoring weight

    Returns:
        ExperimentResults with advanced metrics and analysis
    """
    # Setup configuration
    if config is None:
        config = ExperimentConfig.from_env()

    # Apply overrides
    if rounds is not None:
        config.rounds = rounds
    if use_cot is not None:
        config.use_cot = use_cot
    if alpha_anchor is not None:
        config.alpha = alpha_anchor

    config.validate()
    config.setup_dspy()

    logger.info(f"Starting ADVANCED Cognitive Dissonance experiment with {config.rounds} rounds")
    logger.info(f"Optimization strategy: {optimization_strategy}")
    logger.info(f"Alpha (truth anchoring): {config.alpha}")
    logger.info(f"Chain of Thought: {config.use_cot}")

    # Load and validate datasets
    dev_labeled = get_dev_labeled()
    train_unlabeled = get_train_unlabeled()

    validate_dataset(dev_labeled, require_labels=True)
    validate_dataset(train_unlabeled, require_labels=False)

    logger.info(
        f"Loaded {len(dev_labeled)} labeled examples, {len(train_unlabeled)} unlabeled"
    )

    # Initialize agents with advanced features
    agent_a = CognitiveDissonanceResolver(use_cot=config.use_cot)
    agent_b = CognitiveDissonanceResolver(use_cot=config.use_cot)

    # Initialize advanced components
    uncertainty_quantifier = UncertaintyQuantifier()
    confidence_scorer = EnhancedConfidenceScorer(uncertainty_quantifier)

    results = ExperimentResults()

    try:
        # Advanced baseline optimization
        logger.info("Training baseline agents with advanced optimization...")
        
        # Create advanced optimizers
        optimizer_a = create_advanced_optimizer(optimization_strategy)
        optimizer_b = create_advanced_optimizer(optimization_strategy)

        # Train baseline agents
        agent_a = optimizer_a.compile(agent_a, trainset=dev_labeled)
        agent_b = optimizer_b.compile(agent_b, trainset=dev_labeled)

        # Store optimization history if available
        if hasattr(optimizer_a, 'optimization_history'):
            results.optimization_history.extend(optimizer_a.optimization_history)
        if hasattr(optimizer_b, 'optimization_history'):
            results.optimization_history.extend(optimizer_b.optimization_history)

        # Iterative co-training with advanced metrics
        for round_num in range(1, config.rounds + 1):
            logger.info(f"Starting advanced round {round_num}/{config.rounds}")

            # Choose metric based on alpha value with advanced scoring
            if config.alpha > 0:
                metric_a = blended_metric_factory(agent_b, config.alpha)
                metric_b = blended_metric_factory(agent_a, config.alpha)
                logger.debug(f"Using blended metric with alpha={config.alpha}")
            else:
                metric_a = agreement_metric_factory(agent_b)
                metric_b = agreement_metric_factory(agent_a)
                logger.debug("Using pure agreement metric")

            # Advanced training with GEPA reflection
            logger.debug("Training agent A with advanced optimization...")
            if optimization_strategy in ["gepa", "gepa+ensemble"]:
                advanced_optimizer_a = GEPAOptimizer(metric=metric_a)
            else:
                advanced_optimizer_a = create_advanced_optimizer("ensemble")
            
            agent_a = advanced_optimizer_a.compile(agent_a, trainset=train_unlabeled)

            logger.debug("Training agent B with advanced optimization...")
            if optimization_strategy in ["gepa", "gepa+ensemble"]:
                advanced_optimizer_b = GEPAOptimizer(metric=metric_b)
            else:
                advanced_optimizer_b = create_advanced_optimizer("ensemble")
            
            agent_b = advanced_optimizer_b.compile(agent_b, trainset=train_unlabeled)

            # Evaluate with enhanced metrics
            acc_a = evaluate(agent_a, dev_labeled, metric=dissonance_detection_accuracy, display_progress=False)
            acc_b = evaluate(agent_b, dev_labeled, metric=dissonance_detection_accuracy, display_progress=False)

            # Enhanced reconciliation quality evaluation
            recon_quality_a = evaluate(agent_a, dev_labeled, metric=combined_metric, display_progress=False)
            recon_quality_b = evaluate(agent_b, dev_labeled, metric=combined_metric, display_progress=False)
            avg_recon_quality = (recon_quality_a + recon_quality_b) / 2

            # Calculate agreement rates
            agree_dev = agreement_rate(agent_a, agent_b, dev_labeled)
            train_sample_size = min(60, len(train_unlabeled))
            agree_train = agreement_rate(
                agent_a, agent_b, train_unlabeled[:train_sample_size]
            )

            # Advanced confidence analysis
            sample_predictions_a = []
            sample_predictions_b = []
            
            for example in dev_labeled[:10]:
                try:
                    pred_a = agent_a(text1=example.text1, text2=example.text2)
                    pred_b = agent_b(text1=example.text1, text2=example.text2)
                    sample_predictions_a.append(pred_a)
                    sample_predictions_b.append(pred_b)
                except Exception as e:
                    logger.warning(f"Failed to get sample prediction: {e}")
                    continue

            # Compute confidence metrics
            if sample_predictions_a:
                confidence_summary_a = confidence_scorer.get_scoring_summary(sample_predictions_a)
                confidence_summary_b = confidence_scorer.get_scoring_summary(sample_predictions_b)
                
                avg_confidence = (
                    confidence_summary_a.get('avg_confidence', 0.5) + 
                    confidence_summary_b.get('avg_confidence', 0.5)
                ) / 2
                
                avg_uncertainty = (
                    confidence_summary_a.get('avg_uncertainty', 0.5) + 
                    confidence_summary_b.get('avg_uncertainty', 0.5)
                ) / 2
            else:
                avg_confidence = 0.5
                avg_uncertainty = 0.5

            # Store enhanced results
            results.add_round(
                round_num, acc_a, acc_b, agree_dev, agree_train, avg_recon_quality
            )

            # Store additional metrics in results
            round_data = results.rounds[-1]
            round_data.update({
                'avg_confidence': avg_confidence,
                'avg_uncertainty': avg_uncertainty,
                'confidence_distribution_a': confidence_summary_a.get('confidence_distribution', {}) if sample_predictions_a else {},
                'confidence_distribution_b': confidence_summary_b.get('confidence_distribution', {}) if sample_predictions_b else {}
            })

            # Log enhanced progress
            logger.info(
                f"[round {round_num}] accA={acc_a:.3f} accB={acc_b:.3f} "
                f"agree_dev={agree_dev:.3f} agree_train={agree_train:.3f} "
                f"reconciliation={avg_recon_quality:.3f} "
                f"confidence={avg_confidence:.3f} uncertainty={avg_uncertainty:.3f}"
            )

            print(
                f"[round {round_num}] accA={acc_a:.3f} accB={acc_b:.3f} "
                f"agree_dev={agree_dev:.3f} agree_train={agree_train:.3f} "
                f"reconciliation={avg_recon_quality:.3f} "
                f"confidence={avg_confidence:.3f} uncertainty={avg_uncertainty:.3f}"
            )

        # Store final agents
        results.agent_a = agent_a
        results.agent_b = agent_b

        # Enhanced error analysis
        logger.info("Performing enhanced error analysis...")
        results.error_analysis = analyze_errors(agent_a, dev_labeled, metric=combined_metric)
        
        # Final confidence analysis
        all_predictions = []
        ground_truth = []
        
        for example in dev_labeled:
            try:
                pred = agent_a(text1=example.text1, text2=example.text2)
                all_predictions.append(pred)
                
                # Determine ground truth correctness
                expected_dissonance = getattr(example, 'has_dissonance', 'no')
                actual_dissonance = getattr(pred, 'has_dissonance', 'no')
                ground_truth.append(expected_dissonance.lower() == actual_dissonance.lower())
                
            except Exception as e:
                logger.warning(f"Failed to get prediction for confidence analysis: {e}")
                continue

        # Calibrate confidence scorer
        if all_predictions and ground_truth:
            confidence_scorer.calibrate_scorer(all_predictions, ground_truth)
            results.confidence_analysis = confidence_scorer.get_scoring_summary(all_predictions)
            results.uncertainty_metrics = uncertainty_quantifier.get_calibration_metrics()

        logger.info("Advanced experiment completed successfully")
        logger.info(f"Final summary: {results.summary()}")

        return results

    except Exception as e:
        logger.error(f"Advanced experiment failed: {e}")
        raise


def run_ablation_study(
    base_config: ExperimentConfig = None,
) -> Dict[str, ExperimentResults]:
    """
    Run an ablation study with different configurations.

    Args:
        base_config: Base configuration to modify

    Returns:
        Dictionary mapping configuration names to results
    """
    if base_config is None:
        base_config = ExperimentConfig.from_env()

    configurations = {
        "baseline": {"alpha": 0.0, "use_cot": False},
        "with_cot": {"alpha": 0.0, "use_cot": True},
        "alpha_0.1": {"alpha": 0.1, "use_cot": False},
        "alpha_0.5": {"alpha": 0.5, "use_cot": False},
        "alpha_0.1_cot": {"alpha": 0.1, "use_cot": True},
        "alpha_0.5_cot": {"alpha": 0.5, "use_cot": True},
    }

    results = {}

    logger.info(f"Running ablation study with {len(configurations)} configurations")

    for name, params in configurations.items():
        logger.info(f"Running configuration: {name} with params: {params}")

        # Create config copy with modified parameters
        config = ExperimentConfig(
            model=base_config.model,
            api_base=base_config.api_base,
            api_key=base_config.api_key,
            temperature=base_config.temperature,
            max_tokens=base_config.max_tokens,
            alpha=params.get("alpha", base_config.alpha),
            rounds=base_config.rounds,
            use_cot=params.get("use_cot", base_config.use_cot),
            dissonance_threshold=base_config.dissonance_threshold,
            auto_mode=base_config.auto_mode,
            enable_disk_cache=base_config.enable_disk_cache,
            enable_memory_cache=base_config.enable_memory_cache,
        )

        try:
            results[name] = cognitive_dissonance_experiment(config)
        except Exception as e:
            logger.error(f"Failed configuration {name}: {e}")
            results[name] = None

    # Compare results
    logger.info("Ablation study completed")
    logger.info("\nConfiguration comparison:")
    
    for name, result in results.items():
        if result and result.rounds:  # Check if result exists and has data
            summary = result.summary()
            logger.info(
                f"{name}: final_acc={summary['final_accuracy_a']:.3f}, "
                f"agreement={summary['final_agreement']:.3f}, "
                f"reconciliation={summary['final_reconciliation']:.3f}"
            )

    return results


def run_confidence_analysis(
    config: ExperimentConfig = None
) -> Dict[str, Any]:
    """
    Analyze the impact of confidence weighting.

    Args:
        config: Experiment configuration

    Returns:
        Dictionary with confidence analysis results
    """
    if config is None:
        config = ExperimentConfig.from_env()

    config.validate()
    config.setup_dspy()

    # Load data
    dev_labeled = get_dev_labeled()

    # Create agents with different settings
    agent_no_conf = CognitiveDissonanceResolver(use_cot=False)
    agent_with_conf = CognitiveDissonanceResolver(use_cot=True)

    # Train both
    logger.info("Training agent without confidence weighting...")
    optimizer1 = BootstrapFewShot(metric=dissonance_detection_accuracy)
    agent_no_conf = optimizer1.compile(agent_no_conf, trainset=dev_labeled)

    logger.info("Training agent with confidence weighting...")
    optimizer2 = BootstrapFewShot(metric=confidence_weighted_accuracy)
    agent_with_conf = optimizer2.compile(agent_with_conf, trainset=dev_labeled)

    # Evaluate
    acc_no_conf = evaluate(agent_no_conf, dev_labeled, metric=dissonance_detection_accuracy)
    acc_with_conf = evaluate(agent_with_conf, dev_labeled, metric=dissonance_detection_accuracy)

    acc_weighted = evaluate(agent_with_conf, dev_labeled, metric=confidence_weighted_accuracy)

    results = {
        "accuracy_without_confidence": acc_no_conf,
        "accuracy_with_confidence": acc_with_conf,
        "confidence_weighted_accuracy": acc_weighted,
        "improvement": acc_with_conf - acc_no_conf,
    }

    logger.info(f"Confidence analysis results: {results}")

    return results