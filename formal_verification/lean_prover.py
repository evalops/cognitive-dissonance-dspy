"""Lean 4 theorem prover interface.

Proves Lean 4 theorems by invoking the ``lean`` binary, following the
same FormalSpec -> ProofResult contract as CoqProver.
"""

import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path

from .proof_cache import ProofCache
from .types import FormalSpec, ProofResult, ProofStatus

logger = logging.getLogger(__name__)

# Patterns that indicate an unverified assumption in Lean 4 code.
_ASSUMPTION_PATTERNS: dict[str, str] = {
    "sorry": r"\bsorry\b",
    "admit": r"\badmit\b",
    "axiom": r"\baxiom\b",
}


class LeanProver:
    """Interface to the Lean 4 type-checker for formal verification."""

    def __init__(self, timeout_seconds: int = 30, use_cache: bool = True):
        """Initialize Lean prover.

        Args:
            timeout_seconds: Maximum seconds for a proof attempt.
            use_cache: Whether to cache proof results.
        """
        self.timeout_seconds = timeout_seconds
        self.use_cache = use_cache
        self.cache = ProofCache() if use_cache else None
        self.lean_available = self._check_binary("lean")

        if not self.lean_available:
            logger.warning("Lean 4 theorem prover not available")

    @staticmethod
    def _check_binary(binary: str) -> bool:
        """Check if a binary is installed and callable."""
        try:
            result = subprocess.run(
                [binary, "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    @staticmethod
    def _detect_unverified_assumptions(lean_code: str) -> list[str]:
        """Detect assumptions that prevent a sound proof."""
        markers: list[str] = []
        for label, pattern in _ASSUMPTION_PATTERNS.items():
            if re.search(pattern, lean_code):
                markers.append(label)
        return markers

    def prove_specification(self, spec: FormalSpec) -> ProofResult:
        """Attempt to prove a formal specification using Lean 4.

        Args:
            spec: The formal specification to prove (Lean code in coq_code).

        Returns:
            ProofResult with proof status and timing information.
        """
        lean_code = spec.coq_code

        if self.use_cache and self.cache:
            cached = self.cache.get(spec)
            if cached:
                return cached

        start_time = time.time()

        # Reject code that contains sorry / admit / axiom.
        assumptions = self._detect_unverified_assumptions(lean_code)
        if assumptions:
            return ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=(time.time() - start_time) * 1000,
                error_message=(
                    "Specification contains unverified assumptions: "
                    + ", ".join(assumptions)
                ),
                counter_example=None,
                proof_output="",
                prover_name="lean",
                solver_status=ProofStatus.FORMALIZED_UNPROVED.value,
                assumptions_present=True,
            )

        if not self.lean_available:
            return ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=0,
                error_message="Lean 4 theorem prover not available",
                counter_example=None,
                proof_output="",
                prover_name="lean",
                solver_status=ProofStatus.UNAVAILABLE.value,
            )

        try:
            result = self._run_lean(lean_code, start_time, spec)
        except subprocess.TimeoutExpired:
            logger.warning("Lean proof timeout for: %s", spec.spec_text)
            result = ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=self.timeout_seconds * 1000,
                error_message="Proof attempt timed out",
                counter_example=None,
                proof_output="",
                prover_name="lean",
                solver_status=ProofStatus.TIMEOUT.value,
            )
        except Exception as exc:
            logger.error("Lean proof attempt failed: %s", exc)
            result = ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=(time.time() - start_time) * 1000,
                error_message=str(exc),
                counter_example=None,
                proof_output="",
                prover_name="lean",
                solver_status=ProofStatus.INCONCLUSIVE.value,
            )

        if self.use_cache and self.cache:
            self.cache.put(spec, result)

        return result

    def _run_lean(
        self, lean_code: str, start_time: float, spec: FormalSpec
    ) -> ProofResult:
        """Invoke ``lean`` on a temporary file and interpret the result."""
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "proof.lean"
            source.write_text(lean_code, encoding="utf-8")

            proc = subprocess.run(
                ["lean", source.name],
                capture_output=True,
                timeout=self.timeout_seconds,
                cwd=tmp,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            stdout = proc.stdout.decode("utf-8") if proc.stdout else ""
            stderr = proc.stderr.decode("utf-8") if proc.stderr else ""

            if proc.returncode == 0:
                logger.debug("Lean proof succeeded for: %s", spec.spec_text)
                return ProofResult(
                    spec=spec,
                    proven=True,
                    proof_time_ms=elapsed_ms,
                    error_message=None,
                    counter_example=None,
                    proof_output=stdout,
                    prover_name="lean",
                    solver_status=ProofStatus.MACHINE_CHECKED.value,
                    checker_name="lean",
                )

            logger.debug(
                "Lean proof failed for: %s, error: %s",
                spec.spec_text,
                stderr[:100],
            )
            status = ProofStatus.default_for_solver_result(
                proven=False, prover_name="lean", counter_example=None,
            )
            return ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=elapsed_ms,
                error_message=stderr or "Lean type-check failed",
                counter_example=None,
                proof_output=stdout,
                prover_name="lean",
                solver_status=status.value,
            )
