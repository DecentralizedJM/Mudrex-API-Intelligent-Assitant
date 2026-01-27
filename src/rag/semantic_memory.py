"""
Semantic Memory Layer for storing and retrieving user facts, strategies, and preferences
Uses vector embeddings to find relevant memories during conversations

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from google import genai
import os

from ..config import config

logger = logging.getLogger(__name__)

# Import cache (avoid circular import)
try:
    from .cache import RedisCache
except ImportError:
    RedisCache = None


class SemanticMemory:
    """
    Semantic memory for storing user facts, strategies, preferences, and conversation context.
    Uses vector embeddings for semantic search and Redis for persistence.
    """
    
    def __init__(self):
        """Initialize semantic memory with Gemini embeddings"""
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
        
        self.client = genai.Client()
        self.embedding_model = config.EMBEDDING_MODEL
        
        # Initialize Redis cache for memory storage
        self.cache = RedisCache() if (config.REDIS_ENABLED and RedisCache) else None
        
        # In-memory storage (fallback if Redis unavailable)
        self.memories: List[Dict[str, Any]] = []
        
        logger.info("SemanticMemory initialized")
    
    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for text using Gemini"""
        if not text:
            return None
        
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                content=text
            )
            if response and hasattr(response, 'embeddings') and response.embeddings:
                return response.embeddings[0].values
            return None
        except Exception as e:
            logger.warning(f"Error getting embedding for memory: {e}")
            return None
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            vec1_arr = np.array(vec1).reshape(1, -1)
            vec2_arr = np.array(vec2).reshape(1, -1)
            return float(cosine_similarity(vec1_arr, vec2_arr)[0][0])
        except Exception as e:
            logger.warning(f"Error calculating similarity: {e}")
            return 0.0
    
    def _memory_key(self, memory_id: str) -> str:
        """Generate Redis key for memory"""
        return f"memory:{memory_id}"
    
    def _memory_list_key(self, chat_id: str) -> str:
        """Generate Redis key for memory list per chat"""
        return f"memory_list:{chat_id}"
    
    def store_memory(
        self,
        chat_id: str,
        content: str,
        memory_type: str = "fact",
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> Optional[str]:
        """
        Store a memory (fact, strategy, preference, etc.)
        
        Args:
            chat_id: Chat/group ID
            content: Memory content (e.g., "User prefers Python over JavaScript")
            memory_type: Type of memory (fact, strategy, preference, context)
            metadata: Additional metadata
            importance: Importance score (0.0-1.0) for prioritization
        
        Returns:
            Memory ID if successful, None otherwise
        """
        if not content:
            return None
        
        # Generate embedding
        embedding = self._get_embedding(content)
        if not embedding:
            logger.warning("Failed to generate embedding for memory")
            return None
        
        # Generate memory ID
        memory_id = hashlib.sha256(
            f"{chat_id}:{content}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        memory = {
            'id': memory_id,
            'chat_id': chat_id,
            'content': content,
            'type': memory_type,
            'embedding': embedding,
            'metadata': metadata or {},
            'importance': importance,
            'created_at': datetime.now().isoformat(),
            'access_count': 0,
            'last_accessed': None
        }
        
        # Store in Redis if available
        if self.cache and self.cache.connected:
            try:
                memory_key = self._memory_key(memory_id)
                # Store embedding separately (Redis doesn't handle lists well)
                memory_for_storage = memory.copy()
                memory_for_storage['embedding'] = None  # Don't store embedding in Redis
                
                # Store memory
                memory_json = json.dumps(memory_for_storage)
                self.cache._set(memory_key, memory_json, ttl=config.REDIS_TTL_MEMORY if hasattr(config, 'REDIS_TTL_MEMORY') else 86400 * 30)  # 30 days
                
                # Store embedding separately
                embedding_key = f"{memory_key}:embedding"
                embedding_json = json.dumps(embedding)
                self.cache._set(embedding_key, embedding_json, ttl=config.REDIS_TTL_MEMORY if hasattr(config, 'REDIS_TTL_MEMORY') else 86400 * 30)
                
                # Add to chat's memory list
                list_key = self._memory_list_key(chat_id)
                existing_list = self.cache._get(list_key)
                memory_ids = json.loads(existing_list) if existing_list else []
                if memory_id not in memory_ids:
                    memory_ids.append(memory_id)
                    self.cache._set(list_key, json.dumps(memory_ids), ttl=86400 * 30)
                
                logger.info(f"Stored memory {memory_id} for chat {chat_id}")
            except Exception as e:
                logger.warning(f"Failed to store memory in Redis: {e}")
                # Fallback to in-memory
                self.memories.append(memory)
        else:
            # Fallback to in-memory storage
            self.memories.append(memory)
            logger.debug(f"Stored memory {memory_id} in-memory (Redis unavailable)")
        
        return memory_id
    
    def retrieve_memories(
        self,
        chat_id: str,
        query: str,
        top_k: int = 3,
        memory_types: Optional[List[str]] = None,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for a query
        
        Args:
            chat_id: Chat/group ID
            query: Query to find relevant memories
            top_k: Number of memories to return
            memory_types: Filter by memory types (None = all types)
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of relevant memories with similarity scores
        """
        if not query:
            return []
        
        # Get embedding for query
        query_embedding = self._get_embedding(query)
        if not query_embedding:
            return []
        
        # Load memories for this chat
        memories = self._load_chat_memories(chat_id)
        
        if not memories:
            return []
        
        # Filter by type if specified
        if memory_types:
            memories = [m for m in memories if m.get('type') in memory_types]
        
        # Calculate similarities
        scored_memories = []
        for memory in memories:
            embedding = memory.get('embedding')
            if not embedding:
                # Try to load from Redis if not in memory
                if self.cache and self.cache.connected:
                    embedding_key = f"{self._memory_key(memory['id'])}:embedding"
                    embedding_json = self.cache._get(embedding_key)
                    if embedding_json:
                        try:
                            embedding = json.loads(embedding_json)
                            memory['embedding'] = embedding
                        except:
                            continue
                if not embedding:
                    continue
            
            similarity = self._cosine_similarity(query_embedding, embedding)
            if similarity >= min_similarity:
                scored_memories.append({
                    **memory,
                    'similarity': similarity,
                    'embedding': None  # Remove embedding from result
                })
        
        # Sort by similarity and importance
        scored_memories.sort(
            key=lambda x: (x['similarity'] * 0.7 + x.get('importance', 0.5) * 0.3),
            reverse=True
        )
        
        # Update access stats
        for memory in scored_memories[:top_k]:
            self._update_access_stats(memory['id'])
        
        return scored_memories[:top_k]
    
    def _load_chat_memories(self, chat_id: str) -> List[Dict[str, Any]]:
        """Load all memories for a chat from Redis or in-memory"""
        memories = []
        
        if self.cache and self.cache.connected:
            try:
                list_key = self._memory_list_key(chat_id)
                memory_ids_json = self.cache._get(list_key)
                if not memory_ids_json:
                    return []
                
                memory_ids = json.loads(memory_ids_json)
                for memory_id in memory_ids:
                    memory_key = self._memory_key(memory_id)
                    memory_json = self.cache._get(memory_key)
                    if memory_json:
                        try:
                            memory = json.loads(memory_json)
                            # Load embedding separately
                            embedding_key = f"{memory_key}:embedding"
                            embedding_json = self.cache._get(embedding_key)
                            if embedding_json:
                                memory['embedding'] = json.loads(embedding_json)
                            memories.append(memory)
                        except Exception as e:
                            logger.warning(f"Failed to load memory {memory_id}: {e}")
            except Exception as e:
                logger.warning(f"Error loading memories from Redis: {e}")
        
        # Also check in-memory storage
        in_memory = [m for m in self.memories if m.get('chat_id') == chat_id]
        for mem in in_memory:
            if not any(m['id'] == mem['id'] for m in memories):
                memories.append(mem)
        
        return memories
    
    def _update_access_stats(self, memory_id: str):
        """Update access statistics for a memory"""
        if self.cache and self.cache.connected:
            try:
                memory_key = self._memory_key(memory_id)
                memory_json = self.cache._get(memory_key)
                if memory_json:
                    memory = json.loads(memory_json)
                    memory['access_count'] = memory.get('access_count', 0) + 1
                    memory['last_accessed'] = datetime.now().isoformat()
                    self.cache._set(memory_key, json.dumps(memory), ttl=86400 * 30)
            except Exception as e:
                logger.debug(f"Failed to update access stats: {e}")
    
    def delete_memory(self, chat_id: str, memory_id: str) -> bool:
        """Delete a memory"""
        if self.cache and self.cache.connected:
            try:
                memory_key = self._memory_key(memory_id)
                embedding_key = f"{memory_key}:embedding"
                
                # Remove from Redis
                self.cache.redis_client.delete(memory_key)
                self.cache.redis_client.delete(embedding_key)
                
                # Remove from list
                list_key = self._memory_list_key(chat_id)
                memory_ids_json = self.cache._get(list_key)
                if memory_ids_json:
                    memory_ids = json.loads(memory_ids_json)
                    if memory_id in memory_ids:
                        memory_ids.remove(memory_id)
                        self.cache._set(list_key, json.dumps(memory_ids), ttl=86400 * 30)
                
                logger.info(f"Deleted memory {memory_id}")
                return True
            except Exception as e:
                logger.warning(f"Failed to delete memory: {e}")
                return False
        
        # Remove from in-memory
        self.memories = [m for m in self.memories if m.get('id') != memory_id]
        return True
    
    def clear_chat_memories(self, chat_id: str) -> int:
        """Clear all memories for a chat"""
        memories = self._load_chat_memories(chat_id)
        count = len(memories)
        
        for memory in memories:
            self.delete_memory(chat_id, memory['id'])
        
        logger.info(f"Cleared {count} memories for chat {chat_id}")
        return count
