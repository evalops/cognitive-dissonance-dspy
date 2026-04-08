"""Formal Verification Cognitive Dissonance Detection Module.

This module combines DSPy-based cognitive dissonance detection with formal
verification methods using theorem provers like Coq to provide mathematically
rigorous conflict resolution for agent claims about code properties.
"""

from .detector import FormalVerificationConflictDetector
from .proof_protocol import PreservationAuditor, build_claim_ir, canonicalize_surface_claim
from .prover import CoqProver
from .structured_models import CanonicalClaimIR, PreservationAudit, PreservationLabel
from .translator import ClaimTranslator
from .types import Claim, FormalSpec, ProofResult, ProofStatus, PropertyType

__version__ = "0.1.0"

__all__ = [
    "Claim",
    "ClaimTranslator",
    "CanonicalClaimIR",
    "CoqProver",
    "FormalSpec",
    "FormalVerificationConflictDetector",
    "PreservationAudit",
    "PreservationAuditor",
    "PreservationLabel",
    "ProofResult",
    "ProofStatus",
    "PropertyType",
    "build_claim_ir",
    "canonicalize_surface_claim",
]
