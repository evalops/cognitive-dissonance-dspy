"""Coq theorem prover interface for formal verification."""

import re
import subprocess
import tempfile
import time
import logging
from pathlib import Path
from typing import Optional

from .types import FormalSpec, ProofResult, ProofStatus
from .proof_cache import ProofCache

logger = logging.getLogger(__name__)


class CoqProver:
    """Interface to Coq theorem prover for formal verification."""
    
    def __init__(self, timeout_seconds: int = 30, use_cache: bool = True):
        """Initialize Coq prover interface.
        
        Args:
            timeout_seconds: Maximum time to wait for proof completion
            use_cache: Whether to use proof caching
        """
        self.timeout_seconds = timeout_seconds
        self.use_cache = use_cache
        self.cache = ProofCache() if use_cache else None
        self.coq_available = self._check_binary("coqc")
        self.coqchk_available = self._check_binary("coqchk")
        
        if not self.coq_available:
            logger.warning("Coq theorem prover not available")
        elif not self.coqchk_available:
            logger.warning("coqchk not available; compiled proofs will remain unchecked")
    
    def _check_binary(self, binary: str) -> bool:
        """Check if a Coq binary is installed and available."""
        try:
            result = subprocess.run(
                [binary, "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_coq_installation(self) -> bool:
        """Backward-compatible alias for tests and older callers."""
        return self._check_binary("coqc")

    def _detect_unverified_assumptions(self, coq_code: str) -> list[str]:
        """Detect assumptions that invalidate proof soundness claims."""
        markers: list[str] = []
        patterns = {
            "Admitted": r"\bAdmitted\.",
            "Axiom": r"\bAxiom\b",
            "Axioms": r"\bAxioms\b",
            "Parameter": r"\bParameter\b",
            "Parameters": r"\bParameters\b",
        }
        for label, pattern in patterns.items():
            if re.search(pattern, coq_code):
                markers.append(label)
        return markers

    def _run_coqchk(self, artifact_path: Path, cwd: str) -> subprocess.CompletedProcess:
        """Run coqchk against a compiled .vo artifact."""
        return subprocess.run(
            ["coqchk", artifact_path.name],
            capture_output=True,
            timeout=self.timeout_seconds,
            cwd=cwd,
        )
    
    def prove_specification(self, spec: FormalSpec) -> ProofResult:
        """Attempt to prove a formal specification using Coq.
        
        Args:
            spec: The formal specification to prove
            
        Returns:
            ProofResult with success/failure and timing information
        """
        # Check cache first
        if self.use_cache and self.cache:
            cached_result = self.cache.get(spec)
            if cached_result:
                return cached_result
        
        start_time = time.time()
        assumptions = self._detect_unverified_assumptions(spec.coq_code)
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
                prover_name="coq",
                solver_status=ProofStatus.FORMALIZED_UNPROVED.value,
                assumptions_present=True,
            )

        if not self.coq_available:
            return ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=0,
                error_message="Coq theorem prover not available",
                counter_example=None,
                proof_output="",
                prover_name="coq",
                solver_status=ProofStatus.UNAVAILABLE.value,
            )

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                source_path = Path(temp_dir) / "proof.v"
                artifact_path = source_path.with_suffix(".vo")
                source_path.write_text(spec.coq_code, encoding="utf-8")

                compile_result = subprocess.run(
                    ["coqc", "-q", source_path.name],
                    capture_output=True,
                    timeout=self.timeout_seconds,
                    cwd=temp_dir,
                )

                proof_time = (time.time() - start_time) * 1000
                stdout = compile_result.stdout.decode("utf-8") if compile_result.stdout else ""

                if compile_result.returncode != 0:
                    error_msg = (
                        compile_result.stderr.decode("utf-8")
                        if compile_result.stderr
                        else "Proof failed"
                    )
                    logger.debug(
                        "Proof failed for: %s, error: %s",
                        spec.spec_text,
                        error_msg[:100],
                    )
                    proof_result = ProofResult(
                        spec=spec,
                        proven=False,
                        proof_time_ms=proof_time,
                        error_message=error_msg,
                        counter_example=self._extract_counter_example(error_msg),
                        proof_output=stdout,
                        prover_name="coq",
                        solver_status=ProofStatus.MACHINE_REFUTED.value
                        if self._extract_counter_example(error_msg)
                        else ProofStatus.REFUTED.value,
                    )
                elif not self.coqchk_available:
                    proof_result = ProofResult(
                        spec=spec,
                        proven=False,
                        proof_time_ms=proof_time,
                        error_message=(
                            "Proof compiled with coqc but coqchk is not available for "
                            "independent validation"
                        ),
                        counter_example=None,
                        proof_output=stdout,
                        prover_name="coq",
                        solver_status=ProofStatus.COMPILED_UNCHECKED.value,
                    )
                else:
                    check_result = self._run_coqchk(artifact_path, temp_dir)
                    checker_output = (
                        check_result.stdout.decode("utf-8") if check_result.stdout else ""
                    )
                    combined_output = "\n".join(
                        part for part in [stdout, checker_output] if part
                    )

                    if check_result.returncode == 0:
                        logger.debug("Machine-checked proof successful for: %s", spec.spec_text)
                        proof_result = ProofResult(
                            spec=spec,
                            proven=True,
                            proof_time_ms=proof_time,
                            error_message=None,
                            counter_example=None,
                            proof_output=combined_output,
                            prover_name="coq",
                            solver_status=ProofStatus.MACHINE_CHECKED.value,
                            checker_name="coqchk",
                        )
                    else:
                        error_msg = (
                            check_result.stderr.decode("utf-8")
                            if check_result.stderr
                            else "coqchk validation failed"
                        )
                        proof_result = ProofResult(
                            spec=spec,
                            proven=False,
                            proof_time_ms=proof_time,
                            error_message=error_msg,
                            counter_example=None,
                            proof_output=combined_output,
                            prover_name="coq",
                            solver_status=ProofStatus.CHECKER_FAILED.value,
                            checker_name="coqchk",
                        )

                if self.use_cache and self.cache:
                    self.cache.put(spec, proof_result)

                return proof_result

        except subprocess.TimeoutExpired:
            logger.warning("Proof timeout for: %s", spec.spec_text)
            return ProofResult(
                spec=spec,
                proven=False,
                proof_time_ms=self.timeout_seconds * 1000,
                error_message="Proof attempt timed out",
                counter_example=None,
                proof_output="",
                prover_name="coq",
                solver_status=ProofStatus.TIMEOUT.value,
                assumptions_present=bool(assumptions),
            )
    
    def _extract_counter_example(self, error_msg: str) -> Optional[str]:
        """Extract counter-example from Coq error message if available.
        
        Args:
            error_msg: The error message from Coq
            
        Returns:
            Counter-example string if found, None otherwise
        """
        # Simple heuristic-based counter-example extraction
        if "counter" in error_msg.lower():
            lines = error_msg.split('\n')
            for line in lines:
                if "counter" in line.lower():
                    return line.strip()
        
        return None
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {"cache_disabled": True}
