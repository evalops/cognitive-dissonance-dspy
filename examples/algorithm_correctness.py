#!/usr/bin/env python3
"""
Example: Algorithm correctness verification with cognitive dissonance detection.

This example demonstrates formal verification of sorting algorithm claims,
testing more complex theorem proving scenarios including:
- Sorting correctness (permutation preservation + ordering)
- Search algorithm properties
- Data structure invariants
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


def create_sorting_claims() -> list[Claim]:
    """Create conflicting claims about sorting algorithm correctness."""
    return [
        # Correct sorting claims
        Claim(
            agent_id="alice",
            claim_text="quicksort correctly sorts the input array",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.90,
            timestamp=time.time()
        ),
        Claim(
            agent_id="bob",
            claim_text="mergesort preserves all elements while sorting",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.95,
            timestamp=time.time()
        ),

        # Conflicting complexity claims
        Claim(
            agent_id="charlie",
            claim_text="quicksort has time complexity O(n log n)",
            property_type=PropertyType.TIME_COMPLEXITY,
            confidence=0.80,
            timestamp=time.time()
        ),
        Claim(
            agent_id="dave",
            claim_text="quicksort has time complexity O(n^2) in worst case",
            property_type=PropertyType.TIME_COMPLEXITY,
            confidence=0.85,
            timestamp=time.time()
        ),

        # Memory safety claims
        Claim(
            agent_id="eve",
            claim_text="bubble_sort is memory safe with no buffer overflows",
            property_type=PropertyType.MEMORY_SAFETY,
            confidence=0.92,
            timestamp=time.time()
        )
    ]


def create_search_claims() -> list[Claim]:
    """Create claims about search algorithm properties."""
    return [
        Claim(
            agent_id="frank",
            claim_text="binary_search returns the correct index when element exists",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.88,
            timestamp=time.time()
        ),
        Claim(
            agent_id="grace",
            claim_text="linear_search finds the maximum element correctly",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.93,
            timestamp=time.time()
        ),

        # Complexity comparison
        Claim(
            agent_id="henry",
            claim_text="binary_search has time complexity O(log n)",
            property_type=PropertyType.TIME_COMPLEXITY,
            confidence=0.94,
            timestamp=time.time()
        ),
        Claim(
            agent_id="iris",
            claim_text="linear_search has time complexity O(n)",
            property_type=PropertyType.TIME_COMPLEXITY,
            confidence=0.91,
            timestamp=time.time()
        )
    ]


def print_algorithm_analysis_results(results: dict, domain_name: str):
    """Print formatted algorithm verification results."""
    print("🔍 ALGORITHM CORRECTNESS FORMAL VERIFICATION")
    print("=" * 60)
    print(f"Domain: {domain_name}")
    print(f"Total Claims: {results['summary']['total_claims']}")
    print(f"Conflicts Detected: {results['summary']['conflicts_detected']}")
    print()

    print("📊 ALGORITHM PROOF RESULTS:")
    for result in results['proof_results']:
        status = "✅ FORMALLY VERIFIED" if result.proven else "❌ PROOF FAILED"
        agent = result.spec.claim.agent_id
        claim = result.spec.claim.claim_text
        confidence = result.spec.claim.confidence
        prop_type = result.spec.claim.property_type.value

        print(f"{status}")
        print(f"  Agent: {agent} | Confidence: {confidence:.0%} | Type: {prop_type}")
        print(f"  Claim: '{claim}'")
        print(f"  Verification time: {result.proof_time_ms:.1f}ms")

        if not result.proven and result.error_message:
            error_lines = result.error_message.split('\n')
            relevant_error = next((line for line in error_lines if any(keyword in line for keyword in ['Error:', 'Warning:', 'File'])), "Proof verification failed")
            print(f"  Verification error: {relevant_error[:100]}...")

        print()

    if results['conflicts']:
        print("⚔️  ALGORITHM CONFLICTS DETECTED:")
        for i, (spec1, spec2) in enumerate(results['conflicts']):
            print(f"  {i+1}. '{spec1.claim.claim_text}' vs '{spec2.claim.claim_text}'")
        print()

    print("🏆 AGENT ALGORITHM CORRECTNESS RANKINGS:")
    for agent, accuracy in results['resolution']['agent_rankings'].items():
        print(f"  {agent}: {accuracy:.1%} formal verification success rate")

    print()
    print("📋 ALGORITHM VERIFICATION SUMMARY:")
    summary = results['summary']
    print(f"  • {summary['mathematically_proven']} algorithm properties formally proven")
    print(f"  • {summary['mathematically_disproven']} algorithm claims failed verification")
    print(f"  • {summary['conflicts_detected']} algorithmic conflicts resolved")
    print(f"  • Average proof time: {summary['average_proof_time_ms']:.1f}ms")
    print(f"  • Formal correctness established: {summary['has_ground_truth']}")


def test_sorting_algorithms():
    """Test formal verification of sorting algorithm claims."""
    print("🔄 Testing Sorting Algorithm Formal Verification...\n")

    detector = FormalVerificationConflictDetector(timeout_seconds=30)
    claims = create_sorting_claims()

    # Provide sample sorting algorithm code for analysis
    sorting_code = """
fn quicksort(arr: &mut [i32]) {
    if arr.len() <= 1 { return; }
    let pivot = partition(arr);
    quicksort(&mut arr[0..pivot]);
    quicksort(&mut arr[pivot+1..]);
}

fn mergesort(arr: &[i32]) -> Vec<i32> {
    if arr.len() <= 1 { return arr.to_vec(); }
    let mid = arr.len() / 2;
    merge(mergesort(&arr[0..mid]), mergesort(&arr[mid..]))
}

fn bubble_sort(arr: &mut [i32]) {
    for i in 0..arr.len() {
        for j in 0..arr.len()-1-i {
            if arr[j] > arr[j+1] {
                arr.swap(j, j+1);
            }
        }
    }
}
"""

    try:
        results = detector.analyze_claims(claims, sorting_code)
        print_algorithm_analysis_results(results, "Sorting Algorithms")
        return results

    except Exception as e:
        logger.error(f"Sorting algorithm verification failed: {e}")
        print(f"❌ Sorting verification failed: {e}")
        return None


def test_search_algorithms():
    """Test formal verification of search algorithm claims."""
    print("\n🔍 Testing Search Algorithm Formal Verification...\n")

    detector = FormalVerificationConflictDetector(timeout_seconds=30)
    claims = create_search_claims()

    # Provide sample search algorithm code
    search_code = """
fn binary_search(arr: &[i32], target: i32) -> Option<usize> {
    let mut left = 0;
    let mut right = arr.len();
    while left < right {
        let mid = (left + right) / 2;
        if arr[mid] == target { return Some(mid); }
        if arr[mid] < target { left = mid + 1; }
        else { right = mid; }
    }
    None
}

fn linear_search(arr: &[i32]) -> i32 {
    let mut max = arr[0];
    for &x in arr.iter() {
        if x > max { max = x; }
    }
    max
}
"""

    try:
        results = detector.analyze_claims(claims, search_code)
        print_algorithm_analysis_results(results, "Search Algorithms")
        return results

    except Exception as e:
        logger.error(f"Search algorithm verification failed: {e}")
        print(f"❌ Search verification failed: {e}")
        return None


def main():
    """Main algorithm correctness verification demo."""
    print("Starting Algorithm Correctness Formal Verification Demo...\n")

    # Test sorting algorithms
    sorting_results = test_sorting_algorithms()

    # Test search algorithms
    search_results = test_search_algorithms()

    # Summary of complex theorem proving capabilities
    if sorting_results and search_results:
        total_claims = sorting_results['summary']['total_claims'] + search_results['summary']['total_claims']
        total_proven = sorting_results['summary']['mathematically_proven'] + search_results['summary']['mathematically_proven']
        avg_time = (sorting_results['summary']['average_proof_time_ms'] + search_results['summary']['average_proof_time_ms']) / 2

        print("\n🎯 COMPLEX THEOREM PROVING SUMMARY:")
        print("=" * 50)
        print(f"Total Algorithm Claims Analyzed: {total_claims}")
        print(f"Successfully Verified: {total_proven}")
        print(f"Average Verification Time: {avg_time:.1f}ms")
        print(f"Verification Success Rate: {total_proven/total_claims:.1%}")
        print("\nDemonstrated formal verification capabilities:")
        print("✓ Sorting correctness proofs (permutation + ordering)")
        print("✓ Algorithm complexity analysis")
        print("✓ Memory safety verification")
        print("✓ Search algorithm properties")
        print("✓ Multi-agent conflict resolution via theorem proving")

    print("\n✅ Complex algorithm correctness verification complete!")
    return 0


if __name__ == "__main__":
    exit(main())
