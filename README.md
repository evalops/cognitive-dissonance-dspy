# Cognitive Dissonance DSPy

[![Requirements: Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-Compatible-green.svg)](https://github.com/stanfordnlp/dspy)
[![Coq](https://img.shields.io/badge/Coq-8.18+-orange.svg)](https://coq.inria.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository studies a specific question: when multiple LLM agents disagree
about a claim that is formalizable, can the system resolve that disagreement by
proof instead of by debate?

On the current internal benchmark, the answer is "yes." Once Coq is available
locally, the extraction and verification pipeline reaches full decisive
coverage on the curated suite. The important caveat is that the benchmark is
small and repository-authored, so the remaining research problem is breadth and
external validity, not benchmark accuracy on this suite.

## Current Result Snapshot

Study date: 2026-04-07

Primary artifact paths:
- `research/run_study.py`
- `research/benchmarks/formal_verification_benchmark.json`
- `research/benchmarks/extraction_benchmark.json`
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

Curated symbolic benchmark: 16 cases across arithmetic, multiplication,
subtraction, factorial, Fibonacci, GCD, and inequalities.

| Condition | Decisive Coverage | Overall Decisive Accuracy | Machine-Checked Cases | Mean Proof Time |
| --- | ---: | ---: | ---: | ---: |
| Hybrid + necessity | 100.0% | 100.0% | 3 | 154.0 ms |
| Hybrid without necessity | 100.0% | 100.0% | 3 | 154.0 ms |

Interpretation:
- On this Coq-enabled local run, the symbolic benchmark is fully decisive.
- Three positive cases are machine-checked locally: `factorial`, `fibonacci`,
  and `gcd`.
- Necessity does not improve headline accuracy on this suite once Coq is
  available, because both conditions already saturate the benchmark.

### Extraction Benchmark

Curated natural-language benchmark: 16 cases total.
- 12 formalizable cases
- 4 unformalizable control cases

| Metric | Result |
| --- | ---: |
| Direct translator success on formalizable NL claims | 25.0% |
| Extractor formalizability accuracy | 100.0% |
| Extractor exact canonical match on formalizable claims | 100.0% |
| Translation success after extraction | 100.0% |
| End-to-end decisive proof coverage after extraction | 100.0% |
| End-to-end decisive accuracy after extraction | 100.0% |
| Machine-checked formalizable cases after extraction | 6 |
| Mean extraction latency | 2747 ms/case |

Interpretation:
- The extraction pipeline now solves the normalization problem on the curated
  benchmark.
- With Coq available locally, the extraction-plus-proof pipeline is decisive on
  all 12 formalizable natural-language cases in the suite.
- The evidence mix still matters: 6 of those 12 formalizable cases are
  machine-checked, 3 are `smt_proved`, and 3 are decisive refutations that are
  not machine-checked.

### Stability Check

Repeated extraction on 4 representative cases over 2 trials per case:
- Stable case rate: 100.0%

The checked cases covered:
- arithmetic true claim
- factorial true claim
- implication claim
- unformalizable subjective claim

## Main Conclusions

1. Extraction is no longer the primary problem on the current internal study.
   The OpenAI-compatible extraction pipeline plus deterministic canonicalization
   maps all 12 formalizable natural-language cases into translator-compatible
   canonical forms.
2. On the current internal benchmark, the full pipeline is now decisive after
   Coq installation: symbolic verification is 16/16 decisive and the
   formalizable natural-language slice is 12/12 decisive.
3. Necessity is neutral on the headline metrics for this benchmark once Coq is
   available, which suggests the next useful ablations need harder claims than
   the current suite.
4. The proof-status model is still doing the right thing. The system clearly
   distinguishes SMT-proved, derived, machine-checked, and inconclusive
   outcomes instead of flattening them into "proved."

## What This Repository Currently Does Well

- Detects formalizable conflicts between agent claims.
- Normalizes proof outcomes into explicit evidence-strength categories.
- Uses `coqchk` before labeling a Coq proof as machine-checked.
- Integrates Z3, Coq, necessity-based proving, proof repair, caching, and CI.
- Provides a reproducible study harness rather than only narrative examples.

## What Is Still Limited

- The benchmark suite is small and curated. These numbers are useful, but they
  are not claims about open-domain performance.
- The current benchmark is likely close to the repository's comfort zone after
  targeted iteration, so it is no longer a strong stress test.
- Only part of the decisive evidence is machine-checked. On the extraction
  suite, the formalizable slice resolves via a mix of `machine_checked`,
  `smt_proved`, and `refuted`.
- The semantic bridge for subjective claims remains heuristic.

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
  --stability-trials 2
```

### Tests

```bash
.venv/bin/python -m pytest -q
```

Current local result with Coq installed: `248 passed, 1 skipped`

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

That distinction is the core research claim of this repository: a proof-shaped
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
