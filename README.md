# Cognitive Dissonance DSPy

[![Requirements: Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-Compatible-green.svg)](https://github.com/stanfordnlp/dspy)
[![Coq](https://img.shields.io/badge/Coq-8.18+-orange.svg)](https://coq.inria.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository studies a narrow question: when multiple LLM agents disagree
about a claim that is formalizable, can the system resolve that disagreement by
proof instead of by debate?

The current answer is narrower and more interesting than "we built theorem-
proving agents." On an easy internal benchmark, deterministic canonicalization
plus the proof stack saturate the formalizable slice once Coq is available
locally. On a harder paraphrase stress benchmark, provider-backed extraction
adds real lift beyond deterministic rules, but only reaches 70.6% exact
canonicalization and 70.6% end-to-end decisive accuracy on formalizable cases,
with both false negatives and silent semantic drift. The honest result is that
easy extraction is solved here, while harder paraphrase handling is still the
limiting factor.

## Current Result Snapshot

Study date: 2026-04-07

Primary artifact paths:
- `research/run_study.py`
- `research/benchmarks/formal_verification_benchmark.json`
- `research/benchmarks/extraction_benchmark.json`
- `research/benchmarks/extraction_paraphrase_stress_benchmark.json`
- `research/results/study_results.json`
- `research/results/study_summary.md`
- `reports/cognitive_dissonance_research_report.tex`

Experimental setup:
- Local Python environment: 3.12.8
- SMT backend: `z3-solver`
- Coq local availability during the study: `coqc` and `coqchk` available
- Live extraction provider: OpenRouter-compatible endpoint
- Model used for the live extraction arm: `openai/gpt-4.1-mini`
- Extraction temperature: `0.0`

### Formal Verification Benchmark

Curated symbolic benchmark: 45 cases across arithmetic, multiplication,
subtraction, factorial, Fibonacci, GCD, inequalities, implication, universal
quantification, and existential quantification.

| Condition | Decisive Coverage | Overall Decisive Accuracy | Machine-Checked Cases | Mean Proof Time |
| --- | ---: | ---: | ---: | ---: |
| Hybrid + necessity | 100.0% | 100.0% | 13 | 133.4 ms |
| Hybrid without necessity | 100.0% | 100.0% | 13 | 133.3 ms |

Interpretation:
- The expanded symbolic benchmark is fully decisive in both conditions.
- Thirteen positive cases are machine-checked locally.
- Necessity still does not separate the two conditions on this suite, which
  means the benchmark is no longer useful for that ablation.

### Main Extraction Benchmark

Curated natural-language benchmark: 35 cases total.
- 27 formalizable cases
- 8 unformalizable subjective controls

| Metric | Result |
| --- | ---: |
| Direct translator success on formalizable NL claims | 22.2% |
| Extractor formalizability accuracy | 100.0% |
| Extractor exact canonical match on formalizable claims | 100.0% |
| Translation success after extraction | 100.0% |
| End-to-end decisive proof coverage after extraction | 100.0% |
| End-to-end decisive accuracy after extraction | 100.0% |
| Machine-checked formalizable cases after extraction | 7 |
| Formalizable cases handled by deterministic fast-path normalization | 27 |
| Formalizable cases requiring provider extraction | 0 |
| Mean extraction latency | 476.5 ms/case |

Interpretation:
- Direct translation still fails on most raw natural-language formalizable
  claims: only 6 of 27 succeed without structured extraction.
- Every formalizable benchmark case is now canonicalized deterministically into
  translator-compatible form before any provider call.
- The provider is still used for the 8 unformalizable controls, which it
  rejected correctly on this run.
- The decisive evidence mix on the formalizable slice is 7 `machine_checked`,
  7 `smt_proved`, and 13 `refuted`.

### Paraphrase Stress Benchmark

Harder natural-language paraphrase benchmark: 19 cases total.
- 17 formalizable cases written to defeat the repository's deterministic
  fast-path rules
- 2 unformalizable subjective controls

| Metric | Deterministic Only | Provider Enabled |
| --- | ---: | ---: |
| Direct translator success on formalizable NL claims | 5.9% | 5.9% |
| Extractor formalizability accuracy | 10.5% | 78.9% |
| Extractor category accuracy on formalizable claims | 0.0% | 76.5% |
| Exact canonical match on formalizable claims | 0.0% | 70.6% |
| Translation success after extraction | 0.0% | 76.5% |
| End-to-end decisive proof coverage | 0.0% | 76.5% |
| End-to-end decisive accuracy | 0.0% | 70.6% |
| Machine-checked formalizable cases | 0 | 3 |
| Mean extraction latency | 0.03 ms/case | 2998.2 ms/case |

Interpretation:
- This benchmark is the first one in the repository where the provider is doing
  essential extraction work rather than just triaging subjective controls.
- Provider-backed extraction adds large lift over deterministic-only routing,
  but it still misses 4 of the 17 clearly formalizable claims.
- It also silently rewrites at least one false claim into a different true
  canonical claim, so exact-match auditing is mandatory.

### Stability And Failure Probe

Repeated extraction on 6 representative cases over 2 trials per case:
- Stable case rate: 100.0%

The checked cases covered:
- arithmetic true claim
- factorial base-case claim
- inequality false claim
- implication false claim
- existential true claim
- unformalizable subjective claim

Repeated extraction on 5 hard paraphrase failures over 10 trials per case:
- Stable case rate: 80.0%
- One false arithmetic paraphrase flips between correct extraction and
  rejection even at temperature 0.0.
- Another false arithmetic paraphrase is stable but wrong: it is consistently
  rewritten into a different true subtraction fact.
- Three quantified or implication paraphrases are stable false negatives.

## Main Conclusions

1. The easy internal extraction benchmark is no longer informative about
   provider extraction. Deterministic canonicalization solves all 27
   formalizable cases before any provider call.
2. The harder paraphrase stress benchmark is the real signal. There, provider
   extraction improves exact canonicalization from 0.0% to 70.6% and decisive
   coverage from 0.0% to 76.5%.
3. Provider lift is real, but reliability is not good enough to trust
   unaudited. The current stress run includes 4 formalizable false negatives,
   1 semantic-drift case, and 1 decisive error caused by silent correction.
4. On canonical claims, the proof stack is strong. With Coq installed locally,
   the symbolic benchmark is 45/45 decisive and the easy formalizable
   natural-language slice is 27/27 decisive.
5. Evidence typing still matters. The system distinguishes `machine_checked`,
   `smt_proved`, `refuted`, and weaker statuses instead of flattening
   everything into "proved."

## What This Repository Currently Does Well

- Detects formalizable conflicts between agent claims.
- Canonicalizes obvious mathematical and logical claims deterministically.
- Separates proof outcomes into explicit evidence-strength categories.
- Uses `coqchk` before labeling a Coq proof as machine-checked.
- Integrates Z3, Coq, necessity-based proving, proof repair, caching, and CI.
- Provides a reproducible study harness rather than only narrative examples.

## What Is Still Limited

- The benchmark suite is still small and repository-authored. These results are
  useful, but they are not claims about open-domain performance.
- The main extraction benchmark is now too aligned with repository rules to say
  much about model-driven extraction.
- The harder paraphrase benchmark is still small. It shows the right failure
  modes, but it is not yet broad enough to support a strong novelty claim.
- Only 7 of the 27 decisive easy-suite extraction cases and 3 of the 17 stress
  cases are `machine_checked`; the rest are solver-backed proofs or decisive
  refutations.
- Provider-backed extraction can silently rewrite false claims into different
  true ones, which means exact-match auditing is not optional.
- The next missing work is broader paraphrase coverage, comparative baselines,
  and calibration-oriented evaluation of evidence-status reporting.

## Reproducing The Study

### Local benchmark only

```bash
.venv/bin/python research/run_study.py
```

### Live OpenAI-compatible extraction benchmark

```bash
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export OPENAI_MODEL=openai/gpt-4.1-mini
export OPENAI_APP_NAME="EvalOps Research"
export OPENAI_SITE_URL=https://evalops.dev

.venv/bin/python research/run_study.py \
  --model "$OPENAI_MODEL" \
  --temperature 0.0 \
  --stability-trials 2 \
  --stress-trials 10
```

### Tests

```bash
.venv/bin/python -m pytest -q
```

### Report build

```bash
tectonic --outdir reports reports/cognitive_dissonance_research_report.tex
```

## Proof Statuses Matter

This project intentionally does not treat all successes as equivalent.

- `machine_checked`: independently checked proof object
- `smt_proved`: decisive SMT-backed result
- `derived_proved`: structured or necessity-derived support, not decisive ground truth
- `smt_refuted`: decisive solver-backed refutation
- `derived_refuted`: structured refutation, not machine-checked
- `inconclusive`: no trustworthy deterministic result

That distinction is the core epistemic claim of this repository: a proof-shaped
artifact is not the same thing as ground truth.

## Repository Layout

```text
cognitive_dissonance/
  mathematical_resolver.py   orchestration between agent outputs and proof results

formal_verification/
  detector.py                conflict analysis and proof orchestration
  openai_agents.py           structured extraction and canonicalization
  necessity_prover.py        necessity-first proof construction
  prover.py                  Coq interface and coqchk validation
  translator.py              claim-to-spec translation
  types.py                   normalized proof status model
  z3_prover.py               SMT-backed proving and hybrid routing

research/
  benchmarks/                curated study datasets
  results/                   generated study artifacts
  run_study.py               empirical study harness
```

## Read The Full Report

The research report and PDF are in `reports/`:
- `reports/cognitive_dissonance_research_report.tex`
- `reports/cognitive_dissonance_research_report.pdf`

## License

MIT
