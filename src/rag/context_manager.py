"""
Context Management with Smart Trimming and Summarization
Handles conversation history, context compression, and token optimization

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from google import genai
import os

from ..config import config

logger = logging.getLogger(__name__)

# Import cache and semantic memory
try:
    from .cache import RedisCache
except ImportError:
    RedisCache = None

try:
    from .semantic_memory import SemanticMemory
except ImportError:
    SemanticMemory = None


class ContextManager:
    """
    Manages conversation context with smart trimming, summarization, and persistence.
    Optimizes token usage while maintaining conversation coherence.
    """
    
    def __init__(self):
        """Initialize context manager"""
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
        
        self.client = genai.Client()
        self.model_name = config.GEMINI_MODEL
        
        # Initialize Redis for persistent sessions
        self.cache = RedisCache() if (config.REDIS_ENABLED and RedisCache) else None
        
        # Initialize semantic memory
        self.semantic_memory = SemanticMemory() if SemanticMemory else None
        
        # Configuration
        self.max_history_messages = getattr(config, 'MAX_HISTORY_MESSAGES', 15)
        self.compress_threshold = getattr(config, 'CONTEXT_COMPRESS_THRESHOLD', 20)
        self.max_tokens_per_message = getattr(config, 'MAX_TOKENS_PER_MESSAGE', 200)
        
        logger.info("ContextManager initialized")
    
    def _session_key(self, chat_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{chat_id}"
    
    def load_session(self, chat_id: str) -> List[Dict[str, str]]:
        """
        Load conversation history from persistent storage
        
        Args:
            chat_id: Chat/group ID
            
        Returns:
            List of messages in format [{'role': 'user'|'assistant', 'content': '...'}, ...]
        """
        # Try Redis first
        if self.cache and self.cache.connected:
            try:
                session_key = self._session_key(chat_id)
                session_json = self.cache._get(session_key)
                if session_json:
                    history = json.loads(session_json)
                    logger.debug(f"Loaded {len(history)} messages from Redis for chat {chat_id}")
                    return history
            except Exception as e:
                logger.warning(f"Error loading session from Redis: {e}")
        
        return []
    
    def save_session(self, chat_id: str, history: List[Dict[str, str]]):
        """
        Save conversation history to persistent storage
        
        Args:
            chat_id: Chat/group ID
            history: List of messages
        """
        if self.cache and self.cache.connected:
            try:
                session_key = self._session_key(chat_id)
                session_json = json.dumps(history)
                # Store for 30 days
                ttl = getattr(config, 'REDIS_TTL_SESSION', 86400 * 30)
                self.cache._set(session_key, session_json, ttl)
                logger.debug(f"Saved {len(history)} messages to Redis for chat {chat_id}")
            except Exception as e:
                logger.warning(f"Error saving session to Redis: {e}")
    
    def add_message(self, chat_id: str, role: str, content: str):
        """
        Add a message to conversation history
        
        Args:
            chat_id: Chat/group ID
            role: 'user' or 'assistant'
            content: Message content
        """
        history = self.load_session(chat_id)
        history.append({'role': role, 'content': content})
        
        # Trim if needed
        if len(history) > self.max_history_messages:
            history = self.trim_context(chat_id, history)
        
        self.save_session(chat_id, history)
    
    def get_context(
        self,
        chat_id: str,
        query: str,
        include_recent: int = 5,
        include_memories: bool = True
    ) -> Dict[str, Any]:
        """
        Get optimized context for a query
        
        Args:
            chat_id: Chat/group ID
            query: Current query
            include_recent: Number of recent messages to include verbatim
            include_memories: Whether to include relevant semantic memories
            
        Returns:
            Dict with 'history', 'summary', 'memories', 'compressed'
        """
        history = self.load_session(chat_id)
        
        # Get recent messages
        recent = history[-include_recent:] if len(history) > include_recent else history
        
        # Get older messages for summarization
        older = history[:-include_recent] if len(history) > include_recent else []
        
        # Summarize older messages if needed
        summary = None
        compressed = False
        if len(older) > 0:
            summary = self._summarize_context(older, query)
            compressed = True
        
        # Get relevant memories
        memories = []
        if include_memories and self.semantic_memory:
            memories = self.semantic_memory.retrieve_memories(chat_id, query, top_k=3)
        
        return {
            'history': recent,
            'summary': summary,
            'memories': memories,
            'compressed': compressed,
            'total_messages': len(history)
        }
    
    def trim_context(self, chat_id: str, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Trim context by summarizing old messages and keeping recent ones
        
        Args:
            chat_id: Chat/group ID
            history: Full conversation history
            
        Returns:
            Trimmed history with recent messages + summary
        """
        if len(history) <= self.max_history_messages:
            return history
        
        # Keep recent messages verbatim
        keep_recent = self.max_history_messages // 2  # Keep half as recent
        recent = history[-keep_recent:]
        older = history[:-keep_recent]
        
        # Summarize older messages
        summary = self._summarize_context(older, "Summarize the conversation context")
        
        if summary:
            # Create summary message
            summary_msg = {
                'role': 'system',
                'content': f"[Previous conversation summary]: {summary}"
            }
            return [summary_msg] + recent
        
        # If summarization fails, just keep recent
        return recent
    
    def _summarize_context(
        self,
        messages: List[Dict[str, str]],
        current_query: Optional[str] = None
    ) -> Optional[str]:
        """
        Summarize a list of messages using Gemini
        
        Args:
            messages: List of messages to summarize
            current_query: Current query for context-aware summarization
            
        Returns:
            Summary string or None if summarization fails
        """
        if not messages:
            return None
        
        # Format messages for summarization
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}" for msg in messages
        ])
        
        # Build prompt
        prompt = f"""Summarize the following conversation in 2-3 sentences, focusing on:
- Key facts and information discussed
- User preferences or strategies mentioned
- Important context for future responses

Conversation:
{conversation}

Summary:"""
        
        if current_query:
            prompt += f"\n\nCurrent query context: {current_query}"
        
        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=150
                )
            )
            
            if response and response.text:
                summary = response.text.strip()
                logger.debug(f"Summarized {len(messages)} messages into {len(summary)} chars")
                return summary
        except Exception as e:
            logger.warning(f"Error summarizing context: {e}")
        
        return None
    
    def extract_facts(self, chat_id: str, conversation: List[Dict[str, str]]):
        """
        Extract and store facts from conversation into semantic memory
        
        Args:
            chat_id: Chat/group ID
            conversation: Recent conversation messages
        """
        if not self.semantic_memory:
            return
        
        # Combine recent conversation
        text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation[-5:]])
        
        # Use Gemini to extract facts
        prompt = f"""Extract key facts, preferences, and strategies from this conversation.
Return as a JSON array of objects, each with:
- "content": the fact/preference/strategy
- "type": "fact", "preference", "strategy", or "context"
- "importance": 0.0-1.0

Conversation:
{text}

JSON array:"""
        
        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=500
                )
            )
            
            if response and response.text:
                # Try to parse JSON
                import json
                import re
                
                # Extract JSON from response
                json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
                if json_match:
                    facts = json.loads(json_match.group())
                    for fact in facts:
                        self.semantic_memory.store_memory(
                            chat_id=chat_id,
                            content=fact.get('content', ''),
                            memory_type=fact.get('type', 'fact'),
                            importance=fact.get('importance', 0.5)
                        )
                    logger.info(f"Extracted {len(facts)} facts from conversation")
        except Exception as e:
            logger.debug(f"Error extracting facts: {e}")
