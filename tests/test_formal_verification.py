"""Tests for formal verification cognitive dissonance detection."""

import subprocess
import time
from unittest.mock import Mock, patch

from formal_verification import (
    Claim,
    ClaimTranslator,
    CoqProver,
    FormalSpec,
    FormalVerificationConflictDetector,
    HybridLeanCoqResolver,
    LeanProver,
    LeanTranslator,
    ProofResult,
    ProofStatus,
    PropertyType,
    build_claim_ir,
)
from formal_verification.structured_models import PreservationAudit, PreservationLabel


class TestClaimTranslator:
    """Test claim translation functionality."""

    def test_initialization(self):
        """Test translator initialization."""
        translator = ClaimTranslator()

        assert hasattr(translator, "memory_patterns")
        assert hasattr(translator, "complexity_patterns")
        assert hasattr(translator, "correctness_patterns")

    def test_memory_safety_translation(self):
        """Test memory safety claim translation."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="This function is memory safe",
            property_type=PropertyType.MEMORY_SAFETY,
            confidence=0.8,
            timestamp=time.time(),
        )

        code = "fn test_function() { /* code */ }"
        spec = translator.translate(claim, code)

        assert spec is not None
        assert "test_function" in spec.spec_text
        assert (
            "buffer overflow" in spec.spec_text.lower()
            or "memory safe" in spec.spec_text.lower()
        )
        assert "Coq" in spec.coq_code or "Require" in spec.coq_code

    def test_complexity_translation(self):
        """Test time complexity claim translation."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="This algorithm has time complexity O(n log n)",
            property_type=PropertyType.TIME_COMPLEXITY,
            confidence=0.9,
            timestamp=time.time(),
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
            timestamp=time.time(),
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
            timestamp=time.time(),
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

    def test_canonical_function_claim_translation(self):
        """Canonical extractor outputs should translate without format drift."""
        translator = ClaimTranslator()

        fibonacci_claim = Claim(
            agent_id="test",
            claim_text="fibonacci 8 = 21",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time(),
        )
        fibonacci_spec = translator.translate(fibonacci_claim, "")

        assert fibonacci_spec is not None
        assert "fibonacci 8 = 21" in fibonacci_spec.spec_text.lower()

        gcd_claim = Claim(
            agent_id="test",
            claim_text="gcd 12, 8 = 4",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time(),
        )
        gcd_spec = translator.translate(gcd_claim, "")

        assert gcd_spec is not None
        assert "gcd(12, 8) = 4" in gcd_spec.spec_text.lower()

        exists_claim = Claim(
            agent_id="test",
            claim_text="exists x such that x > 0",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time(),
        )
        exists_spec = translator.translate(exists_claim, "")

        assert exists_spec is not None
        assert "exists" in exists_spec.spec_text.lower()

    def test_translation_prefers_structured_claim_ir(self):
        """Structured IR should remain authoritative over raw surface text."""
        translator = ClaimTranslator()

        claim = Claim(
            agent_id="test",
            claim_text="Adding four and five yields nine.",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time(),
            surface_text="Adding four and five yields nine.",
            claim_ir=build_claim_ir("4 + 5 = 9", "arithmetic"),
        )

        spec = translator.translate(claim, "")

        assert spec is not None
        assert "4 + 5 = 9" in spec.spec_text
        assert spec.claim_ir is not None


class TestCoqProver:
    """Test Coq theorem prover interface."""

    def test_initialization(self):
        """Test prover initialization."""
        prover = CoqProver(timeout_seconds=10)

        assert prover.timeout_seconds == 10
        assert hasattr(prover, "coq_available")

    @patch("subprocess.run")
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
        with patch.object(CoqProver, "_check_binary", return_value=False):
            prover = CoqProver(use_cache=False)

            claim = Claim(
                "test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time()
            )
            spec = FormalSpec(claim, "test spec", "test coq code", {})

            result = prover.prove_specification(spec)

            assert result.proven is False
            assert "not available" in result.error_message
            assert result.proof_time_ms == 0

    @patch("subprocess.run")
    def test_successful_proof(self, mock_run):
        """Test successful proof execution."""
        compile_result = Mock(returncode=0, stdout=b"", stderr=b"")
        check_result = Mock(returncode=0, stdout=b"", stderr=b"")
        mock_run.side_effect = [compile_result, check_result]

        with patch.object(
            CoqProver,
            "_check_binary",
            side_effect=lambda binary: binary in {"coqc", "coqchk"},
        ):
            prover = CoqProver(use_cache=False)

            claim = Claim(
                "test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time()
            )
            spec = FormalSpec(
                claim, "test spec", "Theorem test : True. Proof. exact I. Qed.", {}
            )

            result = prover.prove_specification(spec)

            assert result.proven is True
            assert result.error_message is None
            assert result.proof_time_ms > 0
            assert result.solver_status == "machine_checked"
            assert result.checker_name == "coqchk"

    @patch("subprocess.run")
    def test_failed_proof(self, mock_run):
        """Test failed proof execution."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = b"Error: Unable to prove theorem"

        with patch.object(
            CoqProver,
            "_check_binary",
            side_effect=lambda binary: binary in {"coqc", "coqchk"},
        ):
            prover = CoqProver(use_cache=False)

            claim = Claim(
                "test", "test claim", PropertyType.CORRECTNESS, 0.5, time.time()
            )
            spec = FormalSpec(
                claim, "test spec", "Theorem false : False. Proof. Qed.", {}
            )

            result = prover.prove_specification(spec)

            assert result.proven is False
            assert "Unable to prove theorem" in result.error_message
            assert result.proof_time_ms > 0
            assert result.solver_status == "refuted"

    def test_assumption_based_spec_is_not_marked_proven(self):
        """Specs with Admitted or Axiom should not count as proofs."""
        with patch.object(
            CoqProver,
            "_check_binary",
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


class TestFormalVerificationConflictDetectorAuditGate:
    """Proof attempts should be blocked when preservation audit fails."""

    @patch.object(ClaimTranslator, "translate")
    def test_skips_translation_when_preservation_audit_fails(self, mock_translate):
        """Translation should not run when the preservation audit already failed."""
        claim = Claim(
            agent_id="test",
            claim_text="12 - 5 = 7",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time(),
            surface_text="Subtracting five from twelve gives eight.",
            claim_ir=build_claim_ir("12 - 5 = 7", "subtraction"),
            preservation_audit=PreservationAudit(
                label=PreservationLabel.DRIFT,
                passed=False,
                surface_text="Subtracting five from twelve gives eight.",
                canonical_text="12 - 5 = 7",
                surface_canonical_text="12 - 5 = 8",
                rationale="Deterministic audit found semantic drift.",
            ),
        )

        detector = FormalVerificationConflictDetector(
            use_hybrid=False,
            enable_auto_repair=False,
            enable_necessity=False,
        )
        analysis = detector.analyze_claims([claim])

        mock_translate.assert_not_called()
        assert analysis["proof_results"] == []
        assert analysis["audit_failures"]
        assert analysis["audit_failures"][0]["label"] == "drift"

    def test_assumption_based_spec_is_rejected_without_coq(self):
        """Unsound specs should be rejected before Coq availability checks matter."""
        with patch.object(CoqProver, "_check_binary", return_value=False):
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
        assert (
            ProofStatus.resolve(
                None,
                proven=True,
                prover_name="coq",
            )
            is ProofStatus.COMPILED_UNCHECKED
        )
        assert (
            ProofStatus.resolve(
                None,
                proven=False,
                prover_name="z3",
            )
            is ProofStatus.INCONCLUSIVE
        )
        assert (
            ProofStatus.resolve(
                None,
                proven=False,
                prover_name="z3",
                counter_example={"x": 1},
            )
            is ProofStatus.SMT_REFUTED
        )
        assert (
            ProofStatus.resolve(
                None,
                proven=True,
                prover_name="hybrid",
            )
            is ProofStatus.DERIVED_PROVED
        )


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

        claim1 = Claim(
            "alice",
            "This function is memory safe",
            PropertyType.MEMORY_SAFETY,
            0.9,
            time.time(),
        )
        claim2 = Claim(
            "bob",
            "This function has buffer overflow",
            PropertyType.MEMORY_SAFETY,
            0.8,
            time.time(),
        )

        spec1 = FormalSpec(claim1, "spec1", "coq1", {})
        spec2 = FormalSpec(claim2, "spec2", "coq2", {})

        conflicts = detector.detect_conflicts([spec1, spec2])

        assert len(conflicts) == 1

    def test_no_conflict_detection(self):
        """Test when no conflicts exist."""
        from formal_verification.detector import ConflictDetector

        detector = ConflictDetector()

        claim1 = Claim(
            "alice",
            "This function sorts arrays",
            PropertyType.CORRECTNESS,
            0.9,
            time.time(),
        )
        claim2 = Claim(
            "bob",
            "This function has O(n log n) complexity",
            PropertyType.TIME_COMPLEXITY,
            0.8,
            time.time(),
        )

        spec1 = FormalSpec(claim1, "spec1", "coq1", {})
        spec2 = FormalSpec(claim2, "spec2", "coq2", {})

        conflicts = detector.detect_conflicts([spec1, spec2])

        assert len(conflicts) == 0


class TestFormalVerificationConflictDetector:
    """Test main detector functionality."""

    def test_initialization(self):
        """Test detector initialization."""
        detector = FormalVerificationConflictDetector()

        assert hasattr(detector, "translator")
        assert hasattr(detector, "prover")
        assert hasattr(detector, "conflict_detector")

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
        claim1 = Claim(
            "alice", "correct claim", PropertyType.CORRECTNESS, 0.9, time.time()
        )
        claim2 = Claim(
            "alice", "another correct claim", PropertyType.CORRECTNESS, 0.8, time.time()
        )
        claim3 = Claim(
            "bob", "incorrect claim", PropertyType.CORRECTNESS, 0.7, time.time()
        )

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
        assert rankings["bob"] == 0.0  # 0% accuracy
        assert next(iter(rankings)) == "alice"  # Alice ranked first

    def test_summary_generation(self):
        """Test analysis summary generation."""
        detector = FormalVerificationConflictDetector()

        # Mock proof results
        results = [
            ProofResult(None, True, 100, None, None, solver_status="machine_checked"),
            ProofResult(None, False, 150, "error", None, solver_status="refuted"),
            ProofResult(
                None, False, 75, None, None, solver_status="formalized_unproved"
            ),
        ]

        conflicts = [("conflict1", "conflict2")]

        summary = detector._generate_summary(results, conflicts)

        assert summary["total_claims"] == 3
        assert summary["mathematically_proven"] == 1
        assert summary["derived_proofs"] == 0
        assert summary["mathematically_disproven"] == 1
        assert summary["conflicts_detected"] == 1
        assert summary["average_proof_time_ms"] == (100 + 150 + 75) / 3
        assert summary["has_ground_truth"] is True


class TestIntegration:
    """Integration tests with mocked Coq."""

    @patch.object(CoqProver, "prove_specification")
    def test_full_analysis_flow(self, mock_prove):
        """Test complete analysis workflow."""

        # Mock successful and failed proofs
        def mock_proof_side_effect(spec):
            if "2 + 2 = 4" in spec.claim.claim_text:
                return ProofResult(
                    spec, True, 100, None, None, solver_status="machine_checked"
                )
            else:
                return ProofResult(
                    spec, False, 100, "Proof failed", None, solver_status="refuted"
                )

        mock_prove.side_effect = mock_proof_side_effect

        detector = FormalVerificationConflictDetector()

        claims = [
            Claim("alice", "2 + 2 = 4", PropertyType.CORRECTNESS, 0.9, time.time()),
            Claim("bob", "2 + 2 = 5", PropertyType.CORRECTNESS, 0.8, time.time()),
        ]

        results = detector.analyze_claims(claims)

        assert len(results["original_claims"]) == 2
        assert len(results["proof_results"]) >= 1  # At least one should translate
        assert results["summary"]["total_claims"] >= 1
        assert "agent_rankings" in results["resolution"]


class TestLeanTranslator:
    """Tests for Lean 4 claim translation."""

    def test_translate_arithmetic(self):
        """Translate simple addition claim to Lean."""
        translator = LeanTranslator()
        claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
        spec = translator.translate(claim)

        assert spec is not None
        assert "omega" in spec.coq_code
        assert "(2 + 2 : Nat) = 4" in spec.coq_code

    def test_translate_multiplication(self):
        """Translate multiplication claim to Lean."""
        translator = LeanTranslator()
        claim = Claim("a", "3 * 4 = 12", PropertyType.CORRECTNESS, 1.0, 0)
        spec = translator.translate(claim)

        assert spec is not None
        assert "(3 * 4 : Nat) = 12" in spec.coq_code

    def test_translate_factorial(self):
        """Translate factorial claim to Lean."""
        translator = LeanTranslator()
        claim = Claim("a", "factorial(5) = 120", PropertyType.CORRECTNESS, 1.0, 0)
        spec = translator.translate(claim)

        assert spec is not None
        assert "factorial" in spec.coq_code
        assert "native_decide" in spec.coq_code

    def test_translate_fibonacci(self):
        """Translate Fibonacci claim to Lean."""
        translator = LeanTranslator()
        claim = Claim("a", "fibonacci(6) = 8", PropertyType.CORRECTNESS, 1.0, 0)
        spec = translator.translate(claim)

        assert spec is not None
        assert "fib" in spec.coq_code
        assert "native_decide" in spec.coq_code

    def test_translate_inequality(self):
        """Translate inequality claim to Lean."""
        translator = LeanTranslator()
        claim = Claim("a", "3 < 5", PropertyType.CORRECTNESS, 1.0, 0)
        spec = translator.translate(claim)

        assert spec is not None
        assert "omega" in spec.coq_code

    def test_translate_gcd(self):
        """Translate GCD claim to Lean."""
        translator = LeanTranslator()
        claim = Claim("a", "gcd(12, 8) = 4", PropertyType.CORRECTNESS, 1.0, 0)
        spec = translator.translate(claim)

        assert spec is not None
        assert "Nat.gcd 12 8 = 4" in spec.coq_code

    def test_exists_infers_witness_from_bound(self):
        """Existential witness is derived from the property, not hardcoded."""
        translator = LeanTranslator()
        ir = build_claim_ir("exists x, x > 5")
        if ir is None:
            # If IR parsing doesn't handle this, test regex path
            claim = Claim(
                "a", "exists x such that x > 5",
                PropertyType.CORRECTNESS, 1.0, 0,
            )
        else:
            claim = Claim(
                "a", "exists x, x > 5",
                PropertyType.CORRECTNESS, 1.0, 0, claim_ir=ir,
            )
        spec = translator.translate(claim)
        if spec is not None:
            assert "⟨6," in spec.coq_code

    def test_implication_quantifies_free_variables(self):
        """Implication with free variables wraps them in forall binders."""
        translator = LeanTranslator()
        ir = build_claim_ir("if x > 5 then x > 3")
        if ir is not None:
            claim = Claim(
                "a", "if x > 5 then x > 3",
                PropertyType.CORRECTNESS, 1.0, 0, claim_ir=ir,
            )
            spec = translator.translate(claim)
            assert spec is not None
            assert "∀" in spec.coq_code
            assert "(x : Nat)" in spec.coq_code

    def test_untranslatable_returns_none(self):
        """Return None for claims that cannot be translated."""
        translator = LeanTranslator()
        claim = Claim("a", "the sky is blue", PropertyType.CORRECTNESS, 1.0, 0)
        assert translator.translate(claim) is None

    def test_translate_from_ir(self):
        """Translate from structured claim IR."""
        translator = LeanTranslator()
        ir = build_claim_ir("2 + 3 = 5")
        claim = Claim("a", "2 + 3 = 5", PropertyType.CORRECTNESS, 1.0, 0, claim_ir=ir)
        spec = translator.translate(claim)

        assert spec is not None
        assert "(2 + 3 : Nat) = 5" in spec.coq_code


class TestLeanProver:
    """Tests for Lean 4 prover interface."""

    def test_initialization(self):
        """Test prover initializes and checks binary."""
        with patch.object(LeanProver, "_check_binary", return_value=False):
            prover = LeanProver()
            assert prover.lean_available is False

    def test_unavailable_returns_status(self):
        """Return UNAVAILABLE when lean binary is missing."""
        with patch.object(LeanProver, "_check_binary", return_value=False):
            prover = LeanProver()
            claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
            spec = FormalSpec(claim=claim, spec_text="test", coq_code="", variables={})
            result = prover.prove_specification(spec)

            assert result.proven is False
            assert result.prover_name == "lean"
            assert result.solver_status == "unavailable"

    def test_sorry_detected_as_assumption(self):
        """Detect sorry as an unverified assumption."""
        with patch.object(LeanProver, "_check_binary", return_value=True):
            prover = LeanProver()
            claim = Claim("a", "test", PropertyType.CORRECTNESS, 1.0, 0)
            lean_code = "theorem t : True := by sorry"
            spec = FormalSpec(
                claim=claim, spec_text="test", coq_code=lean_code, variables={}
            )
            result = prover.prove_specification(spec)

            assert result.proven is False
            assert result.assumptions_present is True
            assert result.solver_status == "formalized_unproved"

    @patch("subprocess.run")
    def test_successful_proof(self, mock_run):
        """Successful lean invocation returns machine_checked."""
        mock_run.return_value = Mock(returncode=0, stdout=b"", stderr=b"")
        with patch.object(LeanProver, "_check_binary", return_value=True):
            prover = LeanProver(use_cache=False)
            claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
            lean_code = "theorem t : (2 + 2 : Nat) = 4 := by omega"
            spec = FormalSpec(
                claim=claim, spec_text="test", coq_code=lean_code, variables={}
            )
            result = prover.prove_specification(spec)

            assert result.proven is True
            assert result.prover_name == "lean"
            assert result.solver_status == "machine_checked"
            assert result.checker_name == "lean"

    @patch("subprocess.run")
    def test_failed_proof(self, mock_run):
        """Failed lean invocation returns inconclusive."""
        mock_run.return_value = Mock(
            returncode=1, stdout=b"", stderr=b"type mismatch"
        )
        with patch.object(LeanProver, "_check_binary", return_value=True):
            prover = LeanProver(use_cache=False)
            claim = Claim("a", "2 + 2 = 5", PropertyType.CORRECTNESS, 1.0, 0)
            lean_code = "theorem t : (2 + 2 : Nat) = 5 := by omega"
            spec = FormalSpec(
                claim=claim, spec_text="test", coq_code=lean_code, variables={}
            )
            result = prover.prove_specification(spec)

            assert result.proven is False
            assert result.solver_status == "inconclusive"
            assert "type mismatch" in result.error_message

    @patch("subprocess.run")
    def test_timeout(self, mock_run):
        """Timeout returns TIMEOUT status."""
        mock_run.side_effect = subprocess.TimeoutExpired("lean", 30)
        with patch.object(LeanProver, "_check_binary", return_value=True):
            prover = LeanProver(use_cache=False)
            claim = Claim("a", "test", PropertyType.CORRECTNESS, 1.0, 0)
            spec = FormalSpec(
                claim=claim, spec_text="test", coq_code="theorem t : True := by trivial", variables={}
            )
            result = prover.prove_specification(spec)

            assert result.proven is False
            assert result.solver_status == "timeout"


class TestHybridLeanCoqResolver:
    """Tests for the hybrid Lean/Coq resolver."""

    def test_lean_success_returns_immediately(self):
        """When Lean proves the claim, skip Coq."""
        resolver = HybridLeanCoqResolver(prefer_lean=True)
        lean_result = ProofResult(
            None, True, 10.0, None, None, prover_name="lean",
            solver_status="machine_checked",
        )

        with (
            patch.object(resolver.lean_prover, "prove_specification", return_value=lean_result),
            patch.object(resolver.coq_prover, "prove_specification") as mock_coq,
        ):
            claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
            spec = FormalSpec(claim=claim, spec_text="", coq_code="", variables={})
            result = resolver.prove_specification(spec)

            assert result.proven is True
            assert result.prover_name == "lean"
            mock_coq.assert_not_called()

    def test_lean_failure_falls_back_to_coq(self):
        """When Lean fails and fallback is on, try Coq."""
        resolver = HybridLeanCoqResolver(prefer_lean=True, use_fallback=True)
        lean_fail = ProofResult(
            None, False, 10.0, "failed", None, prover_name="lean",
            solver_status="inconclusive",
        )
        coq_ok = ProofResult(
            None, True, 20.0, None, None, prover_name="coq",
            solver_status="machine_checked",
        )

        with (
            patch.object(resolver.lean_prover, "prove_specification", return_value=lean_fail),
            patch.object(resolver.coq_prover, "prove_specification", return_value=coq_ok),
        ):
            claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
            spec = FormalSpec(claim=claim, spec_text="", coq_code="", variables={})
            result = resolver.prove_specification(spec)

            assert result.proven is True
            assert result.prover_name == "coq"

    def test_no_fallback_returns_first_failure(self):
        """When fallback is off, don't try the second prover."""
        resolver = HybridLeanCoqResolver(prefer_lean=True, use_fallback=False)
        lean_fail = ProofResult(
            None, False, 5.0, "failed", None, prover_name="lean",
            solver_status="inconclusive",
        )

        with (
            patch.object(resolver.lean_prover, "prove_specification", return_value=lean_fail),
            patch.object(resolver.coq_prover, "prove_specification") as mock_coq,
        ):
            claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
            spec = FormalSpec(claim=claim, spec_text="", coq_code="", variables={})
            result = resolver.prove_specification(spec)

            assert result.proven is False
            mock_coq.assert_not_called()

    def test_coq_preferred_tries_coq_first(self):
        """When prefer_lean=False, try Coq before Lean."""
        resolver = HybridLeanCoqResolver(prefer_lean=False)
        coq_ok = ProofResult(
            None, True, 15.0, None, None, prover_name="coq",
            solver_status="machine_checked",
        )

        with (
            patch.object(resolver.coq_prover, "prove_specification", return_value=coq_ok),
            patch.object(resolver.lean_prover, "prove_specification") as mock_lean,
        ):
            claim = Claim("a", "2 + 2 = 4", PropertyType.CORRECTNESS, 1.0, 0)
            spec = FormalSpec(claim=claim, spec_text="", coq_code="", variables={})
            result = resolver.prove_specification(spec)

            assert result.proven is True
            assert result.prover_name == "coq"
            mock_lean.assert_not_called()
