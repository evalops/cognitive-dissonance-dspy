#!/usr/bin/env python3
"""
Demonstrate proof debugging and specification inference.

This shows how the system helps developers understand and fix proof failures,
and how it can convert test suites into formal specifications.
"""

import time
import logging

from formal_verification import (
    FormalVerificationConflictDetector,
    Claim,
    PropertyType
)
from formal_verification.proof_debugger import ProofDebugger, InteractiveProofAssistant
from formal_verification.spec_inference import SpecificationSynthesizer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demonstrate_proof_debugging():
    """Demonstrate the proof debugging system."""
    print("🔍 PROOF DEBUGGING DEMONSTRATION")
    print("=" * 60)
    print("When proofs fail, we provide actionable feedback:\n")

    # Create claims that will fail for different reasons
    failing_claims = [
        # Wrong arithmetic (unification error)
        Claim("test1", "10 + 15 = 26", PropertyType.CORRECTNESS, 0.95, time.time()),

        # Undefined variable (needs intros)
        Claim("test2", "forall x, x > 0 implies x >= 1", PropertyType.CORRECTNESS, 0.90, time.time()),

        # Wrong factorial value
        Claim("test3", "factorial 5 = 100", PropertyType.CORRECTNESS, 0.88, time.time()),
    ]

    detector = FormalVerificationConflictDetector()
    debugger = ProofDebugger()
    assistant = InteractiveProofAssistant()

    results = detector.analyze_claims(failing_claims)

    for result in results['proof_results']:
        if result.spec and not result.proven:
            print(f"\n❌ Failed Proof: '{result.spec.claim.claim_text}'")
            print("-" * 40)

            # Get debugging explanation
            explanation = assistant.explain_failure(result.spec, result)
            print(explanation)

            # Show automated repair if available
            diagnosis = debugger.diagnose_failure(result.spec, result)
            repair = debugger.suggest_repair(result.spec, diagnosis)

            if repair:
                print("\n🔧 Automated Repair:")
                print(f"   {repair.description}")
                print(f"   Confidence: {repair.confidence:.0%}")

                # Show modified proof snippet
                if len(repair.modified_coq) < 500:
                    print("\n📝 Modified Proof Code:")
                    proof_section = repair.modified_coq.split('Proof.')[1].split('Qed.')[0] if 'Proof.' in repair.modified_coq else ""
                    if proof_section:
                        print(f"   Proof.{proof_section}   Qed.")

            print()

    # Show successful proof for comparison
    success_claim = Claim("test4", "10 + 15 = 25", PropertyType.CORRECTNESS, 0.95, time.time())
    success_results = detector.analyze_claims([success_claim])

    if success_results['proof_results'][0].proven:
        print("\n✅ Successful Proof (for comparison): '10 + 15 = 25'")
        print("   This proof succeeded because the arithmetic is correct.")

    return results


def demonstrate_spec_inference():
    """Demonstrate specification inference from tests."""
    print("\n\n📊 SPECIFICATION INFERENCE FROM TESTS")
    print("=" * 60)
    print("Converting test suites to formal specifications:\n")

    # Sample test code
    test_code = '''
def test_addition():
    assert add(2, 3) == 5
    assert add(10, 15) == 25
    assert add(0, 0) == 0
    assert add(100, 200) == 300

def test_multiplication():
    assert multiply(3, 4) == 12
    assert multiply(5, 6) == 30
    assert multiply(0, 10) == 0
    assert multiply(1, 7) == 7

def test_factorial():
    assert factorial(0) == 1
    assert factorial(1) == 1
    assert factorial(5) == 120
    assert factorial(6) == 720

def test_max_function():
    assert max_of_list([1, 5, 3]) == 5
    assert max_of_list([10, 2, 8, 15, 3]) == 15
    assert max_of_list([7]) == 7

def test_is_sorted():
    assert is_sorted([1, 2, 3, 4]) == True
    assert is_sorted([4, 3, 2, 1]) == False
    assert is_sorted([1, 3, 2]) == False
    assert is_sorted([5, 5, 5]) == True
'''

    synthesizer = SpecificationSynthesizer()

    # Analyze the tests
    specs = synthesizer.test_analyzer.analyze_test_file(test_code)

    print(f"📝 Found {len(specs)} function specifications from tests:\n")

    for spec in specs:
        print(f"Function: {spec.function_name}")
        print(f"  Examples: {len(spec.examples)} test cases")

        if spec.patterns:
            print(f"  Patterns: {', '.join(spec.patterns)}")

        if spec.preconditions:
            print(f"  Preconditions: {', '.join(spec.preconditions)}")

        if spec.postconditions:
            print(f"  Postconditions: {', '.join(spec.postconditions)}")

        # Generate Coq specification
        coq_spec = synthesizer._synthesize_coq_from_spec(spec)
        if coq_spec:
            lines = coq_spec.split('\n')
            theorems = [l for l in lines if l.startswith('Theorem')]
            print(f"  Generated {len(theorems)} Coq theorems")

        print()

    # Show example of generated Coq code
    if specs:
        print("📄 Example Generated Coq Specification:")
        print("-" * 40)
        example_spec = specs[0]
        coq_code = synthesizer._synthesize_coq_from_spec(example_spec)
        if coq_code:
            # Show first few lines
            lines = coq_code.split('\n')[:15]
            for line in lines:
                print(line)
            if len(coq_code.split('\n')) > 15:
                print("...")

    return specs


def demonstrate_guided_proof_development():
    """Demonstrate step-by-step proof guidance."""
    print("\n\n👨‍🏫 GUIDED PROOF DEVELOPMENT")
    print("=" * 60)
    print("Step-by-step guidance for developing proofs:\n")

    assistant = InteractiveProofAssistant()

    # Examples of different proof types
    examples = [
        ("5 + 3 = 8", "arithmetic"),
        ("10 < 20", "inequality"),
        ("forall n, n * 0 = 0", "universal"),
        ("if x > 5 then x > 3", "implication"),
    ]

    for claim_text, proof_type in examples:
        print(f"📌 Proving: '{claim_text}' ({proof_type} proof)")

        # Create a spec (simplified)
        from formal_verification.types import FormalSpec
        claim = Claim("guide", claim_text, PropertyType.CORRECTNESS, 0.9, time.time())
        spec = FormalSpec(
            claim=claim,
            spec_text=f"Prove {claim_text}",
            coq_code="",
            variables={}
        )

        # Get step-by-step guidance
        steps = assistant.get_step_by_step_guidance(spec)
        for step in steps:
            print(f"   {step}")
        print()

    return examples


def main():
    """Main demonstration."""
    print("Starting Proof Debugging and Inference Demo...\n")

    # Demonstrate proof debugging
    demonstrate_proof_debugging()

    # Demonstrate specification inference
    demonstrate_spec_inference()

    # Demonstrate guided proof development
    demonstrate_guided_proof_development()

    print("\n" + "=" * 60)
    print("🎯 KEY CAPABILITIES DEMONSTRATED:")
    print("• Actionable debugging feedback for failed proofs")
    print("• Automated proof repair suggestions")
    print("• Specification inference from test suites")
    print("• Step-by-step proof development guidance")
    print("• Converting tests to formal theorems")

    print("\n💡 IMPACT:")
    print("This makes formal verification accessible to developers by:")
    print("1. Explaining proof failures in plain English")
    print("2. Suggesting concrete fixes")
    print("3. Learning from existing tests")
    print("4. Providing interactive guidance")

    print("\n✅ Proof debugging and inference systems ready!")

    return 0


if __name__ == "__main__":
    exit(main())
