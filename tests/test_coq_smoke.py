"""End-to-end smoke coverage for the real Coq/coqchk path."""

import shutil
import time

import pytest

from formal_verification import Claim, CoqProver, FormalSpec, ProofStatus, PropertyType

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not shutil.which("coqc") or not shutil.which("coqchk"),
    reason="coqc/coqchk not installed",
)
def test_coq_prover_machine_checks_minimal_theorem():
    """Exercise the real compiler and checker path with a deterministic theorem."""
    prover = CoqProver(timeout_seconds=20, use_cache=False)
    claim = Claim(
        agent_id="ci-smoke",
        claim_text="True is provable",
        property_type=PropertyType.CORRECTNESS,
        confidence=1.0,
        timestamp=time.time(),
    )
    spec = FormalSpec(
        claim=claim,
        spec_text="Minimal smoke theorem",
        coq_code="""
Theorem smoke_true : True.
Proof.
  exact I.
Qed.
""".strip(),
        variables={},
    )

    result = prover.prove_specification(spec)

    assert result.proven is True
    assert result.status is ProofStatus.MACHINE_CHECKED
    assert result.checker_name == "coqchk"
    assert result.establishes_ground_truth is True
