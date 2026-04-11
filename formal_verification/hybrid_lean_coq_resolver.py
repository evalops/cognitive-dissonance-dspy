"""Hybrid Lean + Coq Conflict Resolution.

Provides intelligent fallback between Lean (via LeanDojo) and Coq provers
for maximum theorem proving coverage when resolving cognitive dissonance.
"""

import time
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from .lean_translator import LeanTranslator, LeanStatement
from .lean_prover import LeanProver, ProofResult as LeanProofResult
from .translator import ClaimTranslator
from .prover import CoqProver
from .types import Claim, PropertyType

logger = logging.getLogger(__name__)


class ProverBackend(Enum):
    """Available theorem proving backends."""
    LEAN_DOJO = "lean_dojo"
    COQ = "coq"
    HYBRID = "hybrid"


@dataclass
class HybridProofResult:
    """Result from hybrid Lean/Coq prover."""
    proven: bool
    prover_used: ProverBackend
    primary_result: Optional[object] = None
    fallback_result: Optional[object] = None
    combined_confidence: float = 0.0


class HybridLeanCoqResolver:
    """Hybrid resolver using Lean (via LeanDojo) with Coq fallback."""

    def __init__(self, prefer_lean: bool = True, use_fallback: bool = True):
        self.prefer_lean = prefer_lean
        self.use_fallback = use_fallback
        self.lean_translator = LeanTranslator()
        self.lean_prover = LeanProver()
        self.coq_translator = ClaimTranslator()
        self.coq_prover = CoqProver()

    def resolve_conflict(
        self, claims: List[Tuple[str, str, str]]
    ) -> HybridProofResult:
        """Resolve a conflict between claims using hybrid approach.
        
        Args:
            claims: List of (agent_id, claim_text, claim_type) tuples
            
        Returns:
            HybridProofResult with proof status and prover backend used
        """
        # Try Lean first if preferred
        if self.prefer_lean:
            lean_result = self._try_lean_proof(claims)
            if lean_result.proven:
                return HybridProofResult(
                    proven=True,
                    prover_used=ProverBackend.LEAN_DOJO,
                    primary_result=lean_result,
                    combined_confidence=0.95,
                )
            
            # Fallback to Coq
            if self.use_fallback:
                coq_result = self._try_coq_proof(claims)
                if coq_result.get("proven"):
                    return HybridProofResult(
                        proven=True,
                        prover_used=ProverBackend.COQ,
                        fallback_result=coq_result,
                        combined_confidence=0.85,
                    )
        else:
            # Try Coq first
            coq_result = self._try_coq_proof(claims)
            if coq_result.get("proven"):
                return HybridProofResult(
                    proven=True,
                    prover_used=ProverBackend.COQ,
                    primary_result=coq_result,
                    combined_confidence=0.90,
                )
            
            # Fallback to Lean
            if self.use_fallback:
                lean_result = self._try_lean_proof(claims)
                if lean_result.proven:
                    return HybridProofResult(
                        proven=True,
                        prover_used=ProverBackend.LEAN_DOJO,
                        fallback_result=lean_result,
                        combined_confidence=0.85,
                    )
        
        return HybridProofResult(proven=False, prover_used=ProverBackend.HYBRID)

    def _try_lean_proof(self, claims: List[Tuple[str, str, str]]) -> LeanProofResult:
        """Attempt proof using Lean/LeanDojo."""
        try:
            # Translate first claim to Lean
            claim_text = claims[0][1]
            claim_type = claims[0][2]
            
            lean_stmt = self.lean_translator.translate_claim(claim_text, claim_type)
            lean_code = self.lean_translator.to_lean_code(lean_stmt)
            
            # Attempt proof
            proof_result = self.lean_prover.prove(lean_code, lean_stmt.name)
            logger.info(f"Lean proof attempt: {proof_result}")
            
            return proof_result
        except Exception as e:
            logger.error(f"Lean proof failed: {e}")
            from .lean_prover import ProofResult
            return ProofResult(
                statement_name="conflict_resolution",
                proven=False,
                error_message=str(e),
            )

    def _try_coq_proof(self, claims: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """Attempt proof using Coq (existing implementation)."""
        try:
            agent_id, claim_text, claim_type = claims[0]
            claim = Claim(
                agent_id=agent_id,
                claim_text=claim_text,
                property_type=self._property_type_from_claim_type(claim_type),
                confidence=1.0,
                timestamp=time.time(),
            )
            spec = self.coq_translator.translate(claim, "")
            if spec is None:
                return {"proven": False, "result": None, "error": "translation_failed"}

            proof_result = self.coq_prover.prove_specification(spec)
            logger.info(f"Coq proof attempt: {proof_result}")
            return {
                "proven": proof_result.proven,
                "result": proof_result,
                "error": proof_result.error_message,
            }
        except Exception as e:
            logger.error(f"Coq proof failed: {e}")
            return {"proven": False, "result": None, "error": str(e)}

    def _property_type_from_claim_type(self, claim_type: str) -> PropertyType:
        normalized = claim_type.strip().lower().replace("-", "_").replace(" ", "_")
        for candidate in PropertyType:
            if candidate.value == normalized or candidate.name.lower() == normalized:
                return candidate
        return PropertyType.CORRECTNESS

    def get_best_backend_for_claim(
        self, claim_type: str
    ) -> ProverBackend:
        """Recommend best prover backend for a given claim type."""
        # Lean excels at inductive proofs and complex algebraic reasoning
        if claim_type in ["induction", "recursion", "algebra"]:
            return ProverBackend.LEAN_DOJO
        # Coq is strong with tactics and automation
        elif claim_type in ["arithmetic", "decidable"]:
            return ProverBackend.COQ
        else:
            return ProverBackend.HYBRID
