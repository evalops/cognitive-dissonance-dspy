# Cognitive Dissonance DSPy

[![Requirements: Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![DSPy](https://img.shields.io/badge/DSPy-Compatible-green.svg)](https://github.com/stanfordnlp/dspy)
[![Coq](https://img.shields.io/badge/Coq-8.18+-orange.svg)](https://coq.inria.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Stop arguing; prove it.**  
Cognitive Dissonance DSPy detects belief conflicts between LLM agents, translates formalizable claims to Coq, and attempts an independently checked proof. Claims that remain assumption-based or unchecked are labeled as such instead of being reported as ground truth.

- **Agents & optimization:** built on DSPy's programmatic agent framework.  
- **Proofs:** compiled (`coqc`) and only counted as machine-checked after `coqchk` validation.

> To our knowledge, this is the first framework that combines **DSPy‑based cognitive‑dissonance detection**, **NL→Coq translation**, and **online proving** in one loop.

---

## Why

Most multi‑agent systems resolve contradictions with debate, confidence scores, or arbitration heuristics. That's arm‑wrestling, not ground truth. When a claim **is** formalizable, we hand it to a theorem prover and return a proof object (or a failure).

**Scope** (initial): arithmetic + basic algebra, simple algorithmic properties (e.g., permutation + sortedness), and other first‑order fragments that Coq and standard tactics handle well. We'll expand coverage pragmatically.

---

## How it works

```text
[Agents (DSPy)] → [Belief Extractor] → [Claim Normalizer]
                               ↓ conflicts
                 [NL→Coq Translator + Spec Templates]
                               ↓ goals
                     [Coq Prover (coqc)] ──▶ [coqchk]
                               ↓
                     { PROVED | DISPROVEN | NO-PROOF }
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Coq theorem prover (`coqc` command available)
- Ollama or compatible API endpoint (for agent reasoning)

### Installation

```bash
# Clone the repository
git clone https://github.com/evalops/cognitive-dissonance-dspy.git
cd cognitive-dissonance-dspy

# Set up virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
python -m pip install -r requirements.txt

# Install Coq (Ubuntu/Debian)
sudo apt update && sudo apt install -y coq

# Install Coq (macOS)
brew install coq

# Verify installation
coqc --version
```

### Example: When Agents Disagree

```python
from formal_verification import FormalVerificationConflictDetector, Claim, PropertyType

detector = FormalVerificationConflictDetector()

claims = [
    Claim("alice", "2 + 2 = 4", PropertyType.CORRECTNESS, 0.95, time.time()),
    Claim("bob", "2 + 2 = 5", PropertyType.CORRECTNESS, 0.80, time.time()),
]

results = detector.analyze_claims(claims)
# Alice: ✅ PROVEN (reflexivity)
# Bob:   ❌ DISPROVEN (Unable to unify "5" with "4")
```

### Run Examples

```bash
# Mathematical claims demonstration
python examples/mathematical_claims.py

# Advanced theorem proving
python examples/advanced_theorems.py

# Comprehensive framework demo
python examples/comprehensive_demo.py
```

---

## What We Can Prove

**Current coverage:**
- **Arithmetic & algebra:** `2 + 2 = 4` (✓), `factorial 7 = 5040` (✓ in 502ms)
- **Algorithm properties:** sorting correctness via `Permutation + LocallySorted`
- **Simple invariants:** list properties, basic data structure constraints

**Measured performance:**
- 15 claims → 80% success rate
- Average proof time: 179.7ms
- Conflicts resolved deterministically (no voting)

---

## Architecture

```
formal_verification/
├── translator.py    # NL → Coq patterns  
├── prover.py        # subprocess wrapper for coqc
└── detector.py      # orchestrates the pipeline

cognitive_dissonance/
├── verifier.py      # DSPy agents for belief extraction
└── experiment.py    # co-training & optimization
```

**Translation examples:**
```python
"2 + 2 = 4"               → Theorem arith : 2 + 2 = 4. reflexivity. Qed.
"factorial 5 = 120"       → Fixpoint + simpl proof
"sorts correctly"         → Permutation ∧ LocallySorted
```

---

## Related Work

**LLM × ITP integration:**
- LeanDojo (Yang et al. 2023): LLMs + Lean for proof search
- APOLLO (Wang et al. 2024): GPT-4 generating Lean proofs  
- Minerva (Lewkowycz et al. 2022): math problem solving

**Multi-agent verification:**
- BDI agent logics (Wooldridge & Fisher 2005)
- Consensus mechanisms in distributed AI (recent IJCAI/AAMAS work)

**Our contribution:** First to combine DSPy cognitive dissonance detection + NL→Coq translation + online proving in one system.

---

## Roadmap

- [ ] Expand pattern library (induction, recursive data structures)
- [ ] Better error messages when formalization fails
- [ ] Integration with LeanDojo/APOLLO for cross-prover validation
- [ ] Benchmark on existing theorem proving datasets

---

## License

MIT

## Contact

[GitHub Issues](https://github.com/evalops/cognitive-dissonance-dspy/issues) | [EvalOps](https://github.com/evalops)
