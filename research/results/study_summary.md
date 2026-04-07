# Research Study Summary

- Source revision: `d11d492-dirty`
- Generated: `2026-04-07T18:16:55Z`

## Questions

1. Does necessity-enhanced hybrid verification improve symbolic claim performance?
2. Does structured OpenAI-compatible extraction improve translation success over direct pattern matching?
3. How much end-to-end proof coverage remains after successful extraction?

## Formal Verification Benchmark

- Cases: `16`
- Hybrid + necessity: decisive coverage `100.0%`, overall decisive accuracy `100.0%`, optimistic accuracy `100.0%`, machine-checked cases `3`, mean proof time `154.0 ms`
- Hybrid without necessity: decisive coverage `100.0%`, overall decisive accuracy `100.0%`, optimistic accuracy `100.0%`, machine-checked cases `3`, mean proof time `154.0 ms`

## Extraction Benchmark

- Cases: `16`
- Direct translator success on formalizable natural-language claims: `25.0%`
- Extractor formalizability accuracy: `100.0%`
- Extractor exact canonical match on formalizable claims: `100.0%`
- Translation success after extraction on formalizable claims: `100.0%`
- End-to-end decisive proof coverage after extraction: `100.0%`
- End-to-end decisive accuracy after extraction: `100.0%`
- Machine-checked formalizable cases after extraction: `6`

## Stability Check

- Stable case rate across `2` trials: `100.0%`

## Interpretation

- The symbolic benchmark quantifies what the current formal verification stack can already resolve decisively.
- The extraction benchmark isolates whether provider-backed normalization actually expands proof-ready coverage.
- On the current internal benchmark, extraction and decisive verification both saturate; the main remaining limitation is benchmark breadth rather than measured pipeline accuracy.
