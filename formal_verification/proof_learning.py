"""Foundational proof strategy learning system.

This module implements deep learning for proof strategies, moving beyond
simple heuristics to understand proof complexity, success patterns, and
optimal prover selection based on mathematical structure.
"""

import hashlib
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .types import Claim, ProofResult

logger = logging.getLogger(__name__)
DEFAULT_PROOF_LEARNING_DATA_FILE = Path(".proof_cache") / "proof_learning_data.json"
PROOF_LEARNING_SCHEMA_VERSION = 1


@dataclass
class ProofFeatures:
    """Mathematical and structural features of a proof attempt."""
    # Syntactic features
    claim_length: int
    mathematical_operators: int  # +, -, *, /, ^
    logical_operators: int       # forall, exists, implies, and, or
    quantifier_depth: int        # nested quantifiers
    variable_count: int
    constant_count: int
    
    # Semantic features  
    proof_type: str             # arithmetic, inductive, logical, constraint
    complexity_class: str       # linear, exponential, polynomial, etc.
    mathematical_domain: str    # number_theory, algebra, logic, etc.
    
    # Contextual features
    code_complexity: float      # cyclomatic complexity if code present
    previous_success_rate: float # historical success for similar claims
    
    # Structural features
    ast_depth: int              # AST depth of claim
    pattern_similarity: float   # similarity to proven claims
    
    def to_vector(self) -> np.ndarray:
        """Convert to feature vector for ML models."""
        return np.array([
            self.claim_length,
            self.mathematical_operators,
            self.logical_operators, 
            self.quantifier_depth,
            self.variable_count,
            self.constant_count,
            hash(self.proof_type) % 1000,  # categorical encoding
            hash(self.complexity_class) % 1000,
            hash(self.mathematical_domain) % 1000,
            self.code_complexity,
            self.previous_success_rate,
            self.ast_depth,
            self.pattern_similarity
        ])


@dataclass
class ProofAttempt:
    """Record of a proof attempt with features and outcome."""
    claim_text: str
    features: ProofFeatures
    prover_used: str
    success: bool
    time_ms: float
    error_type: Optional[str]
    timestamp: float
    
    def get_fingerprint(self) -> str:
        """Get unique fingerprint for this proof attempt."""
        content = f"{self.claim_text}_{self.prover_used}_{self.features.proof_type}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class FeatureExtractor:
    """Extracts mathematical and structural features from claims."""
    
    def __init__(self):
        self.mathematical_patterns = {
            'arithmetic': [r'\+', r'-', r'\*', r'/', r'='],
            'algebra': [r'\^', r'sqrt', r'log', r'exp'],
            'number_theory': [r'prime', r'gcd', r'lcm', r'mod'],
            'analysis': [r'limit', r'derivative', r'integral', r'continuous'],
            'logic': [r'forall', r'exists', r'implies', r'and', r'or', r'not'],
            'set_theory': [r'subset', r'union', r'intersection', r'element']
        }
        
        self.complexity_patterns = {
            'constant': [r'O\(1\)', r'constant'],
            'linear': [r'O\(n\)', r'linear'],
            'polynomial': [r'O\(n\^?\d+\)', r'polynomial'],
            'exponential': [r'O\(2\^n\)', r'exponential'],
            'factorial': [r'O\(n!\)', r'factorial']
        }
    
    def extract_features(self, claim: Claim, code: str = "") -> ProofFeatures:
        """Extract comprehensive features from a claim."""
        text = claim.claim_text.lower()
        
        # Syntactic analysis
        claim_length = len(claim.claim_text)
        math_ops = sum(len(re.findall(pattern, text)) for patterns in self.mathematical_patterns.values() for pattern in patterns[:5])  # arithmetic patterns
        logical_ops = sum(len(re.findall(pattern, text)) for pattern in self.mathematical_patterns['logic'])
        
        # Quantifier analysis
        quantifier_depth = self._analyze_quantifier_depth(text)
        variable_count = len(set(re.findall(r'\b[a-z]\b', text)))  # single letter variables
        constant_count = len(re.findall(r'\b\d+\b', text))
        
        # Semantic classification
        proof_type = self._classify_proof_type(text)
        complexity_class = self._classify_complexity(text)
        domain = self._classify_domain(text)
        
        # Contextual analysis
        code_complexity = self._analyze_code_complexity(code) if code else 0.0
        
        # Structural analysis
        ast_depth = self._estimate_ast_depth(text)
        
        return ProofFeatures(
            claim_length=claim_length,
            mathematical_operators=math_ops,
            logical_operators=logical_ops,
            quantifier_depth=quantifier_depth,
            variable_count=variable_count,
            constant_count=constant_count,
            proof_type=proof_type,
            complexity_class=complexity_class,
            mathematical_domain=domain,
            code_complexity=code_complexity,
            previous_success_rate=0.0,  # Will be updated by learning system
            ast_depth=ast_depth,
            pattern_similarity=0.0  # Will be computed against known patterns
        )
    
    def _analyze_quantifier_depth(self, text: str) -> int:
        """Analyze nesting depth of quantifiers."""
        # Simplified: count maximum nesting
        forall_count = text.count('forall')
        exists_count = text.count('exists') 
        return max(forall_count, exists_count)
    
    def _classify_proof_type(self, text: str) -> str:
        """Classify the fundamental type of proof needed."""
        if any(pattern in text for pattern in ['factorial', 'fibonacci', 'gcd', 'recursive']):
            return 'inductive'
        elif any(pattern in text for pattern in ['forall', 'exists', 'implies']):
            return 'logical'
        elif any(pattern in text for pattern in ['+', '-', '*', '/', '=']):
            return 'arithmetic'
        elif any(pattern in text for pattern in ['<', '>', '<=', '>=']):
            return 'constraint'
        else:
            return 'general'
    
    def _classify_complexity(self, text: str) -> str:
        """Classify computational complexity mentioned in claim."""
        for complexity, patterns in self.complexity_patterns.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return complexity
        return 'unknown'
    
    def _classify_domain(self, text: str) -> str:
        """Classify mathematical domain."""
        for domain, patterns in self.mathematical_patterns.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return domain
        return 'general'
    
    def _analyze_code_complexity(self, code: str) -> float:
        """Compute cyclomatic complexity of associated code."""
        if not code:
            return 0.0
        
        # Simplified cyclomatic complexity
        complexity_indicators = ['if', 'for', 'while', 'try', 'except', 'elif', 'and', 'or']
        complexity = 1  # base complexity
        
        for indicator in complexity_indicators:
            complexity += code.lower().count(indicator)
        
        return float(complexity)
    
    def _estimate_ast_depth(self, text: str) -> int:
        """Estimate AST depth of the logical structure."""
        # Count nested parentheses as proxy for depth
        max_depth = 0
        current_depth = 0
        
        for char in text:
            if char == '(':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ')':
                current_depth -= 1
        
        return max_depth


class ProofStrategyLearner:
    """
    Deep learning system for proof strategies.
    
    This learns from proof attempts to predict:
    1. Which prover is most likely to succeed
    2. Expected proof time  
    3. Likely failure modes
    4. Optimal proof tactics
    """
    
    def __init__(self, data_file: str | Path = DEFAULT_PROOF_LEARNING_DATA_FILE):
        self.data_file = Path(data_file)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.feature_extractor = FeatureExtractor()
        self.proof_history: List[ProofAttempt] = []
        self.success_patterns: Dict[str, List[ProofAttempt]] = defaultdict(list)
        self.failure_patterns: Dict[str, List[ProofAttempt]] = defaultdict(list)
        
        # Load existing data
        self._load_history()
        
        # Pattern matching thresholds
        self.similarity_threshold = 0.7
        
        logger.info(
            "Initialized proof strategy learner with %d historical attempts",
            len(self.proof_history),
        )
    
    def record_proof_attempt(
        self, claim: Claim, prover: str, result: ProofResult, code: str = ""
    ):
        """Record a proof attempt for learning."""
        features = self.feature_extractor.extract_features(claim, code)
        
        # Update historical success rate for similar claims
        features.previous_success_rate = self._compute_historical_success_rate(features)
        features.pattern_similarity = self._compute_pattern_similarity(features)
        
        attempt = ProofAttempt(
            claim_text=claim.claim_text,
            features=features,
            prover_used=prover,
            success=result.proven,
            time_ms=result.proof_time_ms,
            error_type=self._classify_error_type(result.error_message) if not result.proven else None,
            timestamp=time.time()
        )
        
        self.proof_history.append(attempt)
        
        # Update pattern databases
        if attempt.success:
            self.success_patterns[features.proof_type].append(attempt)
        else:
            self.failure_patterns[features.proof_type].append(attempt)
        
        # Save updated data
        self._save_history()
        
        logger.debug(
            "Recorded proof attempt: %s... -> %s -> %s",
            claim.claim_text[:50],
            prover,
            "SUCCESS" if result.proven else "FAIL",
        )
    
    def predict_optimal_strategy(self, claim: Claim, code: str = "") -> Dict[str, Any]:
        """Predict the optimal proving strategy for a claim."""
        features = self.feature_extractor.extract_features(claim, code)
        features.previous_success_rate = self._compute_historical_success_rate(features)
        features.pattern_similarity = self._compute_pattern_similarity(features)
        
        # Find similar successful attempts
        similar_successes = self._find_similar_attempts(features, success_only=True)
        similar_failures = self._find_similar_attempts(features, success_only=False)
        
        # Analyze prover performance on similar claims
        prover_analysis = self._analyze_prover_performance(similar_successes, similar_failures)
        
        # Predict proof complexity
        time_prediction = self._predict_proof_time(features, similar_successes)
        
        # Generate strategy recommendation
        strategy = self._generate_strategy(features, prover_analysis, time_prediction)
        
        return {
            'recommended_prover': strategy['prover'],
            'confidence': strategy['confidence'],
            'expected_time_ms': time_prediction,
            'success_probability': strategy['success_prob'],
            'similar_claims_count': len(similar_successes),
            'reasoning': strategy['reasoning'],
            'suggested_tactics': strategy['tactics']
        }
    
    def _find_similar_attempts(self, features: ProofFeatures, success_only: bool = True) -> List[ProofAttempt]:
        """Find historically similar proof attempts."""
        similar = []
        target_vector = features.to_vector()
        
        for attempt in self.proof_history:
            if success_only and not attempt.success:
                continue
            if not success_only and attempt.success:
                continue
                
            # Compute similarity based on features
            similarity = self._compute_similarity(target_vector, attempt.features.to_vector())
            
            if similarity > self.similarity_threshold:
                similar.append(attempt)
        
        # Sort by similarity (most similar first)
        similar.sort(key=lambda a: self._compute_similarity(target_vector, a.features.to_vector()), reverse=True)
        return similar[:10]  # Top 10 most similar
    
    def _compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between feature vectors."""
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _analyze_prover_performance(self, successes: List[ProofAttempt], failures: List[ProofAttempt]) -> Dict[str, Dict[str, float]]:
        """Analyze which provers perform best on similar claims."""
        prover_stats = defaultdict(lambda: {'successes': 0, 'failures': 0, 'avg_time': 0})
        
        # Count successes
        for attempt in successes:
            prover_stats[attempt.prover_used]['successes'] += 1
            prover_stats[attempt.prover_used]['total_time'] = prover_stats[attempt.prover_used].get('total_time', 0) + attempt.time_ms
        
        # Count failures
        for attempt in failures:
            prover_stats[attempt.prover_used]['failures'] += 1
        
        # Compute statistics
        analysis = {}
        for prover, stats in prover_stats.items():
            total_attempts = stats['successes'] + stats['failures']
            if total_attempts > 0:
                success_rate = stats['successes'] / total_attempts
                avg_time = stats.get('total_time', 0) / max(stats['successes'], 1)
                analysis[prover] = {
                    'success_rate': success_rate,
                    'attempts': total_attempts,
                    'avg_time_ms': avg_time
                }
        
        return analysis
    
    def _predict_proof_time(self, features: ProofFeatures, similar_successes: List[ProofAttempt]) -> float:
        """Predict expected proof time based on similar claims."""
        if not similar_successes:
            return 150.0  # Default estimate
        
        times = [attempt.time_ms for attempt in similar_successes]
        
        # Weight more recent attempts more heavily
        now = time.time()
        weights = [1.0 / (1.0 + (now - attempt.timestamp) / (24 * 3600)) for attempt in similar_successes]  # Decay over days
        
        weighted_avg = np.average(times, weights=weights)
        return max(50.0, weighted_avg)  # Minimum 50ms
    
    def _generate_strategy(self, features: ProofFeatures, prover_analysis: Dict[str, Dict[str, float]], time_prediction: float) -> Dict[str, Any]:
        """Generate optimal strategy recommendation."""
        
        if not prover_analysis:
            # No similar examples - use heuristics
            if features.proof_type == 'constraint' or 'exists' in features.mathematical_domain:
                return {
                    'prover': 'z3',
                    'confidence': 0.6,
                    'success_prob': 0.7,
                    'reasoning': 'Constraint/existential claim - Z3 typically better',
                    'tactics': ['constraint solving', 'satisfiability checking']
                }
            else:
                return {
                    'prover': 'coq',
                    'confidence': 0.6, 
                    'success_prob': 0.8,
                    'reasoning': 'Mathematical/logical claim - Coq typically better',
                    'tactics': ['induction', 'reflexivity', 'ring']
                }
        
        # Find best prover based on historical performance
        best_prover = max(prover_analysis.items(), 
                         key=lambda x: x[1]['success_rate'] * (1.0 / (1.0 + x[1]['avg_time_ms'] / 1000)))[0]
        
        best_stats = prover_analysis[best_prover]
        
        # Generate tactical recommendations
        tactics = self._recommend_tactics(features, best_prover)
        
        return {
            'prover': best_prover,
            'confidence': min(0.95, best_stats['success_rate'] + 0.1),
            'success_prob': best_stats['success_rate'],
            'reasoning': f"Historical data: {best_stats['success_rate']:.1%} success rate ({best_stats['attempts']} similar claims)",
            'tactics': tactics
        }
    
    def _recommend_tactics(self, features: ProofFeatures, prover: str) -> List[str]:
        """Recommend specific proof tactics based on features."""
        tactics = []
        
        if prover == 'coq':
            if features.proof_type == 'arithmetic':
                tactics.extend(['reflexivity', 'ring', 'lia'])
            elif features.proof_type == 'inductive':
                tactics.extend(['induction', 'simpl', 'auto'])
            elif features.proof_type == 'logical':
                tactics.extend(['intros', 'split', 'exists', 'apply'])
            else:
                tactics.extend(['auto', 'intuition', 'omega'])
        
        elif prover == 'z3':
            if features.proof_type == 'constraint':
                tactics.extend(['constraint solving', 'bounds checking'])
            elif features.logical_operators > 0:
                tactics.extend(['satisfiability', 'model finding'])
            else:
                tactics.extend(['arithmetic decision', 'theory reasoning'])
        
        return tactics if tactics else ['auto']
    
    def _compute_historical_success_rate(self, features: ProofFeatures) -> float:
        """Compute success rate for similar historical claims."""
        similar_type = [a for a in self.proof_history if a.features.proof_type == features.proof_type]
        if not similar_type:
            return 0.5  # No data - neutral estimate
        
        successes = sum(1 for a in similar_type if a.success)
        return successes / len(similar_type)
    
    def _compute_pattern_similarity(self, features: ProofFeatures) -> float:
        """Compute similarity to known successful patterns."""
        if not self.success_patterns:
            return 0.0
        
        target_vector = features.to_vector()
        max_similarity = 0.0
        
        for attempts in self.success_patterns.values():
            for attempt in attempts[-5:]:  # Check recent successful attempts
                similarity = self._compute_similarity(target_vector, attempt.features.to_vector())
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _classify_error_type(self, error_message: Optional[str]) -> Optional[str]:
        """Classify the type of proof error."""
        if not error_message:
            return None
        
        error_lower = error_message.lower()
        
        if 'timeout' in error_lower or 'time' in error_lower:
            return 'timeout'
        elif 'unification' in error_lower:
            return 'unification_failure'
        elif 'tactic' in error_lower and 'fail' in error_lower:
            return 'tactic_failure'
        elif 'type' in error_lower and 'error' in error_lower:
            return 'type_error'
        elif 'unknown' in error_lower or 'undefined' in error_lower:
            return 'undefined_reference'
        else:
            return 'other'
    
    def _load_history(self):
        """Load proof history from disk."""
        if not self.data_file.exists():
            return
        
        try:
            with self.data_file.open(encoding="utf-8") as f:
                data = json.load(f)

            schema_version = data.get("schema_version")
            if schema_version != PROOF_LEARNING_SCHEMA_VERSION:
                logger.info(
                    "Ignoring stale proof learning history %s with schema_version=%s",
                    self.data_file,
                    schema_version,
                )
                return
            
            for attempt_data in data.get('attempts', []):
                # Reconstruct ProofFeatures
                features_data = attempt_data['features']
                features = ProofFeatures(**features_data)
                
                # Reconstruct ProofAttempt
                attempt = ProofAttempt(
                    claim_text=attempt_data['claim_text'],
                    features=features,
                    prover_used=attempt_data['prover_used'],
                    success=attempt_data['success'],
                    time_ms=attempt_data['time_ms'],
                    error_type=attempt_data.get('error_type'),
                    timestamp=attempt_data['timestamp']
                )
                
                self.proof_history.append(attempt)
                
                # Update pattern databases
                if attempt.success:
                    self.success_patterns[features.proof_type].append(attempt)
                else:
                    self.failure_patterns[features.proof_type].append(attempt)
        
        except Exception as e:
            logger.warning(f"Failed to load proof history: {e}")
    
    def _save_history(self):
        """Save proof history to disk."""
        try:
            data = {
                'schema_version': PROOF_LEARNING_SCHEMA_VERSION,
                'attempts': [
                    {
                        'claim_text': attempt.claim_text,
                        'features': asdict(attempt.features),
                        'prover_used': attempt.prover_used,
                        'success': attempt.success,
                        'time_ms': attempt.time_ms,
                        'error_type': attempt.error_type,
                        'timestamp': attempt.timestamp
                    }
                    for attempt in self.proof_history
                ]
            }
            
            with self.data_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        
        except Exception as e:
            logger.warning(f"Failed to save proof history: {e}")
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the learning system."""
        total_attempts = len(self.proof_history)
        successful_attempts = sum(1 for a in self.proof_history if a.success)
        
        prover_stats = defaultdict(lambda: {'attempts': 0, 'successes': 0})
        for attempt in self.proof_history:
            prover_stats[attempt.prover_used]['attempts'] += 1
            if attempt.success:
                prover_stats[attempt.prover_used]['successes'] += 1
        
        proof_type_stats = defaultdict(lambda: {'attempts': 0, 'successes': 0})
        for attempt in self.proof_history:
            proof_type_stats[attempt.features.proof_type]['attempts'] += 1
            if attempt.success:
                proof_type_stats[attempt.features.proof_type]['successes'] += 1
        
        return {
            'total_attempts': total_attempts,
            'success_rate': successful_attempts / total_attempts if total_attempts > 0 else 0,
            'prover_performance': {
                prover: {
                    'success_rate': stats['successes'] / stats['attempts'],
                    'attempts': stats['attempts']
                }
                for prover, stats in prover_stats.items()
            },
            'proof_type_performance': {
                ptype: {
                    'success_rate': stats['successes'] / stats['attempts'],
                    'attempts': stats['attempts']
                }
                for ptype, stats in proof_type_stats.items()
            }
        }
