"""
Caching layer for embeddings and frequent queries.
Implements in-memory and optional Redis caching for performance optimization.
"""

import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
from collections import OrderedDict

from physiology_rag.config.settings import get_settings
from physiology_rag.utils.logging import get_logger

logger = get_logger("cache_manager")


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0.0
    size_bytes: int = 0
    
    def __post_init__(self):
        self.last_accessed = self.timestamp
        if isinstance(self.data, (str, bytes)):
            self.size_bytes = len(self.data)
        elif isinstance(self.data, (list, dict)):
            self.size_bytes = len(json.dumps(self.data, default=str))


class InMemoryCache:
    """Thread-safe in-memory cache with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Initialize in-memory cache.
        
        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time-to-live in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        
        logger.info(f"Initialized InMemoryCache with max_size={max_size}, ttl={ttl_seconds}s")
    
    def _generate_key(self, key: Union[str, Dict[str, Any]]) -> str:
        """Generate cache key from input."""
        if isinstance(key, str):
            return hashlib.md5(key.encode()).hexdigest()
        elif isinstance(key, dict):
            # Sort dict for consistent hashing
            sorted_key = json.dumps(key, sort_keys=True)
            return hashlib.md5(sorted_key.encode()).hexdigest()
        else:
            return hashlib.md5(str(key).encode()).hexdigest()
    
    def get(self, key: Union[str, Dict[str, Any]]) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        cache_key = self._generate_key(key)
        
        with self.lock:
            if cache_key not in self.cache:
                self.misses += 1
                return None
            
            entry = self.cache[cache_key]
            current_time = time.time()
            
            # Check if expired
            if current_time - entry.timestamp > self.ttl_seconds:
                del self.cache[cache_key]
                self.misses += 1
                return None
            
            # Update access stats
            entry.access_count += 1
            entry.last_accessed = current_time
            
            # Move to end (most recently used)
            self.cache.move_to_end(cache_key)
            
            self.hits += 1
            return entry.data
    
    def set(self, key: Union[str, Dict[str, Any]], value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        cache_key = self._generate_key(key)
        current_time = time.time()
        
        with self.lock:
            # Create cache entry
            entry = CacheEntry(
                data=value,
                timestamp=current_time,
                last_accessed=current_time
            )
            
            # Remove if already exists
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            # Add new entry
            self.cache[cache_key] = entry
            
            # Evict oldest if over limit
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Evicted cache entry: {oldest_key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
        logger.info("Cleared in-memory cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0
            
            return {
                'entries': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'total_requests': total_requests
            }


class EmbeddingCache:
    """Specialized cache for embeddings with persistence."""
    
    def __init__(self, cache_dir: str = None, max_memory_entries: int = 500):
        """
        Initialize embedding cache.
        
        Args:
            cache_dir: Directory for persistent cache
            max_memory_entries: Maximum in-memory entries
        """
        settings = get_settings()
        self.cache_dir = Path(cache_dir or settings.data_dir) / "cache" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.memory_cache = InMemoryCache(max_size=max_memory_entries, ttl_seconds=7200)  # 2 hours
        
        logger.info(f"Initialized EmbeddingCache with cache_dir={self.cache_dir}")
    
    def _get_cache_file(self, text: str) -> Path:
        """Get cache file path for text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return self.cache_dir / f"{text_hash}.json"
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            Cached embedding or None
        """
        # Try memory cache first
        embedding = self.memory_cache.get(text)
        if embedding is not None:
            return embedding
        
        # Try disk cache
        cache_file = self._get_cache_file(text)
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    embedding = data.get('embedding')
                    if embedding:
                        # Add to memory cache
                        self.memory_cache.set(text, embedding)
                        return embedding
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
        
        return None
    
    def set_embedding(self, text: str, embedding: List[float]) -> None:
        """
        Cache embedding for text.
        
        Args:
            text: Input text
            embedding: Embedding vector
        """
        # Store in memory cache
        self.memory_cache.set(text, embedding)
        
        # Store in disk cache
        cache_file = self._get_cache_file(text)
        try:
            cache_data = {
                'text': text[:100],  # Store first 100 chars for debugging
                'embedding': embedding,
                'timestamp': time.time(),
                'text_length': len(text)
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Error writing cache file {cache_file}: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached embeddings."""
        self.memory_cache.clear()
        
        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except Exception as e:
                logger.warning(f"Error deleting cache file {cache_file}: {e}")
        
        logger.info("Cleared embedding cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        memory_stats = self.memory_cache.get_stats()
        
        # Count disk cache files
        disk_entries = len(list(self.cache_dir.glob("*.json")))
        
        return {
            'memory_cache': memory_stats,
            'disk_entries': disk_entries,
            'cache_dir': str(self.cache_dir)
        }


class QueryCache:
    """Cache for RAG query results."""
    
    def __init__(self, max_entries: int = 200, ttl_seconds: int = 1800):
        """
        Initialize query cache.
        
        Args:
            max_entries: Maximum cached queries
            ttl_seconds: Time-to-live in seconds (30 minutes default)
        """
        self.cache = InMemoryCache(max_size=max_entries, ttl_seconds=ttl_seconds)
        logger.info(f"Initialized QueryCache with max_entries={max_entries}, ttl={ttl_seconds}s")
    
    def get_query_result(self, query: str, context_hash: str = None) -> Optional[Dict[str, Any]]:
        """
        Get cached query result.
        
        Args:
            query: Query string
            context_hash: Optional context hash for cache key
            
        Returns:
            Cached result or None
        """
        cache_key = {
            'query': query.lower().strip(),
            'context_hash': context_hash or 'default'
        }
        
        return self.cache.get(cache_key)
    
    def set_query_result(self, query: str, result: Dict[str, Any], context_hash: str = None) -> None:
        """
        Cache query result.
        
        Args:
            query: Query string
            result: Query result
            context_hash: Optional context hash for cache key
        """
        cache_key = {
            'query': query.lower().strip(),
            'context_hash': context_hash or 'default'
        }
        
        self.cache.set(cache_key, result)
    
    def clear_cache(self) -> None:
        """Clear query cache."""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


class CacheManager:
    """Unified cache manager for all caching needs."""
    
    def __init__(self):
        """Initialize cache manager."""
        self.embedding_cache = EmbeddingCache()
        self.query_cache = QueryCache()
        
        logger.info("Initialized CacheManager")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding."""
        return self.embedding_cache.get_embedding(text)
    
    def set_embedding(self, text: str, embedding: List[float]) -> None:
        """Cache embedding."""
        self.embedding_cache.set_embedding(text, embedding)
    
    def get_query_result(self, query: str, context_hash: str = None) -> Optional[Dict[str, Any]]:
        """Get cached query result."""
        return self.query_cache.get_query_result(query, context_hash)
    
    def set_query_result(self, query: str, result: Dict[str, Any], context_hash: str = None) -> None:
        """Cache query result."""
        self.query_cache.set_query_result(query, result, context_hash)
    
    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.embedding_cache.clear_cache()
        self.query_cache.clear_cache()
        logger.info("Cleared all caches")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            'embedding_cache': self.embedding_cache.get_stats(),
            'query_cache': self.query_cache.get_stats(),
            'timestamp': time.time()
        }


# Global cache manager instance
cache_manager = CacheManager()


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    return cache_manager


def main():
    """CLI entry point for cache testing."""
    cache_mgr = get_cache_manager()
    
    # Test embedding cache
    print("Testing embedding cache...")
    test_text = "The cerebral cortex is responsible for higher-order thinking."
    test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    # Set and get embedding
    cache_mgr.set_embedding(test_text, test_embedding)
    cached_embedding = cache_mgr.get_embedding(test_text)
    
    print(f"Cached embedding matches: {cached_embedding == test_embedding}")
    
    # Test query cache
    print("Testing query cache...")
    test_query = "What is the cerebral cortex?"
    test_result = {'answer': 'The cerebral cortex is...', 'sources': []}
    
    cache_mgr.set_query_result(test_query, test_result)
    cached_result = cache_mgr.get_query_result(test_query)
    
    print(f"Cached result matches: {cached_result == test_result}")
    
    # Show stats
    stats = cache_mgr.get_comprehensive_stats()
    print(f"\nCache statistics:")
    print(f"Embedding cache: {stats['embedding_cache']}")
    print(f"Query cache: {stats['query_cache']}")


if __name__ == "__main__":
    main()