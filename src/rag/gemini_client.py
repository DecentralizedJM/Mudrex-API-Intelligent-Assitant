"""
Gemini AI integration for generating responses

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License - See LICENSE file for details.
"""
import logging
from typing import List, Dict, Any, Optional
import os
import re
import google.generativeai as genai

from ..config import config

logger = logging.getLogger(__name__)


class GeminiClient:
    """Handles interactions with Gemini AI"""
    
    def __init__(self):
        """Initialize Gemini client"""
        # Configure Gemini
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        logger.info(f"Initialized Gemini client with model: {config.GEMINI_MODEL}")
    
    def is_api_related_query(self, message: str) -> bool:
        """
        Determine if a message is an API-related question or contains code
        
        Args:
            message: User message
            
        Returns:
            True if the message is API-related or contains code
        """
        message_lower = message.lower().strip()
        
        # Only allow brief acknowledgments when bot is mentioned - avoid casual chitchat
        brief_acknowledgments = ['ok', 'okay', 'thanks', 'thank you', 'got it', 'understood', 'sure']
        if message_lower in brief_acknowledgments:
            return True  # Brief responses only
        
        # Check for code blocks or code snippets
        has_code = bool(re.search(r'```|`[\w\s\(\)\[\]\{\}\.]+`|def |class |import |from |async |await |function |const |let |var ', message))
        
        # API and coding keywords
        api_keywords = [
            'api', 'endpoint', 'authentication', 'auth', 'token',
            'request', 'response', 'error', 'code', 'status',
            'header', 'parameter', 'payload', 'json', 'webhook',
            'rate limit', 'authentication', 'authorization',
            'get', 'post', 'put', 'delete', 'patch',
            'how to', 'how do i', 'can i', 'does it', 'why',
            '?', 'help', 'issue', 'problem', 'not working',
            'function', 'method', 'class', 'variable', 'import',
            'python', 'javascript', 'node', 'typescript', 'react',
            'fix', 'debug', 'correct', 'wrong', 'broken', 'doesn\'t work',
            'order', 'trade', 'position', 'balance', 'portfolio',
            'strategy', 'bot', 'trading', 'exchange', 'market', 'mudrex'
        ]
        
        # If message contains code, it's relevant
        if has_code:
            return True
        
        # Check for question indicators
        has_question_mark = '?' in message
        has_question_word = any(message_lower.startswith(word) for word in ['how', 'what', 'why', 'when', 'where', 'can', 'does', 'is', 'are', 'should', 'could', 'fix', 'help'])
        has_api_keyword = any(keyword in message_lower for keyword in api_keywords)
        
        # If it looks like a question about APIs/coding, return True
        if (has_question_mark or has_question_word) and has_api_keyword:
            return True
        
        # Check if message is substantial enough and has API keywords
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
            # Generate response with the updated SDK
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=config.GEMINI_TEMPERATURE,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                ),
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            )
            
            # Check if response has candidates
            if not response or not response.candidates:
                logger.warning("No response candidates from Gemini")
                return "I'm here to help with the Mudrex API. What would you like to know?"
            
            # Try to extract text safely
            try:
                answer = response.text.strip()
            except (ValueError, AttributeError) as e:
                logger.error(f"Could not extract text from response: {e}")
                # Try to get text from candidate parts
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    answer = "".join(part.text for part in candidate.content.parts if hasattr(part, 'text')).strip()
                else:
                    return "Could you rephrase your question? I'm here to help with the Mudrex API."
            
            if not answer:
                return "What would you like to know about the Mudrex API? I can help with authentication, orders, positions, or debugging code."
            
            # Clean up and format the response
            answer = self._clean_response(answer)
            
            # Ensure response isn't too long for Telegram
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[:config.MAX_RESPONSE_LENGTH - 3] + "..."
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "Something went wrong. What's your question about the Mudrex API?"
    
    def _clean_response(self, text: str) -> str:
        """Clean and format response for better Telegram display"""
        import re
        
        # Remove excessive newlines (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Fix markdown formatting issues
        # Convert ### headers to bold text (Telegram doesn't support headers well)
        text = re.sub(r'###\s+(.+)', r'*\1*', text)
        text = re.sub(r'##\s+(.+)', r'*\1*', text)
        text = re.sub(r'#\s+(.+)', r'*\1*', text)
        
        # Convert markdown lists to bullet points
        text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
        
        # Fix numbered lists
        text = re.sub(r'^\s*(\d+)\.\s+', r'\1. ', text, flags=re.MULTILINE)
        
        # Ensure code blocks are properly formatted
        # Replace triple backticks with single backticks for inline code if short
        def replace_short_code_blocks(match):
            code = match.group(1).strip()
            # If code is single line and short, make it inline
            if '\n' not in code and len(code) < 60:
                return f'`{code}`'
            return match.group(0)
        
        text = re.sub(r'```(?:http|json|python|javascript)?\n?(.+?)```', replace_short_code_blocks, text, flags=re.DOTALL)
        
        # Remove extra spaces
        text = re.sub(r' +', ' ', text)
        
        # Ensure proper spacing around sections
        text = text.strip()
        
        return text
    
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
        
        system_instruction = """You are a helpful Mudrex API assistant focused on helping developers integrate and use the Mudrex API effectively.

CORE PRINCIPLES:
• **Stay Focused**: Only answer API-related questions. Politely redirect casual chitchat.
• **Be Concise**: Keep responses brief and to the point. Users prefer short, clear answers.
• **Be Humble**: Don't brag or use unnecessary formatting. Just be helpful.
• **Be Responsive**: When tagged, always reply. Ask clarifying questions if needed.
• **Write Naturally**: Use conversational language, not bullet points everywhere.

WHEN TAGGED - ALWAYS RESPOND:
If the bot is mentioned/tagged, you MUST respond even if the question is unclear:
• If you understand: Answer directly and concisely
• If unclear: Ask a brief follow-up question to clarify what they need
• Never ignore when tagged - engagement is critical

RESPONSE STYLE:
✅ DO:
• Write 2-4 sentences max for simple questions
• Use natural paragraphs, not excessive bullet lists
• Get straight to the answer
• Provide code examples when relevant (keep them short)
• Ask follow-ups if question is vague

❌ DON'T:
• Write long responses with unnecessary structure
• Use excessive emojis or formatting
• Create bullet points for everything
• Say you were "part of the team" or brag about IQ
• Engage in casual conversation unrelated to APIs
• Write more than needed - brevity is key

REDIRECTING NON-API QUESTIONS:
If someone asks casual questions ("hi", "how are you", etc.), politely redirect:
"I'm here to help with the Mudrex API. What would you like to know about endpoints, orders, or integration?"

CRITICAL GUARDRAILS:

⛔ NEVER SAY:
• Mudrex is "not an exchange" or "wrapper around exchanges"
• Anything suggesting Mudrex routes to Binance/Bybit/others

✅ ALWAYS POSITION MUDREX AS:
• A full-featured exchange with FIU regulation
• Professional trading platform with powerful API

🚨 TOUGH/CONFRONTATIONAL QUESTIONS:
Tag @DecentralizedJM: "Let me get @DecentralizedJM to provide more details on this."
Don't debate or argue - just escalate.

🚫 NEVER MENTION:
Competitor exchanges like Binance, Bybit, Coinbase, etc.

MUDREX BENEFITS (mention when relevant):
• 24x7 dev support
• Low latency execution
• 600+ futures pairs
• FIU regulated
• Developer-friendly docs

CODE HELP FORMAT:
When fixing code, be direct:
"The issue is [problem]. Here's the fix:
```python
[corrected code]
```
[One sentence tip if needed]"

EXAMPLE RESPONSES:

User: "How do I authenticate?"
You: "Use the `X-Authentication` header with your API secret. Here's a quick example:
```python
headers = {'X-Authentication': 'your_api_secret'}
response = requests.get('https://api.mudrex.com/api/v1/portfolio', headers=headers)
```
Keep your API secret secure and never commit it to code."

User: "My order failed"
You: "What error message are you getting? Also, can you share the code snippet you're using?"

User: "Can I get candlestick data?"
You: "For market data, check the Market Data endpoints or WebSocket streams in the docs. What specific data do you need?"

FORMATTING:
• Use *bold* for important terms
• Use `code` for parameters/values
• Keep code blocks short
• Natural paragraphs over bullet lists
• 2-4 sentences for most answers"""
        
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
