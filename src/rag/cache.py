"""
Redis Cache Client for reducing Gemini API token usage
Caches query responses, document validations, reranking, transformations, and embeddings

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
import hashlib
import json
from typing import Optional, Dict, Any, List
import re

from ..config import config

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache client with graceful fallback when Redis is unavailable.
    Caches expensive Gemini API calls to reduce token usage.
    """
    
    def __init__(self):
        """Initialize Redis cache client with lazy connection"""
        self.redis_client = None
        self.connected = False
        self.stats = {'hits': 0, 'misses': 0}
        
        if not config.REDIS_ENABLED:
            logger.info("Redis caching disabled")
            return
        
        if not config.REDIS_URL:
            logger.warning("REDIS_ENABLED=true but REDIS_URL not set. Caching disabled.")
            return
        
        try:
            import redis
            self.redis_client = redis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
            logger.info("Redis cache connected successfully")
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis>=5.0.0")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Continuing without cache.")
            self.redis_client = None
            self.connected = False
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent hashing"""
        if not text:
            return ""
        # Lowercase, strip whitespace, remove extra punctuation
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        return normalized
    
    def _hash_text(self, text: str) -> str:
        """Generate SHA256 hash of normalized text"""
        normalized = self._normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]  # First 16 chars
    
    def _hash_doc(self, doc: Dict[str, Any]) -> str:
        """Generate hash for a document"""
        doc_text = doc.get('document', '')[:500]  # Use first 500 chars
        return self._hash_text(doc_text)
    
    def _hash_docs(self, docs: List[Dict[str, Any]]) -> str:
        """Generate hash for a list of documents"""
        doc_hashes = [self._hash_doc(doc) for doc in docs]
        combined = "|".join(sorted(doc_hashes))  # Sort for consistency
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _hash_context(self, chat_history: Optional[List[Dict[str, str]]] = None, 
                     mcp_context: Optional[str] = None) -> str:
        """Generate hash for context (chat history + MCP)"""
        parts = []
        
        # Include last 2 messages from chat history
        if chat_history:
            recent = chat_history[-2:] if len(chat_history) > 2 else chat_history
            for msg in recent:
                parts.append(f"{msg.get('role', '')}:{msg.get('content', '')[:100]}")
        
        # Include MCP context hash
        if mcp_context:
            parts.append(self._hash_text(mcp_context[:200]))
        
        combined = "|".join(parts) if parts else "no_context"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
    
    def _get(self, key: str) -> Optional[str]:
        """Get value from Redis with error handling"""
        if not self.connected or not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                self.stats['hits'] += 1
            else:
                self.stats['misses'] += 1
            return value
        except Exception as e:
            logger.warning(f"Redis get error for key {key[:50]}: {e}")
            self.stats['misses'] += 1
            return None
    
    def _set(self, key: str, value: str, ttl: int) -> bool:
        """Set value in Redis with error handling"""
        if not self.connected or not self.redis_client:
            return False
        
        try:
            self.redis_client.setex(key, ttl, value)
            return True
        except Exception as e:
            logger.warning(f"Redis set error for key {key[:50]}: {e}")
            return False
    
    # Response caching
    def get_response(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None,
                    mcp_context: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached response for query"""
        query_hash = self._hash_text(query)
        context_hash = self._hash_context(chat_history, mcp_context)
        key = f"response:{query_hash}:{context_hash}"
        
        cached = self._get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse cached response for {key}")
                return None
        return None
    
    def set_response(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None,
                    mcp_context: Optional[str] = None, result: Dict[str, Any] = None,
                    ttl: Optional[int] = None):
        """Cache response for query"""
        if not result:
            return
        
        query_hash = self._hash_text(query)
        context_hash = self._hash_context(chat_history, mcp_context)
        key = f"response:{query_hash}:{context_hash}"
        
        try:
            value = json.dumps(result)
            ttl = ttl or config.REDIS_TTL_RESPONSE
            self._set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
    
    # Validation caching
    def get_validation(self, query: str, doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached validation result for (query, doc) pair"""
        query_hash = self._hash_text(query)
        doc_hash = self._hash_doc(doc)
        key = f"relevancy:{query_hash}:{doc_hash}"
        
        cached = self._get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_validation(self, query: str, doc: Dict[str, Any], result: Dict[str, Any],
                      ttl: Optional[int] = None):
        """Cache validation result for (query, doc) pair"""
        query_hash = self._hash_text(query)
        doc_hash = self._hash_doc(doc)
        key = f"relevancy:{query_hash}:{doc_hash}"
        
        try:
            value = json.dumps(result)
            ttl = ttl or config.REDIS_TTL_VALIDATION
            self._set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Failed to cache validation: {e}")
    
    # Reranking caching
    def get_rerank(self, query: str, documents: List[Dict[str, Any]]) -> Optional[List[int]]:
        """Get cached reranking indices for (query, docs) combination"""
        query_hash = self._hash_text(query)
        docs_hash = self._hash_docs(documents)
        key = f"rerank:{query_hash}:{docs_hash}"
        
        cached = self._get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_rerank(self, query: str, documents: List[Dict[str, Any]], indices: List[int],
                   ttl: Optional[int] = None):
        """Cache reranking indices for (query, docs) combination"""
        query_hash = self._hash_text(query)
        docs_hash = self._hash_docs(documents)
        key = f"rerank:{query_hash}:{docs_hash}"
        
        try:
            value = json.dumps(indices)
            ttl = ttl or config.REDIS_TTL_RERANK
            self._set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Failed to cache rerank: {e}")
    
    # Query transformation caching
    def get_transform(self, query: str) -> Optional[str]:
        """Get cached transformed query"""
        query_hash = self._hash_text(query)
        key = f"transform:{query_hash}"
        
        cached = self._get(key)
        return cached  # Already a string
    
    def set_transform(self, query: str, transformed: str, ttl: Optional[int] = None):
        """Cache transformed query"""
        query_hash = self._hash_text(query)
        key = f"transform:{query_hash}"
        
        ttl = ttl or config.REDIS_TTL_TRANSFORM
        self._set(key, transformed, ttl)
    
    # Embedding caching
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding for text"""
        text_hash = self._hash_text(text)
        key = f"embedding:{text_hash}"
        
        cached = self._get(key)
        if cached:
            try:
                return json.loads(cached)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_embedding(self, text: str, embedding: List[float], ttl: Optional[int] = None):
        """Cache embedding for text"""
        text_hash = self._hash_text(text)
        key = f"embedding:{text_hash}"
        
        try:
            value = json.dumps(embedding)
            ttl = ttl or config.REDIS_TTL_EMBEDDING
            self._set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
    
    # Statistics
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total * 100) if total > 0 else 0.0
        
        return {
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': hit_rate,
            'connected': self.connected,
            'enabled': config.REDIS_ENABLED
        }
