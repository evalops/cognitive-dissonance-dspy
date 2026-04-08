"""Tests for deterministic proof-preservation parsing and auditing."""

import pytest

from formal_verification import PreservationAuditor, canonicalize_surface_claim
from formal_verification.structured_models import ClaimCategory, PreservationLabel


@pytest.mark.parametrize(
    ("text", "expected_claim", "expected_category"),
    [
        (
            "The factorial of 5 is 120.",
            "factorial 5 = 120",
            ClaimCategory.FACTORIAL,
        ),
        (
            "Five factorial equals one hundred twenty.",
            "factorial 5 = 120",
            ClaimCategory.FACTORIAL,
        ),
        (
            "Fibonacci of 8 equals 21.",
            "fibonacci 8 = 21",
            ClaimCategory.FIBONACCI,
        ),
        (
            "The gcd of 12 and 8 is 4.",
            "gcd(12, 8) = 4",
            ClaimCategory.GCD,
        ),
        (
            "For all n, n plus zero equals n.",
            "forall n, n + 0 = n",
            ClaimCategory.LOGIC_FORALL,
        ),
        (
            "For all n, n is greater than n.",
            "forall n, n > n",
            ClaimCategory.LOGIC_FORALL,
        ),
        (
            "There exists x such that x is greater than zero.",
            "exists x such that x > 0",
            ClaimCategory.LOGIC_EXISTS,
        ),
        (
            "There exists x such that x is greater than x.",
            "exists x such that x > x",
            ClaimCategory.LOGIC_EXISTS,
        ),
    ],
)
def test_canonicalize_surface_claim_supports_current_benchmark_blockers(
    text: str,
    expected_claim: str,
    expected_category: ClaimCategory,
):
    canonical_claim, category = canonicalize_surface_claim(text)

    assert canonical_claim == expected_claim
    assert category == expected_category


def test_canonicalize_surface_claim_handles_symbolic_quantified_equality():
    canonical_claim, category = canonicalize_surface_claim("forall n, n + 0 = n")

    assert canonical_claim == "forall n, n + 0 = n"
    assert category == ClaimCategory.LOGIC_FORALL


@pytest.mark.parametrize(
    ("surface_text", "canonical_text"),
    [
        ("The factorial of 5 is 120.", "factorial 5 = 120"),
        ("Five factorial equals one hundred twenty.", "factorial 5 = 120"),
        ("Fibonacci of 8 equals 21.", "fibonacci 8 = 21"),
        ("The gcd of 12 and 8 is 4.", "gcd(12, 8) = 4"),
        ("For all n, n plus zero equals n.", "forall n, n + 0 = n"),
        ("There exists x such that x is greater than zero.", "exists x such that x > 0"),
        ("forall n, n + 0 = n", "forall n, n + 0 = n"),
    ],
)
def test_preservation_auditor_passes_supported_surface_forms(
    surface_text: str,
    canonical_text: str,
):
    audit = PreservationAuditor().audit(
        surface_text=surface_text,
        canonical_text=canonical_text,
    )

    assert audit.passed is True
    assert audit.label in {PreservationLabel.EXACT, PreservationLabel.EQUIVALENT}


def test_preservation_auditor_detects_drift_on_false_subtraction_rewrite():
    audit = PreservationAuditor().audit(
        surface_text="Subtracting five from twelve gives eight.",
        canonical_text="12 - 5 = 7",
        category=ClaimCategory.SUBTRACTION,
    )

    assert audit.passed is False
    assert audit.label == PreservationLabel.DRIFT
    assert audit.surface_canonical_text == "12 - 5 = 8"
