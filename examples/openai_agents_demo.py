"""
Demonstration of OpenAI Agents SDK integration for claim extraction.

This example shows how the new structured extraction approach improves
upon the DSPy-based approach by:
1. Producing claims that match translator patterns
2. Validating claims before proof attempts
3. Providing clear feedback on why claims fail
4. Achieving higher success rates

Run with:
    python examples/openai_agents_demo.py
"""

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from formal_verification.guardrails import ClaimGuardrails, GuardrailWithRetry
from formal_verification.hybrid_resolver import HybridCognitiveDissonanceResolver
from formal_verification.openai_agents import OpenAIClaimExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_basic_extraction():
    """Demonstrate basic claim extraction."""
    print("\n" + "="*80)
    print("DEMO 1: Basic Claim Extraction")
    print("="*80)

    extractor = OpenAIClaimExtractor()

    test_claims = [
        "Two plus two equals four",
        "The factorial of 5 is 120",
        "If x is greater than 5, then x is greater than 3",
        "The array is sorted correctly",
        "Three is less than five",
    ]

    for i, text in enumerate(test_claims, 1):
        print(f"\n--- Claim {i} ---")
        print(f"Input: {text}")

        result = extractor.extract_claim(text)

        if result.is_formalizable and result.claim:
            print(f"✓ Formalizable: {result.claim.category.value}")
            print(f"  Normalized: {result.claim.claim_text}")
            print(f"  Confidence: {result.claim.confidence:.2f}")
            print(f"  Variables: {result.claim.variables}")
            print(f"  Reasoning: {result.reasoning}")
        else:
            print("✗ Not formalizable")
            print(f"  Reasoning: {result.reasoning}")
            if result.alternative_formulation:
                print(f"  Suggestion: {result.alternative_formulation}")


def demo_with_guardrails():
    """Demonstrate claim extraction with guardrails."""
    print("\n" + "="*80)
    print("DEMO 2: Extraction with Guardrails")
    print("="*80)

    extractor = OpenAIClaimExtractor()
    guardrails = ClaimGuardrails(strict=False)
    guarded_extractor = GuardrailWithRetry(extractor, guardrails, max_retries=2)

    test_claims = [
        "2 + 2 = 4",
        "factorial 7 = 5040",
        "forall n, n + 0 = n",
    ]

    for i, text in enumerate(test_claims, 1):
        print(f"\n--- Claim {i} ---")
        print(f"Input: {text}")

        claim, validation = guarded_extractor.extract_with_validation(text)

        if validation.passed:
            print("✓ Passed guardrails")
            print(f"  Claim: {claim.claim_text}")
            print(f"  Category: {claim.category.value}")
            print(f"  Confidence: {claim.confidence:.2f}")
        else:
            print(f"✗ Failed guardrails ({len(validation.violations)} violations)")
            for violation in validation.violations:
                print(f"  - [{violation.severity}] {violation.message}")
                if violation.suggestion:
                    print(f"    Suggestion: {violation.suggestion}")


def demo_full_analysis():
    """Demonstrate full claim analysis with proof."""
    print("\n" + "="*80)
    print("DEMO 3: Full Claim Analysis with Proof")
    print("="*80)

    resolver = HybridCognitiveDissonanceResolver(use_guardrails=True)

    test_claims = [
        "2 + 2 = 4",
        "2 + 2 = 5",  # This should be disproven
        "factorial 5 = 120",
        "3 < 5",
    ]

    for i, text in enumerate(test_claims, 1):
        print(f"\n--- Claim {i} ---")
        print(f"Input: {text}")

        analysis = resolver.analyze_claim(text)

        print(f"Original: {analysis.original_text}")
        print(f"Formalizable: {analysis.is_formalizable}")

        if analysis.formalized_claim:
            print(f"Category: {analysis.formalized_claim.category.value}")
            print(f"Normalized: {analysis.formalized_claim.claim_text}")

        if analysis.proof_result:
            if analysis.proof_result.proven:
                print(f"✓ PROVEN ({analysis.proof_time_ms:.1f}ms)")
            else:
                print("✗ DISPROVEN or FAILED")
                if analysis.proof_result.error_message:
                    print(f"  Error: {analysis.proof_result.error_message[:100]}")

        print(f"Reasoning: {analysis.reasoning}")
        print(f"Extraction time: {analysis.extraction_time_ms:.1f}ms")


def demo_conflict_detection():
    """Demonstrate conflict detection between multiple claims."""
    print("\n" + "="*80)
    print("DEMO 4: Conflict Detection")
    print("="*80)

    resolver = HybridCognitiveDissonanceResolver(use_guardrails=True)

    # Alice and Bob make conflicting claims
    claims = [
        "2 + 2 = 4",   # Alice (correct)
        "2 + 2 = 5",   # Bob (incorrect)
        "factorial 5 = 120",  # Charlie (correct)
    ]

    agent_names = ["Alice", "Bob", "Charlie"]

    print("\nAgent Claims:")
    for name, claim in zip(agent_names, claims, strict=True):
        print(f"  {name}: '{claim}'")

    print("\nAnalyzing claims...")
    conflict_analysis = resolver.analyze_multiple_claims(claims)

    print("\nResults:")
    print(f"  Total claims: {len(claims)}")
    print(f"  Analysis time: {conflict_analysis.total_time_ms:.1f}ms")

    for i, analysis in enumerate(conflict_analysis.claim_analyses):
        agent = agent_names[i]
        print(f"\n  {agent}:")
        print(f"    Formalizable: {analysis.is_formalizable}")
        if analysis.proof_result:
            if analysis.proof_result.proven:
                print("    Status: ✓ PROVEN")
            else:
                print("    Status: ✗ DISPROVEN/FAILED")

    if conflict_analysis.conflicts_detected:
        print("\n⚠️  Conflicts Detected:")
        for conflict_desc in conflict_analysis.conflict_descriptions:
            print(f"    - {conflict_desc}")
        print(f"\n  Resolution: {conflict_analysis.resolution_strategy}")
    else:
        print("\n✓ No conflicts detected")


def demo_comparison():
    """Demonstrate performance comparison."""
    print("\n" + "="*80)
    print("DEMO 5: Performance Metrics")
    print("="*80)

    resolver = HybridCognitiveDissonanceResolver(use_guardrails=True)

    test_claims = [
        "2 + 2 = 4",
        "3 * 4 = 12",
        "10 - 3 = 7",
        "factorial 5 = 120",
        "factorial 7 = 5040",
        "3 < 5",
        "10 >= 7",
        "forall n, n + 0 = n",
        "if x > 5 then x > 3",
    ]

    print(f"\nTesting {len(test_claims)} claims...")
    metrics = resolver.compare_with_dspy(test_claims)

    print("\nResults:")
    print(f"  Total claims: {metrics['total_claims']}")
    print("\n  OpenAI SDK + Guardrails:")
    print(f"    Formalizable: {metrics['openai']['formalizable_count']}/{metrics['total_claims']} "
          f"({metrics['openai']['formalizable_rate']:.1%})")
    print(f"    Proven: {metrics['openai']['proven_count']}/{metrics['total_claims']} "
          f"({metrics['openai']['proven_rate']:.1%})")
    print(f"    Avg extraction: {metrics['openai']['avg_extraction_time_ms']:.1f}ms")
    print(f"    Avg proof: {metrics['openai']['avg_proof_time_ms']:.1f}ms")
    print(f"    Total time: {metrics['openai']['total_time_ms']:.1f}ms")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("OpenAI Agents SDK Integration for Cognitive Dissonance DSPy")
    print("="*80)

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set in environment")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")
        print("\nDemos will fail without a valid API key.\n")
        return

    try:
        # Run demos
        demo_basic_extraction()
        demo_with_guardrails()
        demo_full_analysis()
        demo_conflict_detection()
        demo_comparison()

        print("\n" + "="*80)
        print("All demos completed!")
        print("="*80)

    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print(f"\n✗ Error: {e}")
        print("\nCommon issues:")
        print("  1. OPENAI_API_KEY not set or invalid")
        print("  2. Coq not installed (required for proof verification)")
        print("  3. Missing dependencies (run: pip install openai pydantic)")


if __name__ == "__main__":
    main()
