"""Optional live smoke coverage for OpenAI-compatible providers."""

import os

import pytest

from formal_verification.hybrid_resolver import HybridCognitiveDissonanceResolver

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _live_api_enabled() -> bool:
    """Whether live provider-backed tests should run."""
    return (
        os.getenv("RUN_LIVE_API_TESTS", "").strip().lower() == "true"
        and bool(os.getenv("OPENAI_API_KEY"))
    )


@pytest.mark.skipif(
    not _live_api_enabled(),
    reason="Live API tests disabled; set RUN_LIVE_API_TESTS=true and OPENAI_API_KEY",
)
def test_openai_compatible_extraction_and_hybrid_proof():
    """Exercise the live extraction -> hybrid proof path for a simple claim."""
    resolver = HybridCognitiveDissonanceResolver(
        model=os.getenv("OPENAI_MODEL", "openai/gpt-4.1-mini"),
        openai_base_url=os.getenv("OPENAI_BASE_URL"),
        openai_app_name=os.getenv("OPENAI_APP_NAME"),
        openai_site_url=os.getenv("OPENAI_SITE_URL"),
        use_guardrails=False,
        proof_timeout_seconds=20,
        use_hybrid_prover=True,
        enable_auto_repair=False,
        enable_necessity=True,
    )

    analysis = resolver.analyze_claim("two plus two equals four")

    assert analysis.is_formalizable
    assert analysis.formalized_claim is not None
    assert analysis.formalized_claim.claim_text == "2 + 2 = 4"
    assert analysis.proof_result is not None
    assert analysis.proof_result.proven is True
