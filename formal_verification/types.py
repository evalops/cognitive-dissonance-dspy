"""Type definitions for formal verification cognitive dissonance detection."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class PropertyType(Enum):
    """Types of properties that can be formally verified."""
    MEMORY_SAFETY = "memory_safety"
    TIME_COMPLEXITY = "time_complexity"
    CORRECTNESS = "correctness"
    CONCURRENCY = "concurrency"
    TERMINATION = "termination"


class ProofStatus(str, Enum):
    """Normalized proof-status values used across provers and resolvers."""

    MACHINE_CHECKED = "machine_checked"
    SMT_PROVED = "smt_proved"
    DERIVED_PROVED = "derived_proved"
    MACHINE_REFUTED = "machine_refuted"
    SMT_REFUTED = "smt_refuted"
    REFUTED = "refuted"
    DERIVED_REFUTED = "derived_refuted"
    FORMALIZED_UNPROVED = "formalized_unproved"
    COMPILED_UNCHECKED = "compiled_unchecked"
    CHECKER_FAILED = "checker_failed"
    INCONCLUSIVE = "inconclusive"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"

    @classmethod
    def from_value(cls, value: Any | None) -> Optional["ProofStatus"]:
        """Convert raw status values into normalized enum members when possible."""
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        if not normalized:
            return None
        try:
            return cls(normalized)
        except ValueError:
            return None

    @classmethod
    def normalize(cls, value: Any | None) -> str | None:
        """Normalize solver status values for stable storage on ProofResult."""
        status = cls.from_value(value)
        if status is not None:
            return status.value
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized.lower() if normalized else None
        return str(value)

    @classmethod
    def default_for_solver_result(
        cls,
        *,
        proven: bool,
        prover_name: str | None,
        counter_example: Any | None = None,
    ) -> "ProofStatus":
        """Infer the safest default status for loosely structured solver outputs."""
        normalized_prover = (prover_name or "").strip().lower()
        has_counter_example = bool(counter_example)

        if normalized_prover == "z3":
            if proven:
                return cls.SMT_PROVED
            return cls.SMT_REFUTED if has_counter_example else cls.INCONCLUSIVE
        if normalized_prover == "coq":
            if proven:
                return cls.COMPILED_UNCHECKED
            return cls.REFUTED if has_counter_example else cls.INCONCLUSIVE
        if proven:
            return cls.DERIVED_PROVED
        if has_counter_example:
            return cls.REFUTED
        return cls.INCONCLUSIVE

    @classmethod
    def resolve(
        cls,
        value: Any | None,
        *,
        proven: bool,
        prover_name: str | None,
        counter_example: Any | None = None,
    ) -> "ProofStatus":
        """Use an explicit status when present, otherwise infer a safe default."""
        return cls.from_value(value) or cls.default_for_solver_result(
            proven=proven,
            prover_name=prover_name,
            counter_example=counter_example,
        )

    @property
    def is_machine_checked(self) -> bool:
        """Whether the proof was independently checked."""
        return self is self.MACHINE_CHECKED

    @property
    def is_definitive_disproof(self) -> bool:
        """Whether the status encodes a concrete refutation."""
        return self in {self.REFUTED, self.SMT_REFUTED, self.MACHINE_REFUTED}

    @property
    def is_formalized_unproved(self) -> bool:
        """Whether the claim was formalized but not independently validated."""
        return self in {
            self.FORMALIZED_UNPROVED,
            self.COMPILED_UNCHECKED,
            self.CHECKER_FAILED,
        }

    @property
    def supports_resolution_as_proven(self) -> bool:
        """Whether the result is strong enough to resolve toward truth."""
        return self in {self.MACHINE_CHECKED, self.SMT_PROVED}

    @property
    def counts_as_inconclusive_evidence(self) -> bool:
        """Whether the status should remain non-decisive downstream."""
        return self in {
            self.DERIVED_PROVED,
            self.DERIVED_REFUTED,
            self.FORMALIZED_UNPROVED,
            self.COMPILED_UNCHECKED,
            self.CHECKER_FAILED,
            self.INCONCLUSIVE,
            self.TIMEOUT,
            self.UNAVAILABLE,
        }


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
    variables: dict[str, str]


@dataclass
class ProofResult:
    """Result of attempting to prove a formal specification."""
    spec: FormalSpec | None
    proven: bool
    proof_time_ms: float
    error_message: str | None
    counter_example: str | None
    proof_output: str = ""
    prover_name: str | None = None
    solver_status: str | None = None
    auto_repaired: bool = False
    assumptions_present: bool = False
    checker_name: str | None = None

    def __post_init__(self) -> None:
        """Normalize status values so all callers observe a stable vocabulary."""
        self.solver_status = ProofStatus.normalize(self.solver_status)

    @property
    def status(self) -> ProofStatus | None:
        """Normalized enum view of the stored solver status."""
        return ProofStatus.from_value(self.solver_status)

    @property
    def is_machine_checked(self) -> bool:
        """Whether this result is backed by an independent proof checker."""
        return self.proven and bool(self.status and self.status.is_machine_checked)

    @property
    def is_definitive_disproof(self) -> bool:
        """Whether this result contains a concrete refutation."""
        return not self.proven and bool(
            self.status and self.status.is_definitive_disproof
        )

    @property
    def is_formalized_unproved(self) -> bool:
        """Whether the claim was formalized but remains unchecked or assumption-based."""
        return bool(self.status and self.status.is_formalized_unproved)

    @property
    def establishes_ground_truth(self) -> bool:
        """Whether this result is strong enough to count as ground truth."""
        return self.is_machine_checked and not self.assumptions_present
