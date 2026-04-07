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
    assumptions_present: bool = False
    checker_name: Optional[str] = None

    @property
    def is_machine_checked(self) -> bool:
        """Whether this result is backed by an independent proof checker."""
        return self.proven and self.solver_status == "machine_checked"

    @property
    def is_definitive_disproof(self) -> bool:
        """Whether this result contains a concrete refutation."""
        return (
            not self.proven
            and self.solver_status in {"refuted", "smt_refuted", "machine_refuted"}
        )

    @property
    def is_formalized_unproved(self) -> bool:
        """Whether the claim was formalized but remains unchecked or assumption-based."""
        return self.solver_status in {
            "formalized_unproved",
            "compiled_unchecked",
            "checker_failed",
        }

    @property
    def establishes_ground_truth(self) -> bool:
        """Whether this result is strong enough to count as ground truth."""
        return self.is_machine_checked and not self.assumptions_present
