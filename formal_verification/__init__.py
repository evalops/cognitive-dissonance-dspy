"""Formal Verification Cognitive Dissonance Detection Module.

This module combines DSPy-based cognitive dissonance detection with formal
verification methods using theorem provers like Coq to provide mathematically
rigorous conflict resolution for agent claims about code properties.
"""

from .detector import FormalVerificationConflictDetector
from .prover import CoqProver
from .translator import ClaimTranslator
from .types import Claim, FormalSpec, ProofResult, ProofStatus, PropertyType

__version__ = "0.1.0"

__all__ = [
    "Claim",
    "ClaimTranslator",
    "CoqProver",
    "FormalSpec",
    "FormalVerificationConflictDetector",
    "ProofResult",
    "ProofStatus",
    "PropertyType",
]
