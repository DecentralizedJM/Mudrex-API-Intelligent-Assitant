# Context Awareness Implementation - Complete ✅

## Overview

Enhanced the Mudrex API Co-pilot with advanced context awareness features:
1. **Semantic Memory** - Stores and retrieves user facts, strategies, preferences
2. **Smart Context Trimming** - Summarizes old messages, keeps recent ones
3. **Persistent Sessions** - Conversation history survives bot restarts

---

## What Was Implemented

### 1. Semantic Memory (`src/rag/semantic_memory.py`)

**Purpose**: Store and retrieve user facts, strategies, preferences across conversations.

**Features**:
- Vector-based semantic search using Gemini embeddings
- Stores memories in Redis (persistent) or in-memory (fallback)
- Automatic importance scoring and access tracking
- Memory types: `fact`, `strategy`, `preference`, `context`

**Usage**:
```python
# Store a memory
memory_id = semantic_memory.store_memory(
    chat_id="123",
    content="User prefers Python over JavaScript",
    memory_type="preference",
    importance=0.8
)

# Retrieve relevant memories
memories = semantic_memory.retrieve_memories(
    chat_id="123",
    query="What programming language does the user prefer?",
    top_k=3
)
```

### 2. Context Manager (`src/rag/context_manager.py`)

**Purpose**: Manage conversation history with smart trimming and summarization.

**Features**:
- **Persistent Sessions**: Stores conversation history in Redis (30-day TTL)
- **Smart Trimming**: Summarizes old messages when history exceeds threshold
- **Context Optimization**: Keeps recent messages verbatim, summarizes older ones
- **Fact Extraction**: Automatically extracts facts from conversations

**Configuration**:
- `MAX_HISTORY_MESSAGES`: 15 (default)
- `CONTEXT_COMPRESS_THRESHOLD`: 20 messages
- `MAX_TOKENS_PER_MESSAGE`: 200 tokens

**Usage**:
```python
# Load session
history = context_manager.load_session(chat_id)

# Get optimized context
context = context_manager.get_context(
    chat_id=chat_id,
    query="How do I authenticate?",
    include_recent=5,
    include_memories=True
)
# Returns: {'history': [...], 'summary': "...", 'memories': [...], 'compressed': True}

# Add message
context_manager.add_message(chat_id, 'user', "Hello")
```

### 3. Integration

**RAG Pipeline** (`src/rag/pipeline.py`):
- Automatically loads enhanced context when `chat_id` is provided
- Includes semantic memories in response generation
- Works for both Mudrex-specific and generic trading queries

**Telegram Bot** (`src/bot/telegram_bot.py`):
- Uses context manager instead of manual history management
- Automatically extracts facts every 5 messages
- Persistent sessions survive bot restarts

---

## Configuration

New environment variables (optional, defaults provided):

```bash
# Context Management
MAX_HISTORY_MESSAGES=15          # Max messages before trimming
CONTEXT_COMPRESS_THRESHOLD=20    # Messages before compression
MAX_TOKENS_PER_MESSAGE=200       # Token limit per message

# Redis TTLs
REDIS_TTL_SESSION=2592000        # 30 days
REDIS_TTL_MEMORY=2592000         # 30 days
```

---

## How It Works

### Conversation Flow:

1. **User sends message** → Bot receives it
2. **Context Manager loads session** → Gets history from Redis (or creates new)
3. **Semantic Memory retrieves** → Finds relevant past facts/strategies
4. **Context optimization** → Summarizes old messages if needed
5. **RAG Pipeline processes** → Uses enhanced context + memories
6. **Response generated** → With full context awareness
7. **Save to session** → Persists conversation to Redis
8. **Extract facts** → Every 5 messages, extract new facts

### Example:

**First conversation:**
```
User: "I prefer Python for API calls"
Bot: [Responds]
→ Memory stored: "User prefers Python over JavaScript"
```

**Later conversation:**
```
User: "Show me how to authenticate"
Bot: [Retrieves memory about Python preference]
Bot: [Responds with Python code example, not JavaScript]
```

---

## Benefits

1. **Better Context**: Bot remembers user preferences, strategies, past discussions
2. **Persistent**: Conversations survive bot restarts (Redis storage)
3. **Efficient**: Smart trimming reduces token usage while maintaining context
4. **Automatic**: No manual configuration needed - works out of the box
5. **Scalable**: Redis handles large conversation histories efficiently

---

## Fallback Behavior

If Redis is unavailable:
- ✅ Context manager falls back to in-memory storage
- ✅ Semantic memory uses in-memory storage
- ✅ Bot continues working (just loses persistence across restarts)

---

## Testing

To test the implementation:

1. **Start a conversation** in Telegram
2. **Mention preferences/strategies**: "I prefer Python", "My strategy is X"
3. **Ask follow-up questions**: Bot should remember and reference previous context
4. **Restart bot**: Conversation history should persist (if Redis available)

---

## Files Modified/Created

**New Files**:
- `src/rag/semantic_memory.py` - Semantic memory implementation
- `src/rag/context_manager.py` - Context management with trimming

**Modified Files**:
- `src/rag/pipeline.py` - Integrated context manager and semantic memory
- `src/bot/telegram_bot.py` - Uses context manager instead of manual history
- `src/config/settings.py` - Added context management config options

---

## Next Steps (Optional Enhancements)

1. **Memory Management UI**: Add commands to view/delete memories
2. **Memory Types**: Add more specific types (e.g., `error_pattern`, `user_skill_level`)
3. **Memory Expiration**: Auto-delete old/unused memories
4. **Context Analytics**: Track context usage and optimization effectiveness

---

## Notes

- **Redis Required**: For persistent sessions, Redis must be enabled
- **Gemini Embeddings**: Uses Gemini for memory embeddings (costs apply)
- **Token Usage**: Summarization uses additional tokens but saves more in long conversations
- **Backward Compatible**: Falls back gracefully if context manager unavailable
