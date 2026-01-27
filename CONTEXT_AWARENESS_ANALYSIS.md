# Context Awareness Analysis & Recommendations

## Current State

### What You Have Now:
1. **Basic Chat History**: Last 6 messages per group stored in `context.chat_data`
2. **RAG Context**: Document retrieval for Mudrex API docs
3. **MCP Context**: Live data from Mudrex MCP server
4. **Dual-Persona**: Mudrex-specific vs generic trading routing

### Limitations:
- ❌ Limited history (only 6 messages)
- ❌ No persistent sessions across bot restarts
- ❌ No context compression/trimming for long conversations
- ❌ No semantic memory (can't remember facts about users/strategies)
- ❌ Context not optimized for token usage

---

## Agent Lightning Analysis

**TL;DR: Agent Lightning is NOT what you need for context awareness.**

### What Agent Lightning Actually Does:
- **Purpose**: Train/optimize agents with Reinforcement Learning (RL)
- **Use Case**: Improve agent performance over time through training
- **Features**: 
  - RL training algorithms
  - Prompt optimization
  - Policy fine-tuning
  - Performance tracking

### Why It Doesn't Help:
- ❌ Not designed for conversation context management
- ❌ Focuses on training, not runtime context
- ❌ Would require significant architecture changes
- ❌ Overkill for a Telegram bot

**Verdict**: Skip Agent Lightning for this use case.

---

## Better Options for Context Awareness

### Option 1: OpenAI Agents SDK ⭐ **RECOMMENDED**

**Why It's Perfect:**
- ✅ **Persistent Sessions**: Automatic conversation persistence
- ✅ **Context Management**: Built-in trimming/compression
- ✅ **MCP Integration**: Native support (you already use MCP!)
- ✅ **Memory Operations**: CRUD helpers for conversation history
- ✅ **Production-Ready**: Built by OpenAI, actively maintained

**Key Features:**
```python
from openai import OpenAI
from openai.agents import Agent, Session

# Persistent session with automatic history
session = SQLiteSession(session_id="group_123")
agent = Agent(
    model="gpt-4o",
    instructions="You are a Mudrex API co-pilot...",
    session=session  # Automatic context management!
)

# Context automatically managed - no manual history stitching
response = agent.run("How do I authenticate?")
```

**Migration Effort**: Medium (need to swap Gemini → OpenAI)

**Cost**: Higher (OpenAI is more expensive than Gemini)

---

### Option 2: Enhance Current Gemini Setup ⭐ **PRAGMATIC**

**Improvements You Can Make:**

#### A. Enhanced Context Management
```python
# Instead of last 6 messages, use:
- Last 10-15 messages with smart trimming
- Summarize old context when it gets too long
- Keep important facts in a separate memory store
```

#### B. Semantic Memory Layer
```python
# Store facts about users/strategies in vector DB
- User preferences
- Previous strategies discussed
- Common patterns
- Reusable across conversations
```

#### C. Context Compression
```python
# When history > 20 messages, compress old ones
- Summarize early conversation
- Keep recent messages verbatim
- Maintain key facts
```

**Migration Effort**: Low (enhance existing code)

**Cost**: Same (keep using Gemini)

---

### Option 3: Hybrid Approach

**Best of Both Worlds:**
1. Keep Gemini for cost efficiency
2. Add OpenAI Agents SDK patterns:
   - Implement session-like persistence
   - Add context compression
   - Build semantic memory layer

**Migration Effort**: Medium

**Cost**: Low (only use OpenAI for critical features if needed)

---

## Detailed Recommendation: Option 2 (Enhanced Gemini)

### Why This Makes Sense:
1. ✅ **You're already on Gemini** - cheaper, good quality
2. ✅ **Minimal disruption** - enhance existing code
3. ✅ **Keep MCP integration** - works with Gemini
4. ✅ **Incremental improvement** - can add features gradually

### Implementation Plan:

#### Phase 1: Enhanced History Management
- [ ] Increase history window (6 → 15 messages)
- [ ] Add context summarization for old messages
- [ ] Implement smart trimming (keep important, summarize rest)

#### Phase 2: Semantic Memory
- [ ] Create `SemanticMemory` class using vector store
- [ ] Store user preferences, strategies, facts
- [ ] Retrieve relevant memories during queries
- [ ] Update memory based on conversations

#### Phase 3: Context Optimization
- [ ] Implement token-aware context window
- [ ] Compress long conversations automatically
- [ ] Prioritize recent + relevant context

#### Phase 4: Persistent Sessions
- [ ] Store sessions in Redis (you already have it!)
- [ ] Persist across bot restarts
- [ ] Session-based memory retrieval

---

## If You Want to Switch to OpenAI Agents SDK

### Migration Steps:

1. **Install SDK**:
```bash
pip install openai-agents
```

2. **Replace Gemini Client**:
```python
# Old: src/rag/gemini_client.py
# New: src/rag/openai_client.py

from openai import OpenAI
from openai.agents import Agent, SQLiteSession

class OpenAIAgent:
    def __init__(self):
        self.client = OpenAI()
        self.sessions = {}  # session_id -> Session
    
    def get_session(self, chat_id: str):
        if chat_id not in self.sessions:
            self.sessions[chat_id] = SQLiteSession(session_id=chat_id)
        return self.sessions[chat_id]
```

3. **Update Pipeline**:
```python
# In pipeline.py, replace Gemini calls with OpenAI Agent
agent = Agent(
    model="gpt-4o-mini",  # or gpt-4o for better quality
    instructions=SYSTEM_INSTRUCTION,
    session=self.get_session(chat_id),
    tools=[...]  # Your MCP tools
)
```

4. **Benefits You Get**:
- ✅ Automatic context management
- ✅ Persistent sessions
- ✅ Better tool integration
- ✅ Built-in tracing/debugging

5. **Trade-offs**:
- ❌ Higher cost (~2-3x Gemini)
- ❌ Need to rewrite response generation
- ❌ Different API patterns

---

## My Recommendation

**Go with Option 2 (Enhanced Gemini)** because:

1. **Cost-Effective**: Gemini is much cheaper
2. **Good Enough**: Gemini 3 Flash is excellent quality
3. **Incremental**: Can improve gradually
4. **Keep What Works**: Your RAG pipeline is solid

**Then add these enhancements:**

1. **Semantic Memory** (High Impact, Medium Effort)
   - Store facts in vector DB
   - Retrieve during queries
   - Update based on conversations

2. **Smart Context Trimming** (Medium Impact, Low Effort)
   - Summarize old messages
   - Keep recent + relevant
   - Token-aware windowing

3. **Persistent Sessions** (High Impact, Low Effort)
   - Use Redis you already have
   - Store full conversation history
   - Retrieve on bot restart

---

## Next Steps

1. **Decide**: Option 2 (enhance Gemini) or Option 1 (switch to OpenAI)?
2. **If Option 2**: I can implement semantic memory + context optimization
3. **If Option 1**: I can help migrate to OpenAI Agents SDK

**Which direction do you want to go?**
