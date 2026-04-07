"""Pydantic models for structured claim extraction using OpenAI Agents SDK."""

import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ClaimCategory(str, Enum):
    """Categories of claims aligned with translator patterns."""
    ARITHMETIC = "arithmetic"
    MULTIPLICATION = "multiplication"
    SUBTRACTION = "subtraction"
    FACTORIAL = "factorial"
    FIBONACCI = "fibonacci"
    GCD = "gcd"
    MAX_ARRAY = "max_array"
    LOGIC_IMPLICATION = "logic_implication"
    LOGIC_FORALL = "logic_forall"
    LOGIC_EXISTS = "logic_exists"
    INEQUALITY = "inequality"
    SORTING = "sorting"
    EXTREMUM = "extremum"
    SUM = "sum"
    BINARY_SEARCH = "binary_search"
    PERMUTATION = "permutation"
    ARRAY_BOUNDS = "array_bounds"
    LOOP_TERMINATION = "loop_termination"
    LIST_APPEND = "list_append"
    MEMORY_SAFETY = "memory_safety"
    TIME_COMPLEXITY = "time_complexity"
    UNFORMALIZABLE = "unformalizable"


class ConfidenceLevel(str, Enum):
    """Confidence levels for claims."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FormalizableClaim(BaseModel):
    """
    Structured claim extraction with formalizability metadata.

    This model ensures claims are extracted in a format that matches
    the translator's regex patterns, significantly improving the
    success rate of formal verification.
    """

    category: ClaimCategory = Field(
        description="The category of the claim, matching translator patterns"
    )

    claim_text: str = Field(
        description="""The extracted claim in NORMALIZED canonical form. Examples:
        - Arithmetic: '2 + 2 = 4' (NOT 'two plus two equals four')
        - Factorial: 'factorial 5 = 120' (NOT 'the factorial of 5 is 120')
        - Logic: 'if x > 5 then x > 3' (NOT 'when x is greater than 5, x must be greater than 3')
        - Sorting: 'sorts the array' (NOT 'the function sorts the input correctly')
        - Inequality: '3 < 5' (NOT 'three is less than five')
        """
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level from 0.0 to 1.0"
    )

    variables: dict[str, str] = Field(
        default_factory=dict,
        description="""Extracted variables from the claim. Examples:
        - For '2 + 2 = 4': {'left': '2', 'right': '2', 'result': '4'}
        - For 'factorial 5 = 120': {'input': '5', 'output': '120'}
        - For 'if x > 5 then x > 3': {'variable': 'x'}
        """
    )

    pattern_hints: list[str] = Field(
        default_factory=list,
        description="""Keywords that help match to formal patterns. Examples:
        - ['factorial', 'equals'] for factorial claims
        - ['sorts', 'array'] for sorting claims
        - ['if', 'then'] for implication claims
        - ['forall'] for universal quantification
        """
    )

    function_name: str | None = Field(
        default=None,
        description="The function name if the claim is about a specific function"
    )

    reasoning: str = Field(
        description="""Brief explanation of why this claim is formalizable
        and which Coq pattern it maps to"""
    )

    @field_validator('claim_text')
    @classmethod
    def validate_claim_format(cls, v: str, info) -> str:
        """Validate that claim text matches expected patterns based on category."""
        category = info.data.get('category')

        if not category:
            return v

        # Validation rules per category
        if category == ClaimCategory.ARITHMETIC:
            if not re.search(r'\d+\s*\+\s*\d+\s*=\s*\d+', v):
                raise ValueError(
                    f"Arithmetic claim must match pattern 'N + M = R'. Got: {v}"
                )

        elif category == ClaimCategory.FACTORIAL:
            if not re.search(r'factorial\s*\(?\d+\)?\s*(?:=|equals)\s*\d+', v, re.IGNORECASE):
                raise ValueError(
                    f"Factorial claim must match pattern 'factorial N = M'. Got: {v}"
                )

        elif category == ClaimCategory.INEQUALITY:
            if not re.search(r'\d+\s*[<>]=?\s*\d+', v):
                raise ValueError(
                    f"Inequality claim must match pattern 'N < M' or 'N > M'. Got: {v}"
                )

        elif category == ClaimCategory.LOGIC_FORALL:
            if not re.search(r'for\s*all|forall', v, re.IGNORECASE):
                raise ValueError(
                    f"Forall claim must contain 'forall' or 'for all'. Got: {v}"
                )

        elif category == ClaimCategory.LOGIC_IMPLICATION:
            if not re.search(r'if\s+.+\s+then|.+\s+implies\s+', v, re.IGNORECASE):
                raise ValueError(
                    f"Implication claim must contain 'if...then' or 'implies'. Got: {v}"
                )

        return v


class ClaimExtractionResult(BaseModel):
    """Result of claim extraction including metadata."""

    claim: FormalizableClaim | None = Field(
        default=None,
        description="The extracted formalizable claim, or None if unformalizable"
    )

    is_formalizable: bool = Field(
        description="Whether the claim can be formalized in Coq"
    )

    reasoning: str = Field(
        description="Explanation of the extraction decision"
    )

    alternative_formulation: str | None = Field(
        default=None,
        description="""If unformalizable, suggest how the claim could be
        reformulated to be formalizable"""
    )

    original_text: str = Field(
        description="The original input text for reference"
    )


class ClaimConflict(BaseModel):
    """Represents a conflict between two claims."""

    claim1: FormalizableClaim
    claim2: FormalizableClaim

    are_contradictory: bool = Field(
        description="Whether the claims are contradictory"
    )

    reasoning: str = Field(
        description="Explanation of why the claims conflict or don't conflict"
    )

    conflict_type: str | None = Field(
        default=None,
        description="""Type of conflict: 'value_mismatch', 'logical_contradiction',
        'property_violation', etc."""
    )


class ProofStrategy(BaseModel):
    """Suggested proof strategy for a claim."""

    claim: FormalizableClaim

    coq_tactics: list[str] = Field(
        description="""Suggested Coq tactics for proving this claim. Examples:
        - ['reflexivity'] for simple arithmetic
        - ['simpl', 'reflexivity'] for factorial
        - ['intros', 'lia'] for inequalities with variables
        - ['induction', 'simpl', 'reflexivity'] for recursive functions
        """
    )

    requires: list[str] = Field(
        default_factory=list,
        description="""Required Coq libraries. Examples:
        - ['Arith'] for arithmetic
        - ['List', 'Permutation', 'Sorted'] for sorting
        - ['Lia'] for linear integer arithmetic
        """
    )

    estimated_difficulty: str = Field(
        description="Difficulty: 'trivial', 'simple', 'moderate', 'complex', 'requires_lemmas'"
    )

    potential_issues: list[str] = Field(
        default_factory=list,
        description="Potential issues that might prevent proof: type mismatches, missing lemmas, etc."
    )
