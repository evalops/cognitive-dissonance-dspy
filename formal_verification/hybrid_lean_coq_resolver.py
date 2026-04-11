"""Hybrid Lean + Coq conflict resolver.

Tries one prover first, falls back to the other on failure.  Exposes
the standard ``prove_specification`` interface so it plugs into the
existing FormalVerificationConflictDetector without changes.
"""

import logging

from .lean_prover import LeanProver
from .lean_translator import LeanTranslator
from .prover import CoqProver
from .types import FormalSpec, ProofResult

logger = logging.getLogger(__name__)


class HybridLeanCoqResolver:
    """Lean-first prover with Coq fallback (or vice versa)."""

    def __init__(
        self,
        prefer_lean: bool = True,
        use_fallback: bool = True,
        timeout_seconds: int = 30,
    ):
        """Initialize hybrid resolver.

        Args:
            prefer_lean: If True, try Lean first; otherwise try Coq first.
            use_fallback: If True, try the other prover when the first fails.
            timeout_seconds: Per-prover timeout.
        """
        self.prefer_lean = prefer_lean
        self.use_fallback = use_fallback
        self.lean_translator = LeanTranslator()
        self.lean_prover = LeanProver(timeout_seconds=timeout_seconds)
        self.coq_prover = CoqProver(timeout_seconds=timeout_seconds)

    def prove_specification(self, spec: FormalSpec) -> ProofResult:
        """Prove a specification, trying both backends if needed.

        Args:
            spec: Formal specification (may contain Coq or Lean code).

        Returns:
            Best ProofResult obtained across backends.
        """
        if self.prefer_lean:
            return self._lean_then_coq(spec)
        return self._coq_then_lean(spec)

    def _lean_then_coq(self, spec: FormalSpec) -> ProofResult:
        """Try Lean first, fall back to Coq."""
        lean_spec = self._ensure_lean_spec(spec)
        if lean_spec is not None:
            result = self.lean_prover.prove_specification(lean_spec)
            if result.proven:
                return result

        if not self.use_fallback:
            if lean_spec is not None:
                return result
            return self._unavailable(spec, "lean")

        return self.coq_prover.prove_specification(spec)

    def _coq_then_lean(self, spec: FormalSpec) -> ProofResult:
        """Try Coq first, fall back to Lean."""
        result = self.coq_prover.prove_specification(spec)
        if result.proven:
            return result

        if not self.use_fallback:
            return result

        lean_spec = self._ensure_lean_spec(spec)
        if lean_spec is None:
            return result
        return self.lean_prover.prove_specification(lean_spec)

    def _ensure_lean_spec(self, spec: FormalSpec) -> FormalSpec | None:
        """Translate the spec's claim to Lean if needed."""
        return self.lean_translator.translate(spec.claim)

    @staticmethod
    def _unavailable(spec: FormalSpec, prover: str) -> ProofResult:
        """Return an UNAVAILABLE result when translation failed."""
        return ProofResult(
            spec=spec,
            proven=False,
            proof_time_ms=0,
            error_message=f"Could not translate claim for {prover} prover",
            counter_example=None,
            proof_output="",
            prover_name=prover,
            solver_status="unavailable",
        )
