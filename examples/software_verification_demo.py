#!/usr/bin/env python3
"""
Demonstrate formal verification of actual software properties.

This shows the framework verifying real code properties that agents
might disagree about, not just abstract mathematical claims.
"""

import time
import logging
from typing import List

from formal_verification import (
    FormalVerificationConflictDetector,
    Claim,
    PropertyType
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_software_property_claims() -> List[Claim]:
    """Create claims about actual software properties."""
    return [
        # Array bounds claims
        Claim("alice", "accessing array[5] when length is 10 is safe",
              PropertyType.MEMORY_SAFETY, 0.95, time.time()),
        Claim("bob", "accessing array[15] when length is 10 causes buffer overflow",
              PropertyType.MEMORY_SAFETY, 0.92, time.time()),

        # Loop termination claims
        Claim("charlie", "for loop from 0 to n terminates",
              PropertyType.TERMINATION, 0.90, time.time()),
        Claim("dave", "while(true) loop terminates",
              PropertyType.TERMINATION, 0.85, time.time()),

        # Algorithm complexity claims
        Claim("eve", "bubble sort has time complexity O(n^2)",
              PropertyType.TIME_COMPLEXITY, 0.88, time.time()),
        Claim("frank", "quick sort has time complexity O(n log n)",
              PropertyType.TIME_COMPLEXITY, 0.91, time.time()),

        # Function correctness claims
        Claim("grace", "max([3, 7, 2]) returns 7",
              PropertyType.CORRECTNESS, 0.94, time.time()),
        Claim("henry", "factorial(5) equals 120",
              PropertyType.CORRECTNESS, 0.96, time.time()),

        # Invariant claims
        Claim("iris", "sorted array remains sorted after binary search",
              PropertyType.CORRECTNESS, 0.89, time.time()),
        Claim("jack", "list size increases by 1 after append",
              PropertyType.CORRECTNESS, 0.93, time.time()),
    ]


def create_conflicting_implementation_claims() -> List[Claim]:
    """Create conflicting claims about the same implementation."""
    return [
        # Different agents claim different things about same function
        Claim("team_a", "our_sort correctly sorts the array",
              PropertyType.CORRECTNESS, 0.92, time.time()),
        Claim("team_b", "our_sort preserves all elements",
              PropertyType.CORRECTNESS, 0.88, time.time()),
        Claim("team_c", "our_sort has O(n log n) complexity",
              PropertyType.TIME_COMPLEXITY, 0.85, time.time()),

        # Conflicting security claims
        Claim("security_audit", "login function is memory safe",
              PropertyType.MEMORY_SAFETY, 0.90, time.time()),
        Claim("pen_tester", "login function has buffer overflow vulnerability",
              PropertyType.MEMORY_SAFETY, 0.87, time.time()),

        # Performance disagreement
        Claim("optimizer", "cache lookup is O(1)",
              PropertyType.TIME_COMPLEXITY, 0.94, time.time()),
        Claim("analyst", "cache lookup is O(log n)",
              PropertyType.TIME_COMPLEXITY, 0.91, time.time()),
    ]


def demonstrate_software_verification():
    """Demonstrate verification of real software properties."""
    print("🔧 Software Property Verification Demo")
    print("=" * 60)
    print("Testing formal verification of real software properties")
    print()

    detector = FormalVerificationConflictDetector(timeout_seconds=10)

    # Sample code context for analysis
    code_context = """
    fn bubble_sort(arr: &mut [i32]) {
        for i in 0..arr.len() {
            for j in 0..arr.len()-1-i {
                if arr[j] > arr[j+1] {
                    arr.swap(j, j+1);
                }
            }
        }
    }

    fn max(arr: &[i32]) -> i32 {
        let mut max_val = arr[0];
        for &val in arr {
            if val > max_val {
                max_val = val;
            }
        }
        max_val
    }

    fn factorial(n: u32) -> u32 {
        if n == 0 { 1 }
        else { n * factorial(n - 1) }
    }
    """

    # Test software property claims
    print("📊 VERIFYING SOFTWARE PROPERTIES:")
    print("-" * 50)

    claims = create_software_property_claims()
    results = detector.analyze_claims(claims, code_context)

    proven_properties = []
    unverified_properties = []

    for result in results['proof_results']:
        if result.spec:
            property_type = result.spec.claim.property_type.value
            claim_text = result.spec.claim.claim_text
            agent = result.spec.claim.agent_id

            if result.proven:
                status = "✅ VERIFIED"
                proven_properties.append((property_type, claim_text))
            else:
                status = "❌ UNVERIFIED"
                unverified_properties.append((property_type, claim_text))

            print(f"{status} | {agent:8s} | {property_type:15s}")
            print(f"  Claim: '{claim_text}'")
            print(f"  Time: {result.proof_time_ms:.1f}ms")

            if not result.proven and result.error_message:
                error_lines = result.error_message.split('\n')
                for line in error_lines[:2]:
                    if line.strip():
                        print(f"  Issue: {line.strip()[:70]}...")
                        break
            print()

    # Test conflicting implementation claims
    print("\n⚔️ RESOLVING CONFLICTING IMPLEMENTATION CLAIMS:")
    print("-" * 50)

    conflicting_claims = create_conflicting_implementation_claims()
    conflict_results = detector.analyze_claims(conflicting_claims, code_context)

    if conflict_results['conflicts']:
        print(f"Found {len(conflict_results['conflicts'])} conflicts:")
        for spec1, spec2 in conflict_results['conflicts']:
            print(f"  • {spec1.claim.agent_id}: '{spec1.claim.claim_text[:40]}...'")
            print("    vs")
            print(f"    {spec2.claim.agent_id}: '{spec2.claim.claim_text[:40]}...'")
            print()

    # Summary
    print("\n📋 SOFTWARE VERIFICATION SUMMARY:")
    print("-" * 50)
    print(f"Total property claims: {len(claims)}")
    print(f"Successfully verified: {len(proven_properties)}")
    print(f"Could not verify: {len(unverified_properties)}")

    if proven_properties:
        print("\n✅ Verified Properties:")
        for prop_type, claim in proven_properties[:5]:  # Show first 5
            print(f"  • [{prop_type}] {claim[:50]}...")

    print("\n🏆 Agent Rankings by Correctness:")
    rankings = results['resolution']['agent_rankings']
    for agent, accuracy in sorted(rankings.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {agent}: {accuracy:.0%} accuracy")

    return len(proven_properties), len(unverified_properties)


def demonstrate_code_review_scenario():
    """Simulate a code review where reviewers disagree."""
    print("\n\n👥 CODE REVIEW DISAGREEMENT RESOLUTION")
    print("=" * 60)
    print("Multiple reviewers disagree about a sorting implementation")
    print()

    detector = FormalVerificationConflictDetector(timeout_seconds=10)

    # Reviewers make conflicting claims about the same code
    review_claims = [
        Claim("alice_reviewer", "quicksort correctly sorts the input array",
              PropertyType.CORRECTNESS, 0.85, time.time()),
        Claim("bob_reviewer", "quicksort has worst-case O(n^2) complexity",
              PropertyType.TIME_COMPLEXITY, 0.90, time.time()),
        Claim("charlie_reviewer", "quicksort has average-case O(n log n) complexity",
              PropertyType.TIME_COMPLEXITY, 0.88, time.time()),
        Claim("dave_reviewer", "quicksort preserves all elements (permutation)",
              PropertyType.CORRECTNESS, 0.82, time.time()),
        Claim("eve_reviewer", "quicksort is not stable (doesn't preserve order of equal elements)",
              PropertyType.CORRECTNESS, 0.87, time.time()),
    ]

    # Analyze reviewer claims
    results = detector.analyze_claims(review_claims)

    print("📝 REVIEW CLAIMS ANALYSIS:")
    for result in results['proof_results']:
        if result.spec:
            reviewer = result.spec.claim.agent_id
            claim = result.spec.claim.claim_text
            confidence = result.spec.claim.confidence

            if result.proven:
                verdict = "✅ CORRECT"
            elif result.error_message and "Unable to unify" in result.error_message:
                verdict = "❌ INCORRECT"
            else:
                verdict = "⚠️  UNVERIFIABLE"

            print(f"{verdict} | {reviewer:15s} (confidence: {confidence:.0%})")
            print(f"         '{claim}'")

    # Determine consensus
    print("\n🎯 FORMAL VERIFICATION CONSENSUS:")
    proven_count = sum(1 for r in results['proof_results'] if r.proven)
    total_count = len(results['proof_results'])

    if proven_count > 0:
        print(f"Ground truth established for {proven_count}/{total_count} claims")
        print("Formal verification resolves the disagreement with mathematical certainty.")
    else:
        print("Unable to formally verify the claims - need human judgment.")

    return results


def main():
    """Main entry point."""
    print("Starting Software Property Verification Demo...\n")

    # Run software verification
    verified, unverified = demonstrate_software_verification()

    # Run code review scenario
    demonstrate_code_review_scenario()

    print("\n" + "=" * 60)
    print("🎯 KEY INSIGHTS:")
    print("• Formal verification can resolve disagreements about software properties")
    print("• Mathematical proofs provide ground truth when applicable")
    print("• Some properties (like algorithm complexity) need more sophisticated proofs")
    print("• The framework bridges the gap between informal claims and formal proofs")

    if verified > unverified:
        print("\n✅ Successfully demonstrated software property verification!")
    else:
        print("\n⚠️ More work needed on translating software properties to formal specs.")

    return 0


if __name__ == "__main__":
    exit(main())
