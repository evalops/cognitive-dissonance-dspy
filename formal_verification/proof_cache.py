"""Proof caching system for improved performance."""

import hashlib
import json
import time
from typing import Dict, Optional, Any
from pathlib import Path
import logging

from .types import FormalSpec, ProofResult

logger = logging.getLogger(__name__)


class ProofCache:
    """
    Cache system for Coq proofs to avoid re-proving the same claims.
    
    This significantly improves performance when dealing with repeated
    claims or similar proof patterns.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize proof cache.
        
        Args:
            cache_dir: Directory to store cache files (defaults to .proof_cache)
        """
        self.cache_dir = Path(cache_dir or ".proof_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache: Dict[str, ProofResult] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_time_saved_ms": 0.0
        }
        
    def _get_cache_key(self, spec: FormalSpec) -> str:
        """Generate a unique cache key for a specification."""
        # Create hash of the Coq code
        content = spec.coq_code.strip()
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def get(self, spec: FormalSpec) -> Optional[ProofResult]:
        """
        Retrieve cached proof result if available.
        
        Args:
            spec: The formal specification to look up
            
        Returns:
            Cached ProofResult if found, None otherwise
        """
        cache_key = self._get_cache_key(spec)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            self.stats["hits"] += 1
            result = self.memory_cache[cache_key]
            self.stats["total_time_saved_ms"] += result.proof_time_ms
            logger.debug(f"Cache hit for {spec.claim.claim_text[:30]}...")
            return result
            
        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    
                result = ProofResult(
                    spec=spec,
                    proven=data["proven"],
                    proof_time_ms=data["proof_time_ms"],
                    error_message=data.get("error_message"),
                    counter_example=data.get("counter_example"),
                    proof_output=data.get("proof_output", ""),
                    prover_name=data.get("prover_name"),
                    solver_status=data.get("solver_status"),
                    auto_repaired=data.get("auto_repaired", False),
                    assumptions_present=data.get("assumptions_present", False),
                    checker_name=data.get("checker_name"),
                )
                
                # Add to memory cache
                self.memory_cache[cache_key] = result
                self.stats["hits"] += 1
                self.stats["total_time_saved_ms"] += result.proof_time_ms
                logger.debug(f"Disk cache hit for {spec.claim.claim_text[:30]}...")
                return result
                
            except Exception as e:
                logger.warning(f"Failed to load cache file {cache_file}: {e}")
        
        self.stats["misses"] += 1
        return None
    
    def put(self, spec: FormalSpec, result: ProofResult):
        """
        Store proof result in cache.
        
        Args:
            spec: The formal specification
            result: The proof result to cache
        """
        cache_key = self._get_cache_key(spec)
        
        # Store in memory cache
        self.memory_cache[cache_key] = result
        
        # Store on disk
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            data = {
                "claim_text": spec.claim.claim_text,
                "proven": result.proven,
                "proof_time_ms": result.proof_time_ms,
                "error_message": result.error_message,
                "proof_output": result.proof_output,
                "counter_example": result.counter_example,
                "prover_name": result.prover_name,
                "solver_status": result.solver_status,
                "auto_repaired": result.auto_repaired,
                "assumptions_present": result.assumptions_present,
                "checker_name": result.checker_name,
                "cached_at": time.time()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Cached proof for {spec.claim.claim_text[:30]}...")
            
        except Exception as e:
            logger.warning(f"Failed to write cache file {cache_file}: {e}")
    
    def clear(self):
        """Clear all cached proofs."""
        self.memory_cache.clear()
        
        # Remove disk cache files
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove cache file {cache_file}: {e}")
                
        self.stats = {
            "hits": 0,
            "misses": 0,
            "total_time_saved_ms": 0.0
        }
        logger.info("Proof cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0.0
        
        return {
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": hit_rate,
            "total_requests": total,
            "time_saved_ms": self.stats["total_time_saved_ms"],
            "memory_cache_size": len(self.memory_cache),
            "disk_cache_size": len(list(self.cache_dir.glob("*.json")))
        }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return f"ProofCache(hit_rate={stats['hit_rate']:.1%}, cached={stats['memory_cache_size']})"
