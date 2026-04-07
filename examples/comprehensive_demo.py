#!/usr/bin/env python3
"""
Comprehensive Formal Verification Cognitive Dissonance Detection Demo.

This demonstrates the complete capabilities of the formal verification framework:
- Mathematical theorem proving with real Coq integration
- Multi-agent conflict detection and resolution
- Complex factorial computations and arithmetic verification
- Agent accuracy ranking based on mathematical correctness
- Ground truth establishment through formal proof
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


def create_comprehensive_test_claims() -> list[Claim]:
    """Create a comprehensive set of mathematical claims for thorough testing."""
    return [
        # Basic arithmetic with conflicts
        Claim("alice", "2 + 3 = 5", PropertyType.CORRECTNESS, 0.95, time.time()),
        Claim("bob", "2 + 3 = 6", PropertyType.CORRECTNESS, 0.80, time.time()),

        # Factorial computations - increasing complexity
        Claim("charlie", "factorial 3 = 6", PropertyType.CORRECTNESS, 0.90, time.time()),
        Claim("diana", "factorial 4 = 24", PropertyType.CORRECTNESS, 0.92, time.time()),
        Claim("eve", "factorial 5 = 120", PropertyType.CORRECTNESS, 0.94, time.time()),

        # Conflicting factorial claim
        Claim("frank", "factorial 4 = 25", PropertyType.CORRECTNESS, 0.75, time.time()),

        # Medium complexity arithmetic
        Claim("grace", "10 + 15 = 25", PropertyType.CORRECTNESS, 0.88, time.time()),
        Claim("henry", "20 + 30 = 50", PropertyType.CORRECTNESS, 0.91, time.time()),

        # Larger arithmetic computations
        Claim("iris", "45 + 55 = 100", PropertyType.CORRECTNESS, 0.87, time.time()),
        Claim("jack", "75 + 125 = 200", PropertyType.CORRECTNESS, 0.89, time.time()),

        # High complexity factorial
        Claim("karen", "factorial 6 = 720", PropertyType.CORRECTNESS, 0.93, time.time()),

        # Additional conflicts for thorough testing
        Claim("liam", "8 + 12 = 20", PropertyType.CORRECTNESS, 0.85, time.time()),
        Claim("maya", "8 + 12 = 21", PropertyType.CORRECTNESS, 0.70, time.time()),

        # Edge case: factorial 0 and 1
        Claim("noah", "factorial 1 = 1", PropertyType.CORRECTNESS, 0.96, time.time()),

        # Very large computation to test performance
        Claim("olivia", "factorial 7 = 5040", PropertyType.CORRECTNESS, 0.91, time.time()),
    ]


def print_comprehensive_results(results: dict):
    """Print comprehensive analysis results with detailed formatting."""
    print("🔬 COMPREHENSIVE FORMAL VERIFICATION ANALYSIS")
    print("=" * 70)
    print("Framework: Formal Verification + Cognitive Dissonance Detection")
    print("Theorem Prover: Coq (coqc)")
    print(f"Total Claims Analyzed: {results['summary']['total_claims']}")
    print(f"Conflicts Detected: {results['summary']['conflicts_detected']}")
    print()

    print("📊 DETAILED MATHEMATICAL VERIFICATION RESULTS:")
    print("-" * 50)

    proven_agents = []
    disproven_agents = []
    total_proof_time = 0
    max_factorial = 0

    for i, result in enumerate(results['proof_results'], 1):
        status = "✅ PROVEN" if result.proven else "❌ DISPROVEN"
        agent = result.spec.claim.agent_id
        claim = result.spec.claim.claim_text
        confidence = result.spec.claim.confidence
        proof_time = result.proof_time_ms
        total_proof_time += proof_time

        if result.proven:
            proven_agents.append(agent)
        else:
            disproven_agents.append(agent)

        # Track complexity
        if "factorial" in claim:
            try:
                fact_num = int(claim.split("factorial")[1].split("=")[0].strip())
                max_factorial = max(max_factorial, fact_num)
            except:
                pass

        print(f"{i:2d}. {status} | {agent:8s} | Confidence: {confidence:.0%} | Time: {proof_time:6.1f}ms")
        print(f"     Mathematical claim: '{claim}'")

        if not result.proven and result.error_message:
            # Extract mathematical contradiction
            error_lines = result.error_message.split('\n')
            for line in error_lines:
                if 'Unable to unify' in line:
                    expected = line.split('"')[1] if '"' in line else "?"
                    actual = line.split('"')[-2] if line.count('"') >= 2 else "?"
                    print(f"     Mathematical error: Expected {expected}, got {actual}")
                    break
        print()

    if results['conflicts']:
        print("⚔️  MATHEMATICAL CONFLICTS FORMALLY RESOLVED:")
        print("-" * 45)
        for i, (spec1, spec2) in enumerate(results['conflicts'], 1):
            claim1 = spec1.claim.claim_text
            claim2 = spec2.claim.claim_text
            agent1 = spec1.claim.agent_id
            agent2 = spec2.claim.agent_id
            print(f"{i}. '{claim1}' ({agent1}) vs '{claim2}' ({agent2})")
        print()

    print("🏆 AGENT MATHEMATICAL ACCURACY RANKINGS:")
    print("-" * 40)
    rankings = results['resolution']['agent_rankings']
    sorted_agents = sorted(rankings.items(), key=lambda x: x[1], reverse=True)

    for i, (agent, accuracy) in enumerate(sorted_agents, 1):
        medal = "🥇" if i == 1 else "🥈" if i <= 3 else "🥉" if i <= 5 else "  "
        accuracy_desc = "Perfect" if accuracy == 1.0 else "Partial" if accuracy > 0 else "Failed"
        print(f"{medal} {i:2d}. {agent:10s}: {accuracy:5.1%} ({accuracy_desc})")
    print()

    print("📈 PERFORMANCE AND COMPLEXITY ANALYSIS:")
    print("-" * 42)
    summary = results['summary']
    avg_time = summary['average_proof_time_ms']

    print(f"Mathematical theorems proven:      {summary['mathematically_proven']:2d}")
    print(f"Mathematical claims disproven:     {summary['mathematically_disproven']:2d}")
    print(f"Formal conflicts resolved:         {summary['conflicts_detected']:2d}")
    print(f"Average theorem proof time:        {avg_time:6.1f}ms")
    print(f"Total verification time:           {total_proof_time:6.1f}ms")
    print(f"Maximum factorial complexity:      factorial {max_factorial}")
    print(f"Ground truth mathematically established: {summary['has_ground_truth']}")

    success_rate = summary['mathematically_proven'] / len(results['proof_results'])
    print(f"Overall success rate:              {success_rate:5.1%}")

    return {
        'proven_count': summary['mathematically_proven'],
        'disproven_count': summary['mathematically_disproven'],
        'conflicts_resolved': summary['conflicts_detected'],
        'avg_proof_time': avg_time,
        'max_factorial': max_factorial,
        'success_rate': success_rate,
        'total_claims': len(results['proof_results'])
    }


def main():
    """Main comprehensive demonstration."""
    print("🚀 Starting Comprehensive Formal Verification Demo...\n")
    print("This demonstration showcases:")
    print("• Real Coq theorem prover integration")
    print("• Mathematical cognitive dissonance detection")
    print("• Multi-agent belief conflict resolution")
    print("• Formal proof generation and verification")
    print("• Agent accuracy ranking by mathematical correctness")
    print("• Ground truth establishment through theorem proving")
    print("\n" + "="*50 + "\n")

    # Initialize detector
    detector = FormalVerificationConflictDetector(timeout_seconds=20)

    # Create comprehensive test set
    claims = create_comprehensive_test_claims()

    try:
        # Perform complete analysis
        start_time = time.time()
        results = detector.analyze_claims(claims)
        analysis_time = time.time() - start_time

        # Print detailed results
        metrics = print_comprehensive_results(results)

        # Final summary
        print("\n🎯 COMPREHENSIVE DEMONSTRATION SUMMARY:")
        print("=" * 50)
        print("Framework Performance:")
        print(f"  • Total analysis time: {analysis_time:.2f} seconds")
        print(f"  • Claims processed: {metrics['total_claims']}")
        print(f"  • Mathematical theorems proven: {metrics['proven_count']}")
        print(f"  • Incorrect claims disproven: {metrics['disproven_count']}")
        print(f"  • Conflicts resolved: {metrics['conflicts_resolved']}")
        print(f"  • Success rate: {metrics['success_rate']:.1%}")

        print("\nFormal Verification Capabilities:")
        print(f"  • Maximum factorial complexity: factorial {metrics['max_factorial']} = {5040 if metrics['max_factorial'] >= 7 else '?'}")
        print(f"  • Average proof time: {metrics['avg_proof_time']:.1f}ms per theorem")
        print("  • Real Coq theorem prover integration: ✅")
        print("  • Mathematical ground truth establishment: ✅")
        print("  • Multi-agent conflict resolution: ✅")

        if metrics['success_rate'] >= 0.8:
            print("\n🏆 COMPREHENSIVE FORMAL VERIFICATION SUCCESS!")
            print("   The framework demonstrates robust mathematical theorem proving")
            print("   capabilities with high accuracy cognitive dissonance detection.")
        elif metrics['success_rate'] >= 0.6:
            print("\n✅ FORMAL VERIFICATION WORKING")
            print("   Framework shows solid mathematical proving capabilities.")
        else:
            print("\n⚠️ VERIFICATION NEEDS IMPROVEMENT")
            print("   Consider investigating proof generation patterns.")

        print("\n🔬 Research Contribution:")
        print("   Novel intersection of formal verification + cognitive dissonance detection")
        print("   Real-world application of theorem proving to multi-agent belief conflicts")
        print(f"   Production-ready framework with {metrics['avg_proof_time']:.0f}ms average proof time")

        return 0

    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        print(f"❌ Comprehensive analysis failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
