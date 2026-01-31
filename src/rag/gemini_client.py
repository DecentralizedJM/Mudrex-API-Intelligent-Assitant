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
from google.genai.errors import ClientError

from ..config import config

# Import error reporter (avoid circular import)
try:
    from ..lib.error_reporter import report_error
except ImportError:
    report_error = None

logger = logging.getLogger(__name__)

# Import cache (avoid circular import)
try:
    from .cache import RedisCache
except ImportError:
    RedisCache = None

# Import error reporter (avoid circular import)
try:
    from ..lib.error_reporter import report_error_sync
    HAS_ERROR_REPORTER = True
except ImportError:
    report_error_sync = None
    HAS_ERROR_REPORTER = False


def _report_gemini_error(error: Exception, context: dict = None):
    """Helper to report Gemini API errors synchronously"""
    if HAS_ERROR_REPORTER and report_error_sync:
        try:
            error_context = {"component": "gemini_client"}
            if context:
                error_context.update(context)
            report_error_sync(error, "exception", error_context)
        except Exception:
            pass  # Don't let error reporting break the bot


class GeminiClient:
    """
    Handles interactions with Gemini AI using the NEW SDK
    Uses google-genai package with genai.Client()
    """
    
    # Bot personality - API Copilot (like GitHub Copilot for Mudrex API)
    SYSTEM_INSTRUCTION = """You are an API Copilot for Mudrex Futures. Think GitHub Copilot — code-first, brief, helpful.

## ROLE
- Code-first: Show working Python/JS snippets (5-15 lines).
- Debug: Analyze errors/logs, provide the fix.
- Build: Help implement features with code skeletons.
- Use live MCP data when provided.
- Mudrex = REST only. No WebSockets, no Webhooks. Suggest polling.

## RULES
1. Code examples mandatory for "how to" questions.
2. Debug first: See error? Show the fix.
3. Facts only: Use Mudrex docs. Don't guess.
4. Be honest: If Mudrex doesn't support it, say so.

## RESPONSE STYLE
- SHORT. 2-4 sentences + code.
- Code is the answer.
- No fluff. Skip theory unless asked.

## AUTH
- Header: `X-Authentication: <api_secret>`
- Base: `https://trade.mudrex.com/fapi/v1`
- No HMAC, no signing. Just the header.

## URLS
- Dashboard: `www.mudrex.com/pro-trading`
- API Base: `https://trade.mudrex.com/fapi/v1`

## ERRORS
- -1121: Invalid symbol (use BTCUSDT, not BTC-USDT)
- -1022: Auth issue
- Rate limit: 2 req/sec

## WHEN YOU DON'T KNOW
- NEVER say "it's not in my documents" or "not in my docs" or "I don't have that in my Mudrex docs"
- Instead: "Couldn't find that. Docs: https://docs.trade.mudrex.com — @DecentralizedJM can help with specifics."
- Keep it brief. Link to docs. Tag @DecentralizedJM.
- Don't guess or make things up.

## LEGACY DOCS (internal — don't mention to users)
- If doc shows `https://api.mudrex.com/api/v1` = LEGACY, ignore it.
- Current API = `https://trade.mudrex.com/fapi/v1` only.
- Don't claim endpoints exist unless in current docs.
- If asked about legacy endpoints: "Couldn't find that. Docs: https://docs.trade.mudrex.com — @DecentralizedJM can help."
- Never mention "legacy" to users.

## WHEN USER SHARES API SECRET
- If the user's message contains what looks like a shared API secret (e.g. they pasted their key or said "my API secret is ..." or "api key is ..."), you MUST end your response with this warning (include it verbatim):
  "⚠️ **Your API key is now exposed.** Please rotate or revoke it immediately in the API Management Dashboard. Do not use this key anymore."
- Give the connection/code help first, then add this warning. Do not skip the warning when they have shared their key."""
    
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
                return "Couldn't find that. Can you share more details — endpoint, error code, or your code? Or check the docs: https://docs.trade.mudrex.com"
            
            # Clean and format
            answer = self._clean_response(answer)
            
            return answer
            
        except ClientError as e:
            logger.error(f"Gemini API error generating response: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "generate_response", "model": self.model_name, "error_type": "ClientError"})
            return "Something went wrong on my end — not your code. Try again in a sec?"
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "generate_response"})
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
        except ClientError as e:
            logger.error(f"Gemini API error generating generic trading answer: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "generate_generic_trading_answer", "error_type": "ClientError"})
            return "Something went wrong on my side while thinking that through. Try again in a moment?"
        except Exception as e:
            logger.error(f"Error generating generic trading answer: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "generate_generic_trading_answer"})
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
                        
                    except ClientError as api_error:
                        error_str = str(api_error)
                        # Report API errors
                        _report_gemini_error(api_error, {"method": "validate_document_relevancy", "attempt": attempt + 1, "error_type": "ClientError"})
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
                    except Exception as api_error:
                        error_str = str(api_error)
                        _report_gemini_error(api_error, {"method": "validate_document_relevancy", "attempt": attempt + 1})
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
                _report_gemini_error(e, {"method": "validate_document_relevancy", "error_type": "validation_failure"})
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
                    
                except ClientError as api_error:
                    error_str = str(api_error)
                    _report_gemini_error(api_error, {"method": "rerank_documents", "attempt": attempt + 1, "error_type": "ClientError"})
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
                        # Other errors - break and fall back
                        break
                except Exception as api_error:
                    error_str = str(api_error)
                    _report_gemini_error(api_error, {"method": "rerank_documents", "attempt": attempt + 1, "error_type": "ClientError"})
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
                        # Other errors - break and fall back
                        break
                except Exception as api_error:
                    error_str = str(api_error)
                    _report_gemini_error(api_error, {"method": "rerank_documents", "attempt": attempt + 1})
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
                        # Other errors - break and fall back
                        break
                        
        except Exception as e:
            logger.warning(f"Error reranking documents: {e}, using similarity order")
            _report_gemini_error(e, {"method": "rerank_documents", "error_type": "rerank_failure"})
        
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
                        
                except ClientError as api_error:
                    error_str = str(api_error)
                    _report_gemini_error(api_error, {"method": "transform_query", "attempt": attempt + 1, "error_type": "ClientError"})
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
                        # Other errors - break and return original query
                        break
                except Exception as api_error:
                    error_str = str(api_error)
                    _report_gemini_error(api_error, {"method": "transform_query", "attempt": attempt + 1})
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
                        # Other errors - break and return original query
                        break
                        
        except Exception as e:
            logger.warning(f"Error transforming query: {e}")
            _report_gemini_error(e, {"method": "transform_query", "error_type": "transform_failure"})
        
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
            'tradingview': "TradingView integration isn't available yet — it's on the roadmap. Stay tuned!",
            'trading view': "TradingView integration isn't available yet — it's on the roadmap. Stay tuned!",
            'webhook': "Mudrex doesn't support webhooks yet — only REST APIs. It's on our roadmap though!",
            'websocket': "Mudrex doesn't support WebSockets — only REST APIs. Use REST polling for real-time-like data.",
            # Trade ideas / signals — community broadcaster (no REST "signals" endpoint on Mudrex trade API)
            'trade ideas': "There’s no trade-ideas endpoint on the Mudrex trade API. For signals, use the community broadcaster: when signals are published, a WebSocket streams them. Install the SDK to receive and execute them: https://github.com/DecentralizedJM/TIA-Service-Broadcaster",
            'signals': "There’s no signals endpoint on the Mudrex trade API. For trade ideas/signals, use the community broadcaster — when signals are published, a WebSocket streams them. Install the SDK to receive and execute: https://github.com/DecentralizedJM/TIA-Service-Broadcaster",
            'signal': "For trade ideas/signals, use the community broadcaster — WebSocket streams when signals are published. Install the SDK to receive and execute: https://github.com/DecentralizedJM/TIA-Service-Broadcaster",
            # SDK / library — community Python SDK
            'sdk': "There's a community-built Python SDK that makes onboarding easier: https://github.com/DecentralizedJM/mudrex-api-trading-python-sdk — supports 500+ pairs, symbol-first trading, MCP, and handles auth for you.",
            'python sdk': "Try the community Python SDK: https://github.com/DecentralizedJM/mudrex-api-trading-python-sdk — symbol-first trading, 500+ pairs, built-in MCP support.",
            'client library': "Check out the community Python SDK: https://github.com/DecentralizedJM/mudrex-api-trading-python-sdk — handles auth, pagination, and has MCP support.",
            'library': "There's a community Python SDK: https://github.com/DecentralizedJM/mudrex-api-trading-python-sdk — makes trading easier with symbol-first orders and built-in MCP.",
        }
        
        for keyword, response in missing_features.items():
            if keyword in query_lower:
                return response
        
        return None
    
    def _get_api_key_usage_response(self, query: str) -> Optional[str]:
        """
        When user asks what to do with their API key / how to use it / guide me,
        return Mudrex-specific auth (X-Authentication only, no HMAC).
        """
        q = query.lower()
        key_phrases = ('key', 'keys', 'api key', 'api secret', 'secret')
        help_phrases = ('what to do', 'how to use', 'guide me', 'don\'t know what to do', 'generated the key', 'generated the keys', 'help me', 'get started', 'getting started')
        if not any(p in q for p in key_phrases):
            return None
        if not any(p in q for p in help_phrases):
            return None
        return (
            "Mudrex uses **only one header**: `X-Authentication` with your API secret. "
            "No HMAC, no signing, no timestamps.\n\n"
            "**Base URL:** `https://trade.mudrex.com/fapi/v1`\n\n"
            "**Minimal example (Python):**\n"
            "```python\n"
            "import requests\n"
            "r = requests.get(\"https://trade.mudrex.com/fapi/v1/wallet/funds\", "
            "headers={\"X-Authentication\": \"your_api_secret\"})\n"
            "print(r.json())\n"
            "```\n\n"
            "**Easier option:** Use the community Python SDK — handles auth for you:\n"
            "https://github.com/DecentralizedJM/mudrex-api-trading-python-sdk\n\n"
            "Docs: https://docs.trade.mudrex.com/docs/authentication-rate-limits"
        )
    
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
        
        # "What to do with my API key" — return Mudrex auth (no HMAC)
        api_key_response = self._get_api_key_usage_response(query)
        if api_key_response:
            logger.info("Using template response for API key usage")
            return api_key_response
        
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
                return "Couldn't find that. Docs: https://docs.trade.mudrex.com — @DecentralizedJM can help with specifics."
            
            answer = self._clean_response(answer)
            
            if len(answer) > config.MAX_RESPONSE_LENGTH:
                answer = answer[:config.MAX_RESPONSE_LENGTH - 100] + "\n\n_(Cut short — ask something more specific?)_"
            
            return answer
        except ClientError as e:
            logger.error(f"Gemini API error in context search response: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "generate_response_with_context_search", "error_type": "ClientError"})
            return "Something went wrong on my end — not your code. Try again in a sec?"
        except Exception as e:
            logger.error(f"Error in context search response: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "generate_response_with_context_search"})
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
        
        # "What to do with my API key" — return Mudrex auth (no HMAC)
        api_key_response = self._get_api_key_usage_response(query)
        if api_key_response:
            return api_key_response
        
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
                return "Couldn't find that. Docs: https://docs.trade.mudrex.com — @DecentralizedJM can help with specifics."
            
            answer = self._clean_response(answer)
            
            # Ensure it acknowledges it's not from Mudrex docs
            if "mudrex" not in answer.lower()[:100] and "docs" not in answer.lower()[:100]:
                answer = f"This isn't in my Mudrex docs, but {answer.lower()}"
            
            return answer
        except ClientError as e:
            logger.error(f"Gemini API error in smart fallback: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "_generate_smart_fallback", "error_type": "ClientError"})
            return "I'm not sure about that one — can you share more details? Or @DecentralizedJM might know."
        except Exception as e:
            logger.error(f"Error in smart fallback: {e}", exc_info=True)
            _report_gemini_error(e, {"method": "_generate_smart_fallback"})
            return "I'm not sure about that one — can you share more details? Or @DecentralizedJM might know."
    
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
        except ClientError as e:
            logger.error(f"Gemini API error parsing intent: {e}")
            _report_gemini_error(e, {"method": "parse_learning_instruction", "error_type": "ClientError"})
            return {"action": "NONE"}
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            _report_gemini_error(e, {"method": "parse_learning_instruction"})
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
