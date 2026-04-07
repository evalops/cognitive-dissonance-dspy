"""Semantic-Logical Bridge System for Grounding Subjective Claims.

This module implements the foundational capability to extract objective components
from subjective claims, enabling formal verification of implicit mathematical or
measurable assertions within natural language disputes.
"""

import logging
import re
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ObjectivityLevel(Enum):
    """Levels of objectivity for claim components."""
    MATHEMATICAL = "mathematical"      # Formally provable (confidence = 1.0)
    MEASURABLE = "measurable"         # Empirically verifiable (confidence = 0.8)
    CONTEXTUAL = "contextual"         # Context-dependent but objective (confidence = 0.6)
    COMPARATIVE = "comparative"       # Relative but grounded (confidence = 0.4)
    SUBJECTIVE = "subjective"         # Pure opinion (confidence = 0.2)


@dataclass
class ObjectiveComponent:
    """An objective component extracted from a subjective claim."""
    original_text: str
    objective_claim: str
    objectivity_level: ObjectivityLevel
    confidence: float
    measurable_property: Optional[str]
    verification_approach: str
    grounding_evidence: List[str]


@dataclass
class SemanticBridge:
    """A bridge between subjective language and objective verification."""
    subjective_term: str
    objective_components: List[ObjectiveComponent]
    total_objectivity_score: float
    suggested_verification: List[str]


class SubjectiveTermExtractor:
    """Extracts potentially objective components from subjective language."""
    
    def __init__(self):
        # Performance-related subjective terms → objective components
        self.performance_semantics = {
            r'(?:in)?efficient|slow|fast|quick|sluggish|snappy': {
                'domain': 'performance',
                'components': [
                    ('execution time', 'measurable', 'runtime < threshold_ms'),
                    ('time complexity', 'mathematical', 'O(f(n)) complexity analysis'),
                    ('resource usage', 'measurable', 'CPU/memory consumption'),
                    ('throughput', 'measurable', 'operations per second')
                ]
            },
            
            r'reliable|unreliable|stable|buggy|broken|robust': {
                'domain': 'reliability',
                'components': [
                    ('error rate', 'measurable', 'failure rate < threshold'),
                    ('test coverage', 'measurable', 'percentage of code tested'),
                    ('uptime', 'measurable', 'availability percentage'),
                    ('exception handling', 'contextual', 'proper error handling')
                ]
            },
            
            r'readable|maintainable|clean|messy|ugly|beautiful': {
                'domain': 'code_quality',
                'components': [
                    ('cyclomatic complexity', 'measurable', 'complexity metrics'),
                    ('code duplication', 'measurable', 'duplicate code percentage'),
                    ('naming convention', 'contextual', 'consistent naming'),
                    ('documentation coverage', 'measurable', 'documented functions percentage')
                ]
            },
            
            r'secure|insecure|safe|vulnerable|protected': {
                'domain': 'security',
                'components': [
                    ('input validation', 'contextual', 'sanitizes user input'),
                    ('buffer overflow', 'mathematical', 'memory safety proof'),
                    ('authentication', 'contextual', 'proper access control'),
                    ('encryption strength', 'measurable', 'cryptographic algorithm strength')
                ]
            },
            
            r'scalable|unscalable|flexible|rigid|adaptable': {
                'domain': 'scalability',
                'components': [
                    ('space complexity', 'mathematical', 'O(f(n)) space analysis'),
                    ('concurrent capacity', 'measurable', 'max concurrent users'),
                    ('modular design', 'contextual', 'separation of concerns'),
                    ('configuration flexibility', 'contextual', 'parameterizable behavior')
                ]
            }
        }
        
        # Quantitative intensifiers that add measurability
        self.intensifiers = {
            r'very|extremely|highly|significantly': 1.2,
            r'somewhat|moderately|fairly|reasonably': 0.8,
            r'barely|slightly|minimally|marginally': 0.6,
            r'completely|totally|absolutely|perfectly': 1.5
        }
        
        # Comparative terms that suggest measurable differences  
        self.comparatives = {
            r'better|worse|superior|inferior|faster|slower': 'comparative_performance',
            r'more|less|higher|lower|greater|smaller': 'comparative_quantity',
            r'easier|harder|simpler|complex': 'comparative_complexity'
        }
    
    def extract_objective_components(self, claim_text: str) -> List[ObjectiveComponent]:
        """Extract objective components from potentially subjective text.
        
        Args:
            claim_text: The claim text to analyze
            
        Returns:
            List of objective components found in the text
        """
        claim_lower = claim_text.lower()
        components = []
        
        # Check for performance-related terms
        for pattern, semantic_info in self.performance_semantics.items():
            if re.search(pattern, claim_lower):
                domain = semantic_info['domain']
                logger.debug(f"Found {domain} semantic pattern: {pattern}")
                
                for prop_name, objectivity, verification in semantic_info['components']:
                    # Determine confidence based on objectivity level
                    if objectivity == 'mathematical':
                        confidence = 1.0
                        obj_level = ObjectivityLevel.MATHEMATICAL
                    elif objectivity == 'measurable':
                        confidence = 0.8
                        obj_level = ObjectivityLevel.MEASURABLE
                    elif objectivity == 'contextual':
                        confidence = 0.6
                        obj_level = ObjectivityLevel.CONTEXTUAL
                    else:
                        confidence = 0.4
                        obj_level = ObjectivityLevel.COMPARATIVE
                    
                    # Check for intensifiers that modify confidence
                    for intensifier_pattern, multiplier in self.intensifiers.items():
                        if re.search(intensifier_pattern, claim_lower):
                            confidence = min(1.0, confidence * multiplier)
                            break
                    
                    component = ObjectiveComponent(
                        original_text=claim_text,
                        objective_claim=f"{prop_name} can be verified through {verification}",
                        objectivity_level=obj_level,
                        confidence=confidence,
                        measurable_property=prop_name,
                        verification_approach=verification,
                        grounding_evidence=[f"Subjective term '{domain}' grounds to measurable '{prop_name}'"]
                    )
                    components.append(component)
        
        # Check for comparative structures
        for comp_pattern, comp_type in self.comparatives.items():
            if re.search(comp_pattern, claim_lower):
                component = ObjectiveComponent(
                    original_text=claim_text,
                    objective_claim=f"Comparative claim suggests measurable difference in {comp_type}",
                    objectivity_level=ObjectivityLevel.COMPARATIVE,
                    confidence=0.4,
                    measurable_property=comp_type,
                    verification_approach=f"Benchmark comparison for {comp_type}",
                    grounding_evidence=["Comparative language indicates objective difference"]
                )
                components.append(component)
        
        return components


class ObjectiveClaimGenerator:
    """Generates formal verification targets from objective components."""
    
    def __init__(self):
        from .necessity_prover import MathematicalStructureAnalyzer
        self.necessity_analyzer = MathematicalStructureAnalyzer()
    
    def generate_verifiable_claims(self, components: List[ObjectiveComponent]) -> List[str]:
        """Generate specific verifiable claims from objective components.
        
        Args:
            components: List of objective components
            
        Returns:
            List of claims that can be formally verified
        """
        verifiable_claims = []
        
        for component in components:
            if component.objectivity_level == ObjectivityLevel.MATHEMATICAL:
                # Try to extract mathematical patterns
                math_claims = self._extract_mathematical_claims(component)
                verifiable_claims.extend(math_claims)
            
            elif component.objectivity_level == ObjectivityLevel.MEASURABLE:
                # Generate measurement-based claims
                measurement_claims = self._generate_measurement_claims(component)
                verifiable_claims.extend(measurement_claims)
            
            elif component.objectivity_level == ObjectivityLevel.CONTEXTUAL:
                # Generate context-dependent verification targets
                context_claims = self._generate_contextual_claims(component)
                verifiable_claims.extend(context_claims)
        
        return verifiable_claims
    
    def _extract_mathematical_claims(self, component: ObjectiveComponent) -> List[str]:
        """Extract mathematical claims that can use necessity-based proving."""
        claims = []
        
        # Check if component contains complexity analysis
        if 'complexity' in component.measurable_property.lower():
            # Generate complexity claims that necessity analyzer can handle
            if 'time' in component.measurable_property.lower():
                claims.append("algorithm has time complexity O(n log n)")
                claims.append("worst-case time complexity is O(n^2)")
            elif 'space' in component.measurable_property.lower():
                claims.append("space complexity is O(n)")
                claims.append("memory usage is O(1)")
        
        # Check if component relates to correctness
        if 'correct' in component.verification_approach.lower():
            claims.append("algorithm produces correct output")
            claims.append("function satisfies specification")
        
        return claims
    
    def _generate_measurement_claims(self, component: ObjectiveComponent) -> List[str]:
        """Generate measurable claims with specific thresholds."""
        claims = []
        prop = component.measurable_property.lower()
        
        if 'time' in prop or 'performance' in prop:
            claims.append("execution time < 100 milliseconds")
            claims.append("response time < 1 second")
        
        if 'error' in prop or 'failure' in prop:
            claims.append("error rate < 0.1%")
            claims.append("failure rate < 0.01%")
        
        if 'coverage' in prop:
            claims.append("test coverage > 90%")
            claims.append("code coverage > 80%")
        
        if 'complexity' in prop:
            claims.append("cyclomatic complexity < 10")
            claims.append("cognitive complexity < 15")
        
        return claims
    
    def _generate_contextual_claims(self, component: ObjectiveComponent) -> List[str]:
        """Generate context-dependent verification targets.""" 
        claims = []
        prop = component.measurable_property.lower()
        
        if 'input' in prop and 'validation' in prop:
            claims.append("all user inputs are sanitized")
            claims.append("input validation prevents injection attacks")
        
        if 'error' in prop and 'handling' in prop:
            claims.append("all exceptions are properly handled")
            claims.append("error states are recoverable")
        
        if 'modular' in prop:
            claims.append("functions have single responsibility")
            claims.append("modules are loosely coupled")
        
        return claims


class SemanticLogicalBridge:
    """Main system for bridging subjective claims to objective verification."""
    
    def __init__(self):
        self.term_extractor = SubjectiveTermExtractor()
        self.claim_generator = ObjectiveClaimGenerator()
    
    def analyze_subjective_claim(self, claim_text: str) -> SemanticBridge:
        """Analyze a subjective claim and extract objective components.
        
        Args:
            claim_text: The potentially subjective claim
            
        Returns:
            SemanticBridge with objective components and verification suggestions
        """
        logger.info(f"Analyzing subjective claim for objective components: '{claim_text}'")
        
        # Extract objective components
        components = self.term_extractor.extract_objective_components(claim_text)
        
        # Calculate overall objectivity score
        if components:
            total_objectivity = sum(comp.confidence for comp in components) / len(components)
        else:
            total_objectivity = 0.0
        
        # Generate verification suggestions
        verification_suggestions = []
        if components:
            verifiable_claims = self.claim_generator.generate_verifiable_claims(components)
            verification_suggestions = [
                f"Verify: {claim}" for claim in verifiable_claims[:5]  # Top 5 suggestions
            ]
        
        # Determine if we found any objective grounding
        if total_objectivity >= 0.4:
            logger.info(f"Found objective grounding (score: {total_objectivity:.2f}) for subjective claim")
        else:
            logger.debug(f"Limited objective grounding (score: {total_objectivity:.2f}) for subjective claim")
        
        return SemanticBridge(
            subjective_term=claim_text,
            objective_components=components,
            total_objectivity_score=total_objectivity,
            suggested_verification=verification_suggestions
        )
    
    def should_attempt_verification(self, bridge: SemanticBridge, threshold: float = 0.4) -> bool:
        """Determine if a claim has enough objective grounding to warrant verification.
        
        Args:
            bridge: The semantic bridge analysis
            threshold: Minimum objectivity score to attempt verification
            
        Returns:
            True if verification should be attempted
        """
        return bridge.total_objectivity_score >= threshold
    
    def get_verification_targets(self, bridge: SemanticBridge) -> List[str]:
        """Get the most promising verification targets from a semantic bridge.
        
        Args:
            bridge: The semantic bridge analysis
            
        Returns:
            List of claims to attempt formal verification on
        """
        if not self.should_attempt_verification(bridge):
            return []
        
        # Prioritize mathematical components (highest confidence)
        mathematical_components = [
            comp for comp in bridge.objective_components 
            if comp.objectivity_level == ObjectivityLevel.MATHEMATICAL
        ]
        
        targets = []
        if mathematical_components:
            # Generate mathematical verification targets
            targets.extend(self.claim_generator.generate_verifiable_claims(mathematical_components))
        
        # Add high-confidence measurable components
        measurable_components = [
            comp for comp in bridge.objective_components
            if comp.objectivity_level == ObjectivityLevel.MEASURABLE and comp.confidence >= 0.7
        ]
        
        if measurable_components:
            targets.extend(self.claim_generator.generate_verifiable_claims(measurable_components))
        
        return targets[:3]  # Return top 3 most promising targets


def bridge_subjective_to_objective(claim_text: str) -> Optional[SemanticBridge]:
    """Utility function to quickly bridge subjective claims to objective components.
    
    Args:
        claim_text: The claim to analyze
        
    Returns:
        SemanticBridge if objective components found, None otherwise
    """
    bridge_system = SemanticLogicalBridge()
    bridge = bridge_system.analyze_subjective_claim(claim_text)
    
    if bridge.total_objectivity_score > 0.0:
        return bridge
    return None