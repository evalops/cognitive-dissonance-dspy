"""Tests for OpenAI Agents SDK integration."""

import pytest
from unittest.mock import patch, MagicMock
import json

from formal_verification.structured_models import (
    FormalizableClaim,
    ClaimCategory
)
from formal_verification.openai_agents import OpenAIClaimExtractor
from formal_verification.guardrails import ClaimGuardrails
from formal_verification.hybrid_resolver import HybridCognitiveDissonanceResolver


class TestStructuredModels:
    """Test Pydantic models for structured claims."""

    def test_formalizable_claim_validation_arithmetic(self):
        """Test that arithmetic claims are validated correctly."""
        # Valid arithmetic claim
        claim = FormalizableClaim(
            category=ClaimCategory.ARITHMETIC,
            claim_text="2 + 2 = 4",
            confidence=0.95,
            variables={"left": "2", "right": "2", "result": "4"},
            pattern_hints=["addition", "equals"],
            reasoning="Simple arithmetic claim"
        )
        assert claim.claim_text == "2 + 2 = 4"

        # Invalid arithmetic claim should raise validation error
        with pytest.raises(ValueError, match="Arithmetic claim must match pattern"):
            FormalizableClaim(
                category=ClaimCategory.ARITHMETIC,
                claim_text="two plus two equals four",  # Wrong format
                confidence=0.95,
                variables={},
                pattern_hints=[],
                reasoning="Invalid format"
            )

    def test_formalizable_claim_validation_factorial(self):
        """Test that factorial claims are validated correctly."""
        # Valid factorial claim
        claim = FormalizableClaim(
            category=ClaimCategory.FACTORIAL,
            claim_text="factorial 5 = 120",
            confidence=0.95,
            variables={"input": "5", "output": "120"},
            pattern_hints=["factorial"],
            reasoning="Factorial calculation"
        )
        assert claim.claim_text == "factorial 5 = 120"

        # Invalid factorial claim
        with pytest.raises(ValueError, match="Factorial claim must match pattern"):
            FormalizableClaim(
                category=ClaimCategory.FACTORIAL,
                claim_text="the factorial of 5 is 120",
                confidence=0.95,
                variables={},
                pattern_hints=[],
                reasoning="Invalid format"
            )

    def test_formalizable_claim_validation_logic(self):
        """Test that logic claims are validated correctly."""
        # Valid implication
        claim = FormalizableClaim(
            category=ClaimCategory.LOGIC_IMPLICATION,
            claim_text="if x > 5 then x > 3",
            confidence=0.9,
            variables={"hypothesis": "x > 5", "conclusion": "x > 3"},
            pattern_hints=["if", "then"],
            reasoning="Logical implication"
        )
        assert "if" in claim.claim_text and "then" in claim.claim_text

        # Valid forall
        claim = FormalizableClaim(
            category=ClaimCategory.LOGIC_FORALL,
            claim_text="forall n, n + 0 = n",
            confidence=0.9,
            variables={"variable": "n", "property": "n + 0 = n"},
            pattern_hints=["forall"],
            reasoning="Universal quantification"
        )
        assert "forall" in claim.claim_text


class TestGuardrails:
    """Test guardrail validation."""

    def test_arithmetic_format_check(self):
        """Test that arithmetic format is validated."""
        guardrails = ClaimGuardrails(strict=True)

        # Valid claim
        valid_claim = FormalizableClaim(
            category=ClaimCategory.ARITHMETIC,
            claim_text="2 + 2 = 4",
            confidence=0.95,
            variables={"left": "2", "right": "2", "result": "4"},
            pattern_hints=["addition"],
            reasoning="Valid arithmetic"
        )

        result = guardrails.validate(valid_claim)
        # May have warnings but should not have errors for well-formed claims
        errors = [v for v in result.violations if v.severity == 'error']
        # Note: translator_compatibility might fail without actual Coq installation
        # so we just check format validation passed
        format_errors = [v for v in errors if v.rule_name == 'arithmetic_format']
        assert len(format_errors) == 0

    def test_natural_language_artifact_detection(self):
        """Test that natural language artifacts are detected."""
        guardrails = ClaimGuardrails(strict=True)

        # Claim with natural language artifacts
        claim = FormalizableClaim(
            category=ClaimCategory.SORTING,
            claim_text="the array is sorted correctly",  # Has "the" and "correctly"
            confidence=0.9,
            variables={},
            pattern_hints=["sorted"],
            reasoning="Has natural language"
        )

        result = guardrails.validate(claim)
        # Should have warnings about natural language artifacts
        nl_warnings = [
            v for v in result.violations
            if v.rule_name == 'natural_language_artifact'
        ]
        assert len(nl_warnings) > 0

    def test_variable_consistency_check(self):
        """Test that variable consistency is checked."""
        guardrails = ClaimGuardrails(strict=False)

        # Claim with inconsistent variables
        claim = FormalizableClaim(
            category=ClaimCategory.ARITHMETIC,
            claim_text="2 + 2 = 4",
            confidence=0.95,
            variables={"left": "3", "right": "5", "result": "8"},  # Wrong values
            pattern_hints=[],
            reasoning="Inconsistent variables"
        )

        result = guardrails.validate(claim)
        var_violations = [
            v for v in result.violations
            if v.rule_name == 'variable_not_in_claim'
        ]
        # Should detect that 3, 5, 8 are not in "2 + 2 = 4"
        assert len(var_violations) > 0


class TestOpenAIClaimExtractor:
    """Test OpenAI claim extraction (mocked)."""

    @patch('formal_verification.openai_agents.OpenAI')
    def test_extract_arithmetic_claim(self, mock_openai_class):
        """Test extraction of arithmetic claim."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock triage response
        triage_response = MagicMock()
        triage_response.choices = [MagicMock()]
        triage_response.choices[0].message.content = json.dumps({
            "is_formalizable": True,
            "category": "arithmetic",
            "reasoning": "Simple arithmetic claim",
            "suggestion": ""
        })

        # Mock math extraction response
        math_response = MagicMock()
        math_response.choices = [MagicMock()]
        math_response.choices[0].message.content = json.dumps({
            "claim_text": "2 + 2 = 4",
            "confidence": 0.95,
            "variables": {"left": "2", "right": "2", "result": "4"},
            "pattern_hints": ["addition", "equals"],
            "reasoning": "Extracted arithmetic claim"
        })

        mock_client.chat.completions.create.side_effect = [
            triage_response,
            math_response
        ]

        extractor = OpenAIClaimExtractor()
        result = extractor.extract_claim("two plus two equals four")

        assert result.is_formalizable
        assert result.claim is not None
        assert result.claim.claim_text == "2 + 2 = 4"
        assert result.claim.category == ClaimCategory.ARITHMETIC

    @patch('formal_verification.openai_agents.OpenAI')
    def test_extract_unformalizable_claim(self, mock_openai_class):
        """Test that unformalizable claims are rejected."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock triage response for unformalizable claim
        triage_response = MagicMock()
        triage_response.choices = [MagicMock()]
        triage_response.choices[0].message.content = json.dumps({
            "is_formalizable": False,
            "category": "unformalizable",
            "reasoning": "Subjective claim without mathematical content",
            "suggestion": "Provide a mathematical or algorithmic claim"
        })

        mock_client.chat.completions.create.return_value = triage_response

        extractor = OpenAIClaimExtractor()
        result = extractor.extract_claim("the code is elegant")

        assert not result.is_formalizable
        assert result.claim is None
        assert "Subjective" in result.reasoning


class TestHybridResolver:
    """Test the hybrid resolver integration."""

    @patch('formal_verification.openai_agents.OpenAI')
    @patch('formal_verification.hybrid_resolver.CoqProver')
    def test_analyze_claim_success(self, mock_prover_class, mock_openai_class):
        """Test successful claim analysis."""
        # Mock OpenAI
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        triage_response = MagicMock()
        triage_response.choices = [MagicMock()]
        triage_response.choices[0].message.content = json.dumps({
            "is_formalizable": True,
            "category": "arithmetic",
            "reasoning": "Arithmetic claim",
            "suggestion": ""
        })

        math_response = MagicMock()
        math_response.choices = [MagicMock()]
        math_response.choices[0].message.content = json.dumps({
            "claim_text": "2 + 2 = 4",
            "confidence": 0.95,
            "variables": {"left": "2", "right": "2", "result": "4"},
            "pattern_hints": ["addition"],
            "reasoning": "Simple arithmetic"
        })

        mock_client.chat.completions.create.side_effect = [
            triage_response,
            math_response
        ]

        # Mock Coq prover
        mock_prover = MagicMock()
        mock_prover_class.return_value = mock_prover

        from formal_verification.types import ProofResult
        mock_proof_result = ProofResult(
            spec=MagicMock(),
            proven=True,
            proof_time_ms=50.0,
            error_message=None,
            counter_example=None
        )
        mock_prover.prove.return_value = mock_proof_result

        # Test
        resolver = HybridCognitiveDissonanceResolver(use_guardrails=False)
        analysis = resolver.analyze_claim("2 + 2 = 4")

        assert analysis.is_formalizable
        assert analysis.formalized_claim is not None
        assert analysis.proof_result is not None
        assert analysis.proof_result.proven


def test_claim_category_enum():
    """Test that all claim categories are defined."""
    categories = [
        ClaimCategory.ARITHMETIC,
        ClaimCategory.FACTORIAL,
        ClaimCategory.LOGIC_IMPLICATION,
        ClaimCategory.SORTING,
        ClaimCategory.MEMORY_SAFETY,
    ]
    assert len(categories) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
