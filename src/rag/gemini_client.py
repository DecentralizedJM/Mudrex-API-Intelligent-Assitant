"""
Gemini AI integration for generating responses

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License - See LICENSE file for details.
"""
import logging
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from ..config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Handles interactions with Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini client"""
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        logger.info(f"Initialized Gemini client with model: {config.GEMINI_MODEL}")
    
    def is_api_related_query(self, message: str) -> bool:
        """
        Determine if a message is an API-related question
        
        Args:
            message: User message
            
        Returns:
            True if the message is API-related
        """
        # Quick keyword check first
        api_keywords = [
            'api', 'endpoint', 'authentication', 'auth', 'token',
            'request', 'response', 'error', 'code', 'status',
            'header', 'parameter', 'payload', 'json', 'webhook',
            'rate limit', 'authentication', 'authorization',
            'get', 'post', 'put', 'delete', 'patch',
            'how to', 'how do i', 'can i', 'does it', 'why',
            '?', 'help', 'issue', 'problem', 'not working'
        ]
        
        message_lower = message.lower()
        
        # Check for question indicators
        has_question_mark = '?' in message
        has_question_word = any(message_lower.startswith(word) for word in ['how', 'what', 'why', 'when', 'where', 'can', 'does', 'is', 'are'])
        has_api_keyword = any(keyword in message_lower for keyword in api_keywords)
        
        # If it looks like a question about APIs, return True
        if (has_question_mark or has_question_word) and has_api_keyword:
            return True
        
        # For more complex cases, use Gemini (optional, can be expensive)
        # For now, use keyword-based detection
        return has_api_keyword and len(message.split()) > 3
    
    def generate_response(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response using RAG
        
        Args:
            query: User query
            context_documents: Relevant documents from vector store
            chat_history: Optional chat history for context
            
        Returns:
            Generated response
        """
        # Build context from retrieved documents
        context = self._build_context(context_documents)
        
        # Create prompt
        prompt = self._create_prompt(query, context, chat_history)
        
        try:
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=config.GEMINI_TEMPERATURE,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                )
            )
            
            answer = response.text.strip()
            
            # Ensure response isn't too long for Telegram
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[:config.MAX_RESPONSE_LENGTH - 3] + "..."
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error while processing your question. Please try again or rephrase your query."
    
    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved documents"""
        if not documents:
            return "No relevant documentation found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            source = doc.get('metadata', {}).get('filename', 'Unknown')
            content = doc.get('document', '')
            context_parts.append(f"[Source {i}: {source}]\n{content}\n")
        
        return "\n".join(context_parts)
    
    def _create_prompt(
        self,
        query: str,
        context: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Create the complete prompt for Gemini"""
        
        system_instruction = """You are a helpful API documentation assistant for Mudrex API.

Your role:
- Answer ONLY questions related to Mudrex APIs, endpoints, authentication, and technical integration
- Use the provided documentation context to give accurate answers
- If the answer isn't in the documentation, say so clearly
- Be concise and technical
- Provide code examples when relevant
- Include relevant endpoint names and parameters

IMPORTANT RULES:
- NEVER answer questions about trading strategies, market analysis, or financial advice
- NEVER answer general cryptocurrency or trading questions
- If asked about non-API topics, politely redirect to API-related questions
- Stay strictly within the scope of API documentation

Format your responses clearly with:
- Direct answers first
- Code examples if applicable
- References to specific endpoints or parameters
"""
        
        prompt_parts = [system_instruction]
        
        # Add chat history if available
        if chat_history:
            prompt_parts.append("\n--- Recent Conversation ---")
            for msg in chat_history[-3:]:  # Last 3 messages
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prompt_parts.append(f"{role.capitalize()}: {content}")
        
        # Add context and query
        prompt_parts.extend([
            f"\n--- Relevant Documentation ---\n{context}",
            f"\n--- User Question ---\n{query}",
            "\n--- Your Response ---"
        ])
        
        return "\n".join(prompt_parts)
