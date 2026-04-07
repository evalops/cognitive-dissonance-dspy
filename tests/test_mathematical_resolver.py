"""Tests for mathematical proof-backed cognitive dissonance resolution."""

from unittest.mock import Mock, patch

import pytest

from cognitive_dissonance.mathematical_resolver import (
    ClaimCategory,
    ClaimClassifier,
    EvidenceStatus,
    MathematicalCognitiveDissonanceResolver,
    MathematicalEvidence,
    ResolutionMethod,
    ResolutionResult,
)
from formal_verification import ProofResult, PropertyType


class TestClaimClassifier:
    """Test claim classification for routing to appropriate resolution methods."""

    def test_mathematical_pattern_recognition(self):
        """Test recognition of mathematical patterns."""
        classifier = ClaimClassifier()

        # Test arithmetic patterns
        assert classifier.classify_claim("2 + 2 = 4") == ClaimCategory.MATHEMATICAL
        assert classifier.classify_claim("factorial(5) = 120") == ClaimCategory.MATHEMATICAL
        assert classifier.classify_claim("fibonacci(7) = 13") == ClaimCategory.MATHEMATICAL
        assert classifier.classify_claim("gcd(12, 8) = 4") == ClaimCategory.MATHEMATICAL

        # Test inequalities
        assert classifier.classify_claim("5 < 10") == ClaimCategory.MATHEMATICAL
        assert classifier.classify_claim("15 >= 10") == ClaimCategory.MATHEMATICAL

        # Test definitional patterns (handled by necessity analyzer)
        assert classifier.classify_claim("forall n, n + 0 = n") == ClaimCategory.MATHEMATICAL  # Definitional patterns work
        assert classifier.classify_claim("n + 0 = n") == ClaimCategory.MATHEMATICAL  # Simple definitional patterns work

    def test_algorithmic_pattern_recognition(self):
        """Test recognition of algorithmic patterns."""
        classifier = ClaimClassifier()

        assert classifier.classify_claim("This algorithm has O(n log n) complexity") == ClaimCategory.ALGORITHMIC
        assert classifier.classify_claim("The function sorts correctly") == ClaimCategory.ALGORITHMIC
        assert classifier.classify_claim("Algorithm terminates in finite time") == ClaimCategory.ALGORITHMIC
        assert classifier.classify_claim("Time complexity is O(1)") == ClaimCategory.ALGORITHMIC

    def test_physical_pattern_recognition(self):
        """Test recognition of physical/scientific patterns."""
        classifier = ClaimClassifier()

        assert classifier.classify_claim("Speed of light is 299792458 m/s") == ClaimCategory.PHYSICAL
        assert classifier.classify_claim("Water boils at 100 degrees Celsius") == ClaimCategory.PHYSICAL
        assert classifier.classify_claim("Gravity acceleration is 9.8 m/s²") == ClaimCategory.PHYSICAL

    def test_software_pattern_recognition(self):
        """Test recognition of software property patterns."""
        classifier = ClaimClassifier()

        assert classifier.classify_claim("This function is memory safe") == ClaimCategory.SOFTWARE
        assert classifier.classify_claim("Buffer overflow vulnerability exists") == ClaimCategory.SOFTWARE
        assert classifier.classify_claim("Race condition detected") == ClaimCategory.SOFTWARE
        assert classifier.classify_claim("No deadlock occurs") == ClaimCategory.SOFTWARE

    def test_subjective_pattern_recognition(self):
        """Test recognition of subjective claims."""
        classifier = ClaimClassifier()

        assert classifier.classify_claim("I think Python is beautiful") == ClaimCategory.SUBJECTIVE
        assert classifier.classify_claim("This approach is better") == ClaimCategory.SUBJECTIVE
        assert classifier.classify_claim("I prefer this solution") == ClaimCategory.SUBJECTIVE
        assert classifier.classify_claim("That code is ugly") == ClaimCategory.SUBJECTIVE

    def test_unverifiable_fallback(self):
        """Test fallback to unverifiable for unknown patterns."""
        classifier = ClaimClassifier()

        assert classifier.classify_claim("Random text without patterns") == ClaimCategory.UNVERIFIABLE
        assert classifier.classify_claim("Some arbitrary statement") == ClaimCategory.UNVERIFIABLE


class TestMathematicalCognitiveDissonanceResolver:
    """Test the main mathematical resolver."""

    def test_initialization_with_formal_verification(self):
        """Test resolver initialization with formal verification enabled."""
        resolver = MathematicalCognitiveDissonanceResolver(
            use_cot=True,
            enable_formal_verification=True
        )

        assert resolver.belief_agent is not None
        assert resolver.dissonance_detector is not None
        assert resolver.reconciliation_agent is not None
        assert resolver.claim_classifier is not None
        assert resolver.formal_detector is not None
        assert resolver.enable_formal_verification is True

    def test_initialization_without_formal_verification(self):
        """Test resolver initialization with formal verification disabled."""
        resolver = MathematicalCognitiveDissonanceResolver(
            use_cot=False,
            enable_formal_verification=False
        )

        assert resolver.belief_agent is not None
        assert resolver.formal_detector is None
        assert resolver.enable_formal_verification is False

    @patch('cognitive_dissonance.mathematical_resolver.BeliefAgent')
    @patch('cognitive_dissonance.mathematical_resolver.DissonanceDetector')
    @patch('cognitive_dissonance.mathematical_resolver.ReconciliationAgent')
    def test_no_conflict_resolution(self, mock_reconciliation, mock_dissonance, mock_belief):
        """Test resolution when no conflict is detected."""
        # Mock agent responses
        mock_belief_result1 = Mock()
        mock_belief_result1.claim = "2 + 2 = 4"
        mock_belief_result1.confidence = "high"

        mock_belief_result2 = Mock()
        mock_belief_result2.claim = "Basic arithmetic works normally"
        mock_belief_result2.confidence = "high"

        mock_belief.return_value.return_value = mock_belief_result1
        mock_belief_instances = [mock_belief_result1, mock_belief_result2]

        def belief_side_effect(**kwargs):
            return mock_belief_instances.pop(0)

        mock_belief.return_value.side_effect = belief_side_effect

        mock_dissonance_result = Mock()
        mock_dissonance_result.are_contradictory = "no"
        mock_dissonance_result.reason = "Claims are compatible"
        mock_dissonance.return_value.return_value = mock_dissonance_result

        mock_reconciliation_result = Mock()
        mock_reconciliation_result.reconciled_claim = "2 + 2 = 4. Basic arithmetic works normally"
        mock_reconciliation.return_value.return_value = mock_reconciliation_result

        resolver = MathematicalCognitiveDissonanceResolver(enable_formal_verification=False)

        result = resolver(text1="2 plus 2 equals 4", text2="Math works as expected")

        assert result.conflict_detected is False
        assert result.resolution_method == ResolutionMethod.PROBABILISTIC
        assert pytest.approx(result.final_confidence, rel=0.01) == 0.85
        assert len(result.mathematical_evidence) == 0

    @patch('cognitive_dissonance.mathematical_resolver.FormalVerificationConflictDetector')
    @patch('cognitive_dissonance.mathematical_resolver.BeliefAgent')
    @patch('cognitive_dissonance.mathematical_resolver.DissonanceDetector')
    def test_mathematical_proof_resolution_success(self, mock_dissonance, mock_belief, mock_formal):
        """Test resolution with successful mathematical proof."""
        # Mock DSPy agent responses
        mock_belief_result1 = Mock()
        mock_belief_result1.claim = "2 + 2 = 4"
        mock_belief_result1.confidence = "high"

        mock_belief_result2 = Mock()
        mock_belief_result2.claim = "2 + 2 = 5"
        mock_belief_result2.confidence = "medium"

        mock_belief_instances = [mock_belief_result1, mock_belief_result2]
        def belief_side_effect(**kwargs):
            return mock_belief_instances.pop(0)

        mock_belief.return_value.side_effect = belief_side_effect

        mock_dissonance_result = Mock()
        mock_dissonance_result.are_contradictory = "yes"
        mock_dissonance_result.reason = "Contradictory arithmetic claims"
        mock_dissonance.return_value.return_value = mock_dissonance_result

        # Mock formal verification success
        spec1 = Mock()
        spec1.claim = Mock()
        spec1.claim.claim_text = "2 + 2 = 4"
        spec1.claim.agent_id = "agent_1"
        spec1.claim.property_type = PropertyType.CORRECTNESS
        spec1.claim.confidence = 0.95

        spec2 = Mock()
        spec2.claim = Mock()
        spec2.claim.claim_text = "2 + 2 = 5"
        spec2.claim.agent_id = "agent_2"
        spec2.claim.property_type = PropertyType.CORRECTNESS
        spec2.claim.confidence = 0.7

        mock_formal_result1 = ProofResult(
            spec=spec1,
            proven=True,
            proof_time_ms=150.0,
            error_message=None,
            counter_example=None,
            proof_output="Z3 Solver",
            prover_name="z3",
            solver_status="smt_proved",
        )

        mock_formal_result2 = ProofResult(
            spec=spec2,
            proven=False,
            proof_time_ms=75.0,
            error_message="Arithmetic contradiction",
            counter_example=None,
            proof_output="Z3 Solver",
            prover_name="z3",
            solver_status="refuted",
        )

        mock_analysis_results = {
            'proof_results': [mock_formal_result1, mock_formal_result2]
        }

        mock_formal_instance = Mock()
        mock_formal_instance.analyze_claims.return_value = mock_analysis_results
        mock_formal.return_value = mock_formal_instance

        resolver = MathematicalCognitiveDissonanceResolver(enable_formal_verification=True)

        result = resolver(text1="2 plus 2 equals 4", text2="Actually 2 plus 2 equals 5")

        assert result.conflict_detected is True
        assert result.resolution_method == ResolutionMethod.MATHEMATICAL_PROOF
        assert result.final_confidence == 1.0  # Mathematical certainty
        assert result.resolved_claim == "2 + 2 = 4"
        assert len(result.mathematical_evidence) == 2
        assert any(e.proven for e in result.mathematical_evidence)
        assert "mathematically proven" in result.reasoning.lower()

    @patch('cognitive_dissonance.mathematical_resolver.BeliefAgent')
    @patch('cognitive_dissonance.mathematical_resolver.DissonanceDetector')
    @patch('cognitive_dissonance.mathematical_resolver.ReconciliationAgent')
    def test_probabilistic_fallback(self, mock_reconciliation, mock_dissonance, mock_belief):
        """Test fallback to probabilistic resolution for unverifiable claims."""
        # Mock subjective claims
        mock_belief_result1 = Mock()
        mock_belief_result1.claim = "Python is the best language"
        mock_belief_result1.confidence = "high"

        mock_belief_result2 = Mock()
        mock_belief_result2.claim = "R is superior for statistics"
        mock_belief_result2.confidence = "high"

        mock_belief_instances = [mock_belief_result1, mock_belief_result2]
        def belief_side_effect(**kwargs):
            return mock_belief_instances.pop(0)

        mock_belief.return_value.side_effect = belief_side_effect

        mock_dissonance_result = Mock()
        mock_dissonance_result.are_contradictory = "yes"
        mock_dissonance_result.reason = "Programming language preferences differ"
        mock_dissonance.return_value.return_value = mock_dissonance_result

        mock_reconciliation_result = Mock()
        mock_reconciliation_result.reconciled_claim = "Both Python and R have strengths for different use cases"
        mock_reconciliation.return_value.return_value = mock_reconciliation_result

        resolver = MathematicalCognitiveDissonanceResolver(enable_formal_verification=False)

        result = resolver(
            text1="Python is the best programming language",
            text2="R is better for statistics"
        )

        assert result.conflict_detected is True
        assert result.resolution_method == ResolutionMethod.PROBABILISTIC
        assert pytest.approx(result.final_confidence, rel=0.05) == 0.6
        assert len(result.mathematical_evidence) == 0
        assert "probabilistic" in result.reasoning.lower()

    def test_mathematical_evidence_creation(self):
        """Test creation of mathematical evidence objects."""
        evidence = MathematicalEvidence(
            claim_text="2 + 2 = 4",
            proven=True,
            proof_time_ms=100.5,
            prover_used="Z3",
            status=EvidenceStatus.PROVEN,
            error_message=None,
            counter_example=None,
            confidence_score=1.0
        )

        assert evidence.claim_text == "2 + 2 = 4"
        assert evidence.proven is True
        assert evidence.proof_time_ms == 100.5
        assert evidence.prover_used == "Z3"
        assert evidence.confidence_score == 1.0
        assert evidence.status is EvidenceStatus.PROVEN

    def test_resolution_result_creation(self):
        """Test creation of resolution result objects."""
        evidence = [MathematicalEvidence(
            claim_text="test",
            proven=True,
            proof_time_ms=50.0,
            prover_used="Coq",
            status=EvidenceStatus.PROVEN,
            error_message=None,
            counter_example=None,
        )]

        result = ResolutionResult(
            original_claim1="claim 1",
            original_claim2="claim 2",
            conflict_detected=True,
            resolution_method=ResolutionMethod.MATHEMATICAL_PROOF,
            resolved_claim="resolved",
            mathematical_evidence=evidence,
            probabilistic_confidence=0.7,
            final_confidence=1.0,
            reasoning="Mathematical proof succeeded",
            audit_metadata={},
            solver_diagnostics=[],
            normalized_specs=[],
        )

        assert result.original_claim1 == "claim 1"
        assert result.conflict_detected is True
        assert result.resolution_method == ResolutionMethod.MATHEMATICAL_PROOF
        assert result.final_confidence == 1.0
        assert len(result.mathematical_evidence) == 1
        assert result.mathematical_evidence[0].proven is True


class TestIntegrationScenarios:
    """Integration tests for complete resolution scenarios."""

    @patch('cognitive_dissonance.mathematical_resolver.FormalVerificationConflictDetector')
    @patch('cognitive_dissonance.mathematical_resolver.BeliefAgent')
    @patch('cognitive_dissonance.mathematical_resolver.DissonanceDetector')
    def test_hybrid_resolution_scenario(self, mock_dissonance, mock_belief, mock_formal):
        """Test hybrid scenario with partial mathematical verification."""
        # Mock one mathematical claim, one subjective claim
        mock_belief_result1 = Mock()
        mock_belief_result1.claim = "factorial(5) = 120"
        mock_belief_result1.confidence = "high"

        mock_belief_result2 = Mock()
        mock_belief_result2.claim = "This algorithm is elegant"
        mock_belief_result2.confidence = "medium"

        mock_belief_instances = [mock_belief_result1, mock_belief_result2]
        def belief_side_effect(**kwargs):
            return mock_belief_instances.pop(0)

        mock_belief.return_value.side_effect = belief_side_effect

        mock_dissonance_result = Mock()
        mock_dissonance_result.are_contradictory = "yes"
        mock_dissonance_result.reason = "Mixed mathematical and subjective claims"
        mock_dissonance.return_value.return_value = mock_dissonance_result

        # Mock formal verification for mathematical claim only
        spec = Mock()
        spec.claim = Mock()
        spec.claim.claim_text = "factorial(5) = 120"
        spec.claim.agent_id = "agent_1"
        spec.claim.property_type = PropertyType.CORRECTNESS
        spec.claim.confidence = 0.95

        mock_formal_result = ProofResult(
            spec=spec,
            proven=True,
            proof_time_ms=200.0,
            error_message=None,
            counter_example=None,
            proof_output="Coq Prover",
            prover_name="coq",
            solver_status="machine_checked",
        )

        mock_analysis_results = {
            'proof_results': [mock_formal_result]
        }

        mock_formal_instance = Mock()
        mock_formal_instance.analyze_claims.return_value = mock_analysis_results
        mock_formal.return_value = mock_formal_instance

        resolver = MathematicalCognitiveDissonanceResolver(enable_formal_verification=True)

        result = resolver(
            text1="The factorial of 5 is 120 mathematically",
            text2="This recursive approach lacks elegance"
        )

        assert result.conflict_detected is True
        assert result.resolution_method == ResolutionMethod.MATHEMATICAL_PROOF
        assert result.final_confidence == 1.0
        assert len(result.mathematical_evidence) == 1
        assert result.mathematical_evidence[0].proven is True

    def test_end_to_end_without_mocking(self):
        """End-to-end test without extensive mocking for basic functionality."""
        resolver = MathematicalCognitiveDissonanceResolver(
            enable_formal_verification=False  # Disable to avoid external dependencies
        )

        # This tests the basic flow without formal verification
        # The actual DSPy agents may not work without proper configuration,
        # but we can test that the resolver doesn't crash

        try:
            result = resolver(
                text1="Simple text one",
                text2="Simple text two"
            )
            # If we get here without exception, basic structure works
            assert isinstance(result, ResolutionResult)
            assert hasattr(result, 'conflict_detected')
            assert hasattr(result, 'resolution_method')
            assert hasattr(result, 'mathematical_evidence')
        except Exception as e:
            # Expected if DSPy not configured, but structure should be sound
            assert "configuration" in str(e).lower() or "model" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
