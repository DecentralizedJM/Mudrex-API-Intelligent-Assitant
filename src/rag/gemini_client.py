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
    
    # Bot personality - friendly Mudrex API helper (no WebSocket/Webhook)
    SYSTEM_INSTRUCTION = """You help developers with the Mudrex Futures API. Friendly and direct — skip the fluff but don't be robotic.

## ROLE
- Use **live data from MCP** when provided (section "Live data (MCP)"). Prefer that over static docs.
- **Mudrex does NOT have WebSocket or Webhook** — only REST. Be clear about this when asked; suggest polling instead.

## CORE RULES
1. **Don't make stuff up.** Answer only from the docs, knowledge base, or MCP data provided. If it's not there, say so.
2. **For Mudrex-specific stuff** (endpoints, errors, behavior): use only what's in the docs. If you don't have it, say "I don't have that in my docs" and tag @DecentralizedJM.
3. **Debug first.** If they share logs or code, analyze that before answering.
4. **Show code.** For "how to" questions, give Python or JS examples. Keep them simple and working.
5. **Be honest about limits.** If Mudrex doesn't support something, say so clearly.

## RESPONSE STYLE
- **If you know it**: Answer directly. Include code when helpful.
- **If you're not sure**: Say "I'm not 100% sure, but..." and be clear it's an estimate.
- **If you don't know**: "I don't have that in my docs. @DecentralizedJM might know more."

Never guess at Mudrex-specific details. It's better to say "I don't know" than give wrong info.

## MUDREX AUTH (important — don't get this wrong)
- Header: `X-Authentication: <your_api_secret>`
- Base URL: `https://trade.mudrex.com/fapi/v1`
- No HMAC, no signatures, no timestamps. Just the one header.
- `Content-Type: application/json` for POST/PATCH/DELETE.

## COMMON ERRORS
- **-1121**: Invalid symbol. Use BTCUSDT, not BTC-USDT.
- **-1022**: Auth issue. Check the API secret.
- **Rate limit**: 2 requests/second.

## PRIVACY
This is a shared service account — public data only. No personal balances or orders."""
    
    def __init__(self):
        """Initialize Gemini client with NEW SDK"""
        # Set API key in environment if provided via config
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
        
        # Initialize the new client
        self.client = genai.Client()
        self.model_name = config.GEMINI_MODEL
        self.temperature = 0.1 # Low temperature for strict factual answers
        
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
        
        # HTTP status codes and Mudrex error codes (High Priority for troubleshooting)
        http_status_patterns = [
            r'\b[45]\d{2}\b',       # 4xx and 5xx errors (404, 500, 401, etc.)
            r'-\d{4}\b',            # Mudrex error codes like -1121, -1022
            r'\bnot working\b',     # Common troubleshooting phrase
            r'\bfailed\b',          # Connection/request failed
            r'\btimeout\b',         # Timeout errors
        ]
        
        for pattern in http_status_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                logger.info("HTTP status or error pattern detected")
                return True
        
        # API and trading keywords
        # STRONG keywords (sufficient alone when msg length > 5)
        strong_keywords = [
            'mudrex', 'fapi', 'api', 'endpoint', 'webhook', 'websocket', 'mcp',
            'x-authentication', 'auth', 'token', 'secret', 'jwt', 'key',
            'btc', 'eth', 'usdt', 'futures', 'perpetual',
            'rest', 'trade.mudrex.com', 'fapi/v1', 'http', 'https',
            # Troubleshooting keywords
            'status', 'response', 'connection', 'broken', 'issue', 'debug',
            'unauthorized', 'forbidden', 'invalid',
            # Error-related (moved from weak - these are clearly API help requests)
            'error', 'errors', 'bug', 'fix', 'help'
        ]
        
        # WEAK keywords (need 2+ when no STRONG, to reduce false positives)
        weak_keywords = [
            'price', 'order', 'trade', 'position', 'balance', 'margin',
            'leverage', 'liquidation', 'profit', 'loss', 'buy', 'sell',
            'long', 'short', 'market', 'limit', 'stop',
            'code', 'python', 'javascript', 'rate', 'latency',
            'request', 'header', 'body', 'json', 'data'
        ]
        
        strong_count = sum(1 for kw in strong_keywords if kw in message_lower)
        weak_count = sum(1 for kw in weak_keywords if kw in message_lower)
        
        # LOGIC: Any STRONG -> Pass. Otherwise 2+ WEAK -> Pass.
        if strong_count >= 1:
            return True
        if weak_count >= 2:
            return True
        return False
    
    def generate_response(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        mcp_context: Optional[str] = None,
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
        prompt = self._build_prompt(query, context_documents, chat_history, mcp_context)
        
        try:
            # Use the new SDK format
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=self.temperature,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                )
            )
            
            # Extract response text
            answer = response.text if response.text else ""
            
            if not answer:
                return "I don't have a specific answer for that. Can you share more details — like the endpoint you're hitting, the error code, or your code?"
            
            # Clean and format
            answer = self._clean_response(answer)
            
            # Truncate if too long
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[:config.MAX_RESPONSE_LENGTH - 100] + "\n\n_(Cut short — ask something more specific?)_"
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "Something went wrong on my end — not your code. Try again in a sec?"

    def generate_response_with_grounding(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        mcp_context: Optional[str] = None,
    ) -> str:
        """
        Generate a response using Gemini with Google Search grounding.
        Used when RAG has no docs but the query is API-related (out-of-context).
        """
        prompt = self._build_prompt(query, context_documents, chat_history, mcp_context)
        model = config.GEMINI_GROUNDING_MODEL
        try:
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=self.temperature,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                    tools=[grounding_tool],
                ),
            )
            answer = response.text if response.text else ""
            if not answer:
                return "Couldn't find much on that. Can you give me more details or rephrase?"
            answer = self._clean_response(answer)
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[: config.MAX_RESPONSE_LENGTH - 100] + "\n\n_(Cut short — ask something more specific?)_"
            return answer
        except Exception as e:
            logger.error(f"Error in grounded response: {e}", exc_info=True)
            return "Something went wrong on my end — not your code. Try again in a sec?"
    
    def _build_prompt(
        self,
        query: str,
        context_documents: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        mcp_context: Optional[str] = None,
    ) -> str:
        """Build the complete prompt"""
        parts = []
        
        # Live data from MCP (use whenever provided — AI co-pilot)
        if mcp_context:
            parts.append(f"## Live data (MCP)\n{mcp_context}\n")
        
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
    
    def parse_learning_instruction(self, text: str) -> Dict[str, Any]:
        """
        Analyze text to see if it's a teaching instruction. Handles unstructured forms.
        Returns:
            {'action': 'LEARN' | 'SET_FACT' | 'NONE', 'content': str, 'key': str?, 'value': str?}
        """
        prompt = f"""
        Analyze this admin message for teaching intent. Handle unstructured forms.
        
        Message: "{text}"
        
        Identify:
        1. SET_FACT: A strict rule/constant (e.g. "Latency is 200ms", "Rate limit is 5", "X is always Y").
        2. LEARN: General knowledge to remember. Examples:
           - "From now on...", "Remember: ...", "If users ask X, say Y"
           - "New endpoint: ...", "We don't support X", FAQ-style Q&A, plain paragraphs
        3. NONE: Regular chat or question, not teaching.
        
        For LEARN, set "content" to a cleaned, normalized version suitable for embedding (one or a few sentences).
        For SET_FACT, set "key" (e.g. LATENCY) and "value".
        
        Return JSON ONLY:
        {{"action": "SET_FACT" | "LEARN" | "NONE", "key": "KEY" or null, "value": "..." or null, "content": "..." or null}}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            import json
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            return {"action": "NONE"}

    def get_brief_response(self, message_type: str) -> str:
        """Get a brief response for greetings/acknowledgments"""
        import random
        
        responses = {
            'greeting': [
                "What's up?",
                "Hey — what do you need help with?",
                "Yo, what's the issue?",
            ],
            'thanks': [
                "No problem!",
                "Sure thing.",
                "Glad that helped.",
            ],
            'acknowledgment': [
                "Let me know if you need anything else.",
                "Cool, just ping me if something comes up.",
                "Got it.",
            ],
        }
        
        return random.choice(responses.get(message_type, responses['acknowledgment']))
