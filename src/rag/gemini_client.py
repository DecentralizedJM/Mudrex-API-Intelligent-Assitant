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

# Import cache (avoid circular import)
try:
    from .cache import RedisCache
except ImportError:
    RedisCache = None


class GeminiClient:
    """
    Handles interactions with Gemini AI using the NEW SDK
    Uses google-genai package with genai.Client()
    """
    
    # Bot personality - API Copilot focused on code and implementation
    SYSTEM_INSTRUCTION = """You are an API Copilot for the Mudrex Futures API. Your job is to help developers write code, debug API issues, and implement features. Think like GitHub Copilot or a senior dev pair-programming.

## YOUR ROLE: API COPILOT
- **Code-first**: Always provide working code examples (Python/JavaScript). Show how to implement, not just explain.
- **Debug-focused**: When users share errors/logs, analyze the code and fix it.
- **Implementation-oriented**: Help users build features, not just understand concepts.
- Use **live data from MCP** when provided. Prefer that over static docs.
- **Mudrex does NOT have WebSocket or Webhook** — only REST. Be clear about this; suggest polling instead.

## CORE RULES
1. **Code examples are mandatory** for "how to" questions. Show working Python/JS snippets (5-15 lines).
2. **Debug code first**: If they share logs/errors, analyze their code and provide the fix.
3. **Strict on facts**: Only use Mudrex docs/knowledge base. If it's not there, say "I don't have that in my docs" and tag @DecentralizedJM.
4. **Implementation help**: When asked to "automate" or "build", provide a code structure/skeleton they can use.
5. **Be honest**: If Mudrex doesn't support something, say so clearly.

## RESPONSE STYLE
- **Keep it SHORT and CONCISE.** 2-4 sentences + code snippet.
- **Code is the answer**: For implementation questions, show code first, explain briefly.
- **Fix bugs**: When debugging, show the corrected code, explain what was wrong.
- **If you don't know**: "I don't have that in my Mudrex docs. @DecentralizedJM might know more."
- **No fluff**: Skip background/theory unless specifically asked. Get to the code.

Never guess at Mudrex-specific details. It's better to say "I don't know" than give wrong info.

## MUDREX AUTH (important — don't get this wrong)
- Header: `X-Authentication: <your_api_secret>`
- Base URL: `https://trade.mudrex.com/fapi/v1`
- No HMAC, no signatures, no timestamps. Just the one header.
- `Content-Type: application/json` for POST/PATCH/DELETE.

## MUDREX URLS (important distinction)
- **Web Dashboard URL** (for accessing API trading in browser): `www.mudrex.com/pro-trading`
- **REST API Base URL** (for making API calls): `https://trade.mudrex.com/fapi/v1`
- When users ask for "web URL", "dashboard URL", or "API trading URL", they mean the web dashboard: `www.mudrex.com/pro-trading`
- When users ask for "API endpoint", "base URL", or "REST API URL", they mean: `https://trade.mudrex.com/fapi/v1`

## COMMON ERRORS
- **-1121**: Invalid symbol. Use BTCUSDT, not BTC-USDT.
- **-1022**: Auth issue. Check the API secret.
- **Rate limit**: 2 requests/second.

## PRIVACY
This is a shared service account — public data only. No personal balances or orders.

## HANDLING OUT-OF-CONTEXT QUESTIONS
- When given low-similarity documents, search through them carefully using your reasoning
- If the question is about a feature not in docs (e.g., TradingView integrations), use the template response
- Template: "I don't have [feature] info in my Mudrex docs, but it's on our roadmap. Our devs are working on it — stay tuned!"
- If truly nothing relevant: "I don't have that in my Mudrex docs. Can you share more details, or @DecentralizedJM might know?"
- **Never use generic web knowledge or guess** - only use what's in the provided documentation.

## CRITICAL: LEGACY DOCUMENTATION WARNING (INTERNAL - DO NOT MENTION TO USERS)
- **NEVER mix legacy docs with current API**: If a document mentions base URL `https://api.mudrex.com/api/v1`, it is LEGACY and does NOT apply to the current Futures API.
- **Current API base URL is ALWAYS**: `https://trade.mudrex.com/fapi/v1`
- **If you see endpoints in legacy docs (like /klines, /ticker, /depth) that are NOT in current API docs, DO NOT claim they exist.**
- **Before claiming an endpoint exists, verify it's documented for the CURRENT API base URL (`https://trade.mudrex.com/fapi/v1`), not the legacy one.**
- **If an endpoint is only in legacy docs, say SIMPLY: "I don't have that endpoint in my Mudrex Futures API docs. If you need this feature, @DecentralizedJM might know more."**
- **NEVER mention "legacy API" or "legacy docs" to users - just say it's not available. Keep responses simple and helpful.**
- **Always complete the @DecentralizedJM tag - never cut it off.**
- **NEVER make up endpoints or claim they exist based on industry standards or legacy documentation.**"""
    
    def __init__(self):
        """Initialize Gemini client with NEW SDK"""
        # Set API key in environment if provided via config
        if config.GEMINI_API_KEY:
            os.environ['GEMINI_API_KEY'] = config.GEMINI_API_KEY
        
        # Initialize the new client
        self.client = genai.Client()
        self.model_name = config.GEMINI_MODEL
        self.temperature = 0.1 # Low temperature for strict factual answers
        
        # Initialize cache if available
        self.cache = RedisCache() if (config.REDIS_ENABLED and RedisCache) else None
        
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
            'error', 'errors', 'bug', 'fix', 'help',
            # URL and dashboard keywords
            'url', 'dashboard', 'web url', 'website', 'access url', 'www.mudrex.com'
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

    def classify_query_domain(self, query: str) -> str:
        """
        Classify query as Mudrex-specific vs generic trading/system-design.
        
        Returns:
            "mudrex_specific" | "generic_trading"
        """
        q = query.lower()

        # Anything that explicitly mentions Mudrex or its API should go through RAG
        mudrex_markers = [
            "mudrex",
            "fapi",
            "trade.mudrex.com",
            "x-authentication",
            "fapi/v1",
            "mudrex api",
            "mudrex futures",
        ]
        if any(marker in q for marker in mudrex_markers):
            return "mudrex_specific"

        # Generic trading / systems questions (no Mudrex mention)
        generic_markers = [
            "partial fill",
            "pnl",
            "p&l",
            "unrealized",
            "unrealised",
            "kill switch",
            "throttle",
            "rate limit",
            "req/sec",
            "order size",
            "position size",
            "cross-margin",
            "cross margin",
            "isolated margin",
            "liquidation",
            "slippage",
            "spoof liquidity",
            "spoofing",
            "risk engine",
            "risk management",
            "retry",
            "backoff",
            "client-side",
            "design a bot",
            "design this",
            "design an emergency",
            # Strategy and automation
            "strategy",
            "strategies",
            "trading strategy",
            "automate",
            "automation",
            "bot strategy",
            "algorithm",
            "algorithmic",
            "accuracy",
            "win rate",
            "backtest",
            "backtesting",
            # General knowledge questions
            "what do you know",
            "what are the things",
            "what can you",
            "what else",
            "apart from",
            "besides",
        ]
        if any(marker in q for marker in generic_markers):
            return "generic_trading"

        # Safe default: treat as Mudrex-specific (RAG + strict rules)
        return "mudrex_specific"
    
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
            
            return answer
            
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "Something went wrong on my end — not your code. Try again in a sec?"

    def generate_generic_trading_answer(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate an answer for generic trading / system-design questions.
        This persona is allowed to use general trading knowledge, but MUST NOT
        make claims about Mudrex-specific behavior or features.
        """
        # System prompt focused on API implementation and code for generic trading/system questions
        generic_system_instruction = """
You are an API Copilot helping developers implement trading bots and risk systems. Focus on CODE and IMPLEMENTATION, not theory.

## ROLE: API IMPLEMENTATION COPILOT
- **Code-first**: Provide working code examples (Python/JavaScript) for implementing features.
- **Implementation help**: When asked to "automate", "design", or "build", show code structure they can use.
- **Generic patterns**: Explain how typical futures exchanges work, but always in the context of "how to implement this in code".
- **Strategy automation**: When users ask about strategies, help them code it — show the implementation, not just explain the concept.
- Answer in generic terms: say "on a typical exchange" or "in most futures venues".

## HARD RULES
- **Always provide code** for implementation questions. Show Python/JS examples (10-20 lines).
- Do NOT claim what Mudrex supports unless explicitly referencing Mudrex AND quoting from Mudrex docs.
- If the user mentions Mudrex but there's no Mudrex docs in context, answer generically with code examples.
- **No strategy guarantees 99% accuracy** — be honest, but still help them code it.

## STYLE
- **Code is the answer**: Show implementation code first, brief explanation after.
- **Keep it SHORT**: 2-3 sentences + code snippet (10-20 lines).
- **Practical**: Focus on "how to code it", not "how it works theoretically".
- **Fix bugs**: If they share code with issues, show the corrected version.
- No long explanations — get to the code.

## EXAMPLE RESPONSES
User: "How do I throttle requests?"
You: "Use a token bucket or rate limiter. Here's Python:

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = deque()
    
    def wait_if_needed(self):
        now = time.time()
        while self.requests and self.requests[0] < now - self.window:
            self.requests.popleft()
        if len(self.requests) >= self.max_requests:
            sleep_time = self.window - (now - self.requests[0])
            time.sleep(sleep_time)
        self.requests.append(time.time())

# Usage
limiter = RateLimiter(2, 1.0)  # 2 req/sec
limiter.wait_if_needed()
# Make API call
```
""".strip()

        parts: List[str] = []
        if chat_history:
            history = self._format_history(chat_history[-4:])
            parts.append(f"Recent conversation (for context):\n{history}")
        parts.append(f"User question:\n{query}")
        prompt = "\n\n".join(parts)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=generic_system_instruction,
                    temperature=0.3,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                ),
            )
            answer = response.text if response.text else ""
            if not answer:
                return "I'm not able to walk through that right now. Try asking again in a bit?"

            answer = self._clean_response(answer)
            return answer
        except Exception as e:
            logger.error(f"Error generating generic trading answer: {e}", exc_info=True)
            return "Something went wrong on my side while thinking that through. Try again in a moment?"

    def validate_document_relevancy(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate that retrieved documents actually answer the query (Reliable RAG).
        Uses Gemini to score relevancy and filter out irrelevant docs.
        
        Args:
            query: User query
            documents: List of retrieved documents with metadata and similarity
            
        Returns:
            Filtered list of documents with relevancy >= RELEVANCY_THRESHOLD
        """
        if not documents:
            return []
        
        # If only 1-2 docs, validate them individually
        # If more, batch validate for efficiency
        validated_docs = []
        
        for doc in documents:
            # Check cache first
            if self.cache:
                cached = self.cache.get_validation(query, doc)
                if cached:
                    if cached.get('relevant', False) and cached.get('score', 0) >= config.RELEVANCY_THRESHOLD:
                        doc['relevancy_score'] = cached.get('score', 0)
                        validated_docs.append(doc)
                        logger.debug(f"Document validated (cached): score={cached.get('score', 0):.2f}")
                    else:
                        logger.debug(f"Document filtered out (cached): score={cached.get('score', 0):.2f}")
                    continue  # Skip Gemini call
            
            # Call Gemini for validation
            doc_text = doc.get('document', '')[:1000]  # Limit for validation prompt
            validation_prompt = f"""Does this document answer the user's question?

User Question: {query}

Document:
{doc_text}

Answer with ONLY a JSON object:
{{"relevant": true/false, "score": 0.0-1.0, "reason": "brief explanation"}}

Score 0.0-1.0 based on how well the document answers the question. Only return true if score >= 0.6."""
            
            try:
                import time
                max_retries = 2
                retry_delay = 1.0
                
                for attempt in range(max_retries + 1):
                    try:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=validation_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.1
                            )
                        )
                        
                        # Check if response.text is None or empty
                        if not response.text:
                            logger.warning(f"Empty response from Gemini (attempt {attempt + 1})")
                            if attempt < max_retries:
                                time.sleep(retry_delay * (attempt + 1))
                                continue
                            # On final attempt, include doc to be safe
                            validated_docs.append(doc)
                            break
                        
                        import json
                        result = json.loads(response.text)
                        
                        # Cache the result
                        if self.cache:
                            self.cache.set_validation(query, doc, result)
                        
                        if result.get('relevant', False) and result.get('score', 0) >= config.RELEVANCY_THRESHOLD:
                            doc['relevancy_score'] = result.get('score', 0)
                            validated_docs.append(doc)
                            logger.debug(f"Document validated: score={result.get('score', 0):.2f}")
                        else:
                            logger.debug(f"Document filtered out: score={result.get('score', 0):.2f}")
                        break  # Success, exit retry loop
                        
                    except Exception as api_error:
                        error_str = str(api_error)
                        # Check if it's a 503 or rate limit error
                        if '503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower():
                            if attempt < max_retries:
                                wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                                logger.warning(f"Gemini overloaded (503), retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                                time.sleep(wait_time)
                                continue
                            else:
                                logger.warning(f"Gemini still overloaded after {max_retries + 1} attempts, including doc to be safe")
                                validated_docs.append(doc)
                                break
                        else:
                            # Other errors - re-raise to outer except
                            raise
                            
            except Exception as e:
                logger.warning(f"Error validating document relevancy: {e}")
                # On error, include the doc to be safe (better than filtering out good docs)
                validated_docs.append(doc)
        
        logger.info(f"Validated {len(validated_docs)}/{len(documents)} documents as relevant")
        return validated_docs
    
    def rerank_documents(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents using LLM-based scoring (Reranking technique).
        Returns top_k most relevant documents.
        
        Args:
            query: User query
            documents: List of documents to rerank
            top_k: Number of top documents to return (defaults to RERANK_TOP_K)
            
        Returns:
            Reranked list of top_k documents
        """
        if not documents:
            return []
        
        if top_k is None:
            top_k = config.RERANK_TOP_K
        
        if len(documents) <= top_k:
            return documents
        
        # Check cache first
        if self.cache:
            cached_indices = self.cache.get_rerank(query, documents)
            if cached_indices:
                # Reorder documents using cached indices
                ranked_docs = []
                for idx in cached_indices[:top_k]:
                    if 0 <= idx < len(documents):
                        ranked_docs.append(documents[idx])
                if ranked_docs:
                    logger.info(f"Reranked {len(ranked_docs)} documents (cached)")
                    return ranked_docs
        
        # Create a prompt to score all documents
        doc_list = []
        for i, doc in enumerate(documents):
            doc_text = doc.get('document', '')[:500]  # Limit per doc
            doc_list.append(f"[{i}] {doc_text}")
        
        rerank_prompt = f"""Rank these documents by relevance to the user's question.

User Question: {query}

Documents:
{chr(10).join(doc_list)}

Return ONLY a JSON array of document indices (0-based) sorted by relevance (most relevant first):
[0, 2, 1, ...]"""
        
        try:
            import time
            max_retries = 2
            retry_delay = 1.0
            
            for attempt in range(max_retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=rerank_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    
                    # Check if response.text is None or empty
                    if not response.text:
                        logger.warning(f"Empty response from Gemini for reranking (attempt {attempt + 1})")
                        if attempt < max_retries:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        # On final attempt, fall back to similarity order
                        break
                    
                    import json
                    ranked_indices = json.loads(response.text)
                    
                    # Cache the result
                    if self.cache:
                        self.cache.set_rerank(query, documents, ranked_indices)
                    
                    # Reorder documents based on ranking
                    ranked_docs = []
                    for idx in ranked_indices[:top_k]:
                        if 0 <= idx < len(documents):
                            ranked_docs.append(documents[idx])
                    
                    # If ranking failed, fall back to similarity-based order
                    if not ranked_docs:
                        ranked_docs = sorted(documents, key=lambda x: x.get('similarity', 0), reverse=True)[:top_k]
                    
                    logger.info(f"Reranked {len(ranked_docs)} documents")
                    return ranked_docs
                    
                except Exception as api_error:
                    error_str = str(api_error)
                    # Check if it's a 503 or rate limit error
                    if '503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower():
                        if attempt < max_retries:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Gemini overloaded (503) for reranking, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.warning(f"Gemini still overloaded after {max_retries + 1} attempts, using similarity order")
                            break
                    else:
                        # Other errors - re-raise to outer except
                        raise
                        
        except Exception as e:
            logger.warning(f"Error reranking documents: {e}, using similarity order")
        
        # Fall back to similarity-based ranking
        return sorted(documents, key=lambda x: x.get('similarity', 0), reverse=True)[:top_k]
    
    def transform_query(self, query: str) -> str:
        """
        Transform query to improve retrieval (Query Transformations technique).
        - Step-back prompting: Generate broader query for context
        - Query expansion: Add relevant synonyms/keywords
        
        Args:
            query: Original user query
            
        Returns:
            Transformed query
        """
        # Check cache first
        if self.cache:
            cached = self.cache.get_transform(query)
            if cached:
                logger.info(f"Query transformed (cached): '{query}' -> '{cached}'")
                return cached
        
        transform_prompt = f"""Transform this query to improve document retrieval for a Mudrex Futures API documentation search.

Original Query: {query}

Analyze the query and:
1. **Extract core intent**: What is the user really asking about?
2. **Identify indirect questions**: If the question is indirect, rewrite it more directly
3. **Break down complex questions**: If it's multi-part, extract the main API-related part
4. **Add synonyms**: "endpoint" -> "API endpoint", "route", "endpoint"
5. **Expand abbreviations**: "auth" -> "authentication", "SL" -> "stop loss"
6. **Add context**: If it's about implementation, add "how to" or "API" keywords

Examples:
- "my bot is broken" -> "API error troubleshooting debugging"
- "how do I automate this" -> "API automation order placement implementation"
- "something wrong with orders" -> "order API error troubleshooting"

Return ONLY the transformed query, nothing else."""
        
        try:
            import time
            max_retries = 2
            retry_delay = 1.0
            
            for attempt in range(max_retries + 1):
                try:
                    response = self.client.models.generate_content(
                        model=self.model_name,
                        contents=transform_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2
                        )
                    )
                    
                    # Check if response.text is None or empty
                    if not response.text:
                        logger.warning(f"Empty response from Gemini for query transformation (attempt {attempt + 1})")
                        if attempt < max_retries:
                            time.sleep(retry_delay * (attempt + 1))
                            continue
                        # On final attempt, fall back to original query
                        break
                    
                    transformed = response.text.strip()
                    if transformed and len(transformed) > 5:
                        logger.info(f"Query transformed: '{query}' -> '{transformed}'")
                        # Cache the result
                        if self.cache:
                            self.cache.set_transform(query, transformed)
                        return transformed
                    else:
                        # Empty or too short transformation, fall back
                        break
                        
                except Exception as api_error:
                    error_str = str(api_error)
                    # Check if it's a 503 or rate limit error
                    if '503' in error_str or 'UNAVAILABLE' in error_str or 'overloaded' in error_str.lower():
                        if attempt < max_retries:
                            wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Gemini overloaded (503) for query transform, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.warning(f"Gemini still overloaded after {max_retries + 1} attempts, using original query")
                            break
                    else:
                        # Other errors - re-raise to outer except
                        raise
                        
        except Exception as e:
            logger.warning(f"Error transforming query: {e}")
        
        # Fall back to original query
        return query
    
    def _get_missing_feature_response(self, query: str) -> Optional[str]:
        """
        Check if query is about a known missing feature and return template response.
        
        Args:
            query: User query
            
        Returns:
            Template response if it's a known missing feature, None otherwise
        """
        query_lower = query.lower()
        
        missing_features = {
            'tradingview': "I don't have TradingView integration info in my Mudrex docs, but it's on our roadmap. Our devs are working on it — stay tuned!",
            'trading view': "I don't have TradingView integration info in my Mudrex docs, but it's on our roadmap. Our devs are working on it — stay tuned!",
            'webhook': "Mudrex doesn't support webhooks yet — only REST APIs. It's on our roadmap though!",
            'websocket': "Mudrex doesn't support WebSockets — only REST APIs. Use REST polling for real-time-like data.",
        }
        
        for keyword, response in missing_features.items():
            if keyword in query_lower:
                return response
        
        return None
    
    def generate_response_with_context_search(
        self,
        query: str,
        low_similarity_docs: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None,
        mcp_context: Optional[str] = None,
    ) -> str:
        """
        Generate response using Gemini's reasoning on all available docs.
        No Google Search - uses Gemini's built-in knowledge + provided docs.
        Checks for missing features template responses.
        
        Args:
            query: User query
            low_similarity_docs: Documents found with lower threshold (may be empty)
            chat_history: Optional chat history
            mcp_context: Optional MCP context
            
        Returns:
            Generated response
        """
        # First check for missing features template
        template_response = self._get_missing_feature_response(query)
        if template_response:
            logger.info("Using template response for missing feature")
            return template_response
        
        # Build prompt with low-similarity docs (if any)
        prompt = self._build_prompt(query, low_similarity_docs, chat_history, mcp_context)
        
        # For no-docs case, use smart fallback with Gemini's knowledge
        if not low_similarity_docs:
            return self._generate_smart_fallback(query, chat_history, mcp_context)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_INSTRUCTION,
                    temperature=self.temperature,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                )
            )
            
            answer = response.text if response.text else ""
            
            if not answer:
                return "I don't have that in my Mudrex docs. Can you share more details, or @DecentralizedJM might know?"
            
            answer = self._clean_response(answer)
            
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[:config.MAX_RESPONSE_LENGTH - 100] + "\n\n_(Cut short — ask something more specific?)_"
            
            return answer
        except Exception as e:
            logger.error(f"Error in context search response: {e}", exc_info=True)
            return "Something went wrong on my end — not your code. Try again in a sec?"
    
    def _generate_smart_fallback(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        mcp_context: Optional[str] = None,
    ) -> str:
        """
        Generate helpful response using Gemini's knowledge when no Mudrex docs found.
        Clearly marks as generic/non-Mudrex knowledge.
        """
        # Check for missing features first
        template_response = self._get_missing_feature_response(query)
        if template_response:
            return template_response
        
        # Build context-aware prompt
        parts = []
        if chat_history:
            history = self._format_history(chat_history[-3:])  # Last 3 messages
            parts.append(f"Recent conversation:\n{history}")
        if mcp_context:
            parts.append(f"Live data context:\n{mcp_context}")
        
        context_str = "\n\n".join(parts) if parts else ""
        
        fallback_prompt = f"""The user asked: "{query}"

{context_str}

## Situation
This question isn't covered in the Mudrex API documentation I have access to. However, as an API Copilot, I should still try to help using general API/trading knowledge.

## Your Task
Provide a helpful response that:
1. **Acknowledges** this isn't in Mudrex docs
2. **Helps anyway** using general knowledge/patterns
3. **Shows code** if it's an implementation question
4. **Marks as generic** - clearly state this is general knowledge, not Mudrex-specific
5. **Offers Mudrex help** - suggest checking Mudrex docs or asking @DecentralizedJM for Mudrex-specific details

## Response Style
- 2-4 sentences + code snippet (if applicable)
- Start with: "This isn't in my Mudrex docs, but..."
- Provide working code examples for implementation questions
- Keep it practical and code-focused

Generate a helpful response:"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=fallback_prompt,
                config=types.GenerateContentConfig(
                    system_instruction="You are an API Copilot. Help developers with code and implementation, even when you don't have specific documentation. Always provide code examples for implementation questions.",
                    temperature=0.4,
                    max_output_tokens=config.GEMINI_MAX_TOKENS,
                )
            )
            
            answer = response.text if response.text else ""
            if not answer:
                return "I don't have that in my Mudrex docs. Can you share more details, or @DecentralizedJM might know?"
            
            answer = self._clean_response(answer)
            
            # Ensure it acknowledges it's not from Mudrex docs
            if "mudrex" not in answer.lower()[:100] and "docs" not in answer.lower()[:100]:
                answer = f"This isn't in my Mudrex docs, but {answer.lower()}"
            
            return answer
        except Exception as e:
            logger.error(f"Error in smart fallback: {e}", exc_info=True)
            return "I don't have that in my Mudrex docs. Can you share more details, or @DecentralizedJM might know?"
    
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
        legacy_warning_added = False
        
        for i, doc in enumerate(documents[:5], 1):  # Max 5 docs
            source = doc.get('metadata', {}).get('filename', 'docs')
            content = doc.get('document', '')[:800]  # Limit each doc
            
            # Check if this is legacy documentation (old API base URL)
            is_legacy = (
                'https://api.mudrex.com/api/v1' in content or
                'api.mudrex.com/api/v1' in content or
                'legacy' in source.lower() or
                'LEGACY' in content[:200]  # Check first 200 chars for legacy warning
            )
            
            if is_legacy and not legacy_warning_added:
                formatted.append("⚠️ WARNING: Some documents below are from the LEGACY API (https://api.mudrex.com/api/v1) and do NOT apply to the current Futures API (https://trade.mudrex.com/fapi/v1). Do NOT claim endpoints from legacy docs exist in the current API.")
                legacy_warning_added = True
            
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
            # Check if response.text is None or empty
            if not response.text:
                logger.warning("Empty response from Gemini for intent parsing")
                return {"action": "NONE"}
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
