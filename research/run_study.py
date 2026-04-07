"""Run a reproducible empirical study for the repository."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from formal_verification import (
    Claim,
    FormalVerificationConflictDetector,
    PropertyType,
)
from formal_verification.openai_agents import OpenAIClaimExtractor
from formal_verification.translator import ClaimTranslator

ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = ROOT / "research" / "benchmarks"
RESULTS_DIR = ROOT / "research" / "results"


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open() as handle:
        return json.load(handle)


def _repo_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _repo_is_dirty() -> bool:
    """Return whether the working tree has uncommitted changes."""
    return bool(
        subprocess.check_output(
            ["git", "status", "--short"],
            cwd=ROOT,
            text=True,
        ).strip()
    )


def _make_claim(text: str) -> Claim:
    return Claim(
        agent_id="research-study",
        claim_text=text,
        property_type=PropertyType.CORRECTNESS,
        confidence=1.0,
        timestamp=time.time(),
    )


def _proof_summary(proof_result: Any | None) -> dict[str, Any]:
    if proof_result is None:
        return {
            "proven": False,
            "status": None,
            "prover_name": None,
            "proof_time_ms": 0.0,
            "decisive_label": None,
            "optimistic_label": None,
            "machine_checked": False,
            "definitive_disproof": False,
            "ground_truth_strength": False,
            "assumptions_present": False,
        }

    status = proof_result.status.value if proof_result.status else None
    decisive_label: bool | None = None
    if proof_result.status and proof_result.status.supports_resolution_as_proven:
        decisive_label = True
    elif proof_result.is_definitive_disproof:
        decisive_label = False

    optimistic_label: bool | None = None
    if proof_result.proven:
        optimistic_label = True
    elif status in {
        "derived_refuted",
        "refuted",
        "smt_refuted",
        "machine_refuted",
    }:
        optimistic_label = False

    return {
        "proven": bool(proof_result.proven),
        "status": status,
        "prover_name": proof_result.prover_name,
        "proof_time_ms": float(proof_result.proof_time_ms),
        "decisive_label": decisive_label,
        "optimistic_label": optimistic_label,
        "machine_checked": bool(proof_result.is_machine_checked),
        "definitive_disproof": bool(proof_result.is_definitive_disproof),
        "ground_truth_strength": bool(proof_result.establishes_ground_truth),
        "assumptions_present": bool(proof_result.assumptions_present),
        "error_message": proof_result.error_message,
    }


def _aggregate_boolean_rate(values: list[bool]) -> float:
    if not values:
        return 0.0
    return sum(1 for value in values if value) / len(values)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return statistics.mean(values)


def _run_formal_verification_benchmark(
    benchmark: list[dict[str, Any]],
) -> dict[str, Any]:
    conditions = {
        "hybrid_with_necessity": FormalVerificationConflictDetector(
            use_hybrid=True,
            enable_auto_repair=True,
            enable_necessity=True,
        ),
        "hybrid_without_necessity": FormalVerificationConflictDetector(
            use_hybrid=True,
            enable_auto_repair=True,
            enable_necessity=False,
        ),
    }

    condition_results: dict[str, Any] = {}

    for condition_name, detector in conditions.items():
        cases = []
        status_counts: Counter[str] = Counter()
        family_summary: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total": 0, "decisive": 0, "correct": 0}
        )

        for entry in benchmark:
            claim = _make_claim(entry["claim_text"])
            analysis = detector.analyze_claims([claim])
            proof_results = analysis.get("proof_results", [])
            proof_result = proof_results[0] if proof_results else None
            summary = _proof_summary(proof_result)

            decisive_correct = summary["decisive_label"] == entry["expected_truth"]
            if summary["status"]:
                status_counts[summary["status"]] += 1

            family = entry["family"]
            family_summary[family]["total"] += 1
            if summary["decisive_label"] is not None:
                family_summary[family]["decisive"] += 1
            if decisive_correct:
                family_summary[family]["correct"] += 1

            cases.append(
                {
                    "id": entry["id"],
                    "family": family,
                    "claim_text": entry["claim_text"],
                    "expected_truth": entry["expected_truth"],
                    "proof": summary,
                    "decisive_correct": decisive_correct,
                    "optimistic_correct": (
                        summary["optimistic_label"] == entry["expected_truth"]
                    ),
                }
            )

        decisive_cases = [
            case for case in cases if case["proof"]["decisive_label"] is not None
        ]
        optimistic_cases = [
            case for case in cases if case["proof"]["optimistic_label"] is not None
        ]
        correct_cases = [case for case in cases if case["decisive_correct"]]
        condition_results[condition_name] = {
            "cases": cases,
            "metrics": {
                "total_cases": len(cases),
                "decisive_coverage": _aggregate_boolean_rate(
                    [case["proof"]["decisive_label"] is not None for case in cases]
                ),
                "overall_decisive_accuracy": _aggregate_boolean_rate(
                    [case["decisive_correct"] for case in cases]
                ),
                "accuracy_given_decisive": _aggregate_boolean_rate(
                    [case["decisive_correct"] for case in decisive_cases]
                ),
                "optimistic_coverage": _aggregate_boolean_rate(
                    [case["proof"]["optimistic_label"] is not None for case in cases]
                ),
                "overall_optimistic_accuracy": _aggregate_boolean_rate(
                    [case["optimistic_correct"] for case in cases]
                ),
                "accuracy_given_optimistic": _aggregate_boolean_rate(
                    [case["optimistic_correct"] for case in optimistic_cases]
                ),
                "mean_proof_time_ms": _mean(
                    [case["proof"]["proof_time_ms"] for case in cases]
                ),
                "status_counts": dict(status_counts),
                "machine_checked_count": sum(
                    1 for case in cases if case["proof"]["machine_checked"]
                ),
                "ground_truth_strength_count": sum(
                    1 for case in cases if case["proof"]["ground_truth_strength"]
                ),
                "correct_case_count": len(correct_cases),
            },
            "family_summary": dict(family_summary),
        }

    return {
        "benchmark_name": "formal_verification_benchmark",
        "num_cases": len(benchmark),
        "conditions": condition_results,
    }


def _run_extraction_benchmark(
    benchmark: list[dict[str, Any]],
    *,
    extractor: OpenAIClaimExtractor,
) -> dict[str, Any]:
    translator = ClaimTranslator()
    detector = FormalVerificationConflictDetector(
        use_hybrid=True,
        enable_auto_repair=True,
        enable_necessity=True,
    )

    cases = []
    formalizable_cases = [
        entry for entry in benchmark if entry["expected_formalizable"]
    ]

    for entry in benchmark:
        raw_claim = _make_claim(entry["text"])
        baseline_spec = translator.translate(raw_claim, "")
        baseline_translation_success = baseline_spec is not None

        started = time.perf_counter()
        extraction_error = None
        try:
            extracted = extractor.extract_claim(entry["text"])
        except Exception as exc:  # pragma: no cover - defensive for live runs
            extracted = None
            extraction_error = str(exc)
        extraction_time_ms = (time.perf_counter() - started) * 1000

        extracted_claim_text = None
        extracted_category = None
        extracted_formalizable = False
        exact_match = False
        category_correct = False
        translation_success_after_extraction = False
        proof_summary = _proof_summary(None)

        if extracted is not None:
            extracted_formalizable = bool(extracted.is_formalizable)
            if extracted.claim is not None:
                extracted_claim_text = extracted.claim.claim_text
                extracted_category = extracted.claim.category.value

        if entry["expected_formalizable"]:
            exact_match = extracted_claim_text == entry["expected_canonical_claim"]
            category_correct = extracted_category == entry["expected_category"]
        else:
            category_correct = extracted_category in {None, "unformalizable"}

        if extracted_formalizable and extracted_claim_text:
            translated_claim = _make_claim(extracted_claim_text)
            translated_spec = translator.translate(translated_claim, "")
            translation_success_after_extraction = translated_spec is not None
            analysis = detector.analyze_claims([translated_claim])
            proof_results = analysis.get("proof_results", [])
            proof_summary = _proof_summary(proof_results[0] if proof_results else None)

        cases.append(
            {
                "id": entry["id"],
                "text": entry["text"],
                "expected_formalizable": entry["expected_formalizable"],
                "expected_category": entry["expected_category"],
                "expected_canonical_claim": entry.get("expected_canonical_claim"),
                "expected_truth": entry.get("expected_truth"),
                "baseline_translation_success": baseline_translation_success,
                "extraction_time_ms": extraction_time_ms,
                "extraction_error": extraction_error,
                "extracted_formalizable": extracted_formalizable,
                "extracted_category": extracted_category,
                "extracted_claim_text": extracted_claim_text,
                "formalizable_correct": (
                    extracted_formalizable == entry["expected_formalizable"]
                ),
                "category_correct": category_correct,
                "exact_match": exact_match,
                "translation_success_after_extraction": (
                    translation_success_after_extraction
                ),
                "proof": proof_summary,
                "end_to_end_decisive_correct": (
                    proof_summary["decisive_label"] == entry.get("expected_truth")
                    if entry["expected_formalizable"]
                    else True
                ),
            }
        )

    return {
        "benchmark_name": "extraction_benchmark",
        "num_cases": len(cases),
        "metrics": {
            "baseline_translation_success_rate_formalizable": _aggregate_boolean_rate(
                [
                    case["baseline_translation_success"]
                    for case in cases
                    if case["expected_formalizable"]
                ]
            ),
            "extractor_formalizable_accuracy": _aggregate_boolean_rate(
                [case["formalizable_correct"] for case in cases]
            ),
            "extractor_category_accuracy_formalizable": _aggregate_boolean_rate(
                [
                    case["category_correct"]
                    for case in cases
                    if case["expected_formalizable"]
                ]
            ),
            "extractor_exact_match_rate_formalizable": _aggregate_boolean_rate(
                [case["exact_match"] for case in cases if case["expected_formalizable"]]
            ),
            "translation_success_rate_after_extraction_formalizable": (
                _aggregate_boolean_rate(
                    [
                        case["translation_success_after_extraction"]
                        for case in cases
                        if case["expected_formalizable"]
                    ]
                )
            ),
            "end_to_end_decisive_coverage_formalizable": _aggregate_boolean_rate(
                [
                    case["proof"]["decisive_label"] is not None
                    for case in cases
                    if case["expected_formalizable"]
                ]
            ),
            "end_to_end_decisive_accuracy_formalizable": _aggregate_boolean_rate(
                [
                    case["end_to_end_decisive_correct"]
                    for case in cases
                    if case["expected_formalizable"]
                ]
            ),
            "machine_checked_count_formalizable": sum(
                1
                for case in cases
                if case["expected_formalizable"] and case["proof"]["machine_checked"]
            ),
            "status_counts_formalizable": dict(
                Counter(
                    case["proof"]["status"]
                    for case in cases
                    if case["expected_formalizable"] and case["proof"]["status"]
                )
            ),
            "mean_extraction_time_ms": _mean(
                [case["extraction_time_ms"] for case in cases]
            ),
            "error_count": sum(1 for case in cases if case["extraction_error"]),
        },
        "cases": cases,
        "formalizable_case_count": len(formalizable_cases),
    }


def _run_stability_check(
    benchmark: list[dict[str, Any]],
    *,
    extractor: OpenAIClaimExtractor,
    trials: int,
) -> dict[str, Any]:
    selected_ids = [
        "nl_arith_true",
        "nl_factorial_true",
        "nl_implication_true",
        "nl_subjective_code",
    ]
    selected = [entry for entry in benchmark if entry["id"] in selected_ids]
    results = []

    for entry in selected:
        trial_outputs = []
        for _ in range(trials):
            extracted = extractor.extract_claim(entry["text"])
            trial_outputs.append(
                {
                    "is_formalizable": extracted.is_formalizable,
                    "category": (
                        extracted.claim.category.value if extracted.claim else None
                    ),
                    "claim_text": (
                        extracted.claim.claim_text if extracted.claim else None
                    ),
                }
            )
        canonicalized = json.dumps(trial_outputs[0], sort_keys=True)
        stable = all(
            json.dumps(output, sort_keys=True) == canonicalized
            for output in trial_outputs[1:]
        )
        results.append(
            {
                "id": entry["id"],
                "text": entry["text"],
                "trials": trial_outputs,
                "stable_across_trials": stable,
            }
        )

    return {
        "num_cases": len(results),
        "trials_per_case": trials,
        "stable_case_rate": _aggregate_boolean_rate(
            [entry["stable_across_trials"] for entry in results]
        ),
        "cases": results,
    }


def _results_summary(study: dict[str, Any]) -> str:
    fv = study["formal_verification_benchmark"]["conditions"]
    extraction = study.get("extraction_benchmark")
    stability = study.get("stability_check")

    with_necessity = fv["hybrid_with_necessity"]["metrics"]
    without_necessity = fv["hybrid_without_necessity"]["metrics"]

    lines = [
        "# Research Study Summary",
        "",
        f"- Source revision: `{study['meta']['source_revision']}`",
        f"- Generated: `{study['meta']['generated_at']}`",
        "",
        "## Questions",
        "",
        (
            "1. Does necessity-enhanced hybrid verification improve "
            "symbolic claim performance?"
        ),
        (
            "2. Does structured OpenAI-compatible extraction improve "
            "translation success over direct pattern matching?"
        ),
        ("3. How much end-to-end proof coverage remains after successful extraction?"),
        "",
        "## Formal Verification Benchmark",
        "",
        f"- Cases: `{study['formal_verification_benchmark']['num_cases']}`",
        (
            "- Hybrid + necessity: "
            f"decisive coverage `{with_necessity['decisive_coverage']:.1%}`, "
            "overall decisive accuracy "
            f"`{with_necessity['overall_decisive_accuracy']:.1%}`, "
            "optimistic accuracy "
            f"`{with_necessity['overall_optimistic_accuracy']:.1%}`, "
            "machine-checked cases "
            f"`{with_necessity['machine_checked_count']}`, "
            f"mean proof time `{with_necessity['mean_proof_time_ms']:.1f} ms`"
        ),
        (
            "- Hybrid without necessity: "
            f"decisive coverage `{without_necessity['decisive_coverage']:.1%}`, "
            "overall decisive accuracy "
            f"`{without_necessity['overall_decisive_accuracy']:.1%}`, "
            "optimistic accuracy "
            f"`{without_necessity['overall_optimistic_accuracy']:.1%}`, "
            "machine-checked cases "
            f"`{without_necessity['machine_checked_count']}`, "
            f"mean proof time `{without_necessity['mean_proof_time_ms']:.1f} ms`"
        ),
        "",
    ]

    if extraction is None:
        lines.extend(
            [
                "## Extraction Benchmark",
                "",
                "- Skipped because no OpenAI-compatible API credentials were provided.",
                "",
            ]
        )
    else:
        metrics = extraction["metrics"]
        lines.extend(
            [
                "## Extraction Benchmark",
                "",
                f"- Cases: `{extraction['num_cases']}`",
                (
                    "- Direct translator success on formalizable "
                    "natural-language claims: "
                    f"`{metrics['baseline_translation_success_rate_formalizable']:.1%}`"
                ),
                (
                    "- Extractor formalizability accuracy: "
                    f"`{metrics['extractor_formalizable_accuracy']:.1%}`"
                ),
                (
                    "- Extractor exact canonical match on formalizable claims: "
                    f"`{metrics['extractor_exact_match_rate_formalizable']:.1%}`"
                ),
                (
                    "- Translation success after extraction on formalizable claims: "
                    f"`{metrics['translation_success_rate_after_extraction_formalizable']:.1%}`"
                ),
                (
                    "- End-to-end decisive proof coverage after extraction: "
                    f"`{metrics['end_to_end_decisive_coverage_formalizable']:.1%}`"
                ),
                (
                    "- End-to-end decisive accuracy after extraction: "
                    f"`{metrics['end_to_end_decisive_accuracy_formalizable']:.1%}`"
                ),
                (
                    "- Machine-checked formalizable cases after extraction: "
                    f"`{metrics['machine_checked_count_formalizable']}`"
                ),
                "",
            ]
        )

    if stability is not None:
        lines.extend(
            [
                "## Stability Check",
                "",
                (
                    f"- Stable case rate across "
                    f"`{stability['trials_per_case']}` trials: "
                    f"`{stability['stable_case_rate']:.1%}`"
                ),
                "",
            ]
        )

    lines.extend(
        [
            "## Interpretation",
            "",
            (
                "- The symbolic benchmark quantifies what the current "
                "formal verification stack can already resolve decisively."
            ),
            (
                "- The extraction benchmark isolates whether "
                "provider-backed normalization actually expands "
                "proof-ready coverage."
            ),
        ]
    )

    if extraction is not None:
        metrics = extraction["metrics"]
        if (
            metrics["translation_success_rate_after_extraction_formalizable"] == 1.0
            and metrics["end_to_end_decisive_coverage_formalizable"] == 1.0
        ):
            lines.append(
                "- On the current internal benchmark, extraction and decisive "
                "verification both saturate; the main remaining limitation is "
                "benchmark breadth rather than measured pipeline accuracy."
            )
        else:
            lines.append(
                "- Any gap between extraction success and decisive proof "
                "coverage indicates that translation/proof support, not "
                "extraction alone, is the dominant remaining bottleneck."
            )

    lines.extend(
        [
            "",
        ]
    )
    return "\n".join(lines)


def run_study(args: argparse.Namespace) -> dict[str, Any]:
    """Execute the full study and write JSON plus markdown artifacts."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    formal_benchmark = _load_json(BENCHMARKS_DIR / "formal_verification_benchmark.json")
    extraction_benchmark = _load_json(BENCHMARKS_DIR / "extraction_benchmark.json")

    study: dict[str, Any] = {
        "meta": {
            "commit": _repo_commit(),
            "dirty_worktree": _repo_is_dirty(),
            "source_revision": (
                f"{_repo_commit()}-dirty" if _repo_is_dirty() else _repo_commit()
            ),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "live_provider_enabled": bool(os.getenv("OPENAI_API_KEY")),
            "provider_base_url": os.getenv("OPENAI_BASE_URL"),
            "provider_model": os.getenv("OPENAI_MODEL", args.model),
            "extraction_temperature": args.temperature,
        },
        "formal_verification_benchmark": _run_formal_verification_benchmark(
            formal_benchmark
        ),
    }

    if os.getenv("OPENAI_API_KEY"):
        extractor = OpenAIClaimExtractor(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL", args.model),
            base_url=os.getenv("OPENAI_BASE_URL"),
            app_name=os.getenv("OPENAI_APP_NAME"),
            site_url=os.getenv("OPENAI_SITE_URL"),
            temperature=args.temperature,
        )
        study["extraction_benchmark"] = _run_extraction_benchmark(
            extraction_benchmark,
            extractor=extractor,
        )
        study["stability_check"] = _run_stability_check(
            extraction_benchmark,
            extractor=extractor,
            trials=args.stability_trials,
        )
    else:
        study["extraction_benchmark"] = None
        study["stability_check"] = None

    json_path = RESULTS_DIR / "study_results.json"
    summary_path = RESULTS_DIR / "study_summary.md"
    json_path.write_text(json.dumps(study, indent=2, sort_keys=True))
    summary_path.write_text(_results_summary(study))
    return study


def main() -> None:
    """CLI entry point for the study runner."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="openai/gpt-4.1-mini",
        help="Provider model for live extraction benchmarks",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Extraction temperature for live provider calls",
    )
    parser.add_argument(
        "--stability-trials",
        type=int,
        default=2,
        help="Number of repeated extraction trials for the stability check",
    )
    args = parser.parse_args()
    study = run_study(args)
    print(
        json.dumps(
            {
                "commit": study["meta"]["commit"],
                "source_revision": study["meta"]["source_revision"],
                "results_path": str(RESULTS_DIR / "study_results.json"),
                "summary_path": str(RESULTS_DIR / "study_summary.md"),
                "live_provider_enabled": study["meta"]["live_provider_enabled"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
