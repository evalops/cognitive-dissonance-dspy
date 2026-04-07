"""Tests for necessity-based proof discovery system."""

import pytest
import time
from unittest.mock import Mock, patch

from formal_verification.necessity_prover import (
    MathematicalStructureAnalyzer,
    NecessityBasedProver,
    NecessityProofIntegrator,
    NecessityType,
    NecessityEvidence,
    enhance_prover_with_necessity
)
from formal_verification import Claim, PropertyType, ProofResult, FormalSpec


class TestMathematicalStructureAnalyzer:
    """Test the mathematical structure analysis for necessity detection."""
    
    def test_arithmetic_necessity_detection(self):
        """Test detection of arithmetic necessity patterns."""
        analyzer = MathematicalStructureAnalyzer()
        
        # Test correct arithmetic
        evidence = analyzer.analyze_claim("2 + 3 = 5")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.DEDUCTIVE
        assert evidence.confidence == 1.0
        assert "arithmetic computation" in evidence.supporting_facts[0].lower()
        
        # Test incorrect arithmetic
        evidence = analyzer.analyze_claim("2 + 3 = 6")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.DEDUCTIVE
        assert evidence.confidence == 0.0
        assert "arithmetic error" in evidence.supporting_facts[0].lower()
    
    def test_factorial_necessity_detection(self):
        """Test detection of factorial necessity patterns."""
        analyzer = MathematicalStructureAnalyzer()
        
        # Test correct factorial
        evidence = analyzer.analyze_claim("factorial(5) = 120")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.INDUCTIVE
        assert evidence.confidence == 1.0
        assert "factorial definition" in evidence.supporting_facts[0].lower()
        
        # Test incorrect factorial  
        evidence = analyzer.analyze_claim("factorial(5) = 100")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.INDUCTIVE
        assert evidence.confidence == 0.0
        assert "factorial computation error" in evidence.supporting_facts[0].lower()
    
    def test_fibonacci_necessity_detection(self):
        """Test detection of Fibonacci necessity patterns."""
        analyzer = MathematicalStructureAnalyzer()
        
        # Test correct Fibonacci number
        evidence = analyzer.analyze_claim("fibonacci(7) = 13")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.INDUCTIVE
        assert evidence.confidence == 0.95
        assert "fibonacci definition" in evidence.supporting_facts[0].lower()
        
        # Test incorrect Fibonacci number
        evidence = analyzer.analyze_claim("fibonacci(7) = 15")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.INDUCTIVE
        assert evidence.confidence == 0.0
        assert "fibonacci error" in evidence.supporting_facts[0].lower()
    
    def test_definitional_necessity_patterns(self):
        """Test detection of definitional necessity patterns."""
        analyzer = MathematicalStructureAnalyzer()
        
        # Test additive identity
        evidence = analyzer.analyze_claim("n + 0 = n")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.DEFINITIONAL
        assert evidence.confidence == 1.0
        assert "additive identity" in evidence.supporting_facts[0].lower()
        
        # Test multiplicative identity
        evidence = analyzer.analyze_claim("x * 1 = x") 
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.DEFINITIONAL
        assert evidence.confidence == 1.0
        assert "multiplicative identity" in evidence.supporting_facts[0].lower()
    
    def test_summation_necessity_detection(self):
        """Test detection of summation formula necessity."""
        analyzer = MathematicalStructureAnalyzer()
        
        # Test correct summation (1+2+...+n = n(n+1)/2)
        evidence = analyzer.analyze_claim("sum(1 to 10) = 55")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.DEDUCTIVE
        assert evidence.confidence == 1.0
        assert "summation formula" in evidence.supporting_facts[0].lower()
        
        # Test incorrect summation
        evidence = analyzer.analyze_claim("sum(1 to 10) = 50")
        assert evidence is not None
        assert evidence.necessity_type == NecessityType.DEDUCTIVE
        assert evidence.confidence == 0.0
        assert "summation error" in evidence.supporting_facts[0].lower()
    
    def test_no_necessity_pattern(self):
        """Test handling of claims without necessity patterns."""
        analyzer = MathematicalStructureAnalyzer()
        
        evidence = analyzer.analyze_claim("This is a random statement")
        assert evidence is None
        
        evidence = analyzer.analyze_claim("The weather is nice today")
        assert evidence is None


class TestNecessityBasedProver:
    """Test the necessity-based proof construction."""
    
    def test_successful_necessity_proof(self):
        """Test successful necessity-based proof construction."""
        prover = NecessityBasedProver()
        
        claim = Claim(
            agent_id="test",
            claim_text="2 + 2 = 4",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time()
        )
        
        result = prover.prove_by_necessity(claim)
        
        assert result.proven is True
        assert result.error_message is None
        assert result.proof_time_ms > 0
        assert "necessity-based prover: proven by deductive" in result.proof_output.lower()
        assert "arithmetic computation" in result.proof_output
    
    def test_failed_necessity_proof(self):
        """Test necessity-based proof that detects false claims."""
        prover = NecessityBasedProver()
        
        claim = Claim(
            agent_id="test",
            claim_text="2 + 2 = 5",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.8,
            timestamp=time.time()
        )
        
        result = prover.prove_by_necessity(claim)
        
        assert result.proven is False
        assert "mathematical necessity analysis shows claim is false" in result.error_message.lower()
        assert result.proof_time_ms > 0
        assert "necessity-based prover: disproven by deductive" in result.proof_output.lower()
        assert result.counter_example is not None
    
    def test_no_necessity_pattern_detected(self):
        """Test handling of claims without necessity patterns."""
        prover = NecessityBasedProver()
        
        claim = Claim(
            agent_id="test",
            claim_text="This algorithm is efficient",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.7,
            timestamp=time.time()
        )
        
        result = prover.prove_by_necessity(claim)
        
        assert result.proven is False
        assert "no mathematical necessity pattern detected" in result.error_message.lower()
        assert "no applicable necessity pattern" in result.proof_output.lower()
    
    def test_factorial_necessity_proof(self):
        """Test necessity proof for factorial claims."""
        prover = NecessityBasedProver()
        
        claim = Claim(
            agent_id="test",
            claim_text="factorial(4) = 24",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.95,
            timestamp=time.time()
        )
        
        result = prover.prove_by_necessity(claim)
        
        assert result.proven is True
        assert result.error_message is None
        assert "inductive" in result.proof_output.lower()
        assert "factorial definition" in result.proof_output
    
    def test_coq_code_generation(self):
        """Test generation of Coq code from necessity evidence."""
        prover = NecessityBasedProver()
        
        claim = Claim(
            agent_id="test", 
            claim_text="3 * 4 = 12",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time()
        )
        
        result = prover.prove_by_necessity(claim)
        
        assert result.spec.coq_code is not None
        assert "Theorem necessity_theorem" in result.spec.coq_code
        assert "Proof by deductive" in result.spec.coq_code
        assert "natural_number_arithmetic" in result.spec.coq_code


class TestNecessityProofIntegrator:
    """Test integration with fallback provers."""
    
    def test_necessity_success_no_fallback(self):
        """Test when necessity proof succeeds, no fallback needed."""
        mock_fallback = Mock(spec=[])
        integrator = NecessityProofIntegrator(fallback_prover=mock_fallback)
        
        claim = Claim(
            agent_id="test",
            claim_text="5 + 3 = 8", 
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time()
        )
        
        result = integrator.prove_with_necessity_priority(claim)
        
        assert result.proven is True
        # Fallback should not have been called
        assert result.solver_status == "derived_proved"
    
    def test_necessity_definitive_failure_no_fallback(self):
        """Test when necessity proof definitively fails, no fallback needed."""
        mock_fallback = Mock(spec=[])
        integrator = NecessityProofIntegrator(fallback_prover=mock_fallback)
        
        claim = Claim(
            agent_id="test",
            claim_text="fibonacci(5) = 10",  # Wrong, should be 5
            property_type=PropertyType.CORRECTNESS,
            confidence=0.8,
            timestamp=time.time()
        )
        
        result = integrator.prove_with_necessity_priority(claim)
        
        assert result.proven is False
        assert result.counter_example is not None
        # Fallback should not have been called since we have a definitive answer
        assert result.solver_status == "derived_refuted"
    
    def test_necessity_inconclusive_with_hybrid_fallback(self):
        """Test fallback to hybrid prover when necessity is inconclusive."""
        mock_hybrid_prover = Mock(spec=["prove_claim"])
        mock_hybrid_prover.prove_claim.return_value = {
            'proven': True,
            'time_ms': 200,
            'prover': 'Z3',
            'error': None,
            'counter_example': {}
        }
        
        integrator = NecessityProofIntegrator(fallback_prover=mock_hybrid_prover)
        
        claim = Claim(
            agent_id="test",
            claim_text="This algorithm terminates",  # No necessity pattern
            property_type=PropertyType.CORRECTNESS,
            confidence=0.7,
            timestamp=time.time()
        )
        
        result = integrator.prove_with_necessity_priority(claim)
        
        assert result.proven is True
        assert "Z3" in result.proof_output
        assert "Necessity + Fallback" in result.proof_output
        mock_hybrid_prover.prove_claim.assert_called_once_with("This algorithm terminates")
    
    def test_necessity_inconclusive_with_coq_fallback(self):
        """Translatable non-necessity claims should fall back to Coq."""
        mock_coq_prover = Mock(spec=["prove_specification"])
        mock_coq_result = Mock()
        mock_coq_result.proven = True
        mock_coq_result.proof_time_ms = 300
        mock_coq_result.proof_output = "Coq Prover"
        mock_coq_result.prover_name = "coq"
        mock_coq_result.solver_status = "machine_checked"
        mock_coq_prover.prove_specification.return_value = mock_coq_result
        
        integrator = NecessityProofIntegrator(fallback_prover=mock_coq_prover)
        
        claim = Claim(
            agent_id="test",
            claim_text="Memory safety holds for this function",  # No necessity pattern
            property_type=PropertyType.MEMORY_SAFETY,
            confidence=0.8,
            timestamp=time.time()
        )
        
        result = integrator.prove_with_necessity_priority(claim)
        
        assert result.proven is True
        assert result.solver_status == "machine_checked"
        mock_coq_prover.prove_specification.assert_called_once()
    
    def test_necessity_inconclusive_fallback_fails(self):
        """Test when both necessity and fallback fail."""
        mock_fallback = Mock(spec=["prove_claim"])
        mock_fallback.prove_claim.side_effect = Exception("Fallback failed")
        
        integrator = NecessityProofIntegrator(fallback_prover=mock_fallback)
        
        claim = Claim(
            agent_id="test", 
            claim_text="Unknown claim type",
            property_type=PropertyType.CORRECTNESS,
            confidence=0.5,
            timestamp=time.time()
        )
        
        result = integrator.prove_with_necessity_priority(claim)
        
        # Should return the original necessity result (inconclusive)
        assert result.proven is False
        assert "no mathematical necessity pattern detected" in result.error_message.lower()


class TestEnhanceProverWithNecessity:
    """Test the enhance_prover_with_necessity utility function."""
    
    def test_enhance_hybrid_prover(self):
        """Test enhancing a hybrid prover with necessity."""
        mock_hybrid_prover = Mock(spec=["prove_claim"])
        mock_hybrid_prover.prove_claim.return_value = {'proven': True, 'time_ms': 100, 'prover': 'Z3'}
        
        enhanced_prover = enhance_prover_with_necessity(mock_hybrid_prover)
        
        assert isinstance(enhanced_prover, NecessityProofIntegrator)
        assert enhanced_prover.fallback_prover == mock_hybrid_prover
        assert hasattr(enhanced_prover, 'prove_with_necessity_priority')
    
    def test_enhance_coq_prover(self):
        """Test enhancing a Coq prover with necessity."""
        mock_coq_prover = Mock(spec=["prove_specification"])
        
        enhanced_prover = enhance_prover_with_necessity(mock_coq_prover)
        
        assert isinstance(enhanced_prover, NecessityProofIntegrator)
        assert enhanced_prover.fallback_prover == mock_coq_prover
    
    def test_enhanced_prover_necessity_first(self):
        """Test that enhanced prover tries necessity first."""
        mock_fallback = Mock(spec=[])
        enhanced_prover = enhance_prover_with_necessity(mock_fallback)
        
        claim = Claim(
            agent_id="test",
            claim_text="7 - 3 = 4",  # Should be handled by necessity
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time()
        )
        
        result = enhanced_prover.prove_with_necessity_priority(claim)
        
        # Should be handled by necessity, not call fallback
        # 7 - 3 should equal 4, so this should succeed
        assert result.proven is True  # This should work with proper arithmetic
        assert "necessity" in result.spec.spec_text.lower()
        # Fallback should not have been called
        assert result.solver_status == "derived_proved"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
