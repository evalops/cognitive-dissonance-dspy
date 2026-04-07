"""Tests for verifier module."""

import dspy
from cognitive_dissonance.verifier import (
    BeliefAgent,
    DissonanceDetector,
    ReconciliationAgent,
    CognitiveDissonanceResolver,
    ExtractClaim,
    DetectDissonance,
    ReconcileClaims
)


class TestSignatures:
    """Test DSPy signatures."""
    
    def test_extract_claim_signature(self):
        """Test ExtractClaim signature fields."""
        sig = ExtractClaim
        
        # Check input fields
        assert "text" in sig.__annotations__
        
        # Check output fields
        assert "claim" in sig.__annotations__
        assert "confidence" in sig.__annotations__
    
    def test_detect_dissonance_signature(self):
        """Test DetectDissonance signature fields."""
        sig = DetectDissonance
        
        # Check input fields
        assert "claim1" in sig.__annotations__
        assert "claim2" in sig.__annotations__
        
        # Check output fields
        assert "are_contradictory" in sig.__annotations__
        assert "reason" in sig.__annotations__
    
    def test_reconcile_claims_signature(self):
        """Test ReconcileClaims signature fields."""
        sig = ReconcileClaims
        
        # Check input fields
        assert "claim1" in sig.__annotations__
        assert "claim2" in sig.__annotations__
        assert "has_conflict" in sig.__annotations__
        
        # Check output fields
        assert "reconciled_claim" in sig.__annotations__


class TestBeliefAgent:
    """Test BeliefAgent class."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        agent = BeliefAgent()
        assert agent.use_cot is False
        assert hasattr(agent, "extract")
    
    def test_initialization_with_cot(self):
        """Test initialization with Chain of Thought."""
        agent = BeliefAgent(use_cot=True)
        assert agent.use_cot is True
        assert hasattr(agent, "extract")
    
    def test_forward_returns_prediction(self, sample_texts):
        """Test that forward returns a prediction."""
        agent = BeliefAgent()
        
        # Mock the extract method
        mock_pred = dspy.Prediction()
        mock_pred.claim = "Test claim"
        mock_pred.confidence = "high"
        agent.extract = lambda text: mock_pred
        
        result = agent.forward(sample_texts["text1"])
        
        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, "claim")
        assert hasattr(result, "confidence")
        assert result.confidence in ["high", "medium", "low"]
    
    def test_forward_handles_invalid_confidence(self, sample_texts):
        """Test that forward normalizes invalid confidence."""
        agent = BeliefAgent()
        
        # Mock with invalid confidence
        mock_pred = dspy.Prediction()
        mock_pred.claim = "Test claim"
        mock_pred.confidence = "invalid"
        agent.extract = lambda text: mock_pred
        
        result = agent.forward(sample_texts["text1"])
        assert result.confidence == "medium"  # Should default to medium
    
    def test_forward_handles_exception(self, sample_texts):
        """Test that forward handles exceptions gracefully."""
        agent = BeliefAgent()
        
        # Make extract raise an exception
        agent.extract = lambda text: (_ for _ in ()).throw(ValueError("Test error"))
        
        result = agent.forward(sample_texts["text1"])
        
        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, "claim")
        assert result.confidence == "low"


class TestDissonanceDetector:
    """Test DissonanceDetector class."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        detector = DissonanceDetector()
        assert detector.use_cot is False
        assert hasattr(detector, "detect")
    
    def test_initialization_with_cot(self):
        """Test initialization with Chain of Thought."""
        detector = DissonanceDetector(use_cot=True)
        assert detector.use_cot is True
        assert hasattr(detector, "detect")
    
    def test_forward_returns_prediction(self):
        """Test that forward returns a prediction."""
        detector = DissonanceDetector()
        
        # Mock the detect method
        mock_pred = dspy.Prediction()
        mock_pred.are_contradictory = "yes"
        mock_pred.reason = "Test reason"
        detector.detect = lambda claim1, claim2: mock_pred
        
        result = detector.forward("Claim 1", "Claim 2")
        
        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, "are_contradictory")
        assert hasattr(result, "reason")
        assert result.are_contradictory in ["yes", "no"]
    
    def test_forward_normalizes_verdict(self):
        """Test that forward normalizes the verdict."""
        detector = DissonanceDetector()
        
        # Test various verdict formats
        test_cases = [
            ("yes", "yes"),
            ("Yes", "yes"),
            ("YES", "yes"),
            ("no", "no"),
            ("No", "no"),
            ("maybe", "no"),  # Uncertain defaults to no
            ("", "no"),  # Empty defaults to no
        ]
        
        for input_verdict, expected in test_cases:
            mock_pred = dspy.Prediction()
            mock_pred.are_contradictory = input_verdict
            mock_pred.reason = "Test"
            detector.detect = lambda mock_pred=mock_pred, **kwargs: mock_pred
            
            result = detector.forward("Claim 1", "Claim 2")
            assert result.are_contradictory == expected
    
    def test_forward_handles_exception(self):
        """Test that forward handles exceptions gracefully."""
        detector = DissonanceDetector()
        
        # Make detect raise an exception
        detector.detect = lambda c1, c2: (_ for _ in ()).throw(ValueError("Test error"))
        
        result = detector.forward("Claim 1", "Claim 2")
        
        assert isinstance(result, dspy.Prediction)
        assert result.are_contradictory == "no"
        assert result.reason == "Unable to determine relationship"


class TestReconciliationAgent:
    """Test ReconciliationAgent class."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        agent = ReconciliationAgent()
        assert agent.use_cot is False
        assert hasattr(agent, "reconcile")
    
    def test_initialization_with_cot(self):
        """Test initialization with Chain of Thought."""
        agent = ReconciliationAgent(use_cot=True)
        assert agent.use_cot is True
        assert hasattr(agent, "reconcile")
    
    def test_forward_with_conflict(self):
        """Test reconciliation with conflict."""
        agent = ReconciliationAgent()
        
        # Mock the reconcile method
        mock_pred = dspy.Prediction()
        mock_pred.reconciled_claim = "Reconciled claim"
        agent.reconcile = lambda **kwargs: mock_pred
        
        result = agent.forward("Claim 1", "Claim 2", has_conflict="yes")
        
        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, "reconciled_claim")
        assert result.reconciled_claim == "Reconciled claim"
    
    def test_forward_without_conflict(self):
        """Test reconciliation without conflict."""
        agent = ReconciliationAgent()
        
        # Mock with no reconciled claim
        mock_pred = dspy.Prediction()
        mock_pred.reconciled_claim = ""
        agent.reconcile = lambda **kwargs: mock_pred
        
        result = agent.forward("Claim 1", "Claim 2", has_conflict="no")
        
        assert isinstance(result, dspy.Prediction)
        assert hasattr(result, "reconciled_claim")
        # Should combine claims when no conflict
        assert "Claim 1" in result.reconciled_claim
        assert "Claim 2" in result.reconciled_claim
    
    def test_forward_handles_exception(self):
        """Test that forward handles exceptions gracefully."""
        agent = ReconciliationAgent()
        
        # Make reconcile raise an exception
        agent.reconcile = lambda **kwargs: (_ for _ in ()).throw(ValueError("Test error"))
        
        result = agent.forward("Claim 1", "Claim 2", has_conflict="yes")
        
        assert isinstance(result, dspy.Prediction)
        assert result.reconciled_claim == "Claim 1"  # Falls back to first claim


class TestCognitiveDissonanceResolver:
    """Test complete CognitiveDissonanceResolver system."""
    
    def test_initialization_default(self):
        """Test default initialization."""
        resolver = CognitiveDissonanceResolver()
        
        assert hasattr(resolver, "belief_agent")
        assert hasattr(resolver, "dissonance_detector")
        assert hasattr(resolver, "reconciliation_agent")
        assert isinstance(resolver.belief_agent, BeliefAgent)
        assert isinstance(resolver.dissonance_detector, DissonanceDetector)
        assert isinstance(resolver.reconciliation_agent, ReconciliationAgent)
    
    def test_initialization_with_cot(self):
        """Test initialization with Chain of Thought."""
        resolver = CognitiveDissonanceResolver(use_cot=True)
        
        assert resolver.belief_agent.use_cot is True
        assert resolver.dissonance_detector.use_cot is True
        assert resolver.reconciliation_agent.use_cot is True
    
    def test_forward_complete_pipeline(self, sample_texts):
        """Test complete pipeline execution."""
        resolver = CognitiveDissonanceResolver()
        
        # Mock sub-components
        belief_pred1 = dspy.Prediction()
        belief_pred1.claim = "Paris is capital"
        belief_pred1.confidence = "high"
        
        belief_pred2 = dspy.Prediction()
        belief_pred2.claim = "Paris is not capital"
        belief_pred2.confidence = "medium"
        
        dissonance_pred = dspy.Prediction()
        dissonance_pred.are_contradictory = "yes"
        dissonance_pred.reason = "Contradictory statements"
        
        reconcile_pred = dspy.Prediction()
        reconcile_pred.reconciled_claim = "Paris is the capital of France"
        
        # Mock the methods
        resolver.belief_agent.forward = lambda text: belief_pred1 if "Paris" in text and "not" not in text else belief_pred2
        resolver.dissonance_detector.forward = lambda **kwargs: dissonance_pred
        resolver.reconciliation_agent.forward = lambda **kwargs: reconcile_pred
        
        result = resolver.forward(sample_texts["text1"], sample_texts["text2"])
        
        assert isinstance(result, dspy.Prediction)
        assert result.claim1 == "Paris is capital"
        assert result.claim2 == "Paris is not capital"
        assert result.confidence1 == "high"
        assert result.confidence2 == "medium"
        assert result.has_dissonance == "yes"
        assert result.dissonance_reason == "Contradictory statements"
        assert result.reconciled == "Paris is the capital of France"
