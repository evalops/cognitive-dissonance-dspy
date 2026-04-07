# Research Study Summary

- Source revision: `56d718c-dirty`
- Generated: `2026-04-07T20:58:39Z`

## Questions

1. Does necessity-enhanced hybrid verification improve symbolic claim performance?
2. Does structured extraction and canonicalization improve translation success over direct pattern matching?
3. How much end-to-end proof coverage remains after successful extraction on the easy suite?
4. On the easy benchmark, how much of the extraction result truly depends on the provider rather than deterministic canonicalization?
5. On paraphrases that defeat deterministic rules, how much lift does provider-backed extraction add and what failure modes remain?

## Formal Verification Benchmark

- Cases: `45`
- Hybrid + necessity: decisive coverage `100.0%`, overall decisive accuracy `100.0%`, optimistic accuracy `100.0%`, machine-checked cases `13`, mean proof time `133.4 ms`
- Hybrid without necessity: decisive coverage `100.0%`, overall decisive accuracy `100.0%`, optimistic accuracy `100.0%`, machine-checked cases `13`, mean proof time `133.4 ms`

## Extraction Benchmark

- Cases: `35`
- Direct translator success on formalizable natural-language claims: `22.2%`
- Extractor formalizability accuracy: `100.0%`
- Extractor exact canonical match on formalizable claims: `100.0%`
- Translation success after extraction on formalizable claims: `100.0%`
- End-to-end decisive proof coverage after extraction: `100.0%`
- End-to-end decisive accuracy after extraction: `100.0%`
- Machine-checked formalizable cases after extraction: `7`
- Formalizable cases handled by deterministic fast-path normalization: `27`
- Formalizable cases requiring provider extraction: `0`
- Formalizable cases corrected back to the literal claim after provider output: `0`
- Mean extraction latency across all cases: `476.5 ms`

## Paraphrase Stress Benchmark

- Cases: `19`
- Deterministic-only exact canonical match on formalizable claims: `0.0%`
- Provider exact canonical match on formalizable claims: `70.6%`
- Provider end-to-end decisive accuracy on formalizable claims: `70.6%`
- Provider end-to-end decisive coverage on formalizable claims: `76.5%`
- Provider formalizable false negatives: `4`
- Provider semantic-drift cases: `1`
- Provider semantic-drift decisive errors: `1`

## Stability Check

- Stable case rate across `2` trials: `100.0%`

## Stress Failure Probe

- Stable case rate across `10` trials: `80.0%`

## Interpretation

- The symbolic benchmark quantifies what the current formal verification stack can already resolve decisively.
- The extraction benchmark isolates whether structured extraction and canonicalization actually expand proof-ready coverage.
- On the current internal benchmark, extraction and decisive verification both saturate; the main remaining limitation is benchmark breadth rather than measured pipeline accuracy.
- Most formalizable benchmark cases now resolve through deterministic canonicalization before any provider call, so the main provider contribution on this suite is unformalizable triage rather than core normalization.
- The paraphrase stress slice shows that provider-backed extraction does add coverage beyond deterministic rules, but it still misses some clearly formalizable logic paraphrases.
- Provider-backed extraction adds real lift on the harder paraphrase slice, but it does not saturate that benchmark.
- More importantly, the provider can silently rewrite false claims into true canonical forms. Exact-match tracking is therefore necessary, not optional.
- The hardest stress failures are not all stable. At least one false arithmetic paraphrase flips between correct extraction and rejection across repeated temperature-0 runs.
