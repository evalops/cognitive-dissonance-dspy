"""Main entry point for Cognitive Dissonance experiments."""

import argparse
import logging
from typing import Optional

from .config import ExperimentConfig, setup_logging
from .experiment import (
    cognitive_dissonance_experiment,
    advanced_cognitive_dissonance_experiment,
    run_ablation_study,
    run_confidence_analysis
)
from .verifier import BeliefAgent, DissonanceDetector, ReconciliationAgent
from .mathematical_resolver import MathematicalCognitiveDissonanceResolver

logger = logging.getLogger(__name__)


def demo_mathematical_resolution():
    """Demonstrate mathematical proof-backed cognitive dissonance resolution."""
    from .config import setup_logging, ExperimentConfig
    
    setup_logging()
    config = ExperimentConfig.from_env()
    config.setup_dspy()
    
    # Initialize the mathematical resolver
    resolver = MathematicalCognitiveDissonanceResolver(
        use_cot=True, 
        enable_formal_verification=True
    )
    
    print("\n=== Mathematical Proof-Backed Cognitive Dissonance Resolution ===\n")
    
    # Example 1: Mathematical conflict that can be formally verified
    text1 = "The sum of 2 plus 2 equals 4. This is basic arithmetic."
    text2 = "Actually, 2 + 2 = 5. Mathematical addition works differently."
    
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}\n")
    
    result = resolver(text1=text1, text2=text2)
    
    print(f"Conflict Detected: {result.conflict_detected}")
    print(f"Resolution Method: {result.resolution_method.value}")
    print(f"Final Confidence: {result.final_confidence:.3f}")
    print(f"Resolved Claim: {result.resolved_claim}")
    print(f"Reasoning: {result.reasoning}")
    
    if result.mathematical_evidence:
        print("\nMathematical Evidence:")
        for evidence in result.mathematical_evidence:
            print(f"  • '{evidence.claim_text}' -> {'PROVEN' if evidence.proven else 'FAILED'} "
                  f"({evidence.proof_time_ms:.1f}ms, {evidence.prover_used})")
    
    print("\n" + "="*70 + "\n")
    
    # Example 2: Algorithm correctness conflict
    text3 = "This sorting function has O(n log n) time complexity and sorts correctly."
    text4 = "The same algorithm has O(n^2) complexity and contains bugs."
    
    print(f"Text 3: {text3}")
    print(f"Text 4: {text4}\n")
    
    # Include sample code for analysis
    sample_code = """
    def quicksort(arr):
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return quicksort(left) + middle + quicksort(right)
    """
    
    result2 = resolver(text1=text3, text2=text4, code=sample_code)
    
    print(f"Conflict Detected: {result2.conflict_detected}")
    print(f"Resolution Method: {result2.resolution_method.value}")  
    print(f"Final Confidence: {result2.final_confidence:.3f}")
    print(f"Resolved Claim: {result2.resolved_claim}")
    print(f"Reasoning: {result2.reasoning}")
    
    if result2.mathematical_evidence:
        print("\nMathematical Evidence:")
        for evidence in result2.mathematical_evidence:
            print(f"  • '{evidence.claim_text[:60]}...' -> {'PROVEN' if evidence.proven else 'FAILED'} "
                  f"({evidence.proof_time_ms:.1f}ms)")
    
    print("\n" + "="*70 + "\n")
    
    # Example 3: Subjective conflict (should fall back to probabilistic)
    text5 = "Python is the best programming language for data science."
    text6 = "R is superior to Python for statistical analysis and data science."
    
    print(f"Text 5: {text5}")
    print(f"Text 6: {text6}\n")
    
    result3 = resolver(text1=text5, text2=text6)
    
    print(f"Conflict Detected: {result3.conflict_detected}")
    print(f"Resolution Method: {result3.resolution_method.value}")
    print(f"Final Confidence: {result3.final_confidence:.3f}")
    print(f"Resolved Claim: {result3.resolved_claim}")
    print(f"Reasoning: {result3.reasoning}")
    
    print("\nDemonstration complete. The system intelligently routes verifiable claims to")
    print("formal verification and falls back to probabilistic reconciliation for")
    print("subjective or unverifiable claims.")


def demo_basic_usage():
    """Demonstrate basic usage of the cognitive dissonance system."""
    from .config import setup_logging, ExperimentConfig
    
    setup_logging()
    config = ExperimentConfig.from_env()
    config.setup_dspy()
    
    # Initialize agents
    belief_agent = BeliefAgent(use_cot=True)
    dissonance_agent = DissonanceDetector(use_cot=True)
    reconciliation_agent = ReconciliationAgent(use_cot=True)
    
    # Example texts with cognitive dissonance
    text1 = "The capital of France is Paris. It is a beautiful city."
    text2 = "Paris is not the capital of France. London holds that title."
    
    print("\n=== Cognitive Dissonance Detection Demo ===\n")
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}\n")
    
    # Agent 1 forms belief
    belief1 = belief_agent(text=text1)
    print(f"Agent 1 Belief: {belief1.claim}")
    print(f"Confidence: {belief1.confidence}\n")
    
    # Agent 2 forms belief
    belief2 = belief_agent(text=text2)
    print(f"Agent 2 Belief: {belief2.claim}")
    print(f"Confidence: {belief2.confidence}\n")
    
    # Detect dissonance
    dissonance_result = dissonance_agent(claim1=belief1.claim, claim2=belief2.claim)
    print(f"Dissonance Detected: {dissonance_result.are_contradictory}")
    
    if dissonance_result.are_contradictory == "yes":
        print(f"Reason: {dissonance_result.reason}\n")
        
        # Reconcile claims
        reconciled = reconciliation_agent(
            claim1=belief1.claim,
            claim2=belief2.claim,
            has_conflict="yes"
        )
        print(f"Reconciled Claim: {reconciled.reconciled_claim}")
    
    print("\n" + "="*50 + "\n")
    
    # Another example
    text3 = "Water boils at 100 degrees Celsius at sea level."
    text4 = "Water boils at 90 degrees Celsius at sea level."
    
    print(f"Text 3: {text3}")
    print(f"Text 4: {text4}\n")
    
    belief3 = belief_agent(text=text3)
    print(f"Agent 3 Belief: {belief3.claim} (Confidence: {belief3.confidence})")
    
    belief4 = belief_agent(text=text4)
    print(f"Agent 4 Belief: {belief4.claim} (Confidence: {belief4.confidence})\n")
    
    dissonance_result2 = dissonance_agent(claim1=belief3.claim, claim2=belief4.claim)
    print(f"Dissonance Detected: {dissonance_result2.are_contradictory}")
    
    if dissonance_result2.are_contradictory == "yes":
        print(f"Reason: {dissonance_result2.reason}")
        reconciled2 = reconciliation_agent(
            claim1=belief3.claim,
            claim2=belief4.claim,
            has_conflict="yes"
        )
        print(f"Reconciled Claim: {reconciled2.reconciled_claim}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cognitive Dissonance Detection and Resolution Experiment"
    )
    
    parser.add_argument(
        "command",
        choices=["demo", "mathematical", "experiment", "advanced", "ablation", "confidence"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Number of co-training rounds"
    )
    
    parser.add_argument(
        "--alpha",
        type=float,
        default=None,
        help="Truth anchoring weight (0.0 to 1.0)"
    )
    
    parser.add_argument(
        "--use-cot",
        action="store_true",
        help="Use Chain of Thought reasoning"
    )
    
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model to use (e.g., ollama_chat/llama3.1:8b)"
    )
    
    parser.add_argument(
        "--api-base",
        type=str,
        default=None,
        help="API base URL"
    )
    
    parser.add_argument(
        "--dissonance-threshold",
        type=float,
        default=None,
        help="Threshold for detecting cognitive dissonance"
    )
    
    parser.add_argument(
        "--optimization",
        type=str,
        default="gepa+ensemble",
        choices=["gepa", "ensemble", "gepa+ensemble"],
        help="Advanced optimization strategy"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(level=args.log_level)
    
    # Create configuration
    config = ExperimentConfig.from_env()
    
    # Apply CLI overrides
    if args.model:
        config.model = args.model
    if args.api_base:
        config.api_base = args.api_base
    if args.rounds:
        config.rounds = args.rounds
    if args.alpha is not None:
        config.alpha = args.alpha
    if args.use_cot:
        config.use_cot = True
    if args.dissonance_threshold is not None:
        config.dissonance_threshold = args.dissonance_threshold
    
    # Run selected command
    if args.command == "demo":
        demo_basic_usage()
    
    elif args.command == "mathematical":
        demo_mathematical_resolution()
    
    elif args.command == "experiment":
        logger.info("Running cognitive dissonance experiment...")
        results = cognitive_dissonance_experiment(config)
        
        print("\n=== Experiment Results ===")
        summary = results.summary()
        print(f"Total rounds: {summary['total_rounds']}")
        print(f"Final accuracy A: {summary['final_accuracy_a']:.3f}")
        print(f"Final accuracy B: {summary['final_accuracy_b']:.3f}")
        print(f"Final agreement: {summary['final_agreement']:.3f}")
        print(f"Final reconciliation quality: {summary['final_reconciliation']:.3f}")
        
        if summary.get('error_analysis'):
            print(f"\nError Analysis:")
            print(f"  Error rate: {summary['error_analysis']['error_rate']:.3f}")
            print(f"  False positive rate: {summary['error_analysis']['false_positive_rate']:.3f}")
            print(f"  False negative rate: {summary['error_analysis']['false_negative_rate']:.3f}")
    
    elif args.command == "advanced":
        logger.info("Running advanced cognitive dissonance experiment...")
        results = advanced_cognitive_dissonance_experiment(config, optimization_strategy=args.optimization)
        
        print("\n=== Advanced Experiment Results ===")
        summary = results.summary()
        print(f"Total rounds: {summary['total_rounds']}")
        print(f"Final accuracy A: {summary['final_accuracy_a']:.3f}")
        print(f"Final accuracy B: {summary['final_accuracy_b']:.3f}")
        print(f"Final agreement: {summary['final_agreement']:.3f}")
        print(f"Final reconciliation quality: {summary['final_reconciliation']:.3f}")
        
        if results.confidence_analysis:
            print(f"\nConfidence Analysis:")
            print(f"  Average confidence: {results.confidence_analysis['avg_confidence']:.3f}")
            print(f"  Average uncertainty: {results.confidence_analysis['avg_uncertainty']:.3f}")
            print(f"  High confidence predictions: {results.confidence_analysis['high_confidence_predictions']}")
        
        if results.uncertainty_metrics:
            print(f"\nUncertainty Metrics:")
            print(f"  Calibration error: {results.uncertainty_metrics['calibration_error']:.3f}")
            print(f"  Calibration samples: {results.uncertainty_metrics['num_calibration_samples']}")
        
        if results.optimization_history:
            print(f"\nOptimization History:")
            for entry in results.optimization_history[-3:]:  # Show last 3 iterations
                print(f"  Iteration {entry['iteration']}: {entry['score']:.3f}")
    
    elif args.command == "ablation":
        logger.info("Running ablation study...")
        results = run_ablation_study(config)
        
        print("\n=== Ablation Study Results ===")
        for name, result in results.items():
            if result:
                summary = result.summary()
                print(f"\n{name}:")
                print(f"  Final accuracy: {summary['final_accuracy_a']:.3f}")
                print(f"  Agreement: {summary['final_agreement']:.3f}")
                print(f"  Reconciliation: {summary['final_reconciliation']:.3f}")
    
    elif args.command == "confidence":
        logger.info("Running confidence analysis...")
        results = run_confidence_analysis(config)
        
        print("\n=== Confidence Analysis Results ===")
        print(f"Accuracy without confidence: {results['accuracy_without_confidence']:.3f}")
        print(f"Accuracy with confidence: {results['accuracy_with_confidence']:.3f}")
        print(f"Confidence-weighted accuracy: {results['confidence_weighted_accuracy']:.3f}")
        print(f"Improvement: {results['improvement']:+.3f}")


if __name__ == "__main__":
    main()