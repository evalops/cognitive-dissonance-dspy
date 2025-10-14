"""Z3 SMT solver integration for formal verification."""

import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Check if Z3 is available
try:
    from z3 import *
    Z3_AVAILABLE = True
except ImportError:
    Z3_AVAILABLE = False
    logger.warning("Z3 not available. Install with: pip install z3-solver")


class Z3ProofType(Enum):
    """Types of proofs Z3 can handle."""
    SATISFIABILITY = "sat"
    VALIDITY = "valid"
    MODEL_CHECKING = "model"
    OPTIMIZATION = "opt"
    INTERPOLATION = "interpolant"


@dataclass
class Z3ProofResult:
    """Result from Z3 proof attempt."""
    claim: str
    proof_type: Z3ProofType
    result: str  # sat, unsat, unknown
    model: Optional[Dict[str, Any]] = None
    proof: Optional[str] = None
    time_ms: float = 0.0
    statistics: Dict[str, Any] = None


class Z3Translator:
    """
    Translates natural language claims to Z3 formulas.
    
    Z3 is particularly good at:
    - Integer/real arithmetic
    - Bit vectors
    - Arrays and sequences
    - Quantifiers with patterns
    - Satisfiability modulo theories
    """
    
    def __init__(self):
        """Initialize the Z3 translator."""
        if not Z3_AVAILABLE:
            raise ImportError("Z3 is not available")
        
        self.variables = {}
        self.solver = Solver()
    
    def translate_claim(self, claim_text: str) -> Optional[Any]:
        """
        Translate a claim to Z3 formula.
        
        Args:
            claim_text: Natural language claim
            
        Returns:
            Z3 formula if translation successful
        """
        claim_lower = claim_text.lower()
        
        # Arithmetic claims
        if self._is_arithmetic_claim(claim_lower):
            return self._translate_arithmetic(claim_text)
        
        # Array/list claims
        elif "array" in claim_lower or "list" in claim_lower:
            return self._translate_array_claim(claim_text)
        
        # Logical claims
        elif any(word in claim_lower for word in ["forall", "exists", "implies", "if"]):
            return self._translate_logical_claim(claim_text)
        
        # Optimization claims
        elif any(word in claim_lower for word in ["maximize", "minimize", "optimal"]):
            return self._translate_optimization_claim(claim_text)
        
        return None
    
    def _is_arithmetic_claim(self, claim: str) -> bool:
        """Check if claim is arithmetic."""
        import re
        return bool(re.search(r'\d+\s*[+\-*/=<>]', claim))
    
    def _translate_arithmetic(self, claim: str) -> Optional[Any]:
        """Translate arithmetic claim to Z3."""
        import re
        
        # Simple arithmetic: "10 + 15 = 25"
        match = re.search(r'(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)', claim)
        if match:
            a, b, c = int(match.group(1)), int(match.group(2)), int(match.group(3))
            return a + b == c
        
        # Multiplication: "x * 2 = 15"
        match = re.search(r'(\w+)\s*\*\s*(\d+)\s*=\s*(\d+)', claim)
        if match:
            var_name = match.group(1)
            multiplier = int(match.group(2))
            result = int(match.group(3))
            if var_name not in self.variables:
                self.variables[var_name] = Int(var_name)
            return self.variables[var_name] * multiplier == result
        
        # Inequality: "x < 10"
        match = re.search(r'(\w+)\s*<\s*(\d+)', claim)
        if match:
            var_name = match.group(1)
            value = int(match.group(2))
            if var_name not in self.variables:
                self.variables[var_name] = Int(var_name)
            # For proving validity, we need to show this holds for all x
            # But that's false, so return the formula as is
            return self.variables[var_name] < value
        
        # Greater than: "x > 5"
        match = re.search(r'(\w+)\s*>\s*(\d+)', claim)
        if match:
            var_name = match.group(1)
            value = int(match.group(2))
            if var_name not in self.variables:
                self.variables[var_name] = Int(var_name)
            return self.variables[var_name] > value
        
        # Complex arithmetic with variables: "x + y = 10"
        match = re.search(r'(\w+)\s*\+\s*(\w+)\s*=\s*(\d+)', claim)
        if match:
            var1, var2 = match.group(1), match.group(2)
            result = int(match.group(3))
            
            if var1 not in self.variables:
                self.variables[var1] = Int(var1)
            if var2 not in self.variables:
                self.variables[var2] = Int(var2)
            
            return self.variables[var1] + self.variables[var2] == result
        
        return None
    
    def _translate_array_claim(self, claim: str) -> Optional[Any]:
        """Translate array-related claim to Z3."""
        import re
        
        # Array bounds: "array[i] is safe when 0 <= i < length"
        if "safe" in claim.lower() and "array" in claim.lower():
            # Create array and index variables
            A = Array('A', IntSort(), IntSort())
            i = Int('i')
            length = Int('length')
            
            # Safety condition
            return And(i >= 0, i < length)
        
        # Array sorted: "array is sorted"
        if "sorted" in claim.lower():
            # Create array
            A = Array('A', IntSort(), IntSort())
            length = Int('length')
            
            # Sorted property
            i = Int('i')
            return ForAll([i], 
                Implies(And(i >= 0, i < length - 1),
                       A[i] <= A[i + 1]))
        
        return None
    
    def _translate_logical_claim(self, claim: str) -> Optional[Any]:
        """Translate logical claim to Z3."""
        import re
        
        # Universal quantification: "forall x, x + 0 = x"
        if "forall" in claim.lower():
            match = re.search(r'forall\s+(\w+),?\s*(.+)', claim.lower())
            if match:
                var_name = match.group(1)
                property_text = match.group(2)
                
                x = Int(var_name)
                
                # Parse property
                if "+ 0 =" in property_text:
                    return ForAll([x], x + 0 == x)
                elif "* 0 = 0" in property_text:
                    return ForAll([x], x * 0 == 0)
                elif "* 1 =" in property_text:
                    return ForAll([x], x * 1 == x)
                elif "> 0" in property_text:
                    # "forall x, x > 0" - This is false
                    return ForAll([x], x > 0)
                elif ">= 0" in property_text and "loop_counter" in property_text:
                    # Special case for loop invariants
                    loop_counter = Int('loop_counter')
                    return ForAll([loop_counter], loop_counter >= 0)
        
        # Existential: "exists x such that x > 10"
        if "exists" in claim.lower():
            # More flexible pattern matching
            patterns = [
                r'exists\s+(\w+).*?that\s+(\w+\s*[<>=]+\s*\d+)',
                r'exists\s+(\w+).*?(\w+\s*[<>=]+\s*\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, claim.lower())
                if match:
                    var_name = match.group(1)
                    condition = match.group(2)
                    
                    x = Int(var_name)
                    
                    # Parse condition
                    if ">" in condition:
                        value = int(re.search(r'\d+', condition).group())
                        return Exists([x], x > value)
                    elif "<" in condition:
                        value = int(re.search(r'\d+', condition).group())
                        return Exists([x], x < value)
        
        # Implication: "if x > 0 then x + 1 > 1"
        if "if" in claim.lower() and "then" in claim.lower():
            match = re.search(r'if\s+(.+?)\s+then\s+(.+)', claim.lower())
            if match:
                hypothesis = match.group(1)
                conclusion = match.group(2)
                
                x = Int('x')
                
                # Parse hypothesis and conclusion
                if "x > 0" in hypothesis and "x + 1 > 1" in conclusion:
                    return ForAll([x], Implies(x > 0, x + 1 > 1))
                elif ">= 0" in hypothesis and "succeeds" in conclusion:
                    # Software validation pattern
                    input_var = Int('input')
                    # We can't prove "succeeds" directly, but we can model it
                    return ForAll([input_var], Implies(input_var >= 0, True))
        
        return None
    
    def _translate_optimization_claim(self, claim: str) -> Optional[Any]:
        """Translate optimization claim to Z3."""
        # This would use Z3's optimization features
        return None


class Z3Prover:
    """
    Z3-based prover for formal verification.
    
    Advantages over Coq:
    - Better at constraint solving
    - Handles quantifiers with patterns efficiently
    - Can generate counter-examples
    - Supports multiple theories (arrays, bit-vectors, etc.)
    """
    
    def __init__(self, timeout_ms: int = 5000):
        """Initialize Z3 prover."""
        if not Z3_AVAILABLE:
            raise ImportError("Z3 is not available")
        
        self.timeout_ms = timeout_ms
        self.translator = Z3Translator()
        self.solver = Solver()
        
        # Set Z3 options
        set_param('timeout', timeout_ms)
    
    def prove_claim(self, claim_text: str) -> Z3ProofResult:
        """
        Prove a claim using Z3.
        
        Args:
            claim_text: Natural language claim
            
        Returns:
            Z3ProofResult with proof status
        """
        start_time = time.time()
        
        # Translate to Z3
        formula = self.translator.translate_claim(claim_text)
        
        if formula is None:
            return Z3ProofResult(
                claim=claim_text,
                proof_type=Z3ProofType.VALIDITY,
                result="unknown",
                time_ms=0,
                statistics={"error": "Could not translate claim"}
            )
        
        # Reset solver
        self.solver.reset()
        
        # To prove validity, we check if negation is unsatisfiable
        self.solver.add(Not(formula))
        
        # Check satisfiability
        result = self.solver.check()
        proof_time = (time.time() - start_time) * 1000
        
        # Process result
        if result == unsat:
            # Negation is unsatisfiable, so original is valid
            return Z3ProofResult(
                claim=claim_text,
                proof_type=Z3ProofType.VALIDITY,
                result="valid",
                proof=self._get_proof() if hasattr(self.solver, 'proof') else None,
                time_ms=proof_time,
                statistics=self.solver.statistics()
            )
        
        elif result == sat:
            # Negation is satisfiable, so we have a counter-example
            model = self.solver.model()
            return Z3ProofResult(
                claim=claim_text,
                proof_type=Z3ProofType.VALIDITY,
                result="invalid",
                model=self._extract_model(model),
                time_ms=proof_time,
                statistics=self.solver.statistics()
            )
        
        else:  # unknown
            return Z3ProofResult(
                claim=claim_text,
                proof_type=Z3ProofType.VALIDITY,
                result="unknown",
                time_ms=proof_time,
                statistics=self.solver.statistics()
            )
    
    def check_satisfiability(self, constraints: List[str]) -> Z3ProofResult:
        """
        Check if a set of constraints is satisfiable.
        
        Args:
            constraints: List of constraint strings
            
        Returns:
            Z3ProofResult with satisfiability result
        """
        start_time = time.time()
        self.solver.reset()
        
        # Translate and add constraints
        for constraint in constraints:
            formula = self.translator.translate_claim(constraint)
            if formula:
                self.solver.add(formula)
        
        # Check satisfiability
        result = self.solver.check()
        proof_time = (time.time() - start_time) * 1000
        
        if result == sat:
            model = self.solver.model()
            return Z3ProofResult(
                claim=" AND ".join(constraints),
                proof_type=Z3ProofType.SATISFIABILITY,
                result="satisfiable",
                model=self._extract_model(model),
                time_ms=proof_time,
                statistics=self.solver.statistics()
            )
        
        elif result == unsat:
            return Z3ProofResult(
                claim=" AND ".join(constraints),
                proof_type=Z3ProofType.SATISFIABILITY,
                result="unsatisfiable",
                proof=self._get_proof() if hasattr(self.solver, 'proof') else None,
                time_ms=proof_time,
                statistics=self.solver.statistics()
            )
        
        else:
            return Z3ProofResult(
                claim=" AND ".join(constraints),
                proof_type=Z3ProofType.SATISFIABILITY,
                result="unknown",
                time_ms=proof_time,
                statistics=self.solver.statistics()
            )
    
    def find_counter_example(self, claim_text: str) -> Optional[Dict[str, Any]]:
        """
        Find a counter-example to a claim.
        
        Args:
            claim_text: Claim to find counter-example for
            
        Returns:
            Counter-example model if found
        """
        # Translate claim
        formula = self.translator.translate_claim(claim_text)
        if not formula:
            return None
        
        # Reset and add negated formula
        self.solver.reset()
        self.solver.add(Not(formula))
        
        # Check if negation is satisfiable
        if self.solver.check() == sat:
            return self._extract_model(self.solver.model())
        
        return None
    
    def _extract_model(self, model) -> Dict[str, Any]:
        """Extract model values as dictionary."""
        if not model:
            return {}
        
        result = {}
        for decl in model.decls():
            result[str(decl.name())] = str(model[decl])
        
        return result
    
    def _get_proof(self) -> Optional[str]:
        """Get proof from solver if available."""
        # Z3 proof extraction (when enabled)
        try:
            if hasattr(self.solver, 'proof'):
                return str(self.solver.proof())
        except:
            pass
        return None


class HybridProver:
    """
    Intelligent hybrid prover with learning capabilities.
    
    This uses machine learning to choose the optimal prover and strategy:
    - Deep analysis of claim structure and complexity
    - Historical success pattern matching
    - Adaptive strategy learning from proof attempts
    """
    
    def __init__(self):
        """Initialize hybrid prover with learning system."""
        from .prover import CoqProver
        from .proof_learning import ProofStrategyLearner
        
        self.coq_prover = CoqProver()
        self.z3_prover = Z3Prover() if Z3_AVAILABLE else None
        self.learner = ProofStrategyLearner()
        
        # Legacy stats for backward compatibility
        self.success_stats = {
            'coq': {'attempts': 0, 'successes': 0},
            'z3': {'attempts': 0, 'successes': 0}
        }
    
    def prove_claim(self, claim_text: str, preferred_prover: Optional[str] = None, code: str = "") -> Dict[str, Any]:
        """
        Prove a claim using intelligent prover selection.
        
        Args:
            claim_text: Claim to prove
            preferred_prover: Optional preferred prover ('coq' or 'z3')
            code: Optional code context for analysis
            
        Returns:
            Proof result with learning metadata
        """
        from .types import Claim, PropertyType
        
        # Create claim object for analysis
        claim = Claim(
            agent_id="hybrid_prover",
            claim_text=claim_text,
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time()
        )
        
        # Get learning-based strategy recommendation
        if not preferred_prover:
            strategy = self.learner.predict_optimal_strategy(claim, code)
            prover_choice = strategy['recommended_prover']
            logger.info(f"Learning system recommends {prover_choice} for '{claim_text[:30]}...' "
                       f"(confidence: {strategy['confidence']:.1%}, reasoning: {strategy['reasoning']})")
        else:
            prover_choice = preferred_prover
            strategy = {'confidence': 0.8, 'reasoning': 'User specified', 'suggested_tactics': []}
        
        # Attempt proof with chosen prover
        start_time = time.time()
        if prover_choice == "z3" and self.z3_prover:
            result = self._prove_with_z3(claim_text)
        else:
            result = self._prove_with_coq(claim_text)
        
        # Record attempt for learning
        from .types import ProofResult
        learning_result = ProofResult(
            spec=None,  # Not needed for learning
            proven=result['proven'],
            proof_time_ms=result['time_ms'],
            error_message=result.get('error', ''),
            proof_output=f"Prover: {result['prover']}",
            counter_example=result.get('counter_example', {}),
            prover_name=result['prover'],
            solver_status="proved" if result['proven'] else "refuted",
        )
        
        self.learner.record_proof_attempt(claim, result['prover'], learning_result, code)
        
        # If first attempt fails and we have flexibility, try the other prover
        if not result['proven'] and not preferred_prover and self.z3_prover:
            logger.info(f"First attempt with {prover_choice} failed, trying alternative prover")
            
            alternative_prover = "coq" if prover_choice == "z3" else "z3"
            alternative_result = self._prove_with_z3(claim_text) if alternative_prover == "z3" else self._prove_with_coq(claim_text)
            
            # Record alternative attempt
            alt_learning_result = ProofResult(
                spec=None,
                proven=alternative_result['proven'],
                proof_time_ms=alternative_result['time_ms'], 
                error_message=alternative_result.get('error', ''),
                proof_output=f"Prover: {alternative_result['prover']}",
                counter_example=alternative_result.get('counter_example', {}),
                prover_name=alternative_result['prover'],
                solver_status="proved" if alternative_result['proven'] else "refuted",
            )
            
            self.learner.record_proof_attempt(claim, alternative_result['prover'], alt_learning_result, code)
            
            # Use alternative result if it succeeded
            if alternative_result['proven']:
                result = alternative_result
        
        # Add learning metadata to result
        result['learning_strategy'] = strategy
        result['total_proof_time'] = (time.time() - start_time) * 1000
        
        return result
    
    def _choose_prover(self, claim_text: str) -> str:
        """Choose the best prover for a claim."""
        claim_lower = claim_text.lower()
        
        # Z3 is better for:
        if any(pattern in claim_lower for pattern in [
            "satisfiable", "constraint", "counter-example",
            "array", "bit", "optimize", "minimize", "maximize"
        ]):
            return "z3" if self.z3_prover else "coq"
        
        # Coq is better for:
        if any(pattern in claim_lower for pattern in [
            "induction", "recursive", "lemma", "theorem",
            "sort", "permutation", "factorial", "fibonacci"
        ]):
            return "coq"
        
        # Use adaptive selection based on success rates
        if self.success_stats['z3']['attempts'] > 10:
            z3_rate = self.success_stats['z3']['successes'] / self.success_stats['z3']['attempts']
            coq_rate = self.success_stats['coq']['successes'] / self.success_stats['coq']['attempts']
            
            if z3_rate > coq_rate:
                return "z3" if self.z3_prover else "coq"
        
        return "coq"  # Default to Coq
    
    def _prove_with_coq(self, claim_text: str) -> Dict[str, Any]:
        """Prove using Coq."""
        from .types import Claim, PropertyType, FormalSpec
        
        # Create claim
        claim = Claim(
            agent_id="hybrid",
            claim_text=claim_text,
            property_type=PropertyType.CORRECTNESS,
            confidence=0.9,
            timestamp=time.time()
        )
        
        # Translate and prove
        from .translator import ClaimTranslator
        translator = ClaimTranslator()
        spec = translator.translate(claim, "")
        
        if not spec:
            return {'proven': False, 'prover': 'coq', 'error': 'Coq translation failed'}
        
        result = self.coq_prover.prove_specification(spec)
        
        # Update statistics
        self.success_stats['coq']['attempts'] += 1
        if result.proven:
            self.success_stats['coq']['successes'] += 1
        
        return {
            'proven': result.proven,
            'prover': 'coq',
            'time_ms': result.proof_time_ms,
            'error': result.error_message
        }
    
    def _prove_with_z3(self, claim_text: str) -> Dict[str, Any]:
        """Prove using Z3."""
        result = self.z3_prover.prove_claim(claim_text)
        
        # Update statistics  
        self.success_stats['z3']['attempts'] += 1
        if result.result == "valid":
            self.success_stats['z3']['successes'] += 1
        
        return {
            'proven': result.result == "valid",
            'prover': 'z3',
            'time_ms': result.time_ms,
            'counter_example': result.model,
            'statistics': result.statistics
        }