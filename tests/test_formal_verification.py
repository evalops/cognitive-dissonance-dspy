"""Tests for formal verification cognitive dissonance detection."""

import time
from unittest.mock import Mock, patch

from formal_verification import (
    Claim,
    ClaimTranslator,
    CoqProver,
    FormalSpec,
    FormalVerificationConflictDetector,
    ProofResult,
    ProofStatus,
    PropertyType,
)


class TestClaimTranslator:
    """Test claim translation functionality."""

    def test_initialization(self):
        """Test translator initialization."""
        translator = ClaimTranslator()

        assert hasattr(translator, 'memory_patterns')
        assert hasattr(translator, 'complexity_patterns')
        assert hasattr(translator, 'correctness_patterns')

    def test_memory_safety_translation(self):
        """Test memory safety claim translation."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="This function is memory safe",
            property_type=PropertyType.MEMORY_SAFETY,
            confidence=0.8,
            timestamp=time.time()
        )

        code = "fn test_function() { /* code */ }"
        spec = translator.translate(claim, code)

        assert spec is not None
        assert "test_function" in spec.spec_text
        assert "buffer overflow" in spec.spec_text.lower() or "memory safe" in spec.spec_text.lower()
        assert "Coq" in spec.coq_code or "Require" in spec.coq_code

    def test_complexity_translation(self):
        """Test time complexity claim translation."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="This algorithm has time complexity O(n log n)",
            property_type=PropertyType.TIME_COMPLEXITY,
            confidence=0.9,
            timestamp=time.time()
        )

        code = "fn sort_algorithm() { /* code */ }"
        spec = translator.translate(claim, code)

        assert spec is not None
        assert "sort_algorithm" in spec.spec_text
        assert "O(" in spec.spec_text
        assert spec.variables.get("complexity") is not None

    def test_sorting_correctness_translation(self):
        """Test sorting correctness claim translation."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="This function sorts the array correctly",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.95,
            timestamp=time.time()
        )

        code = "fn quicksort() { /* sorting code */ }"
        spec = translator.translate(claim, code)

        assert spec is not None
        assert "quicksort" in spec.spec_text
        assert "sort" in spec.spec_text.lower()
        assert "Permutation" in spec.coq_code
        assert "Sorted" in spec.coq_code

    def test_unsupported_claim(self):
        """Test handling of unsupported claims."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="This is an unsupported claim type",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.5,
            timestamp=time.time()
        )

        code = "fn unknown_function() { /* code */ }"
        spec = translator.translate(claim, code)

        assert spec is None

    def test_function_name_extraction(self):
        """Test function name extraction from code."""
        translator = ClaimTranslator()

        # Test with Rust-style function
        assert translator._extract_function_name("fn test_func() {}") == "test_func"

        # Test without function definition
        assert translator._extract_function_name("let x = 5;") == "function"


class TestCoqProver:
    """Test Coq theorem prover interface."""

    def test_initialization(self):
        """Test prover initialization."""
        prover = CoqProver(timeout_seconds=10)

        assert prover.timeout_seconds == 10
        assert hasattr(prover, 'coq_available')

    @patch('subprocess.run')
    def test_coq_availability_check(self, mock_run):
        """Test Coq availability checking."""
        # Mock successful coqc --version
        mock_run.return_value.returncode = 0

        prover = CoqProver()
        assert prover.coq_available is True

        # Mock failed coqc --version
        mock_run.side_effect = FileNotFoundError()

        prover = CoqProver()
        assert prover.coq_available is False

    def test_prove_specification_no_coq(self):
        """Test proof attempt when Coq is not available."""
        with patch.object(CoqProver, '_check_binary', return_value=False):
            prover = CoqProver(use_cache=False)

            claim = Claim("test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time())
            spec = FormalSpec(claim, "test spec", "test coq code", {})

            result = prover.prove_specification(spec)

            assert result.proven is False
            assert "not available" in result.error_message
            assert result.proof_time_ms == 0

    @patch('subprocess.run')
    def test_successful_proof(self, mock_run):
        """Test successful proof execution."""
        compile_result = Mock(returncode=0, stdout=b"", stderr=b"")
        check_result = Mock(returncode=0, stdout=b"", stderr=b"")
        mock_run.side_effect = [compile_result, check_result]

        with patch.object(
            CoqProver,
            '_check_binary',
            side_effect=lambda binary: binary in {"coqc", "coqchk"},
        ):
            prover = CoqProver(use_cache=False)

            claim = Claim("test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time())
            spec = FormalSpec(claim, "test spec", "Theorem test : True. Proof. exact I. Qed.", {})

            result = prover.prove_specification(spec)

            assert result.proven is True
            assert result.error_message is None
            assert result.proof_time_ms > 0
            assert result.solver_status == "machine_checked"
            assert result.checker_name == "coqchk"

    @patch('subprocess.run')
    def test_failed_proof(self, mock_run):
        """Test failed proof execution."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Error: Unable to prove theorem"

        with patch.object(
            CoqProver,
            '_check_binary',
            side_effect=lambda binary: binary in {"coqc", "coqchk"},
        ):
            prover = CoqProver(use_cache=False)

            claim = Claim("test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time())
            spec = FormalSpec(claim, "test spec", "Theorem false : False. Proof. Qed.", {})

            result = prover.prove_specification(spec)

            assert result.proven is False
            assert "Unable to prove theorem" in result.error_message
            assert result.proof_time_ms > 0
            assert result.solver_status == "refuted"

    def test_assumption_based_spec_is_not_marked_proven(self):
        """Specs with Admitted or Axiom should not count as proofs."""
        with patch.object(
            CoqProver,
            '_check_binary',
            side_effect=lambda binary: binary in {"coqc", "coqchk"},
        ):
            prover = CoqProver(use_cache=False)

        claim = Claim("test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time())
        spec = FormalSpec(
            claim,
            "test spec",
            "Theorem test : True. Proof. Admitted.",
            {},
        )

        result = prover.prove_specification(spec)

        assert result.proven is False
        assert result.solver_status == "formalized_unproved"
        assert result.assumptions_present is True

    def test_assumption_based_spec_is_rejected_without_coq(self):
        """Unsound specs should be rejected before Coq availability checks matter."""
        with patch.object(CoqProver, '_check_binary', return_value=False):
            prover = CoqProver(use_cache=False)

        claim = Claim("test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time())
        spec = FormalSpec(
            claim,
            "test spec",
            "Theorem test : True. Proof. Admitted.",
            {},
        )

        result = prover.prove_specification(spec)

        assert result.proven is False
        assert result.solver_status == "formalized_unproved"
        assert result.assumptions_present is True


class TestProofStatus:
    """Test shared proof-status normalization helpers."""

    def test_proof_result_normalizes_status_values(self):
        """ProofResult should canonicalize raw status strings and enums."""
        result = ProofResult(
            spec=None,
            proven=True,
            proof_time_ms=1.0,
            error_message=None,
            counter_example=None,
            solver_status=" Machine_Checked ",
        )
        enum_result = ProofResult(
            spec=None,
            proven=False,
            proof_time_ms=1.0,
            error_message=None,
            counter_example=None,
            solver_status=ProofStatus.CHECKER_FAILED,
        )

        assert result.solver_status == "machine_checked"
        assert result.status is ProofStatus.MACHINE_CHECKED
        assert enum_result.solver_status == "checker_failed"
        assert enum_result.status is ProofStatus.CHECKER_FAILED

    def test_resolve_defaults_conservatively_for_solver_outputs(self):
        """Implicit solver statuses should use safe defaults by prover type."""
        assert ProofStatus.resolve(
            None,
            proven=True,
            prover_name="coq",
        ) is ProofStatus.COMPILED_UNCHECKED
        assert ProofStatus.resolve(
            None,
            proven=False,
            prover_name="z3",
        ) is ProofStatus.INCONCLUSIVE
        assert ProofStatus.resolve(
            None,
            proven=False,
            prover_name="z3",
            counter_example={"x": 1},
        ) is ProofStatus.SMT_REFUTED
        assert ProofStatus.resolve(
            None,
            proven=True,
            prover_name="hybrid",
        ) is ProofStatus.DERIVED_PROVED


class TestConflictDetector:
    """Test conflict detection functionality."""

    def test_arithmetic_conflict_detection(self):
        """Test detection of arithmetic contradictions."""
        from formal_verification.detector import ConflictDetector

        detector = ConflictDetector()

        claim1 = Claim("alice", "2 + 2 = 4", PropertyType.CORRECTNESS, 0.9, time.time())
        claim2 = Claim("bob", "2 + 2 = 5", PropertyType.CORRECTNESS, 0.8, time.time())

        spec1 = FormalSpec(claim1, "spec1", "coq1", {})
        spec2 = FormalSpec(claim2, "spec2", "coq2", {})

        conflicts = detector.detect_conflicts([spec1, spec2])

        assert len(conflicts) == 1
        assert (spec1, spec2) in conflicts or (spec2, spec1) in conflicts

    def test_memory_safety_conflict_detection(self):
        """Test detection of memory safety contradictions."""
        from formal_verification.detector import ConflictDetector

        detector = ConflictDetector()

        claim1 = Claim("alice", "This function is memory safe", PropertyType.MEMORY_SAFETY, 0.9, time.time())
        claim2 = Claim("bob", "This function has buffer overflow", PropertyType.MEMORY_SAFETY, 0.8, time.time())

        spec1 = FormalSpec(claim1, "spec1", "coq1", {})
        spec2 = FormalSpec(claim2, "spec2", "coq2", {})

        conflicts = detector.detect_conflicts([spec1, spec2])

        assert len(conflicts) == 1

    def test_no_conflict_detection(self):
        """Test when no conflicts exist."""
        from formal_verification.detector import ConflictDetector

        detector = ConflictDetector()

        claim1 = Claim("alice", "This function sorts arrays", PropertyType.CORRECTNESS, 0.9, time.time())
        claim2 = Claim("bob", "This function has O(n log n) complexity", PropertyType.TIME_COMPLEXITY, 0.8, time.time())

        spec1 = FormalSpec(claim1, "spec1", "coq1", {})
        spec2 = FormalSpec(claim2, "spec2", "coq2", {})

        conflicts = detector.detect_conflicts([spec1, spec2])

        assert len(conflicts) == 0


class TestFormalVerificationConflictDetector:
    """Test main detector functionality."""

    def test_initialization(self):
        """Test detector initialization."""
        detector = FormalVerificationConflictDetector()

        assert hasattr(detector, 'translator')
        assert hasattr(detector, 'prover')
        assert hasattr(detector, 'conflict_detector')

    def test_solver_proofs_are_not_marked_unresolved(self):
        """Solver-backed proofs should not also appear as unresolved."""
        detector = FormalVerificationConflictDetector()

        claim = Claim("alice", "2 + 2 = 4", PropertyType.CORRECTNESS, 0.9, time.time())
        spec = FormalSpec(claim, "spec1", "coq1", {})
        solver_result = ProofResult(
            spec,
            True,
            100,
            None,
            None,
            solver_status="smt_proved",
        )

        resolution = detector._resolve_conflicts([], [solver_result])

        assert resolution["derived_or_solver_proofs"] == [solver_result]
        assert resolution["unresolved"] == []

    def test_coq_solver_dict_defaults_to_compiled_unchecked(self):
        """Coq solver dictionaries should not default to machine-checked proofs."""
        detector = FormalVerificationConflictDetector()

        claim = Claim("alice", "2 + 2 = 4", PropertyType.CORRECTNESS, 0.9, time.time())
        spec = FormalSpec(claim, "spec1", "coq1", {})

        result = detector._proof_result_from_solver_dict(
            spec,
            {"proven": True, "prover": "coq"},
            "Coq output",
        )

        assert result.solver_status == "compiled_unchecked"
        assert result.is_machine_checked is False
        assert result.establishes_ground_truth is False

    def test_agent_ranking(self):
        """Test agent accuracy ranking."""
        detector = FormalVerificationConflictDetector()

        # Create mock proof results
        claim1 = Claim("alice", "correct claim", PropertyType.CORRECTNESS, 0.9, time.time())
        claim2 = Claim("alice", "another correct claim", PropertyType.CORRECTNESS, 0.8, time.time())
        claim3 = Claim("bob", "incorrect claim", PropertyType.CORRECTNESS, 0.7, time.time())

        spec1 = FormalSpec(claim1, "spec1", "coq1", {})
        spec2 = FormalSpec(claim2, "spec2", "coq2", {})
        spec3 = FormalSpec(claim3, "spec3", "coq3", {})

        results = [
            ProofResult(spec1, True, 100, None, None, solver_status="machine_checked"),
            ProofResult(spec2, True, 100, None, None, solver_status="machine_checked"),
            ProofResult(spec3, False, 100, "error", None, solver_status="refuted"),
        ]

        rankings = detector._rank_agents_by_correctness(results)

        assert rankings["alice"] == 1.0  # 100% accuracy
        assert rankings["bob"] == 0.0    # 0% accuracy
        assert list(rankings.keys())[0] == "alice"  # Alice ranked first

    def test_summary_generation(self):
        """Test analysis summary generation."""
        detector = FormalVerificationConflictDetector()

        # Mock proof results
        results = [
            ProofResult(None, True, 100, None, None, solver_status="machine_checked"),
            ProofResult(None, False, 150, "error", None, solver_status="refuted"),
            ProofResult(None, False, 75, None, None, solver_status="formalized_unproved"),
        ]

        conflicts = [("conflict1", "conflict2")]

        summary = detector._generate_summary(results, conflicts)

        assert summary['total_claims'] == 3
        assert summary['mathematically_proven'] == 1
        assert summary['derived_proofs'] == 0
        assert summary['mathematically_disproven'] == 1
        assert summary['conflicts_detected'] == 1
        assert summary['average_proof_time_ms'] == (100 + 150 + 75) / 3
        assert summary['has_ground_truth'] is True


class TestIntegration:
    """Integration tests with mocked Coq."""

    @patch.object(CoqProver, 'prove_specification')
    def test_full_analysis_flow(self, mock_prove):
        """Test complete analysis workflow."""
        # Mock successful and failed proofs
        def mock_proof_side_effect(spec):
            if "2 + 2 = 4" in spec.claim.claim_text:
                return ProofResult(spec, True, 100, None, None, solver_status="machine_checked")
            else:
                return ProofResult(spec, False, 100, "Proof failed", None, solver_status="refuted")

        mock_prove.side_effect = mock_proof_side_effect

        detector = FormalVerificationConflictDetector()

        claims = [
            Claim("alice", "2 + 2 = 4", PropertyType.CORRECTNESS, 0.9, time.time()),
            Claim("bob", "2 + 2 = 5", PropertyType.CORRECTNESS, 0.8, time.time())
        ]

        results = detector.analyze_claims(claims)

        assert len(results['original_claims']) == 2
        assert len(results['proof_results']) >= 1  # At least one should translate
        assert results['summary']['total_claims'] >= 1
        assert 'agent_rankings' in results['resolution']
