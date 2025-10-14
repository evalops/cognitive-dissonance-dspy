"""Guardrails for validating claim extraction quality.

Guardrails ensure that extracted claims meet quality standards and can be
successfully translated to Coq specifications before being passed to the prover.
"""

import logging
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from .structured_models import FormalizableClaim, ClaimCategory
from .types import Claim, PropertyType
from .translator import ClaimTranslator

logger = logging.getLogger(__name__)


@dataclass
class GuardrailViolation:
    """Represents a violation of a guardrail rule."""
    rule_name: str
    severity: str  # 'error', 'warning'
    message: str
    suggestion: Optional[str] = None


@dataclass
class GuardrailResult:
    """Result of guardrail validation."""
    passed: bool
    violations: List[GuardrailViolation]
    confidence_adjustment: float = 0.0  # Adjust confidence up/down based on checks


class ClaimGuardrails:
    """
    Guardrails for validating extracted claims.

    These guardrails perform multiple checks to ensure claims are
    high-quality and can be successfully formalized.
    """

    def __init__(self, strict: bool = True):
        """
        Initialize guardrails.

        Args:
            strict: If True, fail on warnings. If False, only fail on errors.
        """
        self.strict = strict
        self.translator = ClaimTranslator()
        logger.info(f"Initialized ClaimGuardrails (strict={strict})")

    def validate(
        self,
        claim: FormalizableClaim,
        code_context: str = ""
    ) -> GuardrailResult:
        """
        Validate a claim against all guardrails.

        Args:
            claim: The claim to validate
            code_context: Optional code context

        Returns:
            GuardrailResult with validation status and violations
        """
        violations: List[GuardrailViolation] = []

        # Run all guardrail checks
        violations.extend(self._check_format_validity(claim))
        violations.extend(self._check_translator_compatibility(claim, code_context))
        violations.extend(self._check_variable_consistency(claim))
        violations.extend(self._check_confidence_alignment(claim))
        violations.extend(self._check_pattern_hints(claim))

        # Determine if passed
        has_errors = any(v.severity == 'error' for v in violations)
        has_warnings = any(v.severity == 'warning' for v in violations)

        passed = not has_errors and (not self.strict or not has_warnings)

        # Adjust confidence based on violations
        confidence_adjustment = -0.1 * len([v for v in violations if v.severity == 'warning'])
        confidence_adjustment += -0.3 * len([v for v in violations if v.severity == 'error'])

        result = GuardrailResult(
            passed=passed,
            violations=violations,
            confidence_adjustment=confidence_adjustment
        )

        if not passed:
            logger.warning(
                f"Claim failed guardrails: {claim.claim_text} "
                f"({len(violations)} violations)"
            )
        else:
            logger.debug(f"Claim passed guardrails: {claim.claim_text}")

        return result

    def _check_format_validity(self, claim: FormalizableClaim) -> List[GuardrailViolation]:
        """Check that the claim format matches expected patterns for its category."""
        violations = []

        # Category-specific format checks
        if claim.category == ClaimCategory.ARITHMETIC:
            if not re.search(r'\d+\s*\+\s*\d+\s*=\s*\d+', claim.claim_text):
                violations.append(GuardrailViolation(
                    rule_name="arithmetic_format",
                    severity="error",
                    message=f"Arithmetic claim must match 'N + M = R' pattern",
                    suggestion=f"Reformat as 'N + M = R' with actual numbers"
                ))

        elif claim.category == ClaimCategory.FACTORIAL:
            if not re.search(r'factorial\s*\(?\d+\)?\s*(?:=|equals)\s*\d+', claim.claim_text, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    rule_name="factorial_format",
                    severity="error",
                    message=f"Factorial claim must match 'factorial N = M' pattern",
                    suggestion="Use format: 'factorial 5 = 120'"
                ))

        elif claim.category == ClaimCategory.INEQUALITY:
            if not re.search(r'\d+\s*[<>]=?\s*\d+', claim.claim_text):
                violations.append(GuardrailViolation(
                    rule_name="inequality_format",
                    severity="error",
                    message=f"Inequality must use symbols: <, >, <=, >=",
                    suggestion="Use format: '3 < 5' or '10 >= 7'"
                ))

        elif claim.category in [ClaimCategory.LOGIC_IMPLICATION]:
            if not re.search(r'if\s+.+\s+then|.+\s+implies\s+', claim.claim_text, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    rule_name="implication_format",
                    severity="error",
                    message="Implication must use 'if...then' or 'implies'",
                    suggestion="Use format: 'if x > 5 then x > 3'"
                ))

        elif claim.category == ClaimCategory.LOGIC_FORALL:
            if not re.search(r'forall|for\s+all', claim.claim_text, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    rule_name="forall_format",
                    severity="error",
                    message="Universal quantification must use 'forall'",
                    suggestion="Use format: 'forall n, n + 0 = n'"
                ))

        # Check for natural language artifacts that should be removed
        natural_language_artifacts = [
            (r'\b(the|a|an)\b', "Remove articles like 'the', 'a', 'an'"),
            (r'\b(is|are|was|were)\b', "Remove verb forms like 'is', 'are'"),
            (r'\b(correctly|properly|accurately)\b', "Remove adverbs like 'correctly'"),
        ]

        for pattern, suggestion in natural_language_artifacts:
            if re.search(pattern, claim.claim_text, re.IGNORECASE):
                violations.append(GuardrailViolation(
                    rule_name="natural_language_artifact",
                    severity="warning",
                    message=f"Claim contains natural language artifacts",
                    suggestion=suggestion
                ))

        return violations

    def _check_translator_compatibility(
        self,
        claim: FormalizableClaim,
        code_context: str
    ) -> List[GuardrailViolation]:
        """Check that the claim can be translated by the ClaimTranslator."""
        violations = []

        # Create a dummy Claim object for testing
        dummy_claim = Claim(
            agent_id="guardrail_test",
            claim_text=claim.claim_text,
            property_type=PropertyType.CORRECTNESS,
            confidence=claim.confidence,
            timestamp=0.0
        )

        # Attempt translation
        try:
            formal_spec = self.translator.translate(dummy_claim, code_context)

            if formal_spec is None:
                violations.append(GuardrailViolation(
                    rule_name="translator_compatibility",
                    severity="error",
                    message=f"Claim cannot be translated to Coq specification",
                    suggestion=(
                        f"Claim category is {claim.category.value}. "
                        "Ensure claim text matches expected pattern for this category."
                    )
                ))
            else:
                logger.debug(
                    f"Claim translates to Coq: {formal_spec.spec_text}"
                )

        except Exception as e:
            violations.append(GuardrailViolation(
                rule_name="translator_error",
                severity="error",
                message=f"Translation failed with error: {str(e)}",
                suggestion="Check claim format and category alignment"
            ))

        return violations

    def _check_variable_consistency(
        self,
        claim: FormalizableClaim
    ) -> List[GuardrailViolation]:
        """Check that extracted variables match the claim text."""
        violations = []

        if not claim.variables:
            # Some claims don't need variables (e.g., "sorts the array")
            if claim.category in [
                ClaimCategory.ARITHMETIC,
                ClaimCategory.FACTORIAL,
                ClaimCategory.INEQUALITY,
                ClaimCategory.MULTIPLICATION,
                ClaimCategory.SUBTRACTION
            ]:
                violations.append(GuardrailViolation(
                    rule_name="missing_variables",
                    severity="warning",
                    message=f"Expected variables for {claim.category.value} claim",
                    suggestion="Extract numeric values into variables dict"
                ))
            return violations

        # For arithmetic, check for left, right, result
        if claim.category == ClaimCategory.ARITHMETIC:
            expected_keys = {'left', 'right', 'result'}
            missing = expected_keys - set(claim.variables.keys())
            if missing:
                violations.append(GuardrailViolation(
                    rule_name="arithmetic_variables",
                    severity="warning",
                    message=f"Missing expected variables: {missing}",
                    suggestion="Include 'left', 'right', and 'result' in variables"
                ))

        # For factorial, check for input, output
        elif claim.category == ClaimCategory.FACTORIAL:
            expected_keys = {'input', 'output'}
            missing = expected_keys - set(claim.variables.keys())
            if missing:
                violations.append(GuardrailViolation(
                    rule_name="factorial_variables",
                    severity="warning",
                    message=f"Missing expected variables: {missing}",
                    suggestion="Include 'input' and 'output' in variables"
                ))

        # Verify that variable values actually appear in claim text
        for key, value in claim.variables.items():
            if str(value) not in claim.claim_text:
                violations.append(GuardrailViolation(
                    rule_name="variable_not_in_claim",
                    severity="warning",
                    message=f"Variable '{key}={value}' not found in claim text",
                    suggestion="Ensure extracted variables match claim text"
                ))

        return violations

    def _check_confidence_alignment(
        self,
        claim: FormalizableClaim
    ) -> List[GuardrailViolation]:
        """Check that confidence level is reasonable."""
        violations = []

        # Low confidence for claims that should be certain
        if claim.category in [
            ClaimCategory.ARITHMETIC,
            ClaimCategory.FACTORIAL,
            ClaimCategory.INEQUALITY
        ]:
            if claim.confidence < 0.8:
                violations.append(GuardrailViolation(
                    rule_name="low_confidence_math",
                    severity="warning",
                    message=(
                        f"Mathematical claim has low confidence ({claim.confidence:.2f}). "
                        "These claims are typically verifiable with high confidence."
                    ),
                    suggestion="Review claim extraction quality"
                ))

        # Confidence too high for complex claims
        if claim.category in [
            ClaimCategory.MEMORY_SAFETY,
            ClaimCategory.TIME_COMPLEXITY
        ]:
            if claim.confidence > 0.9:
                violations.append(GuardrailViolation(
                    rule_name="overconfident_complex",
                    severity="warning",
                    message=(
                        f"Complex claim has very high confidence ({claim.confidence:.2f}). "
                        "Memory safety and complexity claims are typically harder to verify."
                    ),
                    suggestion="Consider reducing confidence for complex claims"
                ))

        return violations

    def _check_pattern_hints(
        self,
        claim: FormalizableClaim
    ) -> List[GuardrailViolation]:
        """Check that pattern hints are useful and accurate."""
        violations = []

        if not claim.pattern_hints:
            violations.append(GuardrailViolation(
                rule_name="missing_pattern_hints",
                severity="warning",
                message="No pattern hints provided",
                suggestion="Add keywords to help pattern matching"
            ))
            return violations

        # Check that pattern hints actually appear in claim
        for hint in claim.pattern_hints:
            if hint.lower() not in claim.claim_text.lower():
                violations.append(GuardrailViolation(
                    rule_name="pattern_hint_mismatch",
                    severity="warning",
                    message=f"Pattern hint '{hint}' not found in claim text",
                    suggestion="Ensure pattern hints match claim keywords"
                ))

        return violations


class GuardrailWithRetry:
    """
    Wrapper that allows agents to retry claim extraction if guardrails fail.

    This implements a feedback loop where guardrail violations are fed back
    to the extraction agent for correction.
    """

    def __init__(
        self,
        extractor,
        guardrails: ClaimGuardrails,
        max_retries: int = 2
    ):
        """
        Initialize guardrail with retry mechanism.

        Args:
            extractor: OpenAIClaimExtractor instance
            guardrails: ClaimGuardrails instance
            max_retries: Maximum number of retry attempts
        """
        self.extractor = extractor
        self.guardrails = guardrails
        self.max_retries = max_retries
        logger.info(f"Initialized GuardrailWithRetry (max_retries={max_retries})")

    def extract_with_validation(
        self,
        text: str,
        code_context: str = ""
    ) -> Tuple[Optional[FormalizableClaim], GuardrailResult]:
        """
        Extract a claim with guardrail validation and retry on failure.

        Args:
            text: Text to extract claim from
            code_context: Optional code context

        Returns:
            Tuple of (claim, guardrail_result)
        """
        for attempt in range(self.max_retries + 1):
            logger.debug(f"Extraction attempt {attempt + 1}/{self.max_retries + 1}")

            # Extract claim
            result = self.extractor.extract_claim(text, code_context)

            if not result.is_formalizable or result.claim is None:
                logger.warning(f"Claim not formalizable: {result.reasoning}")
                return None, GuardrailResult(
                    passed=False,
                    violations=[GuardrailViolation(
                        rule_name="not_formalizable",
                        severity="error",
                        message=result.reasoning,
                        suggestion=result.alternative_formulation
                    )]
                )

            # Validate with guardrails
            validation = self.guardrails.validate(result.claim, code_context)

            if validation.passed:
                logger.info(
                    f"Claim extracted and validated successfully on attempt {attempt + 1}"
                )
                return result.claim, validation

            # If failed and we have retries left, provide feedback
            if attempt < self.max_retries:
                logger.debug(
                    f"Guardrail failed, retrying with feedback "
                    f"({len(validation.violations)} violations)"
                )
                # In a full implementation, we would feed violations back to the agent
                # For now, we'll just retry
                continue

        # All retries exhausted
        logger.warning(
            f"Failed to extract valid claim after {self.max_retries + 1} attempts"
        )
        return result.claim, validation
