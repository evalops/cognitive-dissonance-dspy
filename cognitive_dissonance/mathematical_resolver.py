"""Mathematical proof-backed cognitive dissonance resolution.

This module integrates DSPy agents with formal verification so mathematical
certainty can override probabilistic reconciliation for verifiable claims.
"""

import logging
import random
import re
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any

import dspy

from formal_verification import Claim as FormalClaim
from formal_verification import (
    FormalVerificationConflictDetector,
    ProofResult,
    PropertyType,
)
from formal_verification.semantic_bridge import SemanticLogicalBridge

from .verifier import BeliefAgent, DissonanceDetector, ReconciliationAgent

logger = logging.getLogger(__name__)


class ClaimCategory(Enum):
    """Categories of claims for routing to appropriate resolution methods."""

    MATHEMATICAL = "mathematical"  # Arithmetic, algebra, logic
    ALGORITHMIC = "algorithmic"  # Algorithm correctness, complexity
    PHYSICAL = "physical"  # Physical constants, scientific facts
    SOFTWARE = "software"  # Code properties, system behavior
    LINGUISTIC = "linguistic"  # Language facts, definitions
    SUBJECTIVE = "subjective"  # Opinions, preferences
    UNVERIFIABLE = "unverifiable"  # Claims that cannot be formally verified


class ResolutionMethod(Enum):
    """Resolution strategies returned by the resolver."""

    MATHEMATICAL_PROOF = "mathematical_proof"
    PROBABILISTIC = "probabilistic"
    HYBRID = "hybrid"
    DIAGNOSTIC = "diagnostic"


class EvidenceStatus(Enum):
    """Status of an individual mathematical verification attempt."""

    PROVEN = "proven"
    DISPROVEN = "disproven"
    INCONCLUSIVE = "inconclusive"


@dataclass
class MathematicalEvidence:
    """Evidence from mathematical formal verification."""

    claim_text: str
    proven: bool
    proof_time_ms: float
    prover_used: str
    status: EvidenceStatus
    error_message: str | None = None
    counter_example: str | None = None
    confidence_score: float = 1.0
    proof_output: str | None = None
    solver_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResolutionResult:
    """Result of mathematical proof-backed cognitive dissonance resolution."""

    original_claim1: str
    original_claim2: str
    conflict_detected: bool
    resolution_method: ResolutionMethod
    resolved_claim: str
    mathematical_evidence: list[MathematicalEvidence]
    probabilistic_confidence: float
    final_confidence: float
    reasoning: str
    audit_metadata: dict[str, Any]
    solver_diagnostics: list[dict[str, Any]]
    normalized_specs: list[str]


class ClaimClassifier:
    """Classifies claims to determine if they are mathematically verifiable.

    This uses the necessity analyzer as the authoritative source for mathematical
    patterns, avoiding duplication of pattern matching logic.
    """

    def __init__(self):
        # Import here to avoid circular dependency
        from formal_verification.necessity_prover import MathematicalStructureAnalyzer

        self.necessity_analyzer = MathematicalStructureAnalyzer()

        self.algorithmic_patterns = [
            re.compile(r"[Oo]\s*\(\s*[^)]+\s*\)"),
            re.compile(r"\btime complexity\b.*[Oo]\s*\("),
            re.compile(r"\bspace complexity\b.*[Oo]\s*\("),
            re.compile(r"algorithm\b.*\bcorrect(ly)?"),
            re.compile(r"sorts?\b.*\bcorrect(ly)?"),
            re.compile(r"\bfunction\b.*\bterminates?"),
            re.compile(r"\balgorithm\b.*\bterminates?"),
            re.compile(r"\bcomplexity\b.*[Oo]\s*\("),
            re.compile(r"\balgorithm\b.*\bhas\b.*[Oo]\s*\("),
        ]

        self.physical_patterns = [
            re.compile(r"speed of light\D*299792458"),
            re.compile(r"gravity\D*9\.8"),
            re.compile(r"water\D*boils?\D*100\D*celsius"),
            re.compile(r"absolute zero\D*-273\.15"),
        ]

        self.software_patterns = [
            re.compile(r"memory safe"),
            re.compile(r"buffer overflow"),
            re.compile(r"race condition"),
            re.compile(r"deadlock"),
            re.compile(r"null pointer"),
        ]

        self._algorithmic_negative = re.compile(r"\b(correct|right|true)\b")

        self._classify_cached = lru_cache(maxsize=512)(self._classify_uncached)
        self._analyze_necessity_cached = lru_cache(maxsize=256)(self._analyze_necessity)

    def classify_claim(self, claim_text: str) -> ClaimCategory:
        """Classify a claim to determine verification approach.

        Args:
            claim_text: The claim to classify

        Returns:
            Category indicating verification approach
        """
        normalized = claim_text.strip()
        return self._classify_cached(normalized)

    def _classify_uncached(self, claim_text: str) -> ClaimCategory:
        claim_lower = claim_text.lower()

        necessity_evidence = self._analyze_necessity_cached(claim_text)
        if necessity_evidence is not None and necessity_evidence.confidence >= 0.5:
            logger.debug("Classified as MATHEMATICAL via necessity analysis")
            return ClaimCategory.MATHEMATICAL

        for pattern in self.algorithmic_patterns:
            if pattern.search(claim_lower):
                if (
                    self._algorithmic_negative.search(claim_lower)
                    and "algorithm" not in claim_lower
                ):
                    continue
                logger.debug(f"Classified as ALGORITHMIC: {pattern.pattern}")
                return ClaimCategory.ALGORITHMIC

        for pattern in self.physical_patterns:
            if pattern.search(claim_lower):
                logger.debug(f"Classified as PHYSICAL: {pattern.pattern}")
                return ClaimCategory.PHYSICAL

        for pattern in self.software_patterns:
            if pattern.search(claim_lower):
                logger.debug(f"Classified as SOFTWARE: {pattern.pattern}")
                return ClaimCategory.SOFTWARE

        if any(
            word in claim_lower
            for word in ["think", "believe", "opinion", "prefer", "like"]
        ):
            return ClaimCategory.SUBJECTIVE
        if any(
            word in claim_lower
            for word in [
                "beautiful",
                "ugly",
                "good",
                "bad",
                "should",
                "better",
                "worse",
                "best",
            ]
        ):
            return ClaimCategory.SUBJECTIVE
        return ClaimCategory.UNVERIFIABLE

    def _analyze_necessity(self, claim_text: str):
        return self.necessity_analyzer.analyze_claim(claim_text)


class MathematicalCognitiveDissonanceResolver(dspy.Module):
    """Revolutionary proof-backed cognitive dissonance resolution system.

    This system integrates DSPy agents with formal verification to achieve
    mathematical certainty in cognitive dissonance resolution for verifiable claims.
    """

    def __init__(
        self,
        use_cot: bool = True,
        enable_formal_verification: bool = True,
        proof_timeout_seconds: int = 30,
        random_seed: int = 1337,
        temperature: float = 0.0,
        max_bridged_targets: int = 3,
    ):
        """Initialize the mathematical resolver.

        Args:
            use_cot: Enable Chain of Thought reasoning for DSPy agents
            enable_formal_verification: Enable formal verification subsystem
            proof_timeout_seconds: Max time allowable for each proof attempt
            random_seed: Seed to make probabilistic modules deterministic
            temperature: LM temperature used during DSPy inference
            max_bridged_targets: Maximum verification targets per subjective claim
        """
        super().__init__()

        # Initialize DSPy agents
        self.belief_agent = BeliefAgent(use_cot=use_cot)
        self.dissonance_detector = DissonanceDetector(use_cot=use_cot)
        self.reconciliation_agent = ReconciliationAgent(use_cot=use_cot)

        # Initialize mathematical components
        self.claim_classifier = ClaimClassifier()

        # Initialize semantic bridge system
        self.semantic_bridge = SemanticLogicalBridge()

        # Initialize formal verification system
        self.enable_formal_verification = enable_formal_verification
        self._proof_timeout_seconds = proof_timeout_seconds
        self.random_seed = random_seed
        self.temperature = temperature
        self.max_bridged_targets = max(1, max_bridged_targets)
        self._forward_lock = threading.Lock()
        self._invocation_counter = 0
        self.prompt_variant = "cot" if use_cot else "direct"
        self._belief_confidence_map = {
            "high": 0.85,
            "medium": 0.55,
            "low": 0.3,
        }
        self._category_prior = {
            ClaimCategory.MATHEMATICAL: 0.9,
            ClaimCategory.ALGORITHMIC: 0.8,
            ClaimCategory.PHYSICAL: 0.75,
            ClaimCategory.SOFTWARE: 0.7,
            ClaimCategory.LINGUISTIC: 0.4,
            ClaimCategory.SUBJECTIVE: 0.35,
            ClaimCategory.UNVERIFIABLE: 0.3,
        }

        self._software_keyword_map = {
            PropertyType.MEMORY_SAFETY: ["memory", "overflow", "pointer", "safe"],
            PropertyType.CONCURRENCY: ["race", "deadlock", "concurrent", "mutex"],
            PropertyType.TERMINATION: ["terminate", "termination", "halts"],
        }
        self._default_software_property = PropertyType.CORRECTNESS

        if enable_formal_verification:
            self.formal_detector = FormalVerificationConflictDetector(
                timeout_seconds=proof_timeout_seconds,
                use_hybrid=True,  # Use Z3+Coq hybrid proving
                enable_auto_repair=True,  # Enable automatic lemma discovery
                enable_necessity=True,  # Enable necessity-based proof discovery
            )
            logger.info("Initialized with formal verification enabled")
        else:
            self.formal_detector = None
            logger.info("Initialized without formal verification")

    def _normalize_belief_confidence(self, confidence: Any | None) -> float:
        if isinstance(confidence, (int, float)):
            return max(0.0, min(1.0, float(confidence)))
        if isinstance(confidence, str):
            normalized = confidence.strip().lower()
            if normalized in self._belief_confidence_map:
                return self._belief_confidence_map[normalized]
            try:
                return max(0.0, min(1.0, float(normalized)))
            except ValueError:
                return self._belief_confidence_map["medium"]
        return self._belief_confidence_map["medium"]

    def _base_prior(self, belief_confidence: float, category: ClaimCategory) -> float:
        category_weight = self._category_prior.get(category, 0.5)
        return max(0.0, min(1.0, (belief_confidence + category_weight) / 2))

    def _infer_software_property_type(self, claim_text: str) -> PropertyType:
        lowered = claim_text.lower()
        for property_type, keywords in self._software_keyword_map.items():
            if any(keyword in lowered for keyword in keywords):
                return property_type
        return self._default_software_property

    def _property_type_for_category(
        self, category: ClaimCategory, claim_text: str
    ) -> PropertyType:
        if category == ClaimCategory.SOFTWARE:
            return self._infer_software_property_type(claim_text)
        if category in (
            ClaimCategory.MATHEMATICAL,
            ClaimCategory.ALGORITHMIC,
            ClaimCategory.PHYSICAL,
        ):
            return PropertyType.CORRECTNESS
        return PropertyType.CORRECTNESS

    @contextmanager
    def _deterministic_run(self, seed: int):
        random_state = random.getstate()
        numpy_state = None
        numpy_module = None
        try:
            random.seed(seed)
            try:
                import numpy as np  # type: ignore

                numpy_module = np
                numpy_state = np.random.get_state()
                np.random.seed(seed)
            except Exception:
                numpy_module = None
                numpy_state = None

            with dspy.context(temperature=self.temperature, seed=seed):
                yield
        finally:
            random.setstate(random_state)
            if numpy_module is not None and numpy_state is not None:
                numpy_module.random.set_state(numpy_state)

    def _determine_evidence_status(self, proof_result: ProofResult) -> EvidenceStatus:
        status = proof_result.status
        if status and status.supports_resolution_as_proven:
            return EvidenceStatus.PROVEN
        if proof_result.is_definitive_disproof:
            return EvidenceStatus.DISPROVEN
        if status and status.counts_as_inconclusive_evidence:
            return EvidenceStatus.INCONCLUSIVE
        if proof_result.error_message:
            message = proof_result.error_message.lower()
            if any(term in message for term in ["counter", "refuted", "contradiction"]):
                return EvidenceStatus.DISPROVEN
            if any(
                term in message
                for term in ["timeout", "timed out", "no mathematical necessity"]
            ):
                return EvidenceStatus.INCONCLUSIVE
        return EvidenceStatus.INCONCLUSIVE

    def _build_mathematical_evidence(
        self, proof_result: ProofResult
    ) -> MathematicalEvidence:
        status = self._determine_evidence_status(proof_result)
        prover_used = (
            getattr(proof_result, "prover_name", None)
            or proof_result.proof_output
            or "unknown"
        )
        confidence_score = (
            1.0
            if status == EvidenceStatus.PROVEN
            else (
                proof_result.spec.claim.confidence
                if status == EvidenceStatus.INCONCLUSIVE
                else 0.0
            )
        )
        solver_metadata: dict[str, Any] = {
            "agent_id": proof_result.spec.claim.agent_id,
            "property_type": proof_result.spec.claim.property_type.value,
            "status": status.value,
        }
        if proof_result.counter_example:
            solver_metadata["counter_example"] = proof_result.counter_example
        if proof_result.error_message:
            solver_metadata["error"] = proof_result.error_message
        if getattr(proof_result, "auto_repaired", False):
            solver_metadata["auto_repaired"] = True

        return MathematicalEvidence(
            claim_text=proof_result.spec.claim.claim_text,
            proven=status == EvidenceStatus.PROVEN,
            proof_time_ms=proof_result.proof_time_ms,
            prover_used=prover_used,
            status=status,
            error_message=proof_result.error_message,
            counter_example=proof_result.counter_example,
            confidence_score=max(0.0, min(1.0, confidence_score)),
            proof_output=proof_result.proof_output or None,
            solver_metadata=solver_metadata,
        )

    def _compute_final_confidence(
        self,
        resolved_claim: str,
        evidence: list[MathematicalEvidence],
        claim_context: dict[str, dict[str, Any]],
        fallback_confidence: float,
    ) -> float:
        base_prior = claim_context.get(resolved_claim, {}).get(
            "prior", fallback_confidence
        )
        contributions: list[tuple[float, float]] = []

        for ev in evidence:
            if ev.claim_text == resolved_claim:
                if ev.status == EvidenceStatus.PROVEN:
                    contributions.append((1.0, 1.0))
                elif ev.status == EvidenceStatus.DISPROVEN:
                    contributions.append((0.0, 1.0))
                else:
                    prior = claim_context.get(ev.claim_text, {}).get(
                        "prior", ev.confidence_score
                    )
                    contributions.append((prior, 0.5))
            elif ev.status == EvidenceStatus.DISPROVEN:
                # Competing claim refuted increases confidence in resolved claim
                contributions.append((base_prior + 0.2, 0.3))

        if contributions:
            numerator = sum(value * weight for value, weight in contributions)
            denominator = sum(weight for _, weight in contributions)
            if denominator:
                return max(0.0, min(1.0, numerator / denominator))
        return max(0.0, min(1.0, base_prior))

    def _collect_solver_diagnostics(
        self,
        proof_results: list[ProofResult],
        analysis_results: dict[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        diagnostics: list[dict[str, Any]] = []
        normalized_specs: list[str] = []

        if analysis_results:
            specs = analysis_results.get("specifications", []) or []
            normalized_specs = [
                getattr(spec, "spec_text", "")
                for spec in specs
                if getattr(spec, "spec_text", "")
            ]

        for proof in proof_results:
            status = self._determine_evidence_status(proof)
            diagnostics.append(
                {
                    "claim": proof.spec.claim.claim_text,
                    "property_type": proof.spec.claim.property_type.value,
                    "status": status.value,
                    "prover": getattr(proof, "prover_name", None)
                    or proof.proof_output
                    or "unknown",
                    "time_ms": proof.proof_time_ms,
                    "error": proof.error_message,
                    "counter_example": proof.counter_example,
                }
            )

        return diagnostics, normalized_specs

    def forward(self, text1: str, text2: str, code: str = "") -> ResolutionResult:
        """Resolve two claims, using code context when available."""
        with self._forward_lock:
            self._invocation_counter += 1
            invocation_seed = self.random_seed + self._invocation_counter
            with self._deterministic_run(invocation_seed):
                return self._forward_impl(text1, text2, code, invocation_seed)

    def _forward_impl(
        self,
        text1: str,
        text2: str,
        code: str,
        invocation_seed: int,
    ) -> ResolutionResult:
        """Resolve cognitive dissonance with mathematical backing."""
        logger.info(
            "Starting mathematical proof-backed cognitive dissonance resolution"
        )

        # Step 1: Extract claims using DSPy agents
        belief1 = self.belief_agent(text=text1)
        belief2 = self.belief_agent(text=text2)

        claim1_text = belief1.claim
        claim2_text = belief2.claim

        belief_conf1 = self._normalize_belief_confidence(
            getattr(belief1, "confidence", None)
        )
        belief_conf2 = self._normalize_belief_confidence(
            getattr(belief2, "confidence", None)
        )

        claim_context: dict[str, dict[str, Any]] = {
            claim1_text: {
                "belief_confidence": belief_conf1,
            },
            claim2_text: {
                "belief_confidence": belief_conf2,
            },
        }

        logger.debug(f"Extracted claims: '{claim1_text}' vs '{claim2_text}'")

        # Step 2: Detect dissonance using DSPy
        dissonance = self.dissonance_detector(claim1=claim1_text, claim2=claim2_text)
        has_conflict = dissonance.are_contradictory == "yes"

        if not has_conflict:
            logger.info(
                "No cognitive dissonance detected, using probabilistic reconciliation"
            )
            reconciled = self.reconciliation_agent(
                claim1=claim1_text, claim2=claim2_text, has_conflict="no"
            )
            available_confidences = [
                c for c in (belief_conf1, belief_conf2) if c is not None
            ]
            probabilistic_confidence = (
                sum(available_confidences) / len(available_confidences)
                if available_confidences
                else 0.75
            )
            audit_metadata = {
                "seed": invocation_seed,
                "base_seed": self.random_seed,
                "invocation_index": self._invocation_counter,
                "temperature": self.temperature,
                "prompt_variant": self.prompt_variant,
                "probabilistic_only": True,
                "solver_time_budget_ms": self._proof_timeout_seconds * 1000,
            }

            return ResolutionResult(
                original_claim1=claim1_text,
                original_claim2=claim2_text,
                conflict_detected=False,
                resolution_method=ResolutionMethod.PROBABILISTIC,
                resolved_claim=reconciled.reconciled_claim,
                mathematical_evidence=[],
                probabilistic_confidence=probabilistic_confidence,
                final_confidence=probabilistic_confidence,
                reasoning=(
                    "No conflict detected between claims, combined "
                    "probabilistically"
                ),
                audit_metadata=audit_metadata,
                solver_diagnostics=[],
                normalized_specs=[],
            )

        logger.info(f"Cognitive dissonance detected: {dissonance.reason}")

        # Step 3: Classify claims for mathematical verification
        category1 = self.claim_classifier.classify_claim(claim1_text)
        category2 = self.claim_classifier.classify_claim(claim2_text)

        claim_context[claim1_text]["category"] = category1
        claim_context[claim2_text]["category"] = category2
        claim_context[claim1_text]["prior"] = self._base_prior(belief_conf1, category1)
        claim_context[claim2_text]["prior"] = self._base_prior(belief_conf2, category2)

        audit_metadata: dict[str, Any] = {
            "seed": invocation_seed,
            "base_seed": self.random_seed,
            "invocation_index": self._invocation_counter,
            "temperature": self.temperature,
            "prompt_variant": self.prompt_variant,
            "solver_time_budget_ms": self._proof_timeout_seconds * 1000,
            "semantic_bridge_targets": [],
            "num_formal_targets": 0,
        }

        mathematical_evidence: list[MathematicalEvidence] = []
        analysis_results: dict[str, Any] | None = None
        bridged_claims: list[dict[str, Any]] = []

        # Step 4: Attempt formal verification for verifiable claims, including
        # bridged subjective claims.
        if self.enable_formal_verification and self.formal_detector:
            formal_claims: list[FormalClaim] = []

            # Process each claim through classification and semantic bridging
            for i, (claim_text, category) in enumerate(
                [(claim1_text, category1), (claim2_text, category2)]
            ):
                source_confidence = belief_conf1 if i == 0 else belief_conf2

                if category in [
                    ClaimCategory.MATHEMATICAL,
                    ClaimCategory.ALGORITHMIC,
                    ClaimCategory.PHYSICAL,
                    ClaimCategory.SOFTWARE,
                ]:
                    property_type = self._property_type_for_category(
                        category, claim_text
                    )
                    formal_claim = FormalClaim(
                        agent_id=f"agent_{i + 1}",
                        claim_text=claim_text,
                        property_type=property_type,
                        confidence=source_confidence,
                        timestamp=time.time(),
                    )
                    formal_claims.append(formal_claim)

                elif category in [ClaimCategory.SUBJECTIVE, ClaimCategory.UNVERIFIABLE]:
                    logger.info(
                        "Attempting semantic bridging for %s claim: '%s...'",
                        category.value,
                        claim_text[:50],
                    )

                    bridge = self.semantic_bridge.analyze_subjective_claim(claim_text)

                    if self.semantic_bridge.should_attempt_verification(bridge):
                        logger.info(
                            (
                                "Found objective grounding (score: %.2f) - "
                                "creating verification targets"
                            ),
                            bridge.total_objectivity_score,
                        )

                        verification_targets = (
                            self.semantic_bridge.get_verification_targets(bridge)[
                                : self.max_bridged_targets
                            ]
                        )

                        for target_claim in verification_targets:
                            lowered_target = target_claim.lower()
                            if any(
                                word in lowered_target
                                for word in [
                                    "complexity",
                                    "time",
                                    "space",
                                    "o(",
                                    "algorithm",
                                ]
                            ):
                                prop_type = PropertyType.TIME_COMPLEXITY
                                derived_category = ClaimCategory.ALGORITHMIC
                            elif any(
                                word in lowered_target
                                for word in [
                                    "memory",
                                    "buffer",
                                    "safe",
                                    "overflow",
                                    "race",
                                    "deadlock",
                                ]
                            ):
                                prop_type = PropertyType.MEMORY_SAFETY
                                derived_category = ClaimCategory.SOFTWARE
                            else:
                                prop_type = PropertyType.CORRECTNESS
                                derived_category = ClaimCategory.MATHEMATICAL

                            bridged_claim = FormalClaim(
                                agent_id=f"agent_{i + 1}_bridged",
                                claim_text=target_claim,
                                property_type=prop_type,
                                confidence=bridge.total_objectivity_score,
                                timestamp=time.time(),
                            )
                            formal_claims.append(bridged_claim)
                            derived_prior = self._base_prior(
                                bridge.total_objectivity_score, derived_category
                            )
                            claim_context[target_claim] = {
                                "belief_confidence": bridge.total_objectivity_score,
                                "category": derived_category,
                                "prior": derived_prior,
                            }
                            bridged_claims.append(
                                {
                                    "original": claim_text,
                                    "bridged": target_claim,
                                    "objectivity_score": bridge.total_objectivity_score,
                                }
                            )
                    else:
                        logger.debug(
                            (
                                "Insufficient objective grounding (score: %.2f) - "
                                "using probabilistic fallback"
                            ),
                            bridge.total_objectivity_score,
                        )

            if formal_claims:
                logger.info(
                    "Performing formal verification on %d claims", len(formal_claims)
                )
                audit_metadata["num_formal_targets"] = len(formal_claims)

                try:
                    analysis_results = self.formal_detector.analyze_claims(
                        formal_claims, code=code
                    )
                    proof_results = analysis_results.get("proof_results", [])

                    for proof_result in proof_results:
                        evidence = self._build_mathematical_evidence(proof_result)
                        mathematical_evidence.append(evidence)

                        logger.info(
                            "Formal verification: '%s...' -> %s (%.1fms)",
                            evidence.claim_text[:50],
                            "PROVEN"
                            if evidence.proven
                            else evidence.status.value.upper(),
                            evidence.proof_time_ms,
                        )

                except Exception as exc:
                    logger.warning("Formal verification failed: %s", exc)

        audit_metadata["semantic_bridge_targets"] = bridged_claims

        if analysis_results:
            audit_metadata["formal_resolution_summary"] = analysis_results.get(
                "resolution", {}
            )
            audit_metadata["translation_failures"] = len(
                analysis_results.get("translation_failures", []) or []
            )

        proof_results = (
            analysis_results.get("proof_results", []) if analysis_results else []
        )
        solver_diagnostics, normalized_specs = self._collect_solver_diagnostics(
            proof_results, analysis_results
        )

        probabilistic_confidence = (
            claim_context[claim1_text]["prior"] + claim_context[claim2_text]["prior"]
        ) / 2
        audit_metadata["probabilistic_prior"] = probabilistic_confidence

        resolution_method, resolved_claim, final_confidence, reasoning = (
            self._resolve_with_mathematical_evidence(
                claim1_text,
                claim2_text,
                mathematical_evidence,
                dissonance.reason,
                claim_context,
                probabilistic_confidence,
            )
        )

        if bridged_claims:
            bridge_info = [
                (
                    f"Bridged '{bridge_data['original'][:30]}...' → "
                    f"'{bridge_data['bridged']}' "
                    f"(objectivity: {bridge_data['objectivity_score']:.2f})"
                )
                for bridge_data in bridged_claims
            ]
            if resolution_method == ResolutionMethod.MATHEMATICAL_PROOF:
                reasoning += f"\n\nSemantic Bridge Analysis: {'; '.join(bridge_info)}"
            elif resolution_method == ResolutionMethod.HYBRID:
                reasoning = (
                    "Hybrid resolution with semantic bridging: "
                    f"{'; '.join(bridge_info)}. {reasoning}"
                )
            logger.info(
                "Resolution enhanced with %d semantic bridges", len(bridged_claims)
            )

        return ResolutionResult(
            original_claim1=claim1_text,
            original_claim2=claim2_text,
            conflict_detected=True,
            resolution_method=resolution_method,
            resolved_claim=resolved_claim,
            mathematical_evidence=mathematical_evidence,
            probabilistic_confidence=probabilistic_confidence,
            final_confidence=final_confidence,
            reasoning=reasoning,
            audit_metadata=audit_metadata,
            solver_diagnostics=solver_diagnostics,
            normalized_specs=normalized_specs,
        )

    def _resolve_with_mathematical_evidence(
        self,
        claim1: str,
        claim2: str,
        evidence: list[MathematicalEvidence],
        conflict_reason: str,
        claim_context: dict[str, dict[str, Any]],
        probabilistic_confidence: float,
    ) -> tuple[ResolutionMethod, str, float, str]:
        """Resolve conflicts using mathematical and probabilistic evidence."""
        proven_claims = [e for e in evidence if e.status == EvidenceStatus.PROVEN]
        disproven_claims = [e for e in evidence if e.status == EvidenceStatus.DISPROVEN]
        proven_texts = {e.claim_text for e in proven_claims}
        disproven_texts = {e.claim_text for e in disproven_claims}

        if proven_claims:
            if len(proven_texts) > 1:
                reasoning = (
                    "Conflicting proofs: multiple claims verified. "
                    "Flagging for diagnostic review."
                )
                logger.warning(
                    "Multiple conflicting claims proven - diagnostic required"
                )
                return (
                    ResolutionMethod.DIAGNOSTIC,
                    "Manual review required",
                    0.0,
                    reasoning,
                )

            resolved_claim = proven_claims[0].claim_text
            reasoning = (
                f"Claim mathematically proven using {proven_claims[0].prover_used} "
                f"in {proven_claims[0].proof_time_ms:.1f}ms"
            )
            logger.info("Mathematical resolution: '%s' (proven)", resolved_claim)
            return (
                ResolutionMethod.MATHEMATICAL_PROOF,
                resolved_claim,
                1.0,
                reasoning,
            )

        if disproven_claims:
            surviving = [c for c in [claim1, claim2] if c not in disproven_texts]
            if len(surviving) == 1:
                resolved_claim = surviving[0]
                final_confidence = self._compute_final_confidence(
                    resolved_claim,
                    evidence,
                    claim_context,
                    probabilistic_confidence,
                )
                reasoning = (
                    "Competing claim refuted mathematically; accepting surviving claim"
                )
                return (
                    ResolutionMethod.MATHEMATICAL_PROOF,
                    resolved_claim,
                    max(final_confidence, 0.85),
                    reasoning,
                )

            if not surviving:
                resolved_claim = self._probabilistic_fallback(claim1, claim2)
                reasoning = (
                    "All claims refuted; falling back to probabilistic reconciliation"
                )
                final_confidence = min(0.4, probabilistic_confidence / 2)
                return (
                    ResolutionMethod.HYBRID,
                    resolved_claim,
                    final_confidence,
                    reasoning,
                )

        if evidence:
            resolved_claim = self._probabilistic_fallback(claim1, claim2)
            final_confidence = self._compute_final_confidence(
                resolved_claim,
                evidence,
                claim_context,
                probabilistic_confidence,
            )
            reasoning = (
                "Mathematical attempts inconclusive; blending "
                "probabilistic reconciliation "
                "with partial evidence"
            )
            return (
                ResolutionMethod.HYBRID,
                resolved_claim,
                final_confidence,
                reasoning,
            )

        resolved_claim = self._probabilistic_fallback(claim1, claim2)
        reasoning = (
            "Claims not mathematically verifiable, using probabilistic reconciliation: "
            f"{conflict_reason}"
        )
        return (
            ResolutionMethod.PROBABILISTIC,
            resolved_claim,
            probabilistic_confidence,
            reasoning,
        )

    def _probabilistic_fallback(self, claim1: str, claim2: str) -> str:
        """Fallback to probabilistic reconciliation when mathematical proof unavailable.

        Args:
            claim1: First claim
            claim2: Second claim

        Returns:
            Reconciled claim using DSPy agent
        """
        try:
            reconciled = self.reconciliation_agent(
                claim1=claim1, claim2=claim2, has_conflict="yes"
            )
            return reconciled.reconciled_claim
        except Exception as e:
            logger.warning(f"Probabilistic reconciliation failed: {e}")
            # Ultimate fallback - simple preference for first claim
            return claim1
