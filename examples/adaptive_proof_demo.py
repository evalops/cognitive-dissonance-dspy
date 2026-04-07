#!/usr/bin/env python3
"""
Demonstrate the adaptive proof system that learns from successes.

This shows how the framework improves its proof capabilities over time
by learning successful proof strategies and applying them to new problems.
"""

import logging
import time

from formal_verification.code_analyzer import CodeAnalyzer, SpecificationSynthesizer
from formal_verification.proof_strategies import AdaptiveProver

from formal_verification import Claim, FormalVerificationConflictDetector, PropertyType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demonstrate_code_analysis():
    """Demonstrate automatic specification extraction from code."""
    print("📝 CODE ANALYSIS AND SPECIFICATION EXTRACTION")
    print("=" * 60)

    analyzer = CodeAnalyzer()
    synthesizer = SpecificationSynthesizer()

    # Sample Python code with docstring contracts
    python_code = '''
def factorial(n: int) -> int:
    """
    Calculate factorial of n.

    Precondition: n >= 0
    Postcondition: Returns n! = n * (n-1) * ... * 1
    Complexity: O(n)
    """
    if n == 0:
        return 1
    return n * factorial(n - 1)

def binary_search(arr: list, target: int) -> int:
    """
    Binary search in sorted array.

    Precondition: arr is sorted in ascending order
    Postcondition: Returns index of target or -1 if not found
    Complexity: O(log n)
    """
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1

def bubble_sort(arr: list) -> list:
    """
    Sort array using bubble sort.

    Postcondition: Returns sorted array
    Complexity: O(n^2)
    """
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr
'''

    # Analyze the code
    specs = analyzer.analyze(python_code, language="python")

    print(f"Found {len(specs)} function specifications:\n")

    for spec in specs:
        print(f"📌 Function: {spec.function_name}")
        print(f"   Parameters: {spec.parameters}")
        print(f"   Return type: {spec.return_type}")

        if spec.preconditions:
            print(f"   Preconditions: {spec.preconditions}")
        if spec.postconditions:
            print(f"   Postconditions: {spec.postconditions}")
        if spec.complexity:
            print(f"   Complexity: {spec.complexity}")

        # Synthesize Coq specification
        coq_spec = synthesizer.synthesize_coq_spec(spec)
        if coq_spec:
            print(f"   ✅ Generated Coq specification ({len(coq_spec.split(chr(10)))} lines)")
        print()

    return specs


def demonstrate_adaptive_learning():
    """Demonstrate how the system learns from successful proofs."""
    print("\n🧠 ADAPTIVE PROOF LEARNING")
    print("=" * 60)

    # Create training claims
    training_claims = [
        # Simple arithmetic that should succeed
        Claim("trainer1", "5 + 3 = 8", PropertyType.CORRECTNESS, 0.95, time.time()),
        Claim("trainer2", "10 * 4 = 40", PropertyType.CORRECTNESS, 0.93, time.time()),
        Claim("trainer3", "100 - 25 = 75", PropertyType.CORRECTNESS, 0.91, time.time()),

        # Inequalities
        Claim("trainer4", "7 < 15", PropertyType.CORRECTNESS, 0.92, time.time()),
        Claim("trainer5", "20 > 10", PropertyType.CORRECTNESS, 0.94, time.time()),

        # Quantifiers
        Claim("trainer6", "forall x, x + 0 = x", PropertyType.CORRECTNESS, 0.96, time.time()),
    ]

    detector = FormalVerificationConflictDetector()
    adaptive_prover = AdaptiveProver()

    print("Training Phase - Learning proof strategies:")
    print("-" * 40)

    # Train the system
    results = detector.analyze_claims(training_claims)
    successful_strategies = 0

    for result in results['proof_results']:
        if result.proven and result.spec:
            # Learn from successful proof
            adaptive_prover.synthesizer.learner.learn_from_proof(result.spec, result)
            successful_strategies += 1
            print(f"✅ Learned from: {result.spec.claim.claim_text}")

    print(f"\nLearned {successful_strategies} successful proof strategies")

    # Now test with new claims
    test_claims = [
        # Similar patterns to training
        Claim("test1", "8 + 7 = 15", PropertyType.CORRECTNESS, 0.90, time.time()),
        Claim("test2", "12 < 25", PropertyType.CORRECTNESS, 0.88, time.time()),

        # Slightly different patterns
        Claim("test3", "forall n, n * 1 = n", PropertyType.CORRECTNESS, 0.89, time.time()),
        Claim("test4", "50 - 30 = 20", PropertyType.CORRECTNESS, 0.87, time.time()),
    ]

    print("\n\nTesting Phase - Applying learned strategies:")
    print("-" * 40)

    test_results = detector.analyze_claims(test_claims)
    success_count = 0

    for result in test_results['proof_results']:
        if result.spec:
            # Try adaptive proving
            adaptive_result = adaptive_prover.prove_adaptive(result.spec)

            if adaptive_result.proven:
                print(f"✅ PROVEN using learned strategy: {result.spec.claim.claim_text}")
                print(f"   Proof time: {adaptive_result.proof_time_ms:.1f}ms")
                success_count += 1
            else:
                print(f"❌ Could not prove: {result.spec.claim.claim_text}")

    # Show statistics
    stats = adaptive_prover.get_statistics()
    strategies = adaptive_prover.synthesizer.learner.strategies

    print("\n📊 ADAPTIVE LEARNING STATISTICS:")
    print(f"   Strategies learned: {stats['strategies_learned']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    print(f"   Total attempts: {stats['total_attempts']}")

    if strategies:
        print("\n📚 Learned Proof Patterns:")
        for _key, strategy in list(strategies.items())[:3]:  # Show first 3
            print(f"   • {strategy.pattern_type}: {strategy.tactics_sequence}")
            print(f"     Success rate: {strategy.success_rate:.1%}, Avg time: {strategy.avg_proof_time_ms:.1f}ms")

    return stats


def demonstrate_proof_improvement():
    """Show how the system improves proofs over iterations."""
    print("\n\n📈 PROOF IMPROVEMENT OVER TIME")
    print("=" * 60)

    # Create a series of similar problems
    problem_batches = [
        # Batch 1: Simple arithmetic
        [
            Claim("batch1_1", "2 + 3 = 5", PropertyType.CORRECTNESS, 0.95, time.time()),
            Claim("batch1_2", "4 + 6 = 10", PropertyType.CORRECTNESS, 0.93, time.time()),
            Claim("batch1_3", "7 + 8 = 15", PropertyType.CORRECTNESS, 0.91, time.time()),
        ],
        # Batch 2: More arithmetic (should be faster)
        [
            Claim("batch2_1", "10 + 20 = 30", PropertyType.CORRECTNESS, 0.94, time.time()),
            Claim("batch2_2", "15 + 25 = 40", PropertyType.CORRECTNESS, 0.92, time.time()),
            Claim("batch2_3", "30 + 70 = 100", PropertyType.CORRECTNESS, 0.90, time.time()),
        ],
        # Batch 3: Even more (should be even faster with caching)
        [
            Claim("batch3_1", "100 + 200 = 300", PropertyType.CORRECTNESS, 0.93, time.time()),
            Claim("batch3_2", "250 + 250 = 500", PropertyType.CORRECTNESS, 0.91, time.time()),
            Claim("batch3_3", "333 + 667 = 1000", PropertyType.CORRECTNESS, 0.89, time.time()),
        ],
    ]

    detector = FormalVerificationConflictDetector()
    batch_times = []

    for i, batch in enumerate(problem_batches, 1):
        print(f"\nBatch {i} - Processing {len(batch)} claims:")
        start_time = time.time()

        results = detector.analyze_claims(batch)

        batch_time = (time.time() - start_time) * 1000
        batch_times.append(batch_time)

        avg_proof_time = results['summary']['average_proof_time_ms']
        success_rate = results['summary']['mathematically_proven'] / len(batch)

        print(f"  Total time: {batch_time:.1f}ms")
        print(f"  Average proof time: {avg_proof_time:.1f}ms")
        print(f"  Success rate: {success_rate:.1%}")

        # Show cache impact
        cache_stats = detector.prover.get_cache_stats()
        if 'hit_rate' in cache_stats:
            print(f"  Cache hit rate: {cache_stats['hit_rate']:.1%}")

    # Show improvement
    if len(batch_times) >= 2:
        speedup = batch_times[0] / batch_times[-1]
        print("\n🚀 Performance Improvement:")
        print(f"   First batch: {batch_times[0]:.1f}ms")
        print(f"   Last batch: {batch_times[-1]:.1f}ms")
        print(f"   Speedup: {speedup:.1f}x")

    return batch_times


def main():
    """Main demonstration."""
    print("Starting Adaptive Proof System Demo...\n")

    # Demonstrate code analysis
    demonstrate_code_analysis()

    # Demonstrate adaptive learning
    learning_stats = demonstrate_adaptive_learning()

    # Demonstrate improvement over time
    demonstrate_proof_improvement()

    print("\n" + "=" * 60)
    print("🎯 KEY ACHIEVEMENTS:")
    print("• Automatic extraction of specifications from code")
    print("• Learning successful proof strategies from examples")
    print("• Adaptive proof synthesis based on learned patterns")
    print("• Performance improvement through caching and learning")

    if learning_stats['success_rate'] > 0.7:
        print("\n✅ Successfully demonstrated adaptive proof learning!")
        print("   The system is learning and improving its proof capabilities.")
    else:
        print("\n⚠️ Adaptive learning needs more training examples.")

    return 0


if __name__ == "__main__":
    exit(main())
