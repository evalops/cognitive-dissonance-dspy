"""End-to-end smoke coverage for the real Coq/coqchk path."""

import shutil
import time

import pytest

from formal_verification import Claim, CoqProver, FormalSpec, ProofStatus, PropertyType

pytestmark = pytest.mark.integration


def _build_spec(claim_text: str, spec_text: str, coq_code: str) -> FormalSpec:
    """Create a deterministic FormalSpec for real Coq smoke coverage."""
    claim = Claim(
        agent_id="ci-smoke",
        claim_text=claim_text,
        property_type=PropertyType.CORRECTNESS,
        confidence=1.0,
        timestamp=time.time(),
    )
    return FormalSpec(
        claim=claim,
        spec_text=spec_text,
        coq_code=coq_code.strip(),
        variables={},
    )


@pytest.mark.skipif(
    not shutil.which("coqc") or not shutil.which("coqchk"),
    reason="coqc/coqchk not installed",
)
def test_coq_prover_machine_checks_minimal_theorem():
    """Exercise the real compiler and checker path with a deterministic theorem."""
    prover = CoqProver(timeout_seconds=20, use_cache=False)
    spec = _build_spec(
        "True is provable",
        "Minimal smoke theorem",
        """
Theorem smoke_true : True.
Proof.
  exact I.
Qed.
""",
    )

    result = prover.prove_specification(spec)

    assert result.proven is True
    assert result.status is ProofStatus.MACHINE_CHECKED
    assert result.checker_name == "coqchk"
    assert result.establishes_ground_truth is True


@pytest.mark.skipif(
    not shutil.which("coqc") or not shutil.which("coqchk"),
    reason="coqc/coqchk not installed",
)
def test_coq_prover_reports_compile_failure_for_invalid_theorem():
    """A false theorem should fail through the real Coq compile path."""
    prover = CoqProver(timeout_seconds=20, use_cache=False)
    spec = _build_spec(
        "False is provable",
        "Invalid smoke theorem",
        """
Theorem smoke_false : False.
Proof.
  exact I.
Qed.
""",
    )

    result = prover.prove_specification(spec)

    assert result.proven is False
    assert result.status is ProofStatus.REFUTED
    assert result.error_message
    assert result.checker_name is None


def test_coq_prover_rejects_assumption_based_specs_before_execution():
    """Admitted/Axiom specs should stay formalized but unproved."""
    prover = CoqProver(timeout_seconds=20, use_cache=False)
    spec = _build_spec(
        "Admitted theorem should not count",
        "Assumption smoke theorem",
        """
Theorem smoke_assumed : True.
Proof.
Admitted.
""",
    )

    result = prover.prove_specification(spec)

    assert result.proven is False
    assert result.status is ProofStatus.FORMALIZED_UNPROVED
    assert result.assumptions_present is True
