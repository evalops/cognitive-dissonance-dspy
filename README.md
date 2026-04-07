# Cognitive Dissonance DSPy

[![Requirements: Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-Compatible-green.svg)](https://github.com/stanfordnlp/dspy)
[![Coq/Rocq](https://img.shields.io/badge/Coq%2FRocq-required-orange.svg)](https://coq.inria.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository accompanies the manuscript:

**Exact-Match Auditing for Proof-First Conflict Resolution**

The paper studies a narrow problem: how should a system evaluate and resolve
formalizable claim disagreements when proof is available as a resolution
mechanism? The central claim is not that large language models broadly solve
disagreement through theorem proving. The central claim is methodological:

> Proof-first conflict resolution should be evaluated by separating
> deterministic canonicalization, provider-assisted extraction, proof outcome,
> and evidence strength. Exact-match auditing is necessary because provider
> lift on hard paraphrases comes with silent-correction risk.

All reported results presume a correctly configured Coq/Rocq environment. Runs
without `coqc` and `coqchk` are treated as setup failures, not as meaningful
experimental conditions.

## Research Claim

The paper contributes an evaluation decomposition with four distinct layers:

1. deterministic canonicalization
2. provider-assisted extraction
3. proof outcome
4. evidence strength

This separation matters because downstream proof success is not a reliable
proxy for extraction fidelity. A system can prove the wrong proposition if the
extraction layer silently rewrites the original claim.

This should be read as a methods paper with a narrow empirical stress test, not
as a broad systems paper.

## Headline Results

Artifacts reported here were generated on 2026-04-07 from `56d718c-dirty`.

### Symbolic proof baseline

The 45-case symbolic benchmark is fully decisive under the required
Coq/Rocq-backed environment.

| Condition | Decisive Coverage | Decisive Accuracy | Machine-Checked Cases |
| --- | ---: | ---: | ---: |
| Hybrid + necessity | 100.0% | 100.0% | 13 |
| Hybrid without necessity | 100.0% | 100.0% | 13 |

This means:

- the proof stack is strong on canonical symbolic claims
- the necessity ablation is neutral on this benchmark
- necessity should not be positioned as the paper’s main novelty

### Easy extraction benchmark

The 35-case main natural-language benchmark contains 27 formalizable cases and
8 unformalizable controls.

| Metric | Result |
| --- | ---: |
| Direct translator success on formalizable claims | 22.2% |
| Exact canonical match | 100.0% |
| End-to-end decisive coverage | 100.0% |
| End-to-end decisive accuracy | 100.0% |
| Formalizable cases handled by deterministic canonicalization | 27 |
| Formalizable cases requiring provider extraction | 0 |

This benchmark remains useful as a calibration baseline. It does not carry the
main extraction claim, because every formalizable case is solved before any
provider call.

### Hard paraphrase benchmark

The 19-case paraphrase stress benchmark contains 17 formalizable paraphrases
designed to evade deterministic rules and 2 unformalizable controls.

| Metric | Deterministic Only | Provider Enabled |
| --- | ---: | ---: |
| Exact canonical match | 0.0% | 70.6% |
| Translation success after extraction | 0.0% | 76.5% |
| End-to-end decisive coverage | 0.0% | 76.5% |
| End-to-end decisive accuracy | 0.0% | 70.6% |
| Machine-checked formalizable cases | 0 | 3 |

This is the benchmark that carries the paper’s main empirical result:

- provider-assisted extraction adds real lift on hard paraphrases
- that lift is incomplete
- the same provider path can silently rewrite a false claim into a different
  true canonical claim

### Negative result: silent correction

Under provider-assisted extraction on the hard paraphrase benchmark:

| Failure Mode | Count |
| --- | ---: |
| Formalizable false negatives | 4 |
| Semantic-drift cases | 1 |
| Decisive errors caused by semantic drift | 1 |

The 10-trial hard-failure probe shows that some failures are unstable and some
are stably wrong. This is why exact-match auditing is central to the paper.

## Positioning Against Prior Work

The manuscript is positioned relative to four research threads:

- autoformalization and formal math benchmarks such as Autoformalization with
  Large Language Models, ProofNet, Autoformalization in the Wild, and
  ProofNetVerif
- theorem-proving systems and environments such as LeanDojo, BFS-Prover,
  FormalMATH, and DeepSeek-Prover-V2
- debate-based disagreement resolution such as Multi-Agent Debate
- hybrid faithfulness-oriented LLM-theorem-proving systems such as Faithful and
  Robust LLM-Driven Theorem Proving for NLI Explanations

The manuscript’s niche is narrower than theorem-proving state of the art. It
focuses on evaluation discipline under extraction uncertainty.

## What This Work Claims

- proof-first routing is viable on correctly canonicalized formalizable claims
- extraction fidelity and proof success are different capabilities
- evidence strength should remain typed rather than flattened into a generic
  “proved” label
- exact-match auditing is necessary for honest evaluation on hard paraphrases

## What This Work Does Not Claim

- that LLM systems broadly resolve disagreement through proof
- that the current benchmarks justify open-domain performance claims
- that necessity-enhanced reasoning is the main contribution
- that provider extraction is reliable on unrestricted paraphrase variation

## Manuscript And Artifacts

Primary manuscript files:

- `reports/cognitive_dissonance_research_report.tex`
- `reports/cognitive_dissonance_research_report.pdf`

Primary study artifacts:

- `research/run_study.py`
- `research/benchmarks/formal_verification_benchmark.json`
- `research/benchmarks/extraction_benchmark.json`
- `research/benchmarks/extraction_paraphrase_stress_benchmark.json`
- `research/results/study_results.json`
- `research/results/study_summary.md`

## Reproducing The Study

### Local benchmark run

```bash
.venv/bin/python research/run_study.py
```

`research/run_study.py` now fails fast if `coqc` or `coqchk` is missing.

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

### Build the manuscript PDF

```bash
tectonic --outdir reports reports/cognitive_dissonance_research_report.tex
```

## Repository Layout

```text
cognitive_dissonance/
  mathematical_resolver.py   orchestrates agent outputs and proof results

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

## License

MIT
