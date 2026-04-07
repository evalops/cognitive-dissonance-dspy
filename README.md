# Cognitive Dissonance DSPy

[![Requirements: Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-Compatible-green.svg)](https://github.com/stanfordnlp/dspy)
[![Coq](https://img.shields.io/badge/Coq-8.18+-orange.svg)](https://coq.inria.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Cognitive Dissonance DSPy is a proof-first conflict-resolution framework for
formalizable agent disagreements. The main contribution is not a claim that
LLMs broadly solve disagreement through theorem proving. The contribution is an
evaluation framework that cleanly separates:

1. deterministic canonicalization
2. provider-assisted extraction
3. proof outcome
4. evidence strength

That separation matters because the current experiments show both sides of the
story:

- once a claim is correctly canonicalized, the proof stack is strong
- provider-assisted extraction helps on hard paraphrases
- provider-assisted extraction can also silently rewrite false claims into
  different true canonical claims

The central methodological claim is therefore:

> Proof-first conflict resolution should be evaluated with exact-match auditing
> and explicit evidence typing, because extraction lift and proof strength are
> different capabilities and they fail in different ways.

## Thesis

This project argues for a specific evaluation discipline for proof-first
conflict resolution:

- do not collapse canonicalization, extraction, proof, and evidence strength
  into one headline number
- treat exact canonical match as a first-class metric
- distinguish `machine_checked`, `smt_proved`, `refuted`, and weaker derived
  statuses
- evaluate hard paraphrases separately from canonical or rule-aligned cases

The current empirical result is narrower than a generic theorem-proving claim:

- canonical internal cases are largely solved once Coq is available locally
- hard paraphrases still expose brittle extraction behavior
- exact-match auditing is necessary because silent semantic drift is a live
  failure mode

## Main Findings

Study artifacts reported here were generated on 2026-04-07 from
`56d718c-dirty`. The paper-style report is in `reports/`, and the generated
study artifacts are in `research/results/`.

### 1. Canonical claims are no longer the bottleneck

The symbolic benchmark contains 45 claims across arithmetic, multiplication,
subtraction, factorial, Fibonacci, GCD, inequalities, implication, universal
quantification, and existential quantification.

| Condition | Decisive Coverage | Decisive Accuracy | Machine-Checked Cases | Mean Proof Time |
| --- | ---: | ---: | ---: | ---: |
| Hybrid + necessity | 100.0% | 100.0% | 13 | 133.4 ms |
| Hybrid without necessity | 100.0% | 100.0% | 13 | 133.3 ms |

Implication:

- the proof stack is strong on canonical symbolic claims
- the necessity ablation no longer separates conditions on this benchmark
- necessity should be treated as a secondary ablation result, not the paper’s
  main novelty angle

### 2. The easy extraction benchmark is a calibration baseline

The main natural-language benchmark contains 35 cases:

- 27 formalizable claims
- 8 unformalizable controls

| Metric | Result |
| --- | ---: |
| Direct translator success on formalizable claims | 22.2% |
| Formalizability accuracy | 100.0% |
| Exact canonical match | 100.0% |
| Translation success after extraction | 100.0% |
| End-to-end decisive coverage | 100.0% |
| End-to-end decisive accuracy | 100.0% |
| Machine-checked formalizable cases | 7 |
| Formalizable cases handled by deterministic canonicalization | 27 |
| Formalizable cases requiring provider extraction | 0 |
| Mean extraction latency | 476.5 ms/case |

Implication:

- this benchmark still demonstrates that raw NL translation is weak
- it no longer demonstrates provider extraction strength
- all 27 formalizable cases are solved before any provider call

### 3. The hard paraphrase benchmark is the real extraction result

The paraphrase stress benchmark contains 19 cases:

- 17 formalizable claims intentionally written to evade deterministic rules
- 2 unformalizable controls

| Metric | Deterministic Only | Provider Enabled |
| --- | ---: | ---: |
| Direct translator success | 5.9% | 5.9% |
| Formalizability accuracy | 10.5% | 78.9% |
| Category accuracy | 0.0% | 76.5% |
| Exact canonical match | 0.0% | 70.6% |
| Translation success after extraction | 0.0% | 76.5% |
| End-to-end decisive coverage | 0.0% | 76.5% |
| End-to-end decisive accuracy | 0.0% | 70.6% |
| Machine-checked formalizable cases | 0 | 3 |
| Mean extraction latency | 0.03 ms/case | 2998.2 ms/case |

This is the benchmark that carries the main empirical claim:

- provider-assisted extraction adds real lift on hard paraphrases
- that lift is incomplete
- the provider cannot be trusted without literal-match auditing

### 4. Silent correction is the key negative result

On the hard paraphrase benchmark, provider extraction also shows:

| Failure Mode | Count |
| --- | ---: |
| Formalizable false negatives | 4 |
| Semantic-drift cases | 1 |
| Decisive errors caused by semantic drift | 1 |

The stress failure probe repeats 5 hard cases over 10 trials per case:

- stable-case rate: 80.0%
- one false arithmetic paraphrase flips between correct extraction and
  rejection
- one false subtraction paraphrase is stable but wrong, consistently rewritten
  into a different true fact
- quantified and implication paraphrases are stable false negatives

This is the reason exact-match auditing is central to the paper framing. High
downstream proof accuracy is not sufficient if the extracted claim is not the
claim that was asked.

## What The System Contributes

This project should be read as a systems-and-evaluation artifact with four
concrete contributions:

1. A proof-first routing pipeline for formalizable disagreements.
2. An evaluation decomposition that separates deterministic normalization,
   provider extraction, proof success, and evidence strength.
3. An exact-match audit layer that detects silent semantic drift rather than
   rewarding it.
4. A typed evidence model that keeps `machine_checked`, solver-backed, and
   weaker derived support distinct.

## What The Results Do Not Claim

The current results do not justify the following claims:

- that multi-agent LLMs broadly resolve disagreement through proof
- that necessity-enhanced reasoning is the main novelty here
- that provider extraction is reliable on open-ended paraphrase variation
- that these internal benchmarks measure open-domain performance

## Why Evidence Typing Matters

The system intentionally distinguishes:

- `machine_checked`
- `smt_proved`
- `refuted`
- `smt_refuted`
- `derived_proved`
- `derived_refuted`
- `inconclusive`

That distinction is part of the contribution. A proof-shaped artifact is not
the same thing as decisive ground truth, and the evaluation should not pretend
otherwise.

## Reproducing The Study

Primary artifacts:

- `research/run_study.py`
- `research/benchmarks/formal_verification_benchmark.json`
- `research/benchmarks/extraction_benchmark.json`
- `research/benchmarks/extraction_paraphrase_stress_benchmark.json`
- `research/results/study_results.json`
- `research/results/study_summary.md`
- `reports/cognitive_dissonance_research_report.tex`

### Local study run

```bash
.venv/bin/python research/run_study.py
```

### Live provider-backed extraction run

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

### Test suite

```bash
.venv/bin/python -m pytest -q
```

### Report build

```bash
tectonic --outdir reports reports/cognitive_dissonance_research_report.tex
```

## Code Layout

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
  benchmarks/                study datasets
  results/                   generated artifacts
  run_study.py               empirical evaluation harness

reports/
  cognitive_dissonance_research_report.tex
  cognitive_dissonance_research_report.pdf
```

## Recommended Paper Framing

If this work is written up as a paper, the most defensible headline is:

> We present an evaluation framework for proof-first conflict resolution that
> separates canonicalization, provider-assisted extraction, proof strength, and
> evidence strength, and we show that exact-match auditing is necessary because
> provider lift on hard paraphrases comes with silent-correction risk.

## License

MIT
