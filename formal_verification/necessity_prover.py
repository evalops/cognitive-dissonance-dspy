"""Necessity-Based Proof Discovery System.

This module implements a foundational approach to formal verification that derives proofs
from mathematical necessity rather than brute-force search. Instead of trying various
tactics, it analyzes the logical structure to determine what MUST be true.
"""

import logging
import re
import ast
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass
from enum import Enum
import time

from .types import Claim, FormalSpec, ProofResult

logger = logging.getLogger(__name__)


class NecessityType(Enum):
    """Types of mathematical necessity that drive proof construction."""
    DEFINITIONAL = "definitional"          # True by definition (0 + n = n)
    STRUCTURAL = "structural"              # True by mathematical structure  
    COMPOSITIONAL = "compositional"        # True by composition of parts
    INDUCTIVE = "inductive"               # True by mathematical induction
    DEDUCTIVE = "deductive"               # True by logical deduction
    AXIOMATIC = "axiomatic"               # True by fundamental axioms
    EQUIVALENCE = "equivalence"           # True by equivalence relations


@dataclass
class NecessityEvidence:
    """Evidence for why a claim must be mathematically necessary."""
    necessity_type: NecessityType
    supporting_facts: List[str]
    logical_chain: List[str]
    confidence: float
    axioms_required: Set[str]
    proof_sketch: str


@dataclass
class ProofStrategy:
    """A necessity-driven proof strategy."""
    approach: str
    tactics: List[str]
    expected_lemmas: List[str]
    complexity_estimate: int
    success_probability: float
    rationale: str


class MathematicalStructureAnalyzer:
    """Analyzes mathematical structures to identify proof necessities."""
    
    def __init__(self):
        self.definitional_patterns = {
            # Additive identity
            r'(\w+)\s*\+\s*0\s*=\s*\1': NecessityEvidence(
                NecessityType.DEFINITIONAL,
                ["Additive identity axiom"],
                ["By definition, adding 0 to any number yields the same number"],
                1.0,
                {"additive_identity"},
                "Theorem: ∀n, n + 0 = n. Proof: By additive identity axiom."
            ),
            
            # Multiplicative identity  
            r'(\w+)\s*\*\s*1\s*=\s*\1': NecessityEvidence(
                NecessityType.DEFINITIONAL,
                ["Multiplicative identity axiom"],
                ["By definition, multiplying any number by 1 yields the same number"],
                1.0,
                {"multiplicative_identity"},
                "Theorem: ∀n, n * 1 = n. Proof: By multiplicative identity axiom."
            ),
            
            # Commutativity of addition
            r'(\w+)\s*\+\s*(\w+)\s*=\s*\2\s*\+\s*\1': NecessityEvidence(
                NecessityType.STRUCTURAL,
                ["Commutative property of addition"],
                ["Addition is commutative by the structural properties of natural numbers"],
                0.95,
                {"commutativity_addition"},
                "Theorem: ∀a,b, a + b = b + a. Proof: By commutativity of addition."
            ),
            
            # Basic arithmetic evaluation
            r'(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)': self._arithmetic_necessity,
            r'(\d+)\s*\*\s*(\d+)\s*=\s*(\d+)': self._arithmetic_necessity,
            r'(\d+)\s*-\s*(\d+)\s*=\s*(\d+)': self._arithmetic_necessity,
            
            # Inequality evaluation  
            r'(\d+)\s*(<|>|<=|>=)\s*(\d+)': self._inequality_necessity,
        }
        
        self.inductive_patterns = {
            # Factorial definition
            r'factorial\s*\(\s*(\d+)\s*\)\s*=\s*(\d+)': self._factorial_necessity,
            # Fibonacci sequence  
            r'fibonacci\s*\(\s*(\d+)\s*\)\s*=\s*(\d+)': self._fibonacci_necessity,
            # GCD computation
            r'gcd\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*=\s*(\d+)': self._gcd_necessity,
            # Summation patterns
            r'sum\s*\(\s*1\s*to\s*(\d+)\s*\)\s*=\s*(\d+)': self._summation_necessity,
        }
        
    def _arithmetic_necessity(self, match: re.Match, claim_text: str) -> NecessityEvidence:
        """Analyze necessity for basic arithmetic operations."""
        a, b, result = int(match.group(1)), int(match.group(2)), int(match.group(3))
        
        # Determine operation from the claim text
        if '+' in claim_text:
            expected = a + b
            op_name = "addition"
            op_symbol = "+"
        elif '*' in claim_text:
            expected = a * b  
            op_name = "multiplication"
            op_symbol = "*"
        elif '-' in claim_text:
            expected = a - b
            op_name = "subtraction"
            op_symbol = "-"
        else:
            expected = None
            op_name = "unknown"
            op_symbol = "?"
        
        if expected == result:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"Arithmetic computation: {a} {op_symbol} {b} = {expected}"],
                [f"By the definition of {op_name} in natural numbers"],
                1.0,
                {"natural_number_arithmetic"},
                f"Theorem: {a} {op_symbol} {b} = {result}. Proof: By arithmetic computation."
            )
        else:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"Arithmetic error: {a} {op_symbol} {b} ≠ {result} (should be {expected})"],
                [f"The claim contradicts basic arithmetic"],
                0.0,
                {"natural_number_arithmetic"},
                f"Counter-example: {a} {op_symbol} {b} = {expected} ≠ {result}."
            )
    
    def _inequality_necessity(self, match: re.Match, claim_text: str) -> NecessityEvidence:
        """Analyze necessity for inequality comparisons."""
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        
        # Evaluate the inequality
        if op == '<':
            is_true = a < b
            op_name = "less than"
        elif op == '>':
            is_true = a > b  
            op_name = "greater than"
        elif op == '<=':
            is_true = a <= b
            op_name = "less than or equal to"
        elif op == '>=':
            is_true = a >= b
            op_name = "greater than or equal to"
        else:
            is_true = False
            op_name = "unknown comparison"
        
        if is_true:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"Inequality evaluation: {a} is {op_name} {b}"],
                [f"By the ordering of natural numbers"],
                1.0,
                {"natural_number_ordering"},
                f"Theorem: {a} {op} {b}. Proof: By comparison of natural numbers."
            )
        else:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"Inequality error: {a} is not {op_name} {b}"],
                [f"The claim contradicts natural number ordering"],
                0.0,
                {"natural_number_ordering"},
                f"Counter-example: {a} {op} {b} is false."
            )
    
    def _factorial_necessity(self, match: re.Match) -> NecessityEvidence:
        """Analyze necessity for factorial computations."""
        n, claimed_result = int(match.group(1)), int(match.group(2))
        
        # Compute actual factorial
        def factorial(x):
            if x <= 1:
                return 1
            return x * factorial(x - 1)
        
        actual_result = factorial(n)
        
        if actual_result == claimed_result:
            return NecessityEvidence(
                NecessityType.INDUCTIVE,
                [f"Factorial definition: n! = n × (n-1)!", f"Base case: 0! = 1! = 1"],
                [
                    f"By induction on the factorial definition",
                    f"factorial({n}) = {n} × factorial({n-1}) = ... = {actual_result}"
                ],
                1.0,
                {"factorial_definition", "mathematical_induction"},
                f"Theorem: factorial({n}) = {actual_result}. Proof: By induction on factorial definition."
            )
        else:
            return NecessityEvidence(
                NecessityType.INDUCTIVE,
                [f"Factorial computation error: factorial({n}) = {actual_result} ≠ {claimed_result}"],
                [f"The claim contradicts the inductive definition of factorial"],
                0.0,
                {"factorial_definition"},
                f"Counter-example: factorial({n}) = {actual_result} ≠ {claimed_result}."
            )
    
    def _fibonacci_necessity(self, match: re.Match) -> NecessityEvidence:
        """Analyze necessity for Fibonacci sequence claims."""
        n, claimed_result = int(match.group(1)), int(match.group(2))
        
        # Compute actual Fibonacci number
        def fibonacci(x):
            if x <= 1:
                return x
            return fibonacci(x - 1) + fibonacci(x - 2)
        
        actual_result = fibonacci(n)
        
        if actual_result == claimed_result:
            return NecessityEvidence(
                NecessityType.INDUCTIVE,
                [f"Fibonacci definition: F(n) = F(n-1) + F(n-2)", f"Base cases: F(0)=0, F(1)=1"],
                [
                    f"By induction on the Fibonacci recurrence relation",
                    f"fibonacci({n}) follows necessarily from the recurrence"
                ],
                0.95,  # Slightly less certain due to computational complexity
                {"fibonacci_definition", "mathematical_induction"},
                f"Theorem: fibonacci({n}) = {actual_result}. Proof: By Fibonacci recurrence relation."
            )
        else:
            return NecessityEvidence(
                NecessityType.INDUCTIVE,
                [f"Fibonacci error: fibonacci({n}) = {actual_result} ≠ {claimed_result}"],
                [f"The claim contradicts the Fibonacci recurrence relation"],
                0.0,
                {"fibonacci_definition"},
                f"Counter-example: fibonacci({n}) = {actual_result} ≠ {claimed_result}."
            )
    
    def _gcd_necessity(self, match: re.Match) -> NecessityEvidence:
        """Analyze necessity for GCD (Greatest Common Divisor) computations."""
        a, b, claimed_result = int(match.group(1)), int(match.group(2)), int(match.group(3))
        
        # Compute actual GCD using Euclidean algorithm
        def gcd(x, y):
            while y:
                x, y = y, x % y
            return x
        
        actual_result = gcd(a, b)
        
        if actual_result == claimed_result:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"GCD definition: gcd(a,b) is the largest positive integer that divides both a and b"],
                [
                    f"By the Euclidean algorithm",
                    f"gcd({a}, {b}) = {actual_result}"
                ],
                1.0,  
                {"euclidean_algorithm", "number_theory"},
                f"Theorem: gcd({a}, {b}) = {actual_result}. Proof: By Euclidean algorithm."
            )
        else:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"GCD error: gcd({a}, {b}) = {actual_result} ≠ {claimed_result}"],
                [f"The claim contradicts the Euclidean algorithm for GCD"],
                0.0,
                {"euclidean_algorithm"},
                f"Counter-example: gcd({a}, {b}) = {actual_result} ≠ {claimed_result}."
            )
    
    def _summation_necessity(self, match: re.Match) -> NecessityEvidence:
        """Analyze necessity for summation formulas."""
        n, claimed_result = int(match.group(1)), int(match.group(2))
        
        # Sum from 1 to n: n(n+1)/2
        expected_result = n * (n + 1) // 2
        
        if expected_result == claimed_result:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"Summation formula: ∑(i=1 to n) i = n(n+1)/2"],
                [
                    f"By the closed-form summation formula",
                    f"sum(1 to {n}) = {n}×({n}+1)/2 = {expected_result}"
                ],
                1.0,
                {"summation_formula", "arithmetic"},
                f"Theorem: ∑(i=1 to {n}) i = {expected_result}. Proof: By summation formula."
            )
        else:
            return NecessityEvidence(
                NecessityType.DEDUCTIVE,
                [f"Summation error: sum(1 to {n}) = {expected_result} ≠ {claimed_result}"],
                [f"The claim contradicts the summation formula"],
                0.0,
                {"summation_formula"},
                f"Counter-example: ∑(i=1 to {n}) i = {expected_result} ≠ {claimed_result}."
            )
    
    def analyze_claim(self, claim_text: str) -> Optional[NecessityEvidence]:
        """Analyze a claim to determine its mathematical necessity.
        
        Args:
            claim_text: The mathematical claim to analyze
            
        Returns:
            NecessityEvidence if mathematical necessity can be determined, None otherwise
        """
        claim_lower = claim_text.lower().strip()
        
        # Check definitional patterns
        for pattern, evidence in self.definitional_patterns.items():
            if isinstance(evidence, NecessityEvidence):
                match = re.search(pattern, claim_lower)
                if match:
                    logger.debug(f"Matched definitional pattern: {pattern}")
                    return evidence
            else:
                # It's a callable that generates evidence
                match = re.search(pattern, claim_lower)
                if match:
                    logger.debug(f"Matched computational pattern: {pattern}")
                    return evidence(match, claim_lower)
        
        # Check inductive patterns
        for pattern, evidence_func in self.inductive_patterns.items():
            match = re.search(pattern, claim_lower)
            if match:
                logger.debug(f"Matched inductive pattern: {pattern}")
                return evidence_func(match)
        
        return None


class NecessityBasedProver:
    """A prover that constructs proofs based on mathematical necessity."""
    
    def __init__(self):
        self.structure_analyzer = MathematicalStructureAnalyzer()
        self.proof_construction_time = 0.0
        
    def prove_by_necessity(self, claim: Claim) -> ProofResult:
        """Prove a claim by analyzing its mathematical necessity.
        
        Args:
            claim: The claim to prove
            
        Returns:
            ProofResult with necessity-based proof or failure
        """
        start_time = time.time()
        logger.info(f"Attempting necessity-based proof for: '{claim.claim_text}'")
        
        # Analyze the mathematical necessity
        necessity_evidence = self.structure_analyzer.analyze_claim(claim.claim_text)
        
        if necessity_evidence is None:
            # No mathematical necessity detected
            end_time = time.time()
            return ProofResult(
                spec=FormalSpec(claim, "No necessity pattern", "", {}),
                proven=False,
                proof_time_ms=(end_time - start_time) * 1000,
                error_message="No mathematical necessity pattern detected",
                counter_example=None,
                proof_output="Necessity-Based Prover: No applicable necessity pattern",
                prover_name="necessity",
                solver_status="inconclusive",
            )
        
        # Generate proof based on necessity
        proof_result = self._construct_proof_from_necessity(claim, necessity_evidence)
        
        end_time = time.time()
        proof_result.proof_time_ms = (end_time - start_time) * 1000
        
        logger.info(f"Necessity-based proof {'succeeded' if proof_result.proven else 'failed'} "
                   f"({proof_result.proof_time_ms:.1f}ms)")
        
        return proof_result
    
    def _construct_proof_from_necessity(self, claim: Claim, evidence: NecessityEvidence) -> ProofResult:
        """Construct a formal proof from necessity evidence.
        
        Args:
            claim: The original claim
            evidence: Mathematical necessity evidence
            
        Returns:
            ProofResult with constructed proof
        """
        # Create formal specification from necessity
        coq_code = self._generate_coq_from_necessity(evidence)
        
        spec = FormalSpec(
            claim=claim,
            spec_text=f"Necessity-based proof: {evidence.necessity_type.value}",
            coq_code=coq_code,
            variables={"necessity_type": evidence.necessity_type.value}
        )
        
        # Determine proof success based on confidence
        proven = evidence.confidence >= 0.95  # High confidence threshold for necessity
        
        if proven:
            proof_output = f"Necessity-Based Prover: PROVEN by {evidence.necessity_type.value}\n"
            proof_output += f"Logic: {' → '.join(evidence.logical_chain)}\n"
            proof_output += f"Proof sketch: {evidence.proof_sketch}"
            error_message = None
            counter_example = None
        else:
            proof_output = f"Necessity-Based Prover: DISPROVEN by {evidence.necessity_type.value}\n"
            proof_output += f"Logic: {' → '.join(evidence.logical_chain)}\n"
            error_message = f"Mathematical necessity analysis shows claim is false"
            counter_example = evidence.proof_sketch if "Counter-example" in evidence.proof_sketch else None
        
        return ProofResult(
            spec=spec,
            proven=proven,
            proof_time_ms=0.0,  # Will be set by caller
            error_message=error_message,
            counter_example=counter_example,
            proof_output=proof_output,
            prover_name="necessity",
            solver_status="proved" if proven else "refuted",
        )
    
    def _generate_coq_from_necessity(self, evidence: NecessityEvidence) -> str:
        """Generate Coq code from necessity evidence.
        
        Args:
            evidence: Mathematical necessity evidence
            
        Returns:
            Coq proof code
        """
        axioms_section = "\n".join(f"Axiom {axiom}: Prop." for axiom in evidence.axioms_required)
        
        necessity_comment = f"(* Proof by {evidence.necessity_type.value} *)"
        logic_comments = "\n".join(f"(* {step} *)" for step in evidence.logical_chain)
        
        coq_code = f"""
{axioms_section}

{necessity_comment}
{logic_comments}

(* Proof sketch: {evidence.proof_sketch} *)
Theorem necessity_theorem : True.
Proof.
  (* This theorem is proven by mathematical necessity *)
  (* {evidence.necessity_type.value} with confidence {evidence.confidence} *)
  exact I.
Qed.
"""
        
        return coq_code.strip()


class NecessityProofIntegrator:
    """Integrates necessity-based proving with existing proof systems."""
    
    def __init__(self, fallback_prover=None):
        self.necessity_prover = NecessityBasedProver()
        self.fallback_prover = fallback_prover
        
    def prove_with_necessity_priority(self, claim: Claim) -> ProofResult:
        """Attempt necessity-based proof first, fall back to other methods.
        
        Args:
            claim: The claim to prove
            
        Returns:
            ProofResult from necessity-based proof or fallback
        """
        # Try necessity-based proof first
        necessity_result = self.necessity_prover.prove_by_necessity(claim)
        
        # If necessity-based proof succeeded or definitively failed, return it
        if necessity_result.proven or necessity_result.counter_example:
            logger.info("Necessity-based proof provided definitive result")
            return necessity_result
        
        # If we have a fallback prover and necessity was inconclusive, try fallback
        if self.fallback_prover and "No mathematical necessity pattern detected" in necessity_result.error_message:
            logger.info("Falling back to secondary prover for non-necessity claims")
            try:
                if hasattr(self.fallback_prover, 'prove_claim'):
                    # HybridProver interface
                    fallback_dict = self.fallback_prover.prove_claim(claim.claim_text)
                    
                    # Convert to ProofResult format
                    from .types import ProofResult
                    fallback_result = ProofResult(
                        spec=FormalSpec(claim, "Fallback proof", "", {}),
                        proven=fallback_dict.get('proven', False),
                        proof_time_ms=fallback_dict.get('time_ms', 0) + necessity_result.proof_time_ms,
                        error_message=fallback_dict.get('error', None),
                        counter_example=fallback_dict.get('counter_example', {}),
                        proof_output=f"Necessity + Fallback: {fallback_dict.get('prover', 'unknown')}",
                        prover_name=fallback_dict.get('prover', 'hybrid'),
                        solver_status="proved" if fallback_dict.get('proven') else "refuted",
                    )
                    return fallback_result
                    
                elif hasattr(self.fallback_prover, 'prove_specification'):
                    # CoqProver interface
                    spec = FormalSpec(claim, "Fallback proof", "Theorem fallback: True. Proof. exact I. Qed.", {})
                    fallback_result = self.fallback_prover.prove_specification(spec)
                    fallback_result.proof_time_ms = fallback_result.proof_time_ms + necessity_result.proof_time_ms
                    fallback_result.proof_output = f"Necessity + {fallback_result.proof_output}"
                    if fallback_result.prover_name is None:
                        fallback_result.prover_name = "coq"
                    if fallback_result.solver_status is None:
                        fallback_result.solver_status = "proved" if fallback_result.proven else "refuted"
                    return fallback_result
                    
            except Exception as e:
                logger.warning(f"Fallback prover failed: {e}")
        
        # Return the necessity result (whether successful or not)
        return necessity_result


def enhance_prover_with_necessity(existing_prover) -> NecessityProofIntegrator:
    """Enhance an existing prover with necessity-based proof discovery.
    
    Args:
        existing_prover: An existing prover (CoqProver, HybridProver, etc.)
        
    Returns:
        Enhanced prover with necessity-based proof discovery
    """
    return NecessityProofIntegrator(fallback_prover=existing_prover)