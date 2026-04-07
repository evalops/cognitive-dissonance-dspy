"""Tests for proof cache and proof-learning persistence semantics."""

import json
import time

from formal_verification import Claim, FormalSpec, ProofResult, ProofStatus, PropertyType
from formal_verification.proof_cache import CACHE_SCHEMA_VERSION, ProofCache
from formal_verification.proof_learning import (
    PROOF_LEARNING_SCHEMA_VERSION,
    ProofStrategyLearner,
)


def _build_spec() -> FormalSpec:
    claim = Claim(
        agent_id="cache-test",
        claim_text="2 + 2 = 4",
        property_type=PropertyType.CORRECTNESS,
        confidence=1.0,
        timestamp=time.time(),
    )
    return FormalSpec(
        claim=claim,
        spec_text="Arithmetic smoke spec",
        coq_code="Theorem cache_smoke : True. Proof. exact I. Qed.",
        variables={},
    )


def test_proof_cache_persists_schema_version(tmp_path):
    """New cache entries should carry an explicit schema version."""
    cache = ProofCache(cache_dir=tmp_path)
    spec = _build_spec()
    result = ProofResult(
        spec=spec,
        proven=True,
        proof_time_ms=12.5,
        error_message=None,
        counter_example=None,
        solver_status=ProofStatus.MACHINE_CHECKED,
    )

    cache.put(spec, result)

    cache_file = tmp_path / f"{cache._get_cache_key(spec)}.json"
    data = json.loads(cache_file.read_text(encoding="utf-8"))

    assert data["schema_version"] == CACHE_SCHEMA_VERSION
    assert data["solver_status"] == "machine_checked"


def test_proof_cache_ignores_stale_schema_entries(tmp_path):
    """Old cache entries should be discarded instead of being trusted."""
    cache = ProofCache(cache_dir=tmp_path)
    spec = _build_spec()
    cache_file = tmp_path / f"{cache._get_cache_key(spec)}.json"
    cache_file.write_text(
        json.dumps(
            {
                "schema_version": 0,
                "proven": True,
                "proof_time_ms": 1.0,
                "solver_status": "machine_checked",
            }
        ),
        encoding="utf-8",
    )

    assert cache.get(spec) is None
    assert not cache_file.exists()


def test_proof_learning_persists_schema_version(tmp_path):
    """Proof-learning history should record its schema version on save."""
    data_file = tmp_path / "proof_learning_data.json"
    learner = ProofStrategyLearner(data_file=data_file)
    claim = _build_spec().claim
    result = ProofResult(
        spec=None,
        proven=True,
        proof_time_ms=25.0,
        error_message=None,
        counter_example=None,
        solver_status=ProofStatus.SMT_PROVED,
    )

    learner.record_proof_attempt(claim, "z3", result)

    data = json.loads(data_file.read_text(encoding="utf-8"))

    assert data["schema_version"] == PROOF_LEARNING_SCHEMA_VERSION
    assert len(data["attempts"]) == 1


def test_proof_learning_ignores_stale_history(tmp_path):
    """Stale proof-learning files should not be loaded into memory."""
    data_file = tmp_path / "proof_learning_data.json"
    data_file.write_text(
        json.dumps(
            {
                "schema_version": 0,
                "attempts": [
                    {
                        "claim_text": "stale",
                        "features": {
                            "claim_length": 5,
                            "mathematical_operators": 0,
                            "logical_operators": 0,
                            "quantifier_depth": 0,
                            "variable_count": 0,
                            "constant_count": 0,
                            "proof_type": "general",
                            "complexity_class": "unknown",
                            "mathematical_domain": "general",
                            "code_complexity": 0.0,
                            "previous_success_rate": 0.0,
                            "ast_depth": 0,
                            "pattern_similarity": 0.0,
                        },
                        "prover_used": "coq",
                        "success": True,
                        "time_ms": 1.0,
                        "error_type": None,
                        "timestamp": 0.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    learner = ProofStrategyLearner(data_file=data_file)

    assert learner.proof_history == []
