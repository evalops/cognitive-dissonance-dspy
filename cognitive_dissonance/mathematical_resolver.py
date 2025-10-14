"""Mathematical proof-backed cognitive dissonance resolution.

This module creates the foundational integration between DSPy agents and formal verification,
enabling mathematical certainty to override probabilistic reconciliation for verifiable claims.
"""

import logging
import time
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import dspy
from formal_verification import (
    FormalVerificationConflictDetector,
    Claim as FormalClaim,
    PropertyType,
    ProofResult
)
from formal_verification.semantic_bridge import SemanticLogicalBridge
from .verifier import BeliefAgent, DissonanceDetector, ReconciliationAgent

logger = logging.getLogger(__name__)


class ClaimCategory(Enum):
    """Categories of claims for routing to appropriate resolution methods."""
    MATHEMATICAL = "mathematical"      # Arithmetic, algebra, logic
    ALGORITHMIC = "algorithmic"        # Algorithm correctness, complexity
    PHYSICAL = "physical"              # Physical constants, scientific facts  
    SOFTWARE = "software"              # Code properties, system behavior
    LINGUISTIC = "linguistic"          # Language facts, definitions
    SUBJECTIVE = "subjective"          # Opinions, preferences
    UNVERIFIABLE = "unverifiable"      # Claims that cannot be formally verified


@dataclass 
class MathematicalEvidence:
    """Evidence from mathematical formal verification."""
    claim_text: str
    proven: bool
    proof_time_ms: float
    prover_used: str
    error_message: Optional[str] = None
    confidence_score: float = 1.0  # Mathematical proofs are certain


@dataclass
class ResolutionResult:
    """Result of mathematical proof-backed cognitive dissonance resolution."""
    original_claim1: str
    original_claim2: str
    conflict_detected: bool
    resolution_method: str  # "mathematical_proof", "probabilistic", "hybrid"
    resolved_claim: str
    mathematical_evidence: List[MathematicalEvidence]
    probabilistic_confidence: float
    final_confidence: float
    reasoning: str


class ClaimClassifier:
    """Classifies claims to determine if they are mathematically verifiable.
    
    This uses the necessity analyzer as the authoritative source for mathematical
    patterns, avoiding duplication of pattern matching logic.
    """
    
    def __init__(self):
        # Import here to avoid circular dependency
        from formal_verification.necessity_prover import MathematicalStructureAnalyzer
        self.necessity_analyzer = MathematicalStructureAnalyzer()
        
        # Algorithm patterns (not covered by necessity analyzer)
        self.algorithmic_patterns = [
            r'[Oo]\s*\(\s*[^)]+\s*\)',               # Complexity: O(n log n) 
            r'time complexity.*[Oo]\s*\(',           # "has time complexity O(n)"
            r'space complexity.*[Oo]\s*\(',          # "has space complexity O(1)"
            r'algorithm.*correct',                    # "algorithm is correct"
            r'sorts.*correctly',                     # "sorts the array correctly"
            r'function.*terminates',                 # "function always terminates"
            r'algorithm.*terminates',                # "algorithm terminates"
            r'complexity.*[Oo]\(',                   # "has complexity O(n)"
            r'algorithm.*has.*[Oo]\(',               # "algorithm has O(n)"
        ]
        
        # Physical constants and scientific facts
        self.physical_patterns = [
            r'speed of light.*299792458',            # Physical constants
            r'gravity.*9\.8',                        # Gravitational acceleration
            r'water.*boils.*100.*celsius',           # Boiling point
            r'absolute zero.*-273\.15',              # Temperature scale
        ]
        
        # Software properties
        self.software_patterns = [
            r'memory safe',                          # Memory safety
            r'buffer overflow',                      # Security vulnerabilities  
            r'race condition',                       # Concurrency issues
            r'deadlock',                             # Synchronization problems
            r'null pointer',                         # Memory errors
        ]
        
    def classify_claim(self, claim_text: str) -> ClaimCategory:
        """Classify a claim to determine verification approach.
        
        Args:
            claim_text: The claim to classify
            
        Returns:
            Category indicating verification approach
        """
        claim_lower = claim_text.lower()
        
        # First check if necessity analyzer can handle it (authoritative for mathematical)
        necessity_evidence = self.necessity_analyzer.analyze_claim(claim_text)
        if necessity_evidence is not None:
            logger.debug(f"Classified as MATHEMATICAL via necessity analysis")
            return ClaimCategory.MATHEMATICAL
        
        # Check algorithmic patterns  
        for pattern in self.algorithmic_patterns:
            if re.search(pattern, claim_lower):
                logger.debug(f"Classified as ALGORITHMIC: {pattern}")
                return ClaimCategory.ALGORITHMIC
                
        # Check physical patterns
        for pattern in self.physical_patterns:
            if re.search(pattern, claim_lower):
                logger.debug(f"Classified as PHYSICAL: {pattern}")
                return ClaimCategory.PHYSICAL
                
        # Check software patterns
        for pattern in self.software_patterns:
            if re.search(pattern, claim_lower):
                logger.debug(f"Classified as SOFTWARE: {pattern}")
                return ClaimCategory.SOFTWARE
        
        # Default classifications
        if any(word in claim_lower for word in ['think', 'believe', 'opinion', 'prefer', 'like']):
            return ClaimCategory.SUBJECTIVE
        elif any(word in claim_lower for word in ['beautiful', 'ugly', 'good', 'bad', 'should', 'better', 'worse', 'best']):
            return ClaimCategory.SUBJECTIVE
        else:
            return ClaimCategory.UNVERIFIABLE


class MathematicalCognitiveDissonanceResolver(dspy.Module):
    """Revolutionary proof-backed cognitive dissonance resolution system.
    
    This system integrates DSPy agents with formal verification to achieve
    mathematical certainty in cognitive dissonance resolution for verifiable claims.
    """
    
    def __init__(self, use_cot: bool = True, enable_formal_verification: bool = True):
        """Initialize the mathematical resolver.
        
        Args:
            use_cot: Enable Chain of Thought reasoning for DSPy agents
            enable_formal_verification: Enable formal verification subsystem
        """
        super().__init__()
        
        # Initialize DSPy agents
        self.belief_agent = BeliefAgent(use_cot=use_cot)
        self.dissonance_detector = DissonanceDetector(use_cot=use_cot) 
        self.reconciliation_agent = ReconciliationAgent(use_cot=use_cot)
        
        # Initialize mathematical components
        self.claim_classifier = ClaimClassifier()
        
        # Initialize semantic bridge system
        self.semantic_bridge = SemanticLogicalBridge()
        
        # Initialize formal verification system
        self.enable_formal_verification = enable_formal_verification
        if enable_formal_verification:
            self.formal_detector = FormalVerificationConflictDetector(
                use_hybrid=True,  # Use Z3+Coq hybrid proving
                enable_auto_repair=True,  # Enable automatic lemma discovery
                enable_necessity=True  # Enable necessity-based proof discovery
            )
            logger.info("Initialized with formal verification enabled")
        else:
            self.formal_detector = None
            logger.info("Initialized without formal verification")
    
    def forward(self, text1: str, text2: str, code: str = "") -> ResolutionResult:
        """Resolve cognitive dissonance with mathematical backing.
        
        Args:
            text1: First text containing claims
            text2: Second text containing claims  
            code: Optional code being analyzed
            
        Returns:
            ResolutionResult with mathematical evidence and final resolution
        """
        logger.info("Starting mathematical proof-backed cognitive dissonance resolution")
        
        # Step 1: Extract claims using DSPy agents
        belief1 = self.belief_agent(text=text1)
        belief2 = self.belief_agent(text=text2)
        
        claim1_text = belief1.claim
        claim2_text = belief2.claim
        
        logger.debug(f"Extracted claims: '{claim1_text}' vs '{claim2_text}'")
        
        # Step 2: Detect dissonance using DSPy
        dissonance = self.dissonance_detector(claim1=claim1_text, claim2=claim2_text)
        has_conflict = dissonance.are_contradictory == "yes"
        
        if not has_conflict:
            logger.info("No cognitive dissonance detected, using probabilistic reconciliation")
            reconciled = self.reconciliation_agent(
                claim1=claim1_text, 
                claim2=claim2_text, 
                has_conflict="no"
            )
            
            return ResolutionResult(
                original_claim1=claim1_text,
                original_claim2=claim2_text,
                conflict_detected=False,
                resolution_method="probabilistic",
                resolved_claim=reconciled.reconciled_claim,
                mathematical_evidence=[],
                probabilistic_confidence=0.8,  # High confidence when no conflict
                final_confidence=0.8,
                reasoning="No conflict detected between claims, combined probabilistically"
            )
        
        logger.info(f"Cognitive dissonance detected: {dissonance.reason}")
        
        # Step 3: Classify claims for mathematical verification
        category1 = self.claim_classifier.classify_claim(claim1_text)
        category2 = self.claim_classifier.classify_claim(claim2_text)
        
        mathematical_evidence = []
        
        # Step 4: Attempt formal verification for verifiable claims (including bridged subjective)
        if self.enable_formal_verification and self.formal_detector:
            formal_claims = []
            bridged_claims = []  # Track which claims were semantically bridged
            
            # Process each claim through classification and semantic bridging
            for i, (claim_text, category) in enumerate([(claim1_text, category1), (claim2_text, category2)]):
                claims_to_verify = []
                
                # Handle directly verifiable claims
                if category in [ClaimCategory.MATHEMATICAL, ClaimCategory.ALGORITHMIC, 
                               ClaimCategory.PHYSICAL, ClaimCategory.SOFTWARE]:
                    
                    # Map category to PropertyType
                    property_type_map = {
                        ClaimCategory.MATHEMATICAL: PropertyType.CORRECTNESS,
                        ClaimCategory.ALGORITHMIC: PropertyType.CORRECTNESS,
                        ClaimCategory.PHYSICAL: PropertyType.CORRECTNESS,
                        ClaimCategory.SOFTWARE: PropertyType.MEMORY_SAFETY
                    }
                    
                    formal_claim = FormalClaim(
                        agent_id=f"agent_{i+1}",
                        claim_text=claim_text,
                        property_type=property_type_map[category],
                        confidence=float(belief1.confidence == 'high' if i == 0 else belief2.confidence == 'high'),
                        timestamp=time.time()
                    )
                    formal_claims.append(formal_claim)
                
                # Handle subjective/unverifiable claims through semantic bridging
                elif category in [ClaimCategory.SUBJECTIVE, ClaimCategory.UNVERIFIABLE]:
                    logger.info(f"Attempting semantic bridging for {category.value} claim: '{claim_text[:50]}...'")
                    
                    # Analyze for objective components
                    bridge = self.semantic_bridge.analyze_subjective_claim(claim_text)
                    
                    if self.semantic_bridge.should_attempt_verification(bridge):
                        logger.info(f"Found objective grounding (score: {bridge.total_objectivity_score:.2f}) - creating verification targets")
                        
                        # Generate verification targets from bridged components
                        verification_targets = self.semantic_bridge.get_verification_targets(bridge)
                        
                        for target_claim in verification_targets:
                            # Determine property type based on the target claim content
                            if any(word in target_claim.lower() for word in ['complexity', 'time', 'space', 'O(', 'algorithm']):
                                prop_type = PropertyType.TIME_COMPLEXITY
                            elif any(word in target_claim.lower() for word in ['memory', 'buffer', 'safe', 'overflow']):
                                prop_type = PropertyType.MEMORY_SAFETY
                            else:
                                prop_type = PropertyType.CORRECTNESS
                            
                            bridged_claim = FormalClaim(
                                agent_id=f"agent_{i+1}_bridged",
                                claim_text=target_claim,
                                property_type=prop_type,
                                confidence=bridge.total_objectivity_score,
                                timestamp=time.time()
                            )
                            formal_claims.append(bridged_claim)
                            bridged_claims.append({
                                'original': claim_text,
                                'bridged': target_claim,
                                'objectivity_score': bridge.total_objectivity_score
                            })
                    else:
                        logger.debug(f"Insufficient objective grounding (score: {bridge.total_objectivity_score:.2f}) - using probabilistic fallback")
            
            # Perform formal analysis
            if formal_claims:
                logger.info(f"Performing formal verification on {len(formal_claims)} claims")
                
                try:
                    analysis_results = self.formal_detector.analyze_claims(formal_claims, code=code)
                    
                    # Extract mathematical evidence
                    for proof_result in analysis_results.get('proof_results', []):
                        evidence = MathematicalEvidence(
                            claim_text=proof_result.spec.claim.claim_text,
                            proven=proof_result.proven,
                            proof_time_ms=proof_result.proof_time_ms,
                            prover_used=proof_result.proof_output or "unknown",
                            error_message=proof_result.error_message,
                            confidence_score=1.0 if proof_result.proven else 0.0
                        )
                        mathematical_evidence.append(evidence)
                        
                        logger.info(f"Formal verification: '{evidence.claim_text[:50]}...' -> "
                                   f"{'PROVEN' if evidence.proven else 'FAILED'} "
                                   f"({evidence.proof_time_ms:.1f}ms)")
                
                except Exception as e:
                    logger.warning(f"Formal verification failed: {e}")
        
        # Step 5: Resolve using mathematical evidence (including bridged claims)
        resolution_result = self._resolve_with_mathematical_evidence(
            claim1_text, claim2_text, mathematical_evidence, dissonance.reason
        )
        
        # Enhance resolution with semantic bridging information
        if 'bridged_claims' in locals() and bridged_claims:
            bridge_info = []
            for bridge_data in bridged_claims:
                bridge_info.append(
                    f"Bridged '{bridge_data['original'][:30]}...' → '{bridge_data['bridged']}' "
                    f"(objectivity: {bridge_data['objectivity_score']:.2f})"
                )
            
            if resolution_result.resolution_method == "mathematical_proof":
                resolution_result.reasoning += f"\n\nSemantic Bridge Analysis: {'; '.join(bridge_info)}"
            elif resolution_result.resolution_method == "hybrid":
                resolution_result.reasoning = f"Hybrid resolution with semantic bridging: {'; '.join(bridge_info)}. {resolution_result.reasoning}"
            
            logger.info(f"Resolution enhanced with {len(bridged_claims)} semantic bridges")
        
        return resolution_result
    
    def _resolve_with_mathematical_evidence(
        self, 
        claim1: str, 
        claim2: str, 
        evidence: List[MathematicalEvidence],
        conflict_reason: str
    ) -> ResolutionResult:
        """Resolve conflicts using mathematical evidence with fallback to probabilistic.
        
        Args:
            claim1: First claim  
            claim2: Second claim
            evidence: Mathematical evidence from formal verification
            conflict_reason: Reason for the detected conflict
            
        Returns:
            ResolutionResult with optimal resolution strategy
        """
        # Analyze mathematical evidence
        proven_claims = [e for e in evidence if e.proven]
        disproven_claims = [e for e in evidence if not e.proven and e.error_message]
        
        if proven_claims:
            # Mathematical certainty available
            if len(proven_claims) == 1:
                # One claim is mathematically proven
                resolved_claim = proven_claims[0].claim_text
                resolution_method = "mathematical_proof"
                final_confidence = 1.0  # Mathematical certainty
                reasoning = f"Claim mathematically proven using {proven_claims[0].prover_used} in {proven_claims[0].proof_time_ms:.1f}ms"
                
                logger.info(f"Mathematical resolution: '{resolved_claim}' (proven)")
                
            elif len(proven_claims) > 1:
                # Multiple claims proven - this shouldn't happen in true conflicts
                resolved_claim = f"Both claims verified: {proven_claims[0].claim_text}. {proven_claims[1].claim_text}"
                resolution_method = "mathematical_proof"
                final_confidence = 1.0
                reasoning = f"Multiple claims mathematically verified - possible false conflict detection"
                
                logger.warning("Multiple conflicting claims proven - possible misclassification")
            
        elif disproven_claims:
            # Some claims mathematically disproven
            remaining_claims = [claim1, claim2]
            for disproven in disproven_claims:
                if disproven.claim_text in remaining_claims:
                    remaining_claims.remove(disproven.claim_text)
            
            if remaining_claims:
                resolved_claim = remaining_claims[0]
                resolution_method = "mathematical_proof"  
                final_confidence = 1.0
                reasoning = f"Alternative claim disproven mathematically, accepting remaining claim"
            else:
                # All claims disproven - fall back to probabilistic
                resolved_claim = self._probabilistic_fallback(claim1, claim2)
                resolution_method = "hybrid"
                final_confidence = 0.3  # Low confidence when all claims fail
                reasoning = f"All claims mathematically disproven, using probabilistic fallback"
        
        else:
            # No mathematical evidence - pure probabilistic resolution
            resolved_claim = self._probabilistic_fallback(claim1, claim2)
            resolution_method = "probabilistic"
            final_confidence = 0.6  # Medium confidence for probabilistic
            reasoning = f"Claims not mathematically verifiable, using probabilistic reconciliation: {conflict_reason}"
        
        return ResolutionResult(
            original_claim1=claim1,
            original_claim2=claim2,
            conflict_detected=True,
            resolution_method=resolution_method,
            resolved_claim=resolved_claim,
            mathematical_evidence=evidence,
            probabilistic_confidence=0.6,
            final_confidence=final_confidence,
            reasoning=reasoning
        )
    
    def _probabilistic_fallback(self, claim1: str, claim2: str) -> str:
        """Fallback to probabilistic reconciliation when mathematical proof unavailable.
        
        Args:
            claim1: First claim
            claim2: Second claim
            
        Returns:
            Reconciled claim using DSPy agent
        """
        try:
            reconciled = self.reconciliation_agent(
                claim1=claim1,
                claim2=claim2, 
                has_conflict="yes"
            )
            return reconciled.reconciled_claim
        except Exception as e:
            logger.warning(f"Probabilistic reconciliation failed: {e}")
            # Ultimate fallback - simple preference for first claim
            return claim1