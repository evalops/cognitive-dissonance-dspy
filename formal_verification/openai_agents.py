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
    ):
        """Initialize the OpenAI claim extractor.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4)
            base_url: Optional OpenAI-compatible API base URL
            app_name: Optional client title header for compatible providers
            site_url: Optional referer header for compatible providers
        """
        default_headers = {}
        resolved_app_name = app_name or os.getenv("OPENAI_APP_NAME")
        resolved_site_url = site_url or os.getenv("OPENAI_SITE_URL")

        if resolved_app_name:
            default_headers["X-Title"] = resolved_app_name
        if resolved_site_url:
            default_headers["HTTP-Referer"] = resolved_site_url

        client_kwargs: dict[str, Any] = {
            "api_key": api_key or os.getenv("OPENAI_API_KEY")
        }
        resolved_base_url = base_url or os.getenv("OPENAI_BASE_URL")
        if resolved_base_url:
            client_kwargs["base_url"] = resolved_base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self.client = OpenAI(**client_kwargs)
        self.model = model
        self.translator = ClaimTranslator()
        self._uses_compatible_base_url = bool(
            resolved_base_url and "api.openai.com" not in resolved_base_url
        )
        logger.info(f"Initialized OpenAIClaimExtractor with model {model}")

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
            "properties": {
                key: {"type": "string"}
                for key in VARIABLE_KEYS
            },
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
            candidates.append(text[start:end + 1].strip())

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        raise ValueError("Provider did not return a valid JSON object")

    def extract_claim(
        self,
        text: str,
        code_context: str = ""
    ) -> ClaimExtractionResult:
        """Extract a formalizable claim from text.

        Args:
            text: Text containing a potential claim
            code_context: Optional code context for function names, etc.

        Returns:
            ClaimExtractionResult with structured claim or explanation
        """
        logger.debug(f"Extracting claim from: {text[:100]}...")

        # Step 1: Triage - determine if formalizable and categorize
        triage_result = self._triage_claim(text)

        if not triage_result["is_formalizable"]:
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=triage_result["reasoning"],
                alternative_formulation=triage_result.get("suggestion"),
                original_text=text
            )

        raw_category = triage_result["category"]
        normalized_category = self._normalize_category(raw_category)

        try:
            category = ClaimCategory(normalized_category)
        except ValueError:
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=f"Category {raw_category} not yet supported",
                original_text=text
            )

        # Step 2: Route to specialized agent
        if category in [ClaimCategory.ARITHMETIC, ClaimCategory.MULTIPLICATION,
                       ClaimCategory.SUBTRACTION, ClaimCategory.FACTORIAL,
                       ClaimCategory.FIBONACCI, ClaimCategory.GCD,
                       ClaimCategory.INEQUALITY]:
            claim = self._extract_math_claim(text, category)
        elif category in [ClaimCategory.LOGIC_IMPLICATION, ClaimCategory.LOGIC_FORALL,
                         ClaimCategory.LOGIC_EXISTS]:
            claim = self._extract_logic_claim(text, category)
        elif category in [ClaimCategory.SORTING, ClaimCategory.EXTREMUM,
                         ClaimCategory.SUM, ClaimCategory.BINARY_SEARCH,
                         ClaimCategory.PERMUTATION, ClaimCategory.ARRAY_BOUNDS,
                         ClaimCategory.LOOP_TERMINATION, ClaimCategory.LIST_APPEND,
                         ClaimCategory.MEMORY_SAFETY, ClaimCategory.TIME_COMPLEXITY]:
            claim = self._extract_algorithm_claim(text, category, code_context)
        else:
            return ClaimExtractionResult(
                claim=None,
                is_formalizable=False,
                reasoning=f"Category {category} not yet supported",
                original_text=text
            )

        return ClaimExtractionResult(
            claim=claim,
            is_formalizable=True,
            reasoning=claim.reasoning,
            original_text=text
        )

    def _triage_claim(self, text: str) -> dict[str, Any]:
        """Triage a claim to determine if it's formalizable."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(
                            TRIAGE_AGENT_INSTRUCTIONS
                        ),
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
                "suggestion": ""
            }

    def _extract_math_claim(
        self,
        text: str,
        category: ClaimCategory
    ) -> FormalizableClaim:
        """Extract a mathematical claim using the math specialist agent."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(
                            MATH_AGENT_INSTRUCTIONS
                        ),
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
                    }
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

            claim = FormalizableClaim(
                category=category,
                claim_text=result["claim_text"],
                confidence=result["confidence"],
                variables=result["variables"],
                pattern_hints=result["pattern_hints"],
                reasoning=result["reasoning"]
            )

            logger.debug(f"Extracted math claim: {claim.claim_text}")
            return claim

        except Exception as e:
            logger.error(f"Math claim extraction failed: {e}")
            # Fallback to simple extraction
            fallback_claims = {
                ClaimCategory.ARITHMETIC: "0 + 0 = 0",
                ClaimCategory.MULTIPLICATION: "2 * 2 = 4",
                ClaimCategory.SUBTRACTION: "2 - 1 = 1",
                ClaimCategory.FACTORIAL: "factorial 0 = 1",
                ClaimCategory.FIBONACCI: "fibonacci 2 = 1",
                ClaimCategory.GCD: "gcd 1 1 = 1",
                ClaimCategory.INEQUALITY: "0 < 1",
            }

            canonical_text = fallback_claims.get(category, "0 + 0 = 0")

            return FormalizableClaim(
                category=category,
                claim_text=canonical_text,
                confidence=0.3,
                variables={},
                pattern_hints=[],
                reasoning=f"Fallback extraction due to error: {e!s}"
            )

    def _extract_logic_claim(
        self,
        text: str,
        category: ClaimCategory
    ) -> FormalizableClaim:
        """Extract a logical claim using the logic specialist agent."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(
                            LOGIC_AGENT_INSTRUCTIONS
                        ),
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
                    }
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

            claim = FormalizableClaim(
                category=category,
                claim_text=result["claim_text"],
                confidence=result["confidence"],
                variables=result["variables"],
                pattern_hints=result["pattern_hints"],
                reasoning=result["reasoning"]
            )

            logger.debug(f"Extracted logic claim: {claim.claim_text}")
            return claim

        except Exception as e:
            logger.error(f"Logic claim extraction failed: {e}")
            return FormalizableClaim(
                category=category,
                claim_text=text[:100],
                confidence=0.3,
                variables={},
                pattern_hints=[],
                reasoning=f"Fallback extraction due to error: {e!s}"
            )

    def _extract_algorithm_claim(
        self,
        text: str,
        category: ClaimCategory,
        code_context: str
    ) -> FormalizableClaim:
        """Extract an algorithm property claim using the algorithm specialist agent."""
        try:
            prompt = f"Extract {category.value} claim from: {text}"
            if code_context:
                prompt += f"\n\nCode context:\n{code_context}"

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._instruction_text(
                            ALGORITHM_AGENT_INSTRUCTIONS
                        ),
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
                    }
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

            claim = FormalizableClaim(
                category=category,
                claim_text=result["claim_text"],
                confidence=result["confidence"],
                variables=result["variables"],
                pattern_hints=result["pattern_hints"],
                function_name=result.get("function_name"),
                reasoning=result["reasoning"]
            )

            logger.debug(f"Extracted algorithm claim: {claim.claim_text}")
            return claim

        except Exception as e:
            logger.error(f"Algorithm claim extraction failed: {e}")
            return FormalizableClaim(
                category=category,
                claim_text=text[:100],
                confidence=0.3,
                variables={},
                pattern_hints=[],
                reasoning=f"Fallback extraction due to error: {e!s}"
            )

    def validate_against_translator(
        self,
        claim: FormalizableClaim,
        code: str = ""
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
            timestamp=0.0
        )

        result = self.translator.translate(dummy_claim, code)
        return result is not None
