"""
Gemini AI integration using the NEW google-genai SDK
Model: gemini-3-flash-preview

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
import os
from typing import List, Dict, Any, Optional
import re

from google import genai
from google.genai import types

from ..config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Handles interactions with Gemini AI using the NEW SDK
    Uses google-genai package with genai.Client()
    """
    
    # Bot personality - Technical Community Manager & Debugger
    SYSTEM_INSTRUCTION = """You are **MudrexBot** - the **Technical Community Manager** for the Mudrex API group.
You are a Senior DevOps Engineer who creates order from chaos.

## core directives
1.  **DEBUG EVERYTHING**: If a user mentions an error, log, or "it's not working", you DO NOT ask "how can I help". You **diagnose** the issue immediately.
2.  **ZERO CHIT-CHAT**: Do not waste pixels. No "Hello! I am here to help". Just the answer.
3.  **DETECT LOGS**: If you see logs (timestamps, `[ERROR]`, tracebacks), analyze them instantly.
    - `409` -> "Conflict: You have multiple bot instances running."
    - `401/1022` -> "Auth Error: Check your API Secret."
    - `429` -> "Rate Limit: Slow down your requests."

## RESPONSE STYLE
- **User**: "My bot is crashing [logs pasted]"
- **Bad**: "I see you are having an issue. Can you share more?"
- **Good**: "❌ **Conflict Error (409)**. You are running two instances of the bot. Kill the old process."

- **User**: "How do I get candles?"
- **Good**: "Use `GET /fapi/v1/klines`. Example: ..."

## DATA PRIVACY (Service Account)
- You use a shared **Service Account**. You can see PUBLIC data (prices) but NOT private data (balances/orders).
- If asked for personal data: "I use a shared public key. Use the Mudrex Dashboard or Claude Desktop for personal account data."

## KNOWLEDGE BASE
- **Telegram 409**: Conflict (Multiple instances)
- **Error -1121**: Invalid Symbol (Use BTCUSDT, not BTC-USDT)
- **Error -1022**: Signature Mismatch (Check system clock and API Secret)

Be the expert they need, not the chatbot they annoy."""
    
    def __init__(self):
        """Initialize Gemini client with NEW SDK"""
        # Set API key in environment if provided via config
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
        
        # Initialize the new client
        self.client = genai.Client()
        self.model_name = config.GEMINI_MODEL
        
        logger.info(f"Initialized Gemini client (new SDK): {self.model_name}")
    
    def is_api_related_query(self, message: str) -> bool:
        """
        Determine if a message is API-related and worth responding to
        
        Args:
            message: User message
            
        Returns:
            True if the message deserves a response
        """
        message_lower = message.lower().strip()
        
        # LOG DETECTION (High Priority)
        # Check for common log patterns
        log_patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # Timestamp YYYY-MM-DD HH:MM:SS
            r'\[(ERROR|WARNING|INFO|DEBUG|CRITICAL)\]',  # Log levels [ERROR]
            r'Traceback \(most recent call last\)',  # Python traceback
            r'Exception:',  # Exception
            r'Error:',  # Generic error
            r'Telegram API Error:',  # Telegram specific
            r'Rate limited, retrying',  # Bot specific log
            r'bot_log\.txt',  # Filenames in paste
        ]
        
        for pattern in log_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                logger.info("Log pattern detected in message")
                return True
        
        # FILTER CHIT-CHAT (Strict Mode)
        # We ignore pure greetings unless they have substance
        # "Hi" -> Ignore (if not tagged)
        # "Hi, help me" -> Respond
        
        # Very short messages that aren't questions - ignore
        if len(message_lower) < 5:
            return False
            
        # Code detection - always respond to code
        code_patterns = [
            r'```',  # Code blocks
            r'`[^`]+`',  # Inline code
            r'def\s+\w+',  # Python functions
            r'class\s+\w+',  # Python classes
            r'import\s+\w+',  # Python imports
            r'from\s+\w+\s+import',  # Python from imports
            r'async\s+def',  # Async functions
            r'await\s+',  # Await calls
            r'function\s+\w+',  # JS functions
            r'const\s+\w+\s*=',  # JS const
            r'let\s+\w+\s*=',  # JS let
            r'requests\.',  # Python requests
            r'fetch\(',  # JS fetch
            r'axios\.',  # Axios
            r'\.get\(|\.post\(|\.put\(|\.delete\(',  # HTTP methods
            r'X-Authentication',  # Mudrex auth header
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        
        # API and trading keywords
        api_keywords = [
            # API terms
            'api', 'endpoint', 'authentication', 'auth', 'token', 'key', 'secret',
            'request', 'response', 'header', 'parameter', 'param', 'payload', 'json',
            'webhook', 'websocket', 'ws', 'sse', 'stream', 'mcp',
            'rate limit', 'throttle', 'quota',
            
            # HTTP
            'get', 'post', 'put', 'delete', 'patch', 'http', 'https', 'url', 'uri',
            'status code', '200', '400', '401', '403', '404', '500',
            
            # Trading terms
            'order', 'trade', 'position', 'balance', 'portfolio', 'margin',
            'leverage', 'liquidation', 'pnl', 'profit', 'loss',
            'buy', 'sell', 'long', 'short', 'market', 'limit', 'stop',
            'sl', 'tp', 'stop loss', 'take profit',
            
            # Mudrex specific
            'mudrex', 'futures', 'perpetual', 'usdt', 'fapi',
            
            # Development
            'python', 'javascript', 'node', 'typescript', 'sdk', 'library',
            'error', 'bug', 'fix', 'debug', 'issue', 'problem', 'help',
            'example', 'sample', 'code', 'snippet', 'how to', 'how do',
            
            # Questions
            'can i', 'does it', 'is it', 'what is', 'why', 'when', 'where',
        ]
        
        # Check for keywords
        keyword_count = sum(1 for kw in api_keywords if kw in message_lower)
        
        # Stricter Rule: Must have at least one keyword AND be substantial
        if keyword_count >= 1 and len(message.split()) > 3:
            return True
        
        return False
    
    def generate_response(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate a response using the NEW Gemini SDK
        
        Args:
            query: User query
            context_documents: Relevant documents from vector store
            chat_history: Optional chat history
            
        Returns:
            Generated response
        """
        # Build the prompt
        prompt = self._build_prompt(query, context_documents, chat_history)
        
        try:
            # Use the new SDK format
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=config.GEMINI_TEMPERATURE,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                )
            )
            
            # Extract response text
            answer = response.text if response.text else ""
            
            if not answer:
                return "What would you like to know about the Mudrex API? I can help with authentication, orders, positions, or MCP setup."
            
            # Clean and format
            answer = self._clean_response(answer)
            
            # Truncate if too long
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[:config.MAX_RESPONSE_LENGTH - 100] + "\n\n_(Response truncated - ask a more specific question!)_"
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "Hit a snag there. What's your API question? I'll give it another shot."
    
    def _build_prompt(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Build the complete prompt"""
        parts = []
        
        # Add context from RAG
        if context_documents:
            context = self._format_context(context_documents)
            parts.append(f"## Relevant Documentation\n{context}\n")
        
        # Add chat history
        if chat_history:
            history = self._format_history(chat_history[-4:])  # Last 4 messages
            parts.append(f"## Recent Conversation\n{history}\n")
        
        # Add the query
        parts.append(f"## User Question\n{query}")
        
        return "\n".join(parts)
    
    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format context documents"""
        if not documents:
            return "No specific documentation found."
        
        formatted = []
        for i, doc in enumerate(documents[:5], 1):  # Max 5 docs
            source = doc.get('metadata', {}).get('filename', 'docs')
            content = doc.get('document', '')[:800]  # Limit each doc
            formatted.append(f"[{source}]\n{content}")
        
        return "\n\n".join(formatted)
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """Format chat history"""
        formatted = []
        for msg in history:
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')[:200]  # Limit length
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
    
    def _clean_response(self, text: str) -> str:
        """Clean and format response for Telegram"""
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Convert markdown headers to bold (Telegram friendly)
        text = re.sub(r'^#{1,3}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)
        
        # Fix bullet points
        text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
        
        # Ensure code blocks are clean
        text = re.sub(r'```(\w+)?\n', r'```\1\n', text)
        
        # Remove extra spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def get_brief_response(self, message_type: str) -> str:
        """Get a brief response for greetings/acknowledgments"""
        import random
        
        responses = {
            'greeting': [
                "Hey! What API question can I help with?",
                "Hi there! Got an API question?",
                "Hey! Need help with the Mudrex API?",
            ],
            'thanks': [
                "Happy to help! Let me know if you need anything else.",
                "Anytime! More questions? I'm here.",
                "You got it! Ping me if you get stuck.",
            ],
            'acknowledgment': [
                "Let me know if you need more help!",
                "Cool! I'm here if you have more questions.",
                "Got it! Anything else?",
            ],
        }
        
        return random.choice(responses.get(message_type, responses['acknowledgment']))
