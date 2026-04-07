"""Advanced optimization techniques for cognitive dissonance detection."""

import logging
from collections.abc import Callable
from typing import Any

import dspy
from dspy.teleprompt import BootstrapFewShot

logger = logging.getLogger(__name__)


class GEPAOptimizer:
    """
    GEPA (Generative Evolution of Prompts and Answers) optimizer.
    Uses LLM reflection on program trajectories to identify gaps and propose improvements.
    """

    def __init__(self,
                 metric: Callable,
                 reflection_model: str | None = None,
                 max_iterations: int = 3,
                 improvement_threshold: float = 0.05):
        """
        Initialize GEPA optimizer.

        Args:
            metric: Evaluation metric function
            reflection_model: Model for reflection (uses same as main if None)
            max_iterations: Maximum optimization iterations
            improvement_threshold: Minimum improvement required to continue
        """
        self.metric = metric
        self.reflection_model = reflection_model
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.optimization_history = []
        logger.debug(f"Initialized GEPA optimizer with {max_iterations} iterations")

    def reflect_on_trajectory(self,
                             module: dspy.Module,
                             examples: list[dspy.Example],
                             performance: float) -> str:
        """
        Use LLM to reflect on program trajectory and identify improvements.

        Args:
            module: The module being optimized
            examples: Training examples
            performance: Current performance score

        Returns:
            Reflection text with improvement suggestions
        """
        # Sample a few examples to analyze
        sample_examples = examples[:3] if len(examples) >= 3 else examples

        # Get predictions for analysis
        predictions = []
        for ex in sample_examples:
            try:
                pred = module(text1=ex.text1, text2=ex.text2)
                predictions.append({
                    'input': (ex.text1[:100], ex.text2[:100]),
                    'output': {
                        'has_dissonance': getattr(pred, 'has_dissonance', 'unknown'),
                        'reconciled': getattr(pred, 'reconciled', 'unknown')[:100]
                    },
                    'expected': {
                        'has_dissonance': getattr(ex, 'has_dissonance', 'unknown'),
                        'reconciled': getattr(ex, 'reconciled', 'unknown')[:100] if hasattr(ex, 'reconciled') else 'unknown'
                    }
                })
            except Exception as e:
                logger.warning(f"Error getting prediction for reflection: {e}")
                continue

        # Use reflection model or fallback to basic analysis
        try:
            # For now, provide structured analysis based on predictions
            return self._analyze_predictions(predictions, performance)
        except Exception as e:
            logger.warning(f"Reflection failed: {e}")
            return "Unable to generate reflection - using default optimization strategy."

    def _format_predictions(self, predictions: list[dict]) -> str:
        """Format predictions for reflection analysis."""
        formatted = []
        for i, pred in enumerate(predictions):
            formatted.append(f"""
            Example {i+1}:
            Input: "{pred['input'][0]}..." vs "{pred['input'][1]}..."
            Predicted: dissonance={pred['output']['has_dissonance']}, reconciled="{pred['output']['reconciled']}..."
            Expected: dissonance={pred['expected']['has_dissonance']}, reconciled="{pred['expected']['reconciled']}..."
            """)
        return "\n".join(formatted)

    def _analyze_predictions(self, predictions: list[dict], performance: float) -> str:
        """Analyze predictions to generate improvement suggestions."""
        issues = []
        suggestions = []

        # Analyze dissonance detection accuracy
        correct_dissonance = sum(1 for p in predictions
                               if p['output']['has_dissonance'] == p['expected']['has_dissonance'])
        dissonance_accuracy = correct_dissonance / len(predictions) if predictions else 0

        if dissonance_accuracy < 0.7:
            issues.append("Low dissonance detection accuracy")
            suggestions.append("Improve claim contradiction detection by adding more explicit reasoning steps")

        # Analyze reconciliation quality
        empty_reconciliations = sum(1 for p in predictions
                                  if p['output']['reconciled'] in ['unknown', '', 'Unable to reconcile'])
        if empty_reconciliations > len(predictions) * 0.3:
            issues.append("Many empty or failed reconciliations")
            suggestions.append("Add more structured reconciliation templates and examples")

        # Overall performance analysis
        if performance < 0.6:
            suggestions.append("Consider adding Chain of Thought reasoning for complex cases")
            suggestions.append("Increase few-shot examples for better pattern recognition")

        reflection = f"""
        Performance Analysis (Score: {performance:.3f}):

        Issues Identified:
        {chr(10).join(f"- {issue}" for issue in issues)}

        Improvement Suggestions:
        {chr(10).join(f"- {suggestion}" for suggestion in suggestions)}

        Dissonance Detection Accuracy: {dissonance_accuracy:.3f}
        Empty Reconciliations: {empty_reconciliations}/{len(predictions)}
        """

        return reflection

    def compile(self, module: dspy.Module, trainset: list[dspy.Example]) -> dspy.Module:
        """
        Compile module using GEPA optimization strategy.

        Args:
            module: Module to optimize
            trainset: Training examples

        Returns:
            Optimized module
        """
        logger.info("Starting GEPA optimization")

        best_module = module
        best_score = 0.0

        for iteration in range(self.max_iterations):
            logger.info(f"GEPA iteration {iteration + 1}/{self.max_iterations}")

            # Evaluate current module
            from .evaluation import evaluate
            current_score = evaluate(best_module, trainset[:10], metric=self.metric, display_progress=False)

            # Reflect on performance
            reflection = self.reflect_on_trajectory(best_module, trainset, current_score)
            logger.debug(f"Reflection: {reflection}")

            # Store optimization history
            self.optimization_history.append({
                'iteration': iteration + 1,
                'score': current_score,
                'reflection': reflection
            })

            # Try to improve using reflection insights
            try:
                optimizer = BootstrapFewShot(metric=self.metric)
                improved_module = optimizer.compile(best_module, trainset=trainset)

                # Evaluate improvement
                new_score = evaluate(improved_module, trainset[:10], metric=self.metric, display_progress=False)

                if new_score > best_score + self.improvement_threshold:
                    best_module = improved_module
                    best_score = new_score
                    logger.info(f"Improved score: {best_score:.3f} (+{new_score - current_score:.3f})")
                else:
                    logger.info(f"No significant improvement: {new_score:.3f}")
                    break

            except Exception as e:
                logger.warning(f"Optimization iteration {iteration + 1} failed: {e}")
                continue

        logger.info(f"GEPA optimization complete. Final score: {best_score:.3f}")
        return best_module


class EnsembleOptimizer:
    """
    Creates ensemble of optimized modules for improved performance.
    """

    def __init__(self,
                 base_optimizers: list[Any],
                 ensemble_size: int = 5,
                 voting_strategy: str = "majority"):
        """
        Initialize ensemble optimizer.

        Args:
            base_optimizers: List of optimizer instances
            ensemble_size: Number of modules in ensemble
            voting_strategy: How to combine predictions ('majority', 'weighted')
        """
        self.base_optimizers = base_optimizers
        self.ensemble_size = ensemble_size
        self.voting_strategy = voting_strategy
        logger.debug(f"Initialized ensemble optimizer with {ensemble_size} modules")

    def compile(self, module: dspy.Module, trainset: list[dspy.Example]) -> 'EnsembleModule':
        """
        Create ensemble of optimized modules.

        Args:
            module: Base module to optimize
            trainset: Training examples

        Returns:
            EnsembleModule containing multiple optimized modules
        """
        logger.info("Creating ensemble of optimized modules")

        optimized_modules = []
        scores = []

        for i, optimizer in enumerate(self.base_optimizers[:self.ensemble_size]):
            try:
                logger.info(f"Training ensemble member {i + 1}/{min(len(self.base_optimizers), self.ensemble_size)}")
                optimized = optimizer.compile(module, trainset)
                optimized_modules.append(optimized)

                # Evaluate performance for weighting
                from .evaluation import evaluate
                from .metrics import combined_metric
                score = evaluate(optimized, trainset[:10], metric=combined_metric, display_progress=False)
                scores.append(score)

            except Exception as e:
                logger.warning(f"Failed to optimize ensemble member {i + 1}: {e}")
                continue

        if not optimized_modules:
            logger.warning("No modules successfully optimized, returning original")
            return module

        logger.info(f"Created ensemble with {len(optimized_modules)} members")
        return EnsembleModule(optimized_modules, scores, self.voting_strategy)


class EnsembleModule(dspy.Module):
    """
    Ensemble module that combines predictions from multiple optimized modules.
    """

    def __init__(self, modules: list[dspy.Module], scores: list[float], voting_strategy: str = "majority"):
        super().__init__()
        self.modules = modules
        self.scores = scores
        self.voting_strategy = voting_strategy
        self.weights = self._compute_weights(scores)
        logger.debug(f"Created ensemble with {len(modules)} modules")

    def _compute_weights(self, scores: list[float]) -> list[float]:
        """Compute voting weights based on individual module performance."""
        if not self.modules:
            return []

        if not scores or all(s == 0 for s in scores):
            return [1.0 / len(self.modules)] * len(self.modules)

        # Normalize scores to weights
        total = sum(scores)
        return [s / total for s in scores] if total > 0 else [1.0 / len(scores)] * len(scores)

    def forward(self, **kwargs) -> dspy.Prediction:
        """
        Forward pass through ensemble, combining predictions.

        Returns:
            Combined prediction from all ensemble members
        """
        predictions = []

        # Get predictions from all modules
        for module in self.modules:
            try:
                pred = module(**kwargs)
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"Ensemble member failed: {e}")
                continue

        if not predictions:
            # Fallback prediction
            result = dspy.Prediction()
            result.has_dissonance = "no"
            result.reconciled = "Unable to determine"
            return result

        # Combine predictions based on voting strategy
        if self.voting_strategy == "majority":
            return self._majority_vote(predictions)
        elif self.voting_strategy == "weighted":
            return self._weighted_vote(predictions)
        else:
            return predictions[0]  # Fallback to first prediction

    def _majority_vote(self, predictions: list[dspy.Prediction]) -> dspy.Prediction:
        """Combine predictions using majority voting."""
        # Count dissonance votes
        dissonance_votes = {"yes": 0, "no": 0}
        reconciled_texts = []

        for pred in predictions:
            dissonance = getattr(pred, 'has_dissonance', 'no').lower()
            if 'yes' in dissonance:
                dissonance_votes['yes'] += 1
            else:
                dissonance_votes['no'] += 1

            reconciled = getattr(pred, 'reconciled', '')
            if reconciled:
                reconciled_texts.append(reconciled)

        # Create combined prediction
        result = dspy.Prediction()
        result.has_dissonance = "yes" if dissonance_votes['yes'] > dissonance_votes['no'] else "no"

        # Use most common reconciliation or combine them
        if reconciled_texts:
            # For simplicity, use the first non-empty reconciliation
            # In practice, could use more sophisticated combination
            result.reconciled = reconciled_texts[0]
        else:
            result.reconciled = "No reconciliation available"

        # Add ensemble metadata
        result.ensemble_confidence = max(dissonance_votes.values()) / sum(dissonance_votes.values())
        result.ensemble_size = len(predictions)

        return result

    def _weighted_vote(self, predictions: list[dspy.Prediction]) -> dspy.Prediction:
        """Combine predictions using weighted voting based on module performance."""
        if len(predictions) != len(self.weights):
            return self._majority_vote(predictions)

        weighted_dissonance = 0.0
        reconciled_texts = []

        for pred, weight in zip(predictions, self.weights, strict=True):
            dissonance = getattr(pred, 'has_dissonance', 'no').lower()
            if 'yes' in dissonance:
                weighted_dissonance += weight

            reconciled = getattr(pred, 'reconciled', '')
            if reconciled:
                reconciled_texts.append((reconciled, weight))

        # Create weighted prediction
        result = dspy.Prediction()
        result.has_dissonance = "yes" if weighted_dissonance > 0.5 else "no"

        # Use highest-weighted reconciliation
        if reconciled_texts:
            best_reconciliation = max(reconciled_texts, key=lambda x: x[1])
            result.reconciled = best_reconciliation[0]
        else:
            result.reconciled = "No reconciliation available"

        # Add ensemble metadata
        result.ensemble_confidence = max(weighted_dissonance, 1.0 - weighted_dissonance)
        result.ensemble_size = len(predictions)

        return result


def create_advanced_optimizer(optimization_strategy: str = "gepa+ensemble") -> Any:
    """
    Factory function to create advanced optimizers.

    Args:
        optimization_strategy: Strategy to use ('gepa', 'ensemble', 'gepa+ensemble')

    Returns:
        Optimizer instance
    """
    from .metrics import combined_metric, dissonance_detection_accuracy

    if optimization_strategy == "gepa":
        return GEPAOptimizer(metric=combined_metric)

    if optimization_strategy == "ensemble":
        base_optimizers: list[Any] = [
            GEPAOptimizer(metric=combined_metric),
            BootstrapFewShot(metric=combined_metric),
            BootstrapFewShot(metric=dissonance_detection_accuracy),
        ]
        return EnsembleOptimizer(base_optimizers)

    if optimization_strategy == "gepa+ensemble":
        gepa = GEPAOptimizer(metric=combined_metric)
        base_optimizers = [
            gepa,
            BootstrapFewShot(metric=combined_metric),
            BootstrapFewShot(metric=dissonance_detection_accuracy),
        ]
        return EnsembleOptimizer(base_optimizers, ensemble_size=len(base_optimizers))

    logger.warning(f"Unknown optimization strategy: {optimization_strategy}")
    return GEPAOptimizer(metric=combined_metric)
