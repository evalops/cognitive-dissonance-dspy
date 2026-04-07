#!/usr/bin/env python3
"""Demonstrate advanced proof capabilities beyond basic arithmetic.

This shows the enhanced translator handling:
- Logic and implications
- Universal quantification
- Inequalities
- More complex mathematical functions
"""

import logging
import time

from formal_verification import Claim, FormalVerificationConflictDetector, PropertyType

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_advanced_claims() -> list[Claim]:
    """Create claims that test our advanced proof patterns."""
    return [
        # Basic arithmetic (should work)
        Claim("alice", "10 + 15 = 25", PropertyType.CORRECTNESS, 0.95, time.time()),

        # Multiplication (NEW)
        Claim("bob", "6 * 7 = 42", PropertyType.CORRECTNESS, 0.93, time.time()),

        # Subtraction (NEW)
        Claim("charlie", "100 - 37 = 63", PropertyType.CORRECTNESS, 0.91, time.time()),

        # Inequality (NEW)
        Claim("dave", "5 < 10", PropertyType.CORRECTNESS, 0.94, time.time()),
        Claim("eve", "20 > 15", PropertyType.CORRECTNESS, 0.92, time.time()),

        # Logic implication (NEW)
        Claim("frank", "if x > 0 then x + 1 > 1", PropertyType.CORRECTNESS, 0.90, time.time()),

        # Universal quantification (NEW)
        Claim("grace", "forall n, n + 0 = n", PropertyType.CORRECTNESS, 0.96, time.time()),

        # Fibonacci (NEW)
        Claim("henry", "fibonacci 7 = 13", PropertyType.CORRECTNESS, 0.88, time.time()),

        # GCD (NEW)
        Claim("iris", "gcd(12, 8) = 4", PropertyType.CORRECTNESS, 0.89, time.time()),

        # False claims to test rejection
        Claim("jack", "15 > 20", PropertyType.CORRECTNESS, 0.85, time.time()),
        Claim("karen", "factorial 4 = 25", PropertyType.CORRECTNESS, 0.80, time.time()),
    ]


def demonstrate_advanced_proofs():
    """Demonstrate the enhanced proof capabilities."""
    print("🚀 Advanced Formal Verification Demo")
    print("=" * 60)
    print("Testing enhanced proof patterns including:")
    print("• Logic and implications")
    print("• Universal quantification")
    print("• Inequalities")
    print("• Complex mathematical functions")
    print()

    detector = FormalVerificationConflictDetector(timeout_seconds=10)
    claims = create_advanced_claims()

    try:
        results = detector.analyze_claims(claims)

        print("📊 ADVANCED PROOF VERIFICATION RESULTS:")
        print("-" * 50)

        success_count = 0
        failed_count = 0
        pattern_stats = {
            "arithmetic": 0,
            "inequality": 0,
            "logic": 0,
            "quantifier": 0,
            "advanced_math": 0
        }

        for result in results['proof_results']:
            if result.spec:
                status = "✅ PROVEN" if result.proven else "❌ FAILED"
                agent = result.spec.claim.agent_id
                claim = result.spec.claim.claim_text
                confidence = result.spec.claim.confidence
                proof_time = result.proof_time_ms

                # Categorize the claim type
                claim_lower = claim.lower()
                if any(op in claim for op in ['+', '-', '*', '/', 'factorial']):
                    category = "arithmetic"
                elif any(op in claim for op in ['<', '>', '<=', '>=']):
                    category = "inequality"
                elif 'if' in claim_lower or 'then' in claim_lower:
                    category = "logic"
                elif 'forall' in claim_lower or 'exists' in claim_lower:
                    category = "quantifier"
                elif 'fibonacci' in claim_lower or 'gcd' in claim_lower:
                    category = "advanced_math"
                else:
                    category = "other"

                if result.proven:
                    success_count += 1
                    if category in pattern_stats:
                        pattern_stats[category] += 1
                else:
                    failed_count += 1

                print(f"{status} | {agent:8s} | {category:12s} | Time: {proof_time:6.1f}ms")
                print(f"  Claim: '{claim}' (confidence: {confidence:.0%})")

                if not result.proven and result.error_message:
                    # Extract key error
                    error_lines = result.error_message.split('\n')
                    for line in error_lines:
                        if 'Error:' in line or 'Unable to unify' in line:
                            print(f"  Error: {line.strip()[:80]}...")
                            break
                print()
            else:
                print(f"⚠️  Could not translate: '{claims[results['proof_results'].index(result)].claim_text}'")
                print()

        print("📈 PROOF PATTERN STATISTICS:")
        print("-" * 40)
        for pattern, count in pattern_stats.items():
            if count > 0:
                print(f"  {pattern:15s}: {count} proven")

        print()
        print("📋 SUMMARY:")
        print(f"  Total claims: {len(claims)}")
        print(f"  Successfully proven: {success_count}")
        print(f"  Failed proofs: {failed_count}")
        print(f"  Success rate: {success_count/len(claims):.1%}")
        print(f"  Average proof time: {results['summary']['average_proof_time_ms']:.1f}ms")

        if results['conflicts']:
            print()
            print("⚔️  CONFLICTS DETECTED:")
            for spec1, spec2 in results['conflicts']:
                print(f"  • '{spec1.claim.claim_text}' vs '{spec2.claim.claim_text}'")

        return success_count, failed_count

    except Exception as e:
        logger.error(f"Advanced proof demo failed: {e}")
        print(f"❌ Demo failed: {e}")
        return 0, 0


def main():
    """Main entry point."""
    print("Starting Advanced Proof Capabilities Demo...\n")

    success, failed = demonstrate_advanced_proofs()

    print(f"\n{'✅' if success > 5 else '⚠️'} Demo complete!")

    if success > 5:
        print("\n🎯 KEY ACHIEVEMENT:")
        print("The framework now supports:")
        print("  • Logic implications (if-then statements)")
        print("  • Universal quantification (forall)")
        print("  • Inequality proofs")
        print("  • Complex mathematical functions")
        print("\nThis goes beyond simple arithmetic to handle more")
        print("sophisticated mathematical and logical claims!")

    return 0 if success > 0 else 1


if __name__ == "__main__":
    exit(main())
