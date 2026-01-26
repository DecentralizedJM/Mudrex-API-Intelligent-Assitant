# Redis Caching Plan to Reduce Gemini Token Usage

## Problem Analysis

### Current Expensive Gemini API Calls Per Query

1. **Document Relevancy Validation** - 1 call per document (typically 1-5 calls per query)
   - **Most expensive**: ~400-500 tokens per validation
   - **Total**: ~500-2500 tokens per query

2. **Response Generation** - 1 call per query
   - **Cost**: ~1000-2000 tokens (input + output)

3. **Reranking** - 1 call per query (when docs found)
   - **Cost**: ~500-1000 tokens

4. **Query Transformation** - 0-2 calls (during iterative retrieval)
   - **Cost**: ~200-400 tokens per call

5. **Embeddings** - 1 call per query
   - **Cost**: ~100-200 tokens (relatively cheap)

**Total estimated tokens per query**: 2200-5400 tokens

### Cost Analysis

Assuming:
- 1000 queries/day
- Average 3000 tokens/query
- Gemini pricing: $0.075 per 1M input tokens, $0.30 per 1M output tokens

**Current daily cost**: ~$0.90/day (~$27/month)

## Solution: Multi-Level Redis Caching

### Cache Strategy (Priority Order)

#### 1. Query-Response Cache (Highest ROI - 100% reduction for cached queries)
- **Cache Key**: `response:{query_hash}:{context_hash}`
- **What**: Full response answer
- **TTL**: 24 hours
- **Benefit**: Skip entire pipeline for repeated questions
- **Expected Hit Rate**: 30-50% (common questions like "how to auth", "error codes")

#### 2. Relevancy Validation Cache (High ROI - Skip N validation calls)
- **Cache Key**: `relevancy:{query_hash}:{doc_hash}`
- **What**: Validation result `{"relevant": bool, "score": float}`
- **TTL**: 7 days (doc relevancy is stable)
- **Benefit**: Skip validation for same (query, doc) pairs
- **Expected Hit Rate**: 40-60% (same docs get validated for similar queries)

#### 3. Reranking Cache (Medium ROI)
- **Cache Key**: `rerank:{query_hash}:{docs_hash}`
- **What**: Reranked document indices `[0, 2, 1, ...]`
- **TTL**: 7 days
- **Benefit**: Skip reranking for same query+doc combinations

#### 4. Query Transformation Cache (Medium ROI)
- **Cache Key**: `transform:{query_hash}`
- **What**: Transformed query string
- **TTL**: 7 days
- **Benefit**: Skip transformation for similar queries

#### 5. Embedding Cache (Low ROI, but easy to implement)
- **Cache Key**: `embedding:{text_hash}`
- **What**: Embedding vector (768 floats, store as JSON)
- **TTL**: 30 days (embeddings never change)
- **Benefit**: Skip embedding generation for repeated queries/texts

### Expected Token Reduction

**Without caching**: ~2200-5400 tokens per query

**With caching**:
- **First query**: Same as above (cache miss)
- **Cached query**: ~0 tokens (100% reduction)
- **Similar query** (partial cache): 50-80% reduction

**For community bot with repeated questions**:
- Estimated cache hit rate: 30-50%
- **Token savings: 30-50% overall**
- **Cost savings: ~$8-13/month**

## Implementation Plan

### Phase 1: Add Redis Client and Configuration

**File**: `src/config/settings.py`
```python
# Redis Caching
REDIS_ENABLED: bool = True
REDIS_URL: str = "redis://localhost:6379/0"
REDIS_TTL_RESPONSE: int = 86400  # 24 hours
REDIS_TTL_VALIDATION: int = 604800  # 7 days
REDIS_TTL_RERANK: int = 604800  # 7 days
REDIS_TTL_TRANSFORM: int = 604800  # 7 days
REDIS_TTL_EMBEDDING: int = 2592000  # 30 days
```

**File**: `src/rag/cache.py` (NEW)
- Create `RedisCache` class with:
  - Connection management (lazy connection, reconnect on failure)
  - Cache get/set with TTL
  - Hash generation for keys (SHA256 of normalized text)
  - Batch operations for multiple validations
  - Graceful fallback when Redis unavailable

### Phase 2: Integrate Caching in Pipeline

**File**: `src/rag/pipeline.py`
- Add cache check at start of `query()`:
  ```python
  # Check cache first
  if cache:
      cached_response = cache.get_response(question, chat_history, mcp_context)
      if cached_response:
          logger.info("Cache hit: returning cached response")
          return cached_response
  ```
- Cache result after generation:
  ```python
  # Cache the response
  if cache:
      cache.set_response(question, chat_history, mcp_context, result)
  ```

**File**: `src/rag/gemini_client.py`
- Add caching to `validate_document_relevancy()`:
  ```python
  for doc in documents:
      # Check cache first
      cached = cache.get_validation(query, doc) if cache else None
      if cached:
          # Use cached result
      else:
          # Call Gemini and cache result
  ```

- Add caching to `rerank_documents()` and `transform_query()`

**File**: `src/rag/vector_store.py`
- Add caching to `_get_embedding()`:
  ```python
  cached = cache.get_embedding(text) if cache else None
  if cached:
      return cached
  # Generate and cache
  ```

### Phase 3: Cache Key Design

**Hash Strategy**:
- Normalize: lowercase, strip whitespace, remove punctuation variations
- Use SHA256 hash of normalized query/text
- Include context hash for responses (chat history, MCP context)

**Key Format**:
```
response:{query_hash}:{context_hash}
relevancy:{query_hash}:{doc_hash}
rerank:{query_hash}:{docs_hash}
transform:{query_hash}
embedding:{text_hash}
```

### Phase 4: Fallback and Monitoring

- **Graceful Fallback**: If Redis unavailable, continue without caching (no errors)
- **Cache Statistics**: Track hits/misses, add to `/stats` command
- **Logging**: Log cache hits/misses for monitoring

## Files to Modify

1. **`requirements.txt`** - Add `redis>=5.0.0`
2. **`src/config/settings.py`** - Add Redis config
3. **`src/rag/cache.py`** (NEW) - Redis cache client
4. **`src/rag/pipeline.py`** - Add response caching
5. **`src/rag/gemini_client.py`** - Add validation/rerank/transform caching
6. **`src/rag/vector_store.py`** - Add embedding caching
7. **`src/bot/telegram_bot.py`** - Add cache stats to `/stats` command

## Railway Setup

1. Add Redis service in Railway dashboard
2. Get Redis URL from Railway environment variables
3. Set `REDIS_URL` environment variable (or use default)
4. Set `REDIS_ENABLED=true` (or false to disable)

## Testing Strategy

1. Test cache hits for identical queries
2. Test cache misses for new queries
3. Test Redis connection failure fallback
4. Test TTL expiration
5. Measure token usage before/after
6. Test with Railway Redis

## Success Criteria

- ✅ Redis caching reduces Gemini API calls by 30%+ for repeated queries
- ✅ Cache hit rate > 30% in production
- ✅ No performance degradation (cache lookups < 10ms)
- ✅ Graceful fallback when Redis unavailable
- ✅ Cache statistics visible in `/stats` command
- ✅ Monthly cost savings of $8-13

## Trade-offs

### Pros
- Significant token/cost savings (30-50%)
- Faster responses for cached queries
- Reduced API rate limit issues
- Better user experience (faster responses)

### Cons
- Additional infrastructure (Redis service)
- Slight complexity increase
- Cache invalidation complexity (if docs change)
- Memory usage (Redis storage)

### Recommendation

**YES, implement Redis caching** - The benefits (30-50% cost savings, faster responses) outweigh the costs (Redis service, slight complexity). For a community bot with repeated questions, this is a high-value optimization.
