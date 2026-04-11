"""Lean 4 Theorem Prover using LeanDojo.

Proves Lean statements using LeanDojo's API for automated proof search
and verification of cognitive dissonance resolutions.
"""

import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ProofResult:
    """Result of a proof attempt."""
    statement_name: str
    proven: bool
    proof_term: str | None = None
    error_message: str | None = None
    proof_time_ms: float = 0.0


class LeanProver:
    """Proves Lean 4 theorems using LeanDojo."""

    def __init__(self, leandojo_path: str | None = None, timeout_ms: int = 30000):
        self.leandojo_path = leandojo_path or "leandojo"
        self.timeout_ms = timeout_ms
        self.proof_cache: dict[str, ProofResult] = {}

    def prove(self, lean_code: str, statement_name: str) -> ProofResult:
        """Prove a Lean theorem.

        Args:
            lean_code: Complete Lean 4 code including theorem
            statement_name: Name of the theorem to prove

        Returns:
            ProofResult with proof status and details
        """
        cache_key = f"{statement_name}:{hash(lean_code)}"
        if cache_key in self.proof_cache:
            return self.proof_cache[cache_key]

        result = self._attempt_proof(lean_code, statement_name)
        self.proof_cache[cache_key] = result
        return result

    def _attempt_proof(self, lean_code: str, statement_name: str) -> ProofResult:
        """Attempt to prove using LeanDojo."""
        try:
            # Write code to temporary file
            temp_file = f"/tmp/lean_{statement_name}.lean"
            with Path(temp_file).open("w") as f:
                f.write(lean_code)

            # Call LeanDojo
            cmd = [
                self.leandojo_path,
                "prove",
                "--file", temp_file,
                "--theorem", statement_name,
                "--timeout", str(self.timeout_ms),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_ms / 1000.0 + 5,  # Add buffer
            )

            if result.returncode == 0:
                # Parse proof result
                proof_data = json.loads(result.stdout)
                return ProofResult(
                    statement_name=statement_name,
                    proven=True,
                    proof_term=proof_data.get("proof"),
                    proof_time_ms=float(proof_data.get("time_ms", 0)),
                )
            else:
                return ProofResult(
                    statement_name=statement_name,
                    proven=False,
                    error_message=result.stderr,
                )

        except subprocess.TimeoutExpired:
            return ProofResult(
                statement_name=statement_name,
                proven=False,
                error_message="Proof search timed out",
            )
        except Exception as e:
            logger.error(f"Proof attempt failed: {e}")
            return ProofResult(
                statement_name=statement_name,
                proven=False,
                error_message=str(e),
            )
        finally:
            # Cleanup
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def batch_prove(
        self, theorems: list[tuple[str, str]]
    ) -> list[ProofResult]:
        """Prove multiple theorems.

        Args:
            theorems: List of (lean_code, statement_name) tuples

        Returns:
            List of ProofResults
        """
        return [self.prove(code, name) for code, name in theorems]

    def verify_proof(self, lean_code: str) -> bool:
        """Verify that Lean code type-checks."""
        try:
            temp_file = "/tmp/lean_verify.lean"
            with Path(temp_file).open("w") as f:
                f.write(lean_code)

            result = subprocess.run(
                ["lean", temp_file],
                capture_output=True,
                timeout=5,
            )

            return result.returncode == 0
        except Exception:
            return False
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
