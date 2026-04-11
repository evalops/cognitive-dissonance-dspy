"""Tests for numeric claim handling in the Z3 prover."""

from types import SimpleNamespace

import pytest

from formal_verification.z3_prover import Z3_AVAILABLE, HybridProver, Z3Prover

pytestmark = pytest.mark.skipif(not Z3_AVAILABLE, reason="z3-solver not installed")


def test_numeric_multiplication_claims_are_handled_decisively():
    """Concrete multiplication claims should not be parsed as symbolic variables."""
    prover = Z3Prover()

    assert prover.prove_claim("3 * 4 = 12").result == "valid"
    assert prover.prove_claim("3 * 4 = 11").result == "invalid"


def test_numeric_subtraction_claims_are_handled_decisively():
    """Concrete subtraction claims should produce valid or invalid verdicts."""
    prover = Z3Prover()

    assert prover.prove_claim("10 - 3 = 7").result == "valid"
    assert prover.prove_claim("10 - 3 = 8").result == "invalid"


def test_numeric_inequality_claims_are_handled_decisively():
    """Concrete inequalities should be translated without introducing variables."""
    prover = Z3Prover()

    assert prover.prove_claim("3 < 5").result == "valid"
    assert prover.prove_claim("5 < 3").result == "invalid"
    assert prover.prove_claim("10 >= 7").result == "valid"
    assert prover.prove_claim("7 >= 10").result == "invalid"


def test_hybrid_prover_preserves_unknown_z3_results_as_inconclusive():
    """Unsupported claims should not be mislabeled as SMT refutations."""
    prover = HybridProver.__new__(HybridProver)
    prover.z3_prover = SimpleNamespace(
        prove_claim=lambda claim_text: SimpleNamespace(
            result="unknown",
            time_ms=12.5,
            model=None,
            statistics={"error": "Could not translate claim"},
        )
    )
    prover.success_stats = {"z3": {"attempts": 0, "successes": 0}}

    result = HybridProver._prove_with_z3(prover, "gcd(12, 8) = 4")

    assert result["proven"] is False
    assert result["solver_status"] == "inconclusive"
    assert result["counter_example"] is None
    assert result["error"] == "Could not translate claim"
