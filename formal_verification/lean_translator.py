"""Lean 4 claim translator.

Translates natural language claims to Lean 4 theorem statements,
following the same Claim -> FormalSpec pipeline as the Coq translator.
"""

import logging
import re

from .structured_models import ClaimIRKind
from .types import Claim, FormalSpec

logger = logging.getLogger(__name__)


class LeanTranslator:
    """Translates natural language claims to Lean 4 formal specifications."""

    def translate(self, claim: Claim, code: str = "") -> FormalSpec | None:
        """Convert a claim to a Lean 4 formal specification.

        Args:
            claim: The claim to translate
            code: Optional source code context

        Returns:
            FormalSpec with Lean 4 code, or None if untranslatable
        """
        spec = self._translate_from_ir(claim)
        if spec is not None:
            return spec

        spec = self._translate_from_text(claim)
        if spec is not None:
            return spec

        logger.warning("Could not translate claim to Lean: %s", claim.claim_text)
        return None

    def _translate_from_ir(self, claim: Claim) -> FormalSpec | None:
        """Translate from structured claim IR when available."""
        ir = claim.claim_ir
        if ir is None:
            return None

        kind = ir.kind
        b = ir.bindings

        if kind == ClaimIRKind.ARITHMETIC:
            return self._arithmetic(
                claim, int(b["left"]), int(b["right"]), int(b["result"])
            )
        if kind == ClaimIRKind.MULTIPLICATION:
            return self._multiplication(
                claim, int(b["left"]), int(b["right"]), int(b["result"])
            )
        if kind == ClaimIRKind.SUBTRACTION:
            return self._subtraction(
                claim, int(b["left"]), int(b["right"]), int(b["result"])
            )
        if kind == ClaimIRKind.FACTORIAL:
            return self._factorial(claim, int(b["input"]), int(b["output"]))
        if kind == ClaimIRKind.FIBONACCI:
            return self._fibonacci(claim, int(b["n"]), int(b["result"]))
        if kind == ClaimIRKind.GCD:
            return self._gcd(claim, int(b["a"]), int(b["b"]), int(b["result"]))
        if kind == ClaimIRKind.INEQUALITY:
            return self._inequality(claim, b["left"], b["op"], b["right"])
        if kind == ClaimIRKind.LOGIC_IMPLICATION:
            return self._implication(claim, b["hypothesis"], b["conclusion"])
        if kind == ClaimIRKind.LOGIC_FORALL:
            return self._forall(claim, b["variable"], b["property"])
        if kind == ClaimIRKind.LOGIC_EXISTS:
            return self._exists(claim, b["variable"], b["property"])

        return None

    def _translate_from_text(self, claim: Claim) -> FormalSpec | None:
        """Regex-based translation from claim text."""
        text = claim.claim_text.lower()

        # Arithmetic: "X + Y = Z"
        m = re.search(r"(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)", text)
        if m:
            return self._arithmetic(claim, int(m[1]), int(m[2]), int(m[3]))

        m = re.search(r"(\d+)\s*\*\s*(\d+)\s*=\s*(\d+)", text)
        if m:
            return self._multiplication(claim, int(m[1]), int(m[2]), int(m[3]))

        m = re.search(r"(\d+)\s*-\s*(\d+)\s*=\s*(\d+)", text)
        if m:
            return self._subtraction(claim, int(m[1]), int(m[2]), int(m[3]))

        m = re.search(
            r"factorial\s*\(?(\d+)\)?\s*(?:=|equals)\s*(\d+)", text, re.IGNORECASE
        )
        if m:
            return self._factorial(claim, int(m[1]), int(m[2]))

        m = re.search(r"fibonacci\s*\(?\s*(\d+)\s*\)?\s*=\s*(\d+)", text)
        if m:
            return self._fibonacci(claim, int(m[1]), int(m[2]))

        m = re.search(r"gcd\s*\(?\s*(\d+)\s*,\s*(\d+)\s*\)?\s*=\s*(\d+)", text)
        if m:
            return self._gcd(claim, int(m[1]), int(m[2]), int(m[3]))

        m = re.search(r"(\d+)\s*(<|>|<=|>=)\s*(\d+)", text)
        if m:
            return self._inequality(claim, m[1], m[2], m[3])

        return None

    # -- Lean 4 code generators ----------------------------------------

    def _arithmetic(
        self, claim: Claim, left: int, right: int, result: int
    ) -> FormalSpec:
        lean = (
            f"theorem arithmetic_claim : "
            f"({left} + {right} : Nat) = {result} := by omega"
        )
        return FormalSpec(
            claim=claim,
            spec_text=f"Arithmetic: {left} + {right} = {result}",
            coq_code=lean,
            variables={"left": str(left), "right": str(right), "result": str(result)},
            claim_ir=claim.claim_ir,
        )

    def _multiplication(
        self, claim: Claim, left: int, right: int, result: int
    ) -> FormalSpec:
        lean = (
            f"theorem mul_claim : ({left} * {right} : Nat) = {result} := by native_decide"
        )
        return FormalSpec(
            claim=claim,
            spec_text=f"Multiplication: {left} * {right} = {result}",
            coq_code=lean,
            variables={"left": str(left), "right": str(right), "result": str(result)},
            claim_ir=claim.claim_ir,
        )

    def _subtraction(
        self, claim: Claim, left: int, right: int, result: int
    ) -> FormalSpec:
        lean = (
            f"theorem sub_claim : ({left} - {right} : Nat) = {result} := by omega"
        )
        return FormalSpec(
            claim=claim,
            spec_text=f"Subtraction: {left} - {right} = {result}",
            coq_code=lean,
            variables={"left": str(left), "right": str(right), "result": str(result)},
            claim_ir=claim.claim_ir,
        )

    def _factorial(self, claim: Claim, n: int, result: int) -> FormalSpec:
        lean = f"""def factorial : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * factorial n

theorem factorial_claim : factorial {n} = {result} := by native_decide"""
        return FormalSpec(
            claim=claim,
            spec_text=f"Factorial: factorial {n} = {result}",
            coq_code=lean,
            variables={"n": str(n), "result": str(result)},
            claim_ir=claim.claim_ir,
        )

    def _fibonacci(self, claim: Claim, n: int, result: int) -> FormalSpec:
        lean = f"""def fib : Nat → Nat
  | 0 => 0
  | 1 => 1
  | n + 2 => fib (n + 1) + fib n

theorem fib_claim : fib {n} = {result} := by native_decide"""
        return FormalSpec(
            claim=claim,
            spec_text=f"Fibonacci: fib {n} = {result}",
            coq_code=lean,
            variables={"n": str(n), "result": str(result)},
            claim_ir=claim.claim_ir,
        )

    def _gcd(self, claim: Claim, a: int, b: int, result: int) -> FormalSpec:
        lean = (
            f"theorem gcd_claim : Nat.gcd {a} {b} = {result} := by native_decide"
        )
        return FormalSpec(
            claim=claim,
            spec_text=f"GCD: gcd({a}, {b}) = {result}",
            coq_code=lean,
            variables={"a": str(a), "b": str(b), "result": str(result)},
            claim_ir=claim.claim_ir,
        )

    def _inequality(
        self, claim: Claim, left: str, op: str, right: str
    ) -> FormalSpec:
        lean_op = {"<": "<", ">": ">", "<=": "≤", ">=": "≥"}.get(op, op)
        lean = (
            f"theorem ineq_claim : ({left} : Nat) {lean_op} {right} := by omega"
        )
        return FormalSpec(
            claim=claim,
            spec_text=f"Inequality: {left} {op} {right}",
            coq_code=lean,
            variables={"left": str(left), "op": op, "right": str(right)},
            claim_ir=claim.claim_ir,
        )

    def _implication(
        self, claim: Claim, hypothesis: str, conclusion: str
    ) -> FormalSpec:
        hyp = self._to_lean_expr(hypothesis)
        conc = self._to_lean_expr(conclusion)
        combined = hypothesis + " " + conclusion
        free_vars = sorted(set(re.findall(r"\b([a-z])\b", combined)))
        if free_vars:
            binders = " ".join(f"({v} : Nat)" for v in free_vars)
            lean = (
                f"theorem impl_claim : ∀ {binders}, "
                f"{hyp} → {conc} := by omega"
            )
        else:
            lean = f"theorem impl_claim : {hyp} → {conc} := by omega"
        return FormalSpec(
            claim=claim,
            spec_text=f"Implication: {hypothesis} → {conclusion}",
            coq_code=lean,
            variables={"hypothesis": hypothesis, "conclusion": conclusion},
            claim_ir=claim.claim_ir,
        )

    def _forall(
        self, claim: Claim, variable: str, prop: str
    ) -> FormalSpec:
        prop_lean = self._to_lean_expr(prop)
        lean = f"theorem forall_claim : ∀ {variable} : Nat, {prop_lean} := by omega"
        return FormalSpec(
            claim=claim,
            spec_text=f"Universal: ∀ {variable}, {prop}",
            coq_code=lean,
            variables={"variable": variable, "property": prop},
            claim_ir=claim.claim_ir,
        )

    def _exists(
        self, claim: Claim, variable: str, prop: str
    ) -> FormalSpec:
        prop_lean = self._to_lean_expr(prop)
        witness = self._infer_witness(variable, prop_lean)
        lean = (
            f"theorem exists_claim : ∃ {variable} : Nat, "
            f"{prop_lean} := ⟨{witness}, by omega⟩"
        )
        return FormalSpec(
            claim=claim,
            spec_text=f"Existential: ∃ {variable}, {prop}",
            coq_code=lean,
            variables={"variable": variable, "property": prop},
            claim_ir=claim.claim_ir,
        )

    @staticmethod
    def _infer_witness(variable: str, prop: str) -> str:
        """Extract a plausible witness from a Lean property expression.

        Handles patterns like ``x > 5`` (witness 6), ``x = 3`` (witness 3),
        ``x >= 10`` (witness 10).  Falls back to ``0`` when no bound is found.
        """
        # "x > N" → N + 1
        m = re.search(rf"\b{re.escape(variable)}\s*>\s*(\d+)", prop)
        if m:
            return str(int(m[1]) + 1)
        # "x >= N" or "x ≥ N" → N
        m = re.search(rf"\b{re.escape(variable)}\s*(?:>=|≥)\s*(\d+)", prop)
        if m:
            return m[1]
        # "x = N" → N
        m = re.search(rf"\b{re.escape(variable)}\s*=\s*(\d+)", prop)
        if m:
            return m[1]
        # "N < x" → N + 1
        m = re.search(rf"(\d+)\s*<\s*{re.escape(variable)}\b", prop)
        if m:
            return str(int(m[1]) + 1)
        # "N <= x" or "N ≤ x" → N
        m = re.search(rf"(\d+)\s*(?:<=|≤)\s*{re.escape(variable)}\b", prop)
        if m:
            return m[1]
        return "0"

    @staticmethod
    def _to_lean_expr(text: str) -> str:
        """Convert natural language fragments to Lean syntax."""
        text = text.replace(" is greater than ", " > ")
        text = text.replace(" is less than ", " < ")
        text = text.replace(" equals ", " = ")
        text = text.replace(" plus ", " + ")
        text = text.replace(" minus ", " - ")
        text = text.replace(" times ", " * ")
        return text
