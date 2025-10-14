"""Type definitions for formal verification cognitive dissonance detection."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class PropertyType(Enum):
    """Types of properties that can be formally verified."""
    MEMORY_SAFETY = "memory_safety"
    TIME_COMPLEXITY = "time_complexity"
    CORRECTNESS = "correctness"
    CONCURRENCY = "concurrency"
    TERMINATION = "termination"


@dataclass
class Claim:
    """A claim made by an agent about code properties."""
    agent_id: str
    claim_text: str
    property_type: PropertyType
    confidence: float
    timestamp: float


@dataclass
class FormalSpec:
    """Formal specification derived from a natural language claim."""
    claim: Claim
    spec_text: str
    coq_code: str
    variables: Dict[str, str]


@dataclass
class ProofResult:
    """Result of attempting to prove a formal specification."""
    spec: Optional[FormalSpec]
    proven: bool
    proof_time_ms: float
    error_message: Optional[str]
    counter_example: Optional[str]
    proof_output: str = ""
    prover_name: Optional[str] = None
    solver_status: Optional[str] = None
    auto_repaired: bool = False