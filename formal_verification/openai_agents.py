"""OpenAI Agents SDK integration for structured claim extraction.

This module provides specialized agents for extracting formalizable claims
with much higher accuracy than the unstructured DSPy approach.
"""

import json
import logging
import os
import re
from typing import Any

from openai import OpenAI

from .structured_models import ClaimCategory, ClaimExtractionResult, FormalizableClaim
from .translator import ClaimTranslator
from .types import Claim, PropertyType

logger = logging.getLogger(__name__)

VARIABLE_KEYS = (
    "left",
    "right",
    "result",
    "input",
    "output",
    "a",
    "b",
    "variable",
    "property",
    "hypothesis",
    "conclusion",
    "index",
    "length",
    "start",
    "end",
    "target",
    "value",
    "size",
    "element",
    "elements",
    "array",
    "maximum",
    "minimum",
)

NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
}

TENS_WORDS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

TOKEN_PATTERN = r"[\w-]+(?:\s+[\w-]+)*"


# Agent instructions for different specializations
TRIAGE_AGENT_INSTRUCTIONS = """You are a Claim Triage Agent for formal verification.

Your job is to analyze text and determine:
1. Whether it contains a formalizable mathematical or algorithmic claim
2. What category of claim it is

FORMALIZABLE categories include:
- Arithmetic: "2 + 2 = 4", "10 - 3 = 7"
- Factorial: "factorial 5 = 120"
- Fibonacci: "fibonacci 8 = 21"
- GCD: "gcd(12, 8) = 4"
- Logic: "if x > 5 then x > 3", "forall n, n + 0 = n"
- Inequality: "3 < 5", "10 >= 7"
- Sorting: "sorts the array", "sorted output"
- Algorithm properties: "finds maximum", "computes sum"

UNFORMALIZABLE claims:
- Subjective: "the code is elegant"
- Vague: "performs well"
- Requires external knowledge: "uses industry best practices"
- Natural language without math: "the user will be happy"

When you identify a claim, categorize it precisely and route to the
appropriate specialist.
Be conservative - if uncertain, mark as unformalizable.
"""


MATH_AGENT_INSTRUCTIONS = """You are a Mathematical Claim Extraction Agent.

Extract mathematical claims in EXACT canonical form that matches Coq patterns:

ARITHMETIC:
- Pattern: 'N + M = R' where N, M, R are integers
- Example: '2 + 2 = 4' (NOT "two plus two equals four")

MULTIPLICATION:
- Pattern: 'N * M = R'
- Example: '3 * 4 = 12'

SUBTRACTION:
- Pattern: 'N - M = R'
- Example: '10 - 3 = 7'

FACTORIAL:
- Pattern: 'factorial N = M'
- Example: 'factorial 5 = 120' (NOT "the factorial of 5 is 120")

FIBONACCI:
- Pattern: 'fibonacci N = M'
- Example: 'fibonacci 8 = 21'

GCD:
- Pattern: 'gcd(N, M) = R'
- Example: 'gcd(12, 8) = 4'

INEQUALITY:
- Pattern: 'N < M', 'N > M', 'N <= M', 'N >= M'
- Example: '3 < 5' (NOT "three is less than five")

Extract variables into a dictionary with keys: 'left', 'right', 'result'
(or 'input', 'output' for functions).

CRITICAL: Output must be in exact format - no natural language, no articles
("the", "a"), no qualifiers.
"""


LOGIC_AGENT_INSTRUCTIONS = """You are a Logical Claim Extraction Agent.

Extract logical claims in formal logic notation:

IMPLICATION:
- Pattern: 'if P then Q' or 'P implies Q'
- Example: 'if x > 5 then x > 3' (NOT "when x exceeds 5, it must exceed 3")
- Variables: Extract into {'hypothesis': 'x > 5', 'conclusion': 'x > 3'}

UNIVERSAL QUANTIFICATION:
- Pattern: 'forall VAR, PROPERTY' or 'for all VAR, PROPERTY'
- Example: 'forall n, n + 0 = n'
- Variables: {'variable': 'n', 'property': 'n + 0 = n'}

EXISTENTIAL QUANTIFICATION:
- Pattern: 'exists VAR such that PROPERTY'
- Example: 'exists x such that x > 5'
- Variables: {'variable': 'x', 'property': 'x > 5'}

Use mathematical notation for operators:
- Greater than: >
- Less than: <
- Equals: =
- Plus: +
- Minus: -
- Times: *

CRITICAL: Use symbolic notation, not words. 'x > 5' not "x is greater than 5".
"""


ALGORITHM_AGENT_INSTRUCTIONS = """You are an Algorithm Property Extraction Agent.

Extract algorithmic correctness claims in canonical form:

SORTING:
- Pattern: 'sorts the array' or 'sorted output' or 'correctly sorts'
- NOT: "the algorithm sorts the input array correctly" (too verbose)
- Function name: Extract from context if available

EXTREMUM (MAX/MIN):
- Pattern: 'finds the maximum' or 'finds the minimum' or 'returns the maximum'
- NOT: "returns the maximum value in the array" (too verbose)

SUM:
- Pattern: 'computes the sum'
- NOT: "computes the sum of all elements"

BINARY SEARCH:
- Pattern: 'binary search returns correct index' or 'binary search finds element'

PERMUTATION:
- Pattern: 'preserves all elements' or 'permutation'

ARRAY BOUNDS:
- Pattern: 'accessing array[N] with length M is safe/unsafe'
- Example: 'accessing array[5] with length 10 is safe'
- Variables: {'index': '5', 'length': '10'}

LOOP TERMINATION:
- Pattern: 'for loop from N to M terminates'
- Example: 'for loop from 0 to 10 terminates'

LIST APPEND:
- Pattern: 'list size increases after append'

MEMORY SAFETY:
- Pattern: 'memory safe', 'no buffer overflow', 'no use-after-free'

TIME COMPLEXITY:
- Pattern: 'O(N)', 'O(1)', 'O(N^2)', 'linear time', 'constant time'
- Example: 'O(n)' NOT "has time complexity of O(n)"

CRITICAL: Use minimal, canonical phrasing. Extract function names from code context.
"""


class OpenAIClaimExtractor:
    """OpenAI Agents SDK-based claim extractor with structured outputs.

    This replaces the DSPy-based BeliefAgent with a more structured approach
    that produces claims matching the translator's regex patterns.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4",
        base_url: str | None = None,
        app_name: str | None = None,
        site_url: str | None = None,
        temperature: float | None = None,
    ):
        """Initialize the OpenAI claim extractor.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4)
            base_url: Optional OpenAI-compatible API base URL
            app_name: Optional client title header for compatible providers
            site_url: Optional referer header for compatible providers
            temperature: Optional decoding temperature for extraction calls
        """
        default_headers = {}
        resolved_app_name = app_name or os.getenv("OPENAI_APP_NAME")
        resolved_site_url = site_url or os.getenv("OPENAI_SITE_URL")

        if resolved_app_name:
            default_headers["X-Title"] = resolved_app_name
        if resolved_site_url:
            default_headers["HTTP-Referer"] = resolved_site_url

        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        client_kwargs: dict[str, Any] = {}
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL")
        if resolved_api_key:
            client_kwargs["api_key"] = resolved_api_key
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self.client = OpenAI(**client_kwargs) if resolved_api_key else None
        self.model = model
        self.temperature = temperature
        self.translator = ClaimTranslator()
        self._uses_compatible_base_url = bool(
            resolved_base_url and "api.openai.com" not in resolved_base_url
        )
        if self.client is None:
            logger.info(
                "Initialized OpenAIClaimExtractor with model %s "
                "in deterministic-only mode",
                model,
            )
        else:
            logger.info(
                "Initialized OpenAIClaimExtractor with model %s",
                model,
            )

    def _require_client(self) -> OpenAI:
        """Return the configured client or raise a clear error."""
        if self.client is None:
            raise RuntimeError(
                "OPENAI_API_KEY is required for provider-backed extraction"
            )
        return self.client

    @staticmethod
    def _normalize_category(raw_category: Any) -> str:
        """Normalize provider category labels to enum-compatible values."""
        if isinstance(raw_category, ClaimCategory):
            return raw_category.value

        normalized = str(raw_category).strip().lower()
        normalized = re.sub(r"[\s\-]+", "_", normalized)
        return normalized

    @staticmethod
    def _variables_schema() -> dict[str, Any]:
        """Return a provider-compatible schema for extracted variables."""
        return {
            "type": "object",
            "properties": {key: {"type": "string"} for key in VARIABLE_KEYS},
            "additionalProperties": False,
        }

    def _response_format(self, name: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return the most portable structured-output format for the provider."""
        if self._uses_compatible_base_url:
            return {"type": "json_object"}

        return {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": schema,
            },
        }

    def _completion_kwargs(self) -> dict[str, Any]:
        """Shared completion kwargs for structured extraction calls."""
        kwargs: dict[str, Any] = {}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        return kwargs

    def _instruction_text(self, instruction: str) -> str:
        """Add portable JSON guidance for compatible providers."""
        if self._uses_compatible_base_url:
            return f"{instruction}\n\nReturn only valid JSON."

        return instruction

    def _user_prompt(self, prompt: str, json_contract: str) -> str:
        """Add an explicit JSON contract for compatible providers."""
        if self._uses_compatible_base_url:
            return (
                f"{prompt}\n\nReturn JSON only. "
                f"Use exactly these keys: {json_contract}."
            )

        return prompt

    @staticmethod
    def _normalize_triage_result(result: dict[str, Any]) -> dict[str, Any]:
        """Normalize looser provider triage payloads to the expected shape."""
        is_formalizable = result.get("is_formalizable")
        if is_formalizable is None:
            is_formalizable = result.get("formalizable", False)
        if isinstance(is_formalizable, str):
            is_formalizable = is_formalizable.strip().lower() in {
                "true",
                "yes",
                "formalizable",
                "supported",
            }

        reasoning = result.get("reasoning")
        if not reasoning:
            reasoning = (
                "Provider classified the claim as formalizable."
                if is_formalizable
                else "Provider classified the claim as unformalizable."
            )

        return {
            "is_formalizable": bool(is_formalizable),
            "category": result.get("category", "unformalizable"),
            "reasoning": reasoning,
            "suggestion": result.get("suggestion", ""),
        }

    @staticmethod
    def _normalize_claim_payload(
        result: dict[str, Any],
        category: ClaimCategory,
    ) -> dict[str, Any]:
        """Normalize looser provider claim payloads to the expected shape."""
        variables = result.get("variables", {})
        if not isinstance(variables, dict):
            variables = {}
        if not variables:
            variables = {
                key: result[key]
                for key in VARIABLE_KEYS
                if key in result and result[key] is not None
            }

        pattern_hints = (
            result.get("pattern_hints")
            or result.get("hints")
            or result.get("keywords")
            or []
        )
        if not isinstance(pattern_hints, list):
            pattern_hints = []

        confidence = result.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5

        return {
            "claim_text": (
                result.get("claim_text")
                or result.get("claim")
                or result.get("normalized_claim")
                or ""
            ),
            "confidence": confidence,
            "variables": {
                str(key): str(value)
                for key, value in variables.items()
                if value is not None
            },
            "pattern_hints": [str(item) for item in pattern_hints],
            "reasoning": result.get(
                "reasoning",
                f"Extracted {category.value} claim",
            ),
            "function_name": result.get("function_name"),
        }

    @staticmethod
    def _parse_response_content(content: str) -> dict[str, Any]:
        """Parse provider JSON content, tolerating code fences and wrappers."""
        text = content.strip()
        candidates = [text]

        fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if fence_match:
            candidates.append(fence_match.group(1).strip())

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1].strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("Provider did not return a valid JSON object")

    @staticmethod
    def _normalize_rule_text(text: str) -> str:
        """Lowercase and trim light punctuation for rule-based extraction."""
        normalized = text.strip().lower()
        return re.sub(r"[.?!]+$", "", normalized)

    @staticmethod
    def _normalize_symbol_token(token: str) -> str | None:
        """Convert simple number words or variable names into canonical tokens."""
        normalized = token.strip().lower().strip(",.")
        if re.fullmatch(r"\d+", normalized):
            return normalized
        if normalized in NUMBER_WORDS:
            return NUMBER_WORDS[normalized]
        compound_parts = re.split(r"[-\s]+", normalized)
        if compound_parts and compound_parts[0] in TENS_WORDS:
            value = TENS_WORDS[compound_parts[0]]
            if len(compound_parts) == 1:
                return str(value)
            if (
                len(compound_parts) == 2
                and compound_parts[1] in NUMBER_WORDS
                and int(NUMBER_WORDS[compound_parts[1]]) < 10
            ):
                return str(value + int(NUMBER_WORDS[compound_parts[1]]))
        if re.fullmatch(r"[a-zA-Z_]\w*", normalized):
            return normalized
        return None

    def _canonicalize_predicate(self, text: str) -> str | None:
        """Normalize simple arithmetic and inequality predicates."""
        normalized = self._normalize_rule_text(text)
        token_pattern = TOKEN_PATTERN
        symbolic_match = re.fullmatch(
            r"([a-zA-Z_]\w*|\d+)\s*(<=|>=|<|>|=)\s*([a-zA-Z_]\w*|\d+)",
            normalized,
        )
        if symbolic_match:
            return (
                f"{symbolic_match.group(1)} {symbolic_match.group(2)} "
                f"{symbolic_match.group(3)}"
            )

        arithmetic_patterns = [
            (
                rf"({token_pattern})\s+plus\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                "+",
            ),
            (
                rf"({token_pattern})\s+minus\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                "-",
            ),
            (
                rf"({token_pattern})\s+(?:times|multiplied by)\s+"
                rf"({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                "*",
            ),
        ]
        for pattern, operator in arithmetic_patterns:
            match = re.fullmatch(pattern, normalized)
            if not match:
                continue
            left = self._normalize_symbol_token(match.group(1))
            right = self._normalize_symbol_token(match.group(2))
            result = self._normalize_symbol_token(match.group(3))
            if left and right and result:
                return f"{left} {operator} {right} = {result}"

        inequality_patterns = [
            (
                rf"({token_pattern})\s+is\s+greater\s+than\s+or\s+equal\s+to\s+"
                rf"({token_pattern})",
                ">=",
            ),
            (
                rf"({token_pattern})\s+is\s+less\s+than\s+or\s+equal\s+to\s+"
                rf"({token_pattern})",
                "<=",
            ),
            (rf"({token_pattern})\s+is\s+greater\s+than\s+({token_pattern})", ">"),
            (rf"({token_pattern})\s+is\s+less\s+than\s+({token_pattern})", "<"),
        ]
        for pattern, operator in inequality_patterns:
            match = re.fullmatch(pattern, normalized)
            if not match:
                continue
            left = self._normalize_symbol_token(match.group(1))
            right = self._normalize_symbol_token(match.group(2))
            if left and right:
                return f"{left} {operator} {right}"

        return None

    def _infer_category_from_claim_text(self, claim_text: str) -> ClaimCategory | None:
        """Infer the strongest category directly from canonical claim text."""
        normalized = self._normalize_rule_text(claim_text)

        patterns = [
            (r"^factorial\b", ClaimCategory.FACTORIAL),
            (r"^fibonacci\b", ClaimCategory.FIBONACCI),
            (r"^gcd\b", ClaimCategory.GCD),
            (r"^if\b.*\bthen\b|implies", ClaimCategory.LOGIC_IMPLICATION),
            (r"^forall\b|^for\s+all\b", ClaimCategory.LOGIC_FORALL),
            (r"^exists\b|^there\s+exists\b", ClaimCategory.LOGIC_EXISTS),
            (r"^\d+\s*\*\s*\d+\s*=\s*\d+$", ClaimCategory.MULTIPLICATION),
            (r"^\d+\s*-\s*\d+\s*=\s*\d+$", ClaimCategory.SUBTRACTION),
            (r"^\d+\s*[<>]=?\s*\d+$", ClaimCategory.INEQUALITY),
            (r"^\d+\s*\+\s*\d+\s*=\s*\d+$", ClaimCategory.ARITHMETIC),
        ]
        for pattern, category in patterns:
            if re.search(pattern, normalized):
                return category

        return None

    def _build_claim(
        self,
        *,
        category: ClaimCategory,
        claim_text: str,
        confidence: float,
        variables: dict[str, str],
        pattern_hints: list[str],
        reasoning: str,
        function_name: str | None = None,
    ) -> FormalizableClaim:
        """Construct a claim after inferring the most specific category."""
        inferred_category = self._infer_category_from_claim_text(claim_text)
        final_category = inferred_category or category
        return FormalizableClaim(
            category=final_category,
            claim_text=claim_text,
            confidence=confidence,
            variables=variables,
            pattern_hints=pattern_hints,
            function_name=function_name,
            reasoning=reasoning,
        )

    def _rule_based_claim(self, text: str) -> FormalizableClaim | None:
        """Use lightweight deterministic normalization for obvious claim forms."""
        normalized = self._normalize_rule_text(text)
        token_pattern = TOKEN_PATTERN

        arithmetic_patterns = [
            (
                rf"({token_pattern})\s+plus\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                ClaimCategory.ARITHMETIC,
                "+",
            ),
            (
                rf"({token_pattern})\s+(?:times|multiplied by)\s+"
                rf"({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                ClaimCategory.MULTIPLICATION,
                "*",
            ),
            (
                rf"({token_pattern})\s+minus\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                ClaimCategory.SUBTRACTION,
                "-",
            ),
        ]
        for pattern, category, operator in arithmetic_patterns:
            match = re.fullmatch(pattern, normalized)
            if not match:
                continue
            left = self._normalize_symbol_token(match.group(1))
            right = self._normalize_symbol_token(match.group(2))
            result = self._normalize_symbol_token(match.group(3))
            if left and right and result:
                return self._build_claim(
                    category=category,
                    claim_text=f"{left} {operator} {right} = {result}",
                    confidence=0.9,
                    variables={"left": left, "right": right, "result": result},
                    pattern_hints=[category.value],
                    reasoning="Rule-based normalization of arithmetic language.",
                )

        function_patterns = [
            (
                rf"(?:the\s+)?factorial(?:\s+of)?\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                ClaimCategory.FACTORIAL,
                "factorial {input} = {output}",
            ),
            (
                rf"fibonacci(?:\s+of)?\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                ClaimCategory.FIBONACCI,
                "fibonacci {input} = {output}",
            ),
            (
                rf"(?:the\s+)?gcd(?:\s+of)?\s+({token_pattern})\s+(?:and|,)\s+({token_pattern})\s+(?:equals|is)\s+({token_pattern})",
                ClaimCategory.GCD,
                "gcd({a}, {b}) = {result}",
            ),
        ]
        for pattern, category, template in function_patterns:
            match = re.fullmatch(pattern, normalized)
            if not match:
                continue
            if category == ClaimCategory.GCD:
                a = self._normalize_symbol_token(match.group(1))
                b = self._normalize_symbol_token(match.group(2))
                result = self._normalize_symbol_token(match.group(3))
                if a and b and result:
                    return self._build_claim(
                        category=category,
                        claim_text=template.format(a=a, b=b, result=result),
                        confidence=0.9,
                        variables={"a": a, "b": b, "result": result},
                        pattern_hints=["gcd"],
                        reasoning="Rule-based normalization of number-theory language.",
                    )
            else:
                input_value = self._normalize_symbol_token(match.group(1))
                output_value = self._normalize_symbol_token(match.group(2))
                if input_value and output_value:
                    return self._build_claim(
                        category=category,
                        claim_text=template.format(
                            input=input_value,
                            output=output_value,
                        ),
                        confidence=0.9,
                        variables={"input": input_value, "output": output_value},
                        pattern_hints=[category.value],
                        reasoning=(
                            "Rule-based normalization of recursive math language."
                        ),
                    )

        inequality_patterns = [
            (
                rf"({token_pattern})\s+is\s+greater\s+than\s+or\s+equal\s+to\s+"
                rf"({token_pattern})",
                ">=",
            ),
            (
                rf"({token_pattern})\s+is\s+less\s+than\s+or\s+equal\s+to\s+"
                rf"({token_pattern})",
                "<=",
            ),
            (rf"({token_pattern})\s+is\s+greater\s+than\s+({token_pattern})", ">"),
            (rf"({token_pattern})\s+is\s+less\s+than\s+({token_pattern})", "<"),
        ]
        for pattern, operator in inequality_patterns:
            match = re.fullmatch(pattern, normalized)
            if not match:
                continue
            left = self._normalize_symbol_token(match.group(1))
            right = self._normalize_symbol_token(match.group(2))
            if left and right:
                return self._build_claim(
                    category=ClaimCategory.INEQUALITY,
                    claim_text=f"{left} {operator} {right}",
                    confidence=0.9,
                    variables={"left": left, "right": right},
                    pattern_hints=["inequality"],
                    reasoning="Rule-based normalization of comparison language.",
                )

        implication_match = re.fullmatch(r"if\s+(.+?),\s+then\s+(.+)", normalized)
        if implication_match:
            hypothesis = self._canonicalize_predicate(implication_match.group(1))
            conclusion = self._canonicalize_predicate(implication_match.group(2))
            if hypothesis and conclusion:
                return self._build_claim(
                    category=ClaimCategory.LOGIC_IMPLICATION,
                    claim_text=f"if {hypothesis} then {conclusion}",
                    confidence=0.85,
                    variables={
                        "hypothesis": hypothesis,
                        "conclusion": conclusion,
                    },
                    pattern_hints=["if", "then"],
                    reasoning="Rule-based normalization of implication language.",
                )

        forall_match = re.fullmatch(r"for\s+all\s+([a-zA-Z_]\w*),\s+(.+)", normalized)
        if forall_match:
            variable = forall_match.group(1)
            property_text = self._canonicalize_predicate(forall_match.group(2))
            if property_text:
                return self._build_claim(
                    category=ClaimCategory.LOGIC_FORALL,
                    claim_text=f"forall {variable}, {property_text}",
                    confidence=0.85,
                    variables={"variable": variable, "property": property_text},
                    pattern_hints=["forall"],
                    reasoning="Rule-based normalization of universal quantification.",
                )

        exists_match = re.fullmatch(
            r"there\s+exists\s+([a-zA-Z_]\w*)\s+such\s+that\s+(.+)",
            normalized,
        )
        if exists_match:
            variable = exists_match.group(1)
            property_text = self._canonicalize_predicate(exists_match.group(2))
            if property_text:
                return self._build_claim(
                    category=ClaimCategory.LOGIC_EXISTS,
                    claim_text=f"exists {variable} such that {property_text}",
                    confidence=0.85,
                    variables={"variable": variable, "property": property_text},
                    pattern_hints=["exists"],
                    reasoning="Rule-based normalization of existential quantification.",
                )

        return None

    def extract_claim(self, text: str, code_context: str = "") -> ClaimExtractionResult:
        """Extract a formalizable claim from text.

        Args:
            text: Text containing a potential claim
            code_context: Optional code context for function names, etc.

        Returns:
            ClaimExtractionResult with structured claim or explanation
        """
        logger.debug(f"Extracting claim from: {text[:100]}...")

        rule_based_claim = self._rule_based_claim(text)
        if rule_based_claim is not None and self.validate_against_translator(
            rule_based_claim,
            code_context,
        ):
            return ClaimExtractionResult(
                claim=rule_based_claim,
                is_formalizable=True,
                reasoning=rule_based_claim.reasoning,
                extraction_mode="rule_based",
                original_text=text,
            )

        if self.client is None:
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=(
                    "OpenAI-compatible API credentials are required for "
                    "non-deterministic extraction."
                ),
                extraction_mode="unavailable",
                original_text=text,
            )

        # Step 1: Triage - determine if formalizable and categorize
        triage_result = self._triage_claim(text)

        if not triage_result["is_formalizable"]:
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=triage_result["reasoning"],
                alternative_formulation=triage_result.get("suggestion"),
                extraction_mode="provider_triage",
                original_text=text,
            )

        raw_category = triage_result["category"]
        normalized_category = self._normalize_category(raw_category)

        try:
            category = ClaimCategory(normalized_category)
        except ValueError:
            rule_based_claim = self._rule_based_claim(text)
            if rule_based_claim is not None:
                return ClaimExtractionResult(
                    claim=rule_based_claim,
                    is_formalizable=True,
                    reasoning=rule_based_claim.reasoning,
                    extraction_mode="provider_with_rule_correction",
                    original_text=text,
                )
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=f"Category {raw_category} not yet supported",
                extraction_mode="provider_triage",
                original_text=text,
            )

        # Step 2: Route to specialized agent
        if category in [
            ClaimCategory.ARITHMETIC,
            ClaimCategory.MULTIPLICATION,
            ClaimCategory.SUBTRACTION,
            ClaimCategory.FACTORIAL,
            ClaimCategory.FIBONACCI,
            ClaimCategory.GCD,
            ClaimCategory.INEQUALITY,
        ]:
            claim = self._extract_math_claim(text, category)
        elif category in [
            ClaimCategory.LOGIC_IMPLICATION,
            ClaimCategory.LOGIC_FORALL,
            ClaimCategory.LOGIC_EXISTS,
        ]:
            claim = self._extract_logic_claim(text, category)
        elif category in [
            ClaimCategory.SORTING,
            ClaimCategory.EXTREMUM,
            ClaimCategory.SUM,
            ClaimCategory.BINARY_SEARCH,
            ClaimCategory.PERMUTATION,
            ClaimCategory.ARRAY_BOUNDS,
            ClaimCategory.LOOP_TERMINATION,
            ClaimCategory.LIST_APPEND,
            ClaimCategory.MEMORY_SAFETY,
            ClaimCategory.TIME_COMPLEXITY,
        ]:
            claim = self._extract_algorithm_claim(text, category, code_context)
        else:
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=f"Category {category} not yet supported",
                extraction_mode="provider_triage",
                original_text=text,
            )

        extraction_mode = "provider"
        if claim is None and rule_based_claim is not None:
            claim = rule_based_claim
            extraction_mode = "provider_with_rule_correction"
        elif (
            claim is not None
            and rule_based_claim is not None
            and claim.claim_text != rule_based_claim.claim_text
        ):
            # For simple canonicalizable claims, preserve the literal claim the
            # user stated instead of a provider-normalized "corrected" variant.
            claim = rule_based_claim
            extraction_mode = "provider_with_rule_correction"

        if claim is None:
            if rule_based_claim is None:
                return ClaimExtractionResult(
                    claim=None,
                    is_formalizable=False,
                    reasoning=f"Unable to extract a canonical {category.value} claim",
                    extraction_mode="provider_failed",
                    original_text=text,
                )
            claim = rule_based_claim
            extraction_mode = "provider_with_rule_correction"

        if not self.validate_against_translator(claim, code_context):
            if rule_based_claim is not None and self.validate_against_translator(
                rule_based_claim, code_context
            ):
                claim = rule_based_claim
                extraction_mode = "provider_with_rule_correction"
            else:
                return ClaimExtractionResult(
                    claim=None,
                    is_formalizable=False,
                    reasoning=(
                        "Extracted claim did not match a supported translator pattern"
                    ),
                    extraction_mode="provider_failed",
                    original_text=text,
                )

        return ClaimExtractionResult(
            claim=claim,
            is_formalizable=True,
            reasoning=claim.reasoning,
            extraction_mode=extraction_mode,
            original_text=text,
        )

    def _triage_claim(self, text: str) -> dict[str, Any]:
        """Triage a claim to determine if it's formalizable."""
        try:
            response = self._require_client().chat.completions.create(
                model=self.model,
                **self._completion_kwargs(),
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(TRIAGE_AGENT_INSTRUCTIONS),
                    },
                    {
                        "role": "user",
                        "content": self._user_prompt(
                            f"Analyze this text: {text}",
                            (
                                "is_formalizable (boolean), category (string), "
                                "reasoning (string), suggestion (string)"
                            ),
                        ),
                    },
                ],
                response_format=self._response_format(
                    "triage_result",
                    {
                        "type": "object",
                        "properties": {
                            "is_formalizable": {"type": "boolean"},
                            "category": {"type": "string"},
                            "reasoning": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                        "required": [
                            "is_formalizable",
                            "category",
                            "reasoning",
                            "suggestion",
                        ],
                        "additionalProperties": False,
                    },
                ),
            )

            result = self._normalize_triage_result(
                self._parse_response_content(response.choices[0].message.content)
            )
            logger.debug(f"Triage result: {result}")
            return result

        except Exception as e:
            logger.error(f"Triage failed: {e}")
            return {
                "is_formalizable": False,
                "category": "unformalizable",
                "reasoning": f"Error during triage: {e!s}",
                "suggestion": "",
            }

    def _extract_math_claim(
        self, text: str, category: ClaimCategory
    ) -> FormalizableClaim | None:
        """Extract a mathematical claim using the math specialist agent."""
        try:
            response = self._require_client().chat.completions.create(
                model=self.model,
                **self._completion_kwargs(),
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(MATH_AGENT_INSTRUCTIONS),
                    },
                    {
                        "role": "user",
                        "content": self._user_prompt(
                            f"Extract {category.value} claim from: {text}",
                            (
                                "claim_text (string), confidence (number), "
                                "variables (object), pattern_hints "
                                "(array of strings), reasoning (string)"
                            ),
                        ),
                    },
                ],
                response_format=self._response_format(
                    "math_claim",
                    {
                        "type": "object",
                        "properties": {
                            "claim_text": {"type": "string"},
                            "confidence": {"type": "number"},
                            "variables": self._variables_schema(),
                            "pattern_hints": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "reasoning": {"type": "string"},
                        },
                        "required": [
                            "claim_text",
                            "confidence",
                            "variables",
                            "pattern_hints",
                            "reasoning",
                        ],
                        "additionalProperties": False,
                    },
                ),
            )

            result = self._normalize_claim_payload(
                self._parse_response_content(response.choices[0].message.content),
                category,
            )

            claim = self._build_claim(
                category=category,
                claim_text=result["claim_text"],
                confidence=result["confidence"],
                variables=result["variables"],
                pattern_hints=result["pattern_hints"],
                reasoning=result["reasoning"],
            )

            logger.debug(f"Extracted math claim: {claim.claim_text}")
            return claim

        except Exception as e:
            logger.error(f"Math claim extraction failed: {e}")
            return self._rule_based_claim(text)

    def _extract_logic_claim(
        self, text: str, category: ClaimCategory
    ) -> FormalizableClaim | None:
        """Extract a logical claim using the logic specialist agent."""
        try:
            response = self._require_client().chat.completions.create(
                model=self.model,
                **self._completion_kwargs(),
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(LOGIC_AGENT_INSTRUCTIONS),
                    },
                    {
                        "role": "user",
                        "content": self._user_prompt(
                            f"Extract {category.value} claim from: {text}",
                            (
                                "claim_text (string), confidence (number), "
                                "variables (object), pattern_hints "
                                "(array of strings), reasoning (string)"
                            ),
                        ),
                    },
                ],
                response_format=self._response_format(
                    "logic_claim",
                    {
                        "type": "object",
                        "properties": {
                            "claim_text": {"type": "string"},
                            "confidence": {"type": "number"},
                            "variables": self._variables_schema(),
                            "pattern_hints": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "reasoning": {"type": "string"},
                        },
                        "required": [
                            "claim_text",
                            "confidence",
                            "variables",
                            "pattern_hints",
                            "reasoning",
                        ],
                        "additionalProperties": False,
                    },
                ),
            )

            result = self._normalize_claim_payload(
                self._parse_response_content(response.choices[0].message.content),
                category,
            )

            claim = self._build_claim(
                category=category,
                claim_text=result["claim_text"],
                confidence=result["confidence"],
                variables=result["variables"],
                pattern_hints=result["pattern_hints"],
                reasoning=result["reasoning"],
            )

            logger.debug(f"Extracted logic claim: {claim.claim_text}")
            return claim

        except Exception as e:
            logger.error(f"Logic claim extraction failed: {e}")
            return self._rule_based_claim(text)

    def _extract_algorithm_claim(
        self, text: str, category: ClaimCategory, code_context: str
    ) -> FormalizableClaim | None:
        """Extract an algorithm property claim using the algorithm specialist agent."""
        try:
            prompt = f"Extract {category.value} claim from: {text}"
            if code_context:
                prompt += f"\n\nCode context:\n{code_context}"

            response = self._require_client().chat.completions.create(
                model=self.model,
                **self._completion_kwargs(),
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(ALGORITHM_AGENT_INSTRUCTIONS),
                    },
                    {
                        "role": "user",
                        "content": self._user_prompt(
                            prompt,
                            (
                                "claim_text (string), confidence (number), "
                                "variables (object), pattern_hints "
                                "(array of strings), function_name "
                                "(string or null), reasoning (string)"
                            ),
                        ),
                    },
                ],
                response_format=self._response_format(
                    "algorithm_claim",
                    {
                        "type": "object",
                        "properties": {
                            "claim_text": {"type": "string"},
                            "confidence": {"type": "number"},
                            "variables": self._variables_schema(),
                            "pattern_hints": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "function_name": {"type": ["string", "null"]},
                            "reasoning": {"type": "string"},
                        },
                        "required": [
                            "claim_text",
                            "confidence",
                            "variables",
                            "pattern_hints",
                            "reasoning",
                        ],
                        "additionalProperties": False,
                    },
                ),
            )

            result = self._normalize_claim_payload(
                self._parse_response_content(response.choices[0].message.content),
                category,
            )

            claim = self._build_claim(
                category=category,
                claim_text=result["claim_text"],
                confidence=result["confidence"],
                variables=result["variables"],
                pattern_hints=result["pattern_hints"],
                function_name=result.get("function_name"),
                reasoning=result["reasoning"],
            )

            logger.debug(f"Extracted algorithm claim: {claim.claim_text}")
            return claim

        except Exception as e:
            logger.error(f"Algorithm claim extraction failed: {e}")
            return self._rule_based_claim(text)

    def validate_against_translator(
        self, claim: FormalizableClaim, code: str = ""
    ) -> bool:
        """Validate that a claim can be translated to Coq.

        Args:
            claim: The claim to validate
            code: Optional code context

        Returns:
            True if translator can handle this claim
        """
        dummy_claim = Claim(
            agent_id="validator",
            claim_text=claim.claim_text,
            property_type=PropertyType.CORRECTNESS,
            confidence=claim.confidence,
            timestamp=0.0,
        )

        result = self.translator.translate(dummy_claim, code)
        return result is not None
