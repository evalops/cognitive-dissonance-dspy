"""Automated lemma discovery engine for proof failures.

When proofs fail, this system automatically discovers and synthesizes
helper lemmas that would enable the proof to succeed. This is a foundational
improvement that moves from manual proof repair to automated proof synthesis.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

from .types import Claim, FormalSpec, ProofResult, ProofStatus, PropertyType

logger = logging.getLogger(__name__)


class FailureMode(Enum):
    """Types of proof failures that can be automatically resolved."""

    INDUCTION_NEEDED = "induction_needed"
    MISSING_LEMMA = "missing_lemma"
    ARITHMETIC_OVERFLOW = "arithmetic_overflow"
    UNIFICATION_FAILED = "unification_failed"
    TACTIC_FAILED = "tactic_failed"
    UNDEFINED_SYMBOL = "undefined_symbol"
    TYPE_MISMATCH = "type_mismatch"
    BOUNDEDNESS_NEEDED = "boundedness_needed"
    MONOTONICITY_NEEDED = "monotonicity_needed"
    COMMUTATIVITY_NEEDED = "commutativity_needed"


@dataclass
class SuggestedLemma:
    """A lemma suggested to help a failed proof."""

    name: str
    statement: str
    coq_code: str
    reasoning: str
    confidence: float
    failure_mode: FailureMode
    dependencies: list[str]  # Other lemmas this depends on


@dataclass
class ProofFailureAnalysis:
    """Analysis of why a proof failed."""

    failure_mode: FailureMode
    error_location: str | None
    missing_concepts: list[str]
    suggested_lemmas: list[SuggestedLemma]
    repair_strategy: str


class ErrorPatternAnalyzer:
    """Analyzes Coq error messages to understand failure modes."""

    def __init__(self):
        self.error_patterns = {
            FailureMode.INDUCTION_NEEDED: [
                r"Unable to unify.*with.*",
                r"This expression should be a type.*",
                r"Cannot infer.*inductive.*",
            ],
            FailureMode.MISSING_LEMMA: [
                r"Unable to apply lemma.*",
                r"No applicable tactic.*",
                r"Cannot find.*",
            ],
            FailureMode.ARITHMETIC_OVERFLOW: [
                r"omega.*failed.*",
                r"lia.*failed.*",
                r"arithmetic.*out of range.*",
            ],
            FailureMode.UNIFICATION_FAILED: [
                r"Unable to unify.*",
                r"Unification failure.*",
                r"Cannot unify.*with.*",
            ],
            FailureMode.UNDEFINED_SYMBOL: [
                r"The reference.*was not found.*",
                r"Unbound.*",
                r"Unknown identifier.*",
            ],
            FailureMode.TYPE_MISMATCH: [
                r"This expression has type.*but.*expected.*",
                r"Type error.*",
                r"Cannot apply.*type mismatch.*",
            ],
        }

    def analyze_error(self, error_message: str) -> FailureMode:
        """Analyze error message to determine failure mode."""
        if not error_message:
            return FailureMode.TACTIC_FAILED

        error_lower = error_message.lower()

        for failure_mode, patterns in self.error_patterns.items():
            for pattern in patterns:
                if re.search(pattern.lower(), error_lower):
                    return failure_mode

        return FailureMode.TACTIC_FAILED


class LemmaDiscoveryEngine:
    """Main engine for discovering helpful lemmas from proof failures.

    This analyzes failed proofs and automatically synthesizes lemmas
    that would help the proof succeed.
    """

    def __init__(self):
        self.error_analyzer = ErrorPatternAnalyzer()
        self.lemma_templates = self._initialize_lemma_templates()

    def discover_supporting_lemmas(
        self, failed_result: ProofResult, original_claim: Claim
    ) -> ProofFailureAnalysis:
        """Discover lemmas that would help a failed proof succeed.

        Args:
            failed_result: The failed proof result
            original_claim: The original claim that failed

        Returns:
            Analysis with suggested lemmas
        """
        failure_mode = self.error_analyzer.analyze_error(failed_result.error_message)

        logger.info(
            "Analyzing proof failure: %s for claim '%s...'",
            failure_mode.value,
            original_claim.claim_text[:50],
        )

        # Generate lemmas based on failure mode
        suggested_lemmas = []

        if failure_mode == FailureMode.INDUCTION_NEEDED:
            suggested_lemmas.extend(self._generate_induction_lemmas(original_claim))
        elif failure_mode == FailureMode.ARITHMETIC_OVERFLOW:
            suggested_lemmas.extend(self._generate_boundedness_lemmas(original_claim))
        elif failure_mode == FailureMode.MISSING_LEMMA:
            suggested_lemmas.extend(self._generate_helper_lemmas(original_claim))
        elif failure_mode == FailureMode.UNIFICATION_FAILED:
            suggested_lemmas.extend(self._generate_equality_lemmas(original_claim))

        # Always try fundamental mathematical lemmas
        suggested_lemmas.extend(self._generate_fundamental_lemmas(original_claim))

        return ProofFailureAnalysis(
            failure_mode=failure_mode,
            error_location=self._extract_error_location(failed_result.error_message),
            missing_concepts=self._identify_missing_concepts(
                original_claim, failed_result
            ),
            suggested_lemmas=suggested_lemmas,
            repair_strategy=self._generate_repair_strategy(
                failure_mode, suggested_lemmas
            ),
        )

    def _generate_induction_lemmas(self, claim: Claim) -> list[SuggestedLemma]:
        """Generate induction-related lemmas."""
        lemmas = []
        claim_text = claim.claim_text.lower()

        # Detect recursive functions that need induction
        if "factorial" in claim_text:
            lemmas.append(
                SuggestedLemma(
                    name="factorial_base_case",
                    statement="factorial 0 = 1 /\\ factorial 1 = 1",
                    coq_code="""
Lemma factorial_base_case : factorial 0 = 1 /\\ factorial 1 = 1.
Proof.
  split.
  - unfold factorial. reflexivity.
  - unfold factorial. simpl. reflexivity.
Qed.
                """.strip(),
                    reasoning="Base cases for factorial induction",
                    confidence=0.9,
                    failure_mode=FailureMode.INDUCTION_NEEDED,
                    dependencies=[],
                )
            )

            lemmas.append(
                SuggestedLemma(
                    name="factorial_inductive_step",
                    statement="forall n, factorial (S n) = (S n) * factorial n",
                    coq_code="""
Lemma factorial_inductive_step : forall n, factorial (S n) = (S n) * factorial n.
Proof.
  intro n.
  unfold factorial.
  reflexivity.
Qed.
                """.strip(),
                    reasoning="Inductive step for factorial",
                    confidence=0.85,
                    failure_mode=FailureMode.INDUCTION_NEEDED,
                    dependencies=["factorial_base_case"],
                )
            )

        elif "fibonacci" in claim_text:
            lemmas.append(
                SuggestedLemma(
                    name="fibonacci_base_cases",
                    statement="fibonacci 0 = 0 /\\ fibonacci 1 = 1",
                    coq_code="""
Lemma fibonacci_base_cases : fibonacci 0 = 0 /\\ fibonacci 1 = 1.
Proof.
  split.
  - unfold fibonacci. reflexivity.
  - unfold fibonacci. reflexivity.
Qed.
                """.strip(),
                    reasoning="Base cases for Fibonacci induction",
                    confidence=0.9,
                    failure_mode=FailureMode.INDUCTION_NEEDED,
                    dependencies=[],
                )
            )

        # Generic induction lemma for natural numbers
        if any(
            pattern in claim_text for pattern in ["forall n", "for all n", "every n"]
        ):
            lemmas.append(
                SuggestedLemma(
                    name="nat_induction_principle",
                    statement=(
                        "forall P : nat -> Prop, P 0 -> "
                        "(forall n, P n -> P (S n)) -> forall n, P n"
                    ),
                    coq_code="""
Lemma nat_induction_principle : forall P : nat -> Prop,
  P 0 -> (forall n, P n -> P (S n)) -> forall n, P n.
Proof.
  intros P H0 Hstep.
  induction n.
  - exact H0.
  - apply Hstep. exact IHn.
Qed.
                """.strip(),
                    reasoning="General induction principle for natural numbers",
                    confidence=0.7,
                    failure_mode=FailureMode.INDUCTION_NEEDED,
                    dependencies=[],
                )
            )

        return lemmas

    def _generate_boundedness_lemmas(self, claim: Claim) -> list[SuggestedLemma]:
        """Generate lemmas about bounds and ranges."""
        lemmas = []
        claim_text = claim.claim_text.lower()

        # Extract numeric bounds
        numbers = re.findall(r"\b\d+\b", claim_text)

        if numbers:
            max_num = max(int(n) for n in numbers)
            lemmas.append(
                SuggestedLemma(
                    name=f"bound_lemma_{max_num}",
                    statement=f"forall n, n <= {max_num} -> 0 <= n <= {max_num}",
                    coq_code=f"""
Lemma bound_lemma_{max_num} : forall n, n <= {max_num} -> 0 <= n <= {max_num}.
Proof.
  intros n H.
  split.
  - apply Nat.le_0_l.
  - exact H.
Qed.
                """.strip(),
                    reasoning=f"Boundedness property for values up to {max_num}",
                    confidence=0.8,
                    failure_mode=FailureMode.BOUNDEDNESS_NEEDED,
                    dependencies=[],
                )
            )

        # Monotonicity lemmas
        if any(op in claim_text for op in ["<", ">", "<=", ">="]):
            lemmas.append(
                SuggestedLemma(
                    name="addition_monotonicity",
                    statement="forall a b c, a <= b -> a + c <= b + c",
                    coq_code="""
Lemma addition_monotonicity : forall a b c, a <= b -> a + c <= b + c.
Proof.
  intros a b c H.
  apply Nat.add_le_mono_r.
  exact H.
Qed.
                """.strip(),
                    reasoning="Monotonicity of addition",
                    confidence=0.75,
                    failure_mode=FailureMode.MONOTONICITY_NEEDED,
                    dependencies=[],
                )
            )

        return lemmas

    def _generate_helper_lemmas(self, claim: Claim) -> list[SuggestedLemma]:
        """Generate general helper lemmas."""
        lemmas = []
        claim_text = claim.claim_text.lower()

        # Arithmetic helper lemmas
        if any(op in claim_text for op in ["+", "plus", "add"]):
            lemmas.append(
                SuggestedLemma(
                    name="addition_commutativity",
                    statement="forall a b, a + b = b + a",
                    coq_code="""
Lemma addition_commutativity : forall a b, a + b = b + a.
Proof.
  intros a b.
  ring.
Qed.
                """.strip(),
                    reasoning="Addition is commutative",
                    confidence=0.9,
                    failure_mode=FailureMode.COMMUTATIVITY_NEEDED,
                    dependencies=[],
                )
            )

            lemmas.append(
                SuggestedLemma(
                    name="addition_identity",
                    statement="forall n, n + 0 = n /\\ 0 + n = n",
                    coq_code="""
Lemma addition_identity : forall n, n + 0 = n /\\ 0 + n = n.
Proof.
  intro n.
  split.
  - ring.
  - ring.
Qed.
                """.strip(),
                    reasoning="Zero is the additive identity",
                    confidence=0.95,
                    failure_mode=FailureMode.MISSING_LEMMA,
                    dependencies=[],
                )
            )

        if any(op in claim_text for op in ["*", "mult", "multiply"]):
            lemmas.append(
                SuggestedLemma(
                    name="multiplication_identity",
                    statement="forall n, n * 1 = n /\\ 1 * n = n",
                    coq_code="""
Lemma multiplication_identity : forall n, n * 1 = n /\\ 1 * n = n.
Proof.
  intro n.
  split.
  - ring.
  - ring.
Qed.
                """.strip(),
                    reasoning="One is the multiplicative identity",
                    confidence=0.95,
                    failure_mode=FailureMode.MISSING_LEMMA,
                    dependencies=[],
                )
            )

        return lemmas

    def _generate_equality_lemmas(self, claim: Claim) -> list[SuggestedLemma]:
        """Generate lemmas about equality and unification."""
        lemmas = []

        lemmas.append(
            SuggestedLemma(
                name="equality_reflexivity",
                statement="forall x, x = x",
                coq_code="""
Lemma equality_reflexivity : forall x, x = x.
Proof.
  intro x.
  reflexivity.
Qed.
            """.strip(),
                reasoning="Equality is reflexive",
                confidence=0.95,
                failure_mode=FailureMode.UNIFICATION_FAILED,
                dependencies=[],
            )
        )

        lemmas.append(
            SuggestedLemma(
                name="equality_symmetry",
                statement="forall x y, x = y -> y = x",
                coq_code="""
Lemma equality_symmetry : forall x y, x = y -> y = x.
Proof.
  intros x y H.
  symmetry.
  exact H.
Qed.
            """.strip(),
                reasoning="Equality is symmetric",
                confidence=0.9,
                failure_mode=FailureMode.UNIFICATION_FAILED,
                dependencies=[],
            )
        )

        return lemmas

    def _generate_fundamental_lemmas(self, claim: Claim) -> list[SuggestedLemma]:
        """Generate fundamental mathematical lemmas that are often needed."""
        lemmas = []
        claim_text = claim.claim_text.lower()

        # Peano axioms for natural numbers
        if any(pattern in claim_text for pattern in ["nat", "natural", "number"]):
            lemmas.append(
                SuggestedLemma(
                    name="successor_injective",
                    statement="forall n m, S n = S m -> n = m",
                    coq_code="""
Lemma successor_injective : forall n m, S n = S m -> n = m.
Proof.
  intros n m H.
  injection H.
  trivial.
Qed.
                """.strip(),
                    reasoning="Successor function is injective",
                    confidence=0.8,
                    failure_mode=FailureMode.MISSING_LEMMA,
                    dependencies=[],
                )
            )

        # Decidability lemmas
        lemmas.append(
            SuggestedLemma(
                name="nat_equality_decidable",
                statement="forall n m : nat, {n = m} + {n <> m}",
                coq_code="""
Lemma nat_equality_decidable : forall n m : nat, {n = m} + {n <> m}.
Proof.
  intros n m.
  decide equality.
Qed.
            """.strip(),
                reasoning="Equality on natural numbers is decidable",
                confidence=0.75,
                failure_mode=FailureMode.MISSING_LEMMA,
                dependencies=[],
            )
        )

        return lemmas

    def _initialize_lemma_templates(self) -> dict[str, str]:
        """Initialize templates for common lemma patterns."""
        return {
            "induction_base": "Lemma {name}_base : P 0.\nProof.\n  {proof}\nQed.",
            "induction_step": (
                "Lemma {name}_step : forall n, P n -> P (S n).\n"
                "Proof.\n  {proof}\nQed."
            ),
            "commutativity": (
                "Lemma {op}_commutative : forall a b, {op} a b = {op} b a.\n"
                "Proof.\n  ring.\nQed."
            ),
            "identity": (
                "Lemma {op}_identity : forall n, {op} n {identity} = n.\n"
                "Proof.\n  ring.\nQed."
            ),
            "monotonicity": (
                "Lemma {op}_monotonic : forall a b c, a <= b -> {op} a c <= "
                "{op} b c.\nProof.\n  {proof}\nQed."
            ),
        }

    def _extract_error_location(self, error_message: str) -> str | None:
        """Extract the location where the error occurred."""
        if not error_message:
            return None

        # Look for line/position information
        line_match = re.search(r"line (\d+)", error_message)
        if line_match:
            return f"line {line_match.group(1)}"

        # Look for tactic names
        tactic_match = re.search(r"tactic (\w+)", error_message.lower())
        if tactic_match:
            return f"tactic {tactic_match.group(1)}"

        return None

    def _identify_missing_concepts(
        self, claim: Claim, failed_result: ProofResult
    ) -> list[str]:
        """Identify mathematical concepts that might be missing."""
        concepts = []
        claim_text = claim.claim_text.lower()
        error_msg = (
            failed_result.error_message.lower() if failed_result.error_message else ""
        )

        # Mathematical operations
        if "+" in claim_text and ("commutative" in error_msg or "unify" in error_msg):
            concepts.append("addition_commutativity")
        if "*" in claim_text and ("commutative" in error_msg or "unify" in error_msg):
            concepts.append("multiplication_commutativity")

        # Inductive structures
        if any(word in claim_text for word in ["factorial", "fibonacci", "recursive"]):
            concepts.append("induction_principle")

        # Bounds and ordering
        if any(op in claim_text for op in ["<", ">", "<=", ">="]):
            concepts.append("ordering_properties")

        return concepts

    def _generate_repair_strategy(
        self, failure_mode: FailureMode, lemmas: list[SuggestedLemma]
    ) -> str:
        """Generate a human-readable repair strategy."""
        if not lemmas:
            return (
                "No automatic repair available for "
                f"{failure_mode.value}. Manual intervention required."
            )

        strategies = {
            FailureMode.INDUCTION_NEEDED: (
                f"Add {len(lemmas)} induction-related lemmas and retry "
                "with induction tactic"
            ),
            FailureMode.MISSING_LEMMA: (
                f"Add {len(lemmas)} helper lemmas to establish required properties"
            ),
            FailureMode.ARITHMETIC_OVERFLOW: (
                "Add boundedness lemmas and use 'lia' instead of 'omega'"
            ),
            FailureMode.UNIFICATION_FAILED: "Add equality lemmas to help unification",
            FailureMode.BOUNDEDNESS_NEEDED: (
                f"Establish bounds with {len(lemmas)} boundedness lemmas"
            ),
        }

        return strategies.get(
            failure_mode, f"Add {len(lemmas)} supporting lemmas and retry"
        )


class AutomatedProofRepairer:
    """Attempt to repair failed proofs by adding discovered lemmas."""

    def __init__(self):
        self.lemma_engine = LemmaDiscoveryEngine()

    def repair_failed_proof(
        self, failed_result: ProofResult, original_spec: FormalSpec
    ) -> FormalSpec | None:
        """Attempt to repair a failed proof automatically.

        Args:
            failed_result: The failed proof result
            original_spec: The original specification that failed

        Returns:
            Modified specification with added lemmas, or None if repair not possible
        """
        # Discover helpful lemmas
        analysis = self.lemma_engine.discover_supporting_lemmas(
            failed_result, original_spec.claim
        )

        if not analysis.suggested_lemmas:
            logger.info(
                "No lemmas discovered for failed proof of '%s...'",
                original_spec.claim.claim_text[:50],
            )
            return None

        logger.info(
            f"Discovered {len(analysis.suggested_lemmas)} potential helper lemmas"
        )

        # Generate repaired Coq code with lemmas
        repaired_coq = self._integrate_lemmas(
            original_spec.coq_code, analysis.suggested_lemmas
        )

        # Create new specification with lemmas
        repaired_spec = FormalSpec(
            claim=original_spec.claim,
            spec_text=(
                f"{original_spec.spec_text} "
                f"(with {len(analysis.suggested_lemmas)} helper lemmas)"
            ),
            coq_code=repaired_coq,
            variables=original_spec.variables,
        )

        return repaired_spec

    def _integrate_lemmas(self, original_coq: str, lemmas: list[SuggestedLemma]) -> str:
        """Integrate discovered lemmas into the original Coq code."""
        lines = ["(* Original theorem with auto-discovered supporting lemmas *)", ""]

        # Add all lemmas first
        for lemma in lemmas:
            lines.append(f"(* {lemma.reasoning} *)")
            lines.append(lemma.coq_code)
            lines.append("")

        # Add original theorem with modified proof
        lines.append("(* Main theorem *)")
        lines.append(original_coq)

        return "\n".join(lines)


def demo_lemma_discovery():
    """Demo the lemma discovery system."""
    # Simulate a failed proof
    import time

    claim = Claim(
        agent_id="demo",
        claim_text="factorial 5 = 120",
        property_type=PropertyType.CORRECTNESS,
        confidence=0.9,
        timestamp=time.time(),
    )

    failed_result = ProofResult(
        spec=None,
        proven=False,
        proof_time_ms=1500,
        error_message=(
            "Unable to unify (factorial 5) with 120. "
            "This usually indicates that an inductive proof is needed."
        ),
        counter_example={},
        proof_output="Tactic 'reflexivity' failed.",
        prover_name="coq",
        solver_status=ProofStatus.REFUTED.value,
    )

    engine = LemmaDiscoveryEngine()
    analysis = engine.discover_supporting_lemmas(failed_result, claim)

    print(f"Failure mode: {analysis.failure_mode.value}")
    print(f"Discovered {len(analysis.suggested_lemmas)} lemmas:")

    for lemma in analysis.suggested_lemmas:
        print(f"\n- {lemma.name} (confidence: {lemma.confidence:.1%})")
        print(f"  Statement: {lemma.statement}")
        print(f"  Reasoning: {lemma.reasoning}")


if __name__ == "__main__":
    demo_lemma_discovery()
