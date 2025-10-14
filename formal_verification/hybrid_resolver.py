"""Hybrid cognitive dissonance resolver combining OpenAI SDK and DSPy.

This module integrates the structured OpenAI SDK claim extraction with the
existing DSPy-based dissonance detection and reconciliation pipeline.
"""

import logging
import time
from typing import List, Optional, Tuple
from dataclasses import dataclass

from .openai_agents import OpenAIClaimExtractor
from .guardrails import ClaimGuardrails, GuardrailWithRetry
from .structured_models import FormalizableClaim, ClaimCategory
from .types import Claim, PropertyType, ProofResult
from .translator import ClaimTranslator
from .prover import CoqProver

logger = logging.getLogger(__name__)


@dataclass
class ClaimAnalysis:
    """Analysis result for a single claim."""
    original_text: str
    formalized_claim: Optional[FormalizableClaim]
    is_formalizable: bool
    proof_result: Optional[ProofResult]
    extraction_time_ms: float
    proof_time_ms: float
    reasoning: str


@dataclass
class ConflictAnalysis:
    """Analysis of conflicts between multiple claims."""
    claim_analyses: List[ClaimAnalysis]
    conflicts_detected: List[Tuple[int, int]]  # Indices of conflicting claims
    conflict_descriptions: List[str]
    resolution_strategy: str
    total_time_ms: float


class HybridCognitiveDissonanceResolver:
    """
    Hybrid resolver that uses:
    - OpenAI SDK for structured claim extraction
    - Guardrails for validation
    - Coq prover for formal verification
    - DSPy for dissonance detection (optional fallback)

    This provides much better claim extraction than pure DSPy while maintaining
    the formal verification capabilities.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4",
        use_guardrails: bool = True,
        strict_guardrails: bool = False
    ):
        """
        Initialize the hybrid resolver.

        Args:
            openai_api_key: OpenAI API key
            model: Model to use for claim extraction
            use_guardrails: Whether to use guardrails
            strict_guardrails: Whether to fail on warnings
        """
        self.extractor = OpenAIClaimExtractor(api_key=openai_api_key, model=model)
        self.translator = ClaimTranslator()
        self.prover = CoqProver()

        if use_guardrails:
            guardrails = ClaimGuardrails(strict=strict_guardrails)
            self.guarded_extractor = GuardrailWithRetry(
                self.extractor,
                guardrails,
                max_retries=2
            )
        else:
            self.guarded_extractor = None

        logger.info(
            f"Initialized HybridCognitiveDissonanceResolver "
            f"(model={model}, guardrails={use_guardrails})"
        )

    def analyze_claim(
        self,
        text: str,
        code_context: str = ""
    ) -> ClaimAnalysis:
        """
        Analyze a single claim: extract, validate, translate, and prove.

        Args:
            text: Text containing the claim
            code_context: Optional code context

        Returns:
            ClaimAnalysis with full analysis results
        """
        start_time = time.time()

        # Extract claim with guardrails
        if self.guarded_extractor:
            formalized_claim, validation = self.guarded_extractor.extract_with_validation(
                text, code_context
            )

            if not validation.passed:
                extraction_time = (time.time() - start_time) * 1000
                return ClaimAnalysis(
                    original_text=text,
                    formalized_claim=None,
                    is_formalizable=False,
                    proof_result=None,
                    extraction_time_ms=extraction_time,
                    proof_time_ms=0.0,
                    reasoning=f"Guardrail validation failed: {validation.violations[0].message}"
                )
        else:
            result = self.extractor.extract_claim(text, code_context)
            formalized_claim = result.claim

            if not result.is_formalizable or formalized_claim is None:
                extraction_time = (time.time() - start_time) * 1000
                return ClaimAnalysis(
                    original_text=text,
                    formalized_claim=None,
                    is_formalizable=False,
                    proof_result=None,
                    extraction_time_ms=extraction_time,
                    proof_time_ms=0.0,
                    reasoning=result.reasoning
                )

        extraction_time = (time.time() - start_time) * 1000

        # Translate to Coq
        claim_obj = Claim(
            agent_id="hybrid_resolver",
            claim_text=formalized_claim.claim_text,
            property_type=self._map_category_to_property_type(formalized_claim.category),
            confidence=formalized_claim.confidence,
            timestamp=time.time()
        )

        formal_spec = self.translator.translate(claim_obj, code_context)

        if formal_spec is None:
            return ClaimAnalysis(
                original_text=text,
                formalized_claim=formalized_claim,
                is_formalizable=False,
                proof_result=None,
                extraction_time_ms=extraction_time,
                proof_time_ms=0.0,
                reasoning="Translation to Coq failed"
            )

        # Prove with Coq
        prove_start = time.time()
        proof_result = self.prover.prove(formal_spec)
        proof_time = (time.time() - prove_start) * 1000

        reasoning = (
            f"Claim extracted as {formalized_claim.category.value}. "
            f"Proof {'succeeded' if proof_result.proven else 'failed'}."
        )

        if not proof_result.proven and proof_result.error_message:
            reasoning += f" Error: {proof_result.error_message}"

        return ClaimAnalysis(
            original_text=text,
            formalized_claim=formalized_claim,
            is_formalizable=True,
            proof_result=proof_result,
            extraction_time_ms=extraction_time,
            proof_time_ms=proof_time,
            reasoning=reasoning
        )

    def analyze_multiple_claims(
        self,
        texts: List[str],
        code_context: str = ""
    ) -> ConflictAnalysis:
        """
        Analyze multiple claims and detect conflicts.

        Args:
            texts: List of texts containing claims
            code_context: Optional code context

        Returns:
            ConflictAnalysis with conflict detection results
        """
        start_time = time.time()

        # Analyze each claim
        analyses = []
        for text in texts:
            analysis = self.analyze_claim(text, code_context)
            analyses.append(analysis)

        # Detect conflicts
        conflicts = []
        conflict_descriptions = []

        for i in range(len(analyses)):
            for j in range(i + 1, len(analyses)):
                analysis_i = analyses[i]
                analysis_j = analyses[j]

                # Both must be formalizable and have proof results
                if (analysis_i.is_formalizable and analysis_j.is_formalizable
                    and analysis_i.proof_result and analysis_j.proof_result):

                    # Conflict if one proves and one disproves
                    if analysis_i.proof_result.proven != analysis_j.proof_result.proven:
                        conflicts.append((i, j))
                        conflict_descriptions.append(
                            f"Claim {i} ({'proven' if analysis_i.proof_result.proven else 'disproven'}) "
                            f"conflicts with Claim {j} "
                            f"({'proven' if analysis_j.proof_result.proven else 'disproven'})"
                        )

                    # Check for semantic conflicts (e.g., "2+2=4" vs "2+2=5")
                    elif self._are_semantically_conflicting(
                        analysis_i.formalized_claim,
                        analysis_j.formalized_claim
                    ):
                        conflicts.append((i, j))
                        conflict_descriptions.append(
                            f"Claims {i} and {j} make contradictory assertions"
                        )

        # Determine resolution strategy
        if not conflicts:
            resolution_strategy = "No conflicts detected"
        elif all(a.proof_result and a.proof_result.proven for a in analyses if a.proof_result):
            resolution_strategy = "All provable claims are consistent"
        else:
            resolution_strategy = (
                "Conflicts detected. Trust proven claims over unproven ones. "
                "Disproven claims should be rejected."
            )

        total_time = (time.time() - start_time) * 1000

        return ConflictAnalysis(
            claim_analyses=analyses,
            conflicts_detected=conflicts,
            conflict_descriptions=conflict_descriptions,
            resolution_strategy=resolution_strategy,
            total_time_ms=total_time
        )

    def _map_category_to_property_type(
        self,
        category: ClaimCategory
    ) -> PropertyType:
        """Map claim category to property type."""
        if category in [
            ClaimCategory.SORTING,
            ClaimCategory.EXTREMUM,
            ClaimCategory.SUM,
            ClaimCategory.BINARY_SEARCH,
            ClaimCategory.PERMUTATION
        ]:
            return PropertyType.CORRECTNESS

        elif category == ClaimCategory.MEMORY_SAFETY:
            return PropertyType.MEMORY_SAFETY

        elif category == ClaimCategory.TIME_COMPLEXITY:
            return PropertyType.TIME_COMPLEXITY

        elif category in [ClaimCategory.LOOP_TERMINATION]:
            return PropertyType.TERMINATION

        else:
            return PropertyType.CORRECTNESS

    def _are_semantically_conflicting(
        self,
        claim1: Optional[FormalizableClaim],
        claim2: Optional[FormalizableClaim]
    ) -> bool:
        """
        Determine if two claims are semantically conflicting.

        For example:
        - "2 + 2 = 4" vs "2 + 2 = 5" (same left side, different results)
        - "factorial 5 = 120" vs "factorial 5 = 100"
        """
        if not claim1 or not claim2:
            return False

        # Must be same category
        if claim1.category != claim2.category:
            return False

        # For arithmetic operations, check if same inputs but different outputs
        if claim1.category in [
            ClaimCategory.ARITHMETIC,
            ClaimCategory.MULTIPLICATION,
            ClaimCategory.SUBTRACTION,
            ClaimCategory.FACTORIAL,
            ClaimCategory.FIBONACCI,
            ClaimCategory.GCD
        ]:
            # Check if inputs match
            if claim1.category == ClaimCategory.ARITHMETIC:
                if (claim1.variables.get('left') == claim2.variables.get('left')
                    and claim1.variables.get('right') == claim2.variables.get('right')):
                    # Same inputs - check if outputs differ
                    return claim1.variables.get('result') != claim2.variables.get('result')

            elif claim1.category in [ClaimCategory.FACTORIAL, ClaimCategory.FIBONACCI]:
                if claim1.variables.get('input') == claim2.variables.get('input'):
                    return claim1.variables.get('output') != claim2.variables.get('output')

            elif claim1.category == ClaimCategory.GCD:
                if (claim1.variables.get('a') == claim2.variables.get('a')
                    and claim1.variables.get('b') == claim2.variables.get('b')):
                    return claim1.variables.get('result') != claim2.variables.get('result')

        # For inequalities, check for direct contradictions
        elif claim1.category == ClaimCategory.INEQUALITY:
            # Extract the comparison from claim text
            # e.g., "3 < 5" vs "3 > 5" or "3 >= 5"
            import re

            match1 = re.search(r'(\d+)\s*([<>]=?)\s*(\d+)', claim1.claim_text)
            match2 = re.search(r'(\d+)\s*([<>]=?)\s*(\d+)', claim2.claim_text)

            if match1 and match2:
                left1, op1, right1 = match1.groups()
                left2, op2, right2 = match2.groups()

                # Same numbers being compared
                if left1 == left2 and right1 == right2:
                    # Check for contradictory operators
                    contradictions = {
                        ('<', '>'), ('<', '>='), ('>', '<'), ('>', '<='),
                        ('<=', '>'), ('>=', '<')
                    }
                    return (op1, op2) in contradictions

        return False

    def compare_with_dspy(
        self,
        texts: List[str],
        code_context: str = ""
    ) -> Dict:
        """
        Compare OpenAI SDK extraction with DSPy extraction.

        This is useful for benchmarking and understanding the improvement.

        Args:
            texts: List of texts to extract claims from
            code_context: Optional code context

        Returns:
            Dictionary with comparison metrics
        """
        # Run OpenAI extraction
        openai_start = time.time()
        openai_results = []
        for text in texts:
            analysis = self.analyze_claim(text, code_context)
            openai_results.append(analysis)
        openai_time = (time.time() - openai_start) * 1000

        # Count successes
        openai_formalizable = sum(1 for r in openai_results if r.is_formalizable)
        openai_proven = sum(
            1 for r in openai_results
            if r.proof_result and r.proof_result.proven
        )

        # For DSPy comparison, we'd need to import and run the DSPy pipeline
        # For now, just return OpenAI metrics
        return {
            "total_claims": len(texts),
            "openai": {
                "formalizable_count": openai_formalizable,
                "formalizable_rate": openai_formalizable / len(texts),
                "proven_count": openai_proven,
                "proven_rate": openai_proven / len(texts) if len(texts) > 0 else 0,
                "avg_extraction_time_ms": sum(
                    r.extraction_time_ms for r in openai_results
                ) / len(openai_results),
                "avg_proof_time_ms": sum(
                    r.proof_time_ms for r in openai_results
                ) / len(openai_results),
                "total_time_ms": openai_time
            }
        }
