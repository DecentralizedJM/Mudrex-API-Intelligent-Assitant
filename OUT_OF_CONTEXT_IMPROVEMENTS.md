# Out-of-Context Question Handling - Analysis & Solutions

## Current Problem

The bot becomes "numb" (unresponsive/unhelpful) when:
1. **Out-of-context questions** - Questions not in Mudrex docs
2. **Difficult questions** - Complex, multi-part questions
3. **Indirect questions** - Questions that need interpretation

## Current Behavior

When no docs are found:
- Uses `generate_response_with_context_search`
- Has hard instruction: "You MUST respond: 'I don't have that in my Mudrex docs...'"
- **Result**: Bot gives up and says "I don't know" even when it could help

## Solutions

### Option 1: Smart Fallback with Gemini Knowledge ⭐ **RECOMMENDED**

**What**: Use Gemini's general knowledge for out-of-context questions, but clearly mark it as generic.

**How**:
- When no Mudrex docs found AND query is clearly out-of-context
- Use Gemini's knowledge to answer
- Clearly state: "This isn't in my Mudrex docs, but here's how it typically works..."
- Provide code examples using generic patterns

**Pros**:
- ✅ Bot stays helpful even without docs
- ✅ Users get answers, not "I don't know"
- ✅ Clear distinction: generic vs Mudrex-specific
- ✅ No new dependencies

**Cons**:
- ⚠️ Need to be careful not to hallucinate Mudrex features

---

### Option 2: Enhanced Query Understanding

**What**: Better query rewriting and intent detection for indirect/difficult questions.

**How**:
- Improve `transform_query` to break down complex questions
- Add multi-step reasoning for difficult questions
- Better keyword extraction for indirect questions

**Pros**:
- ✅ Better retrieval for indirect questions
- ✅ Can find relevant docs even with poor phrasing

**Cons**:
- ⚠️ Still fails if truly nothing in docs

---

### Option 3: Hybrid Approach (Best)

**Combine both**:
1. Enhanced query understanding (better retrieval)
2. Smart fallback (helpful when no docs found)

---

## Recommended Implementation

### 1. Smart Fallback Function

```python
def generate_smart_fallback(self, query: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Generate helpful response using Gemini's knowledge when no docs found.
    Clearly marks as generic/non-Mudrex.
    """
    prompt = f"""The user asked: "{query}"

This question isn't covered in the Mudrex API documentation I have access to.

However, as an API Copilot, I should still try to help using general API/trading knowledge.

Rules:
- Provide helpful code examples or implementation patterns
- Clearly state this is generic knowledge, not Mudrex-specific
- If it's about API implementation, show code
- If it's about trading concepts, explain generically
- Always offer to help with Mudrex-specific implementation if they want

Generate a helpful response (2-4 sentences + code if applicable):"""

    # Use Gemini to generate helpful response
    # Mark as generic knowledge
```

### 2. Enhanced Query Understanding

- Improve query transformation to handle indirect questions
- Add question decomposition for complex queries
- Better intent detection

### 3. Update Pipeline

When no docs found:
1. Try enhanced query understanding (rewrite/breakdown)
2. If still no docs → Use smart fallback
3. Clearly mark response as "generic knowledge" vs "Mudrex docs"

---

## Implementation Plan

1. **Add `generate_smart_fallback` method** to GeminiClient
2. **Update pipeline** to use smart fallback when no docs found
3. **Enhance query transformation** for indirect questions
4. **Add response marking** to distinguish generic vs Mudrex answers

---

## Example Behavior

**Before** (numb):
```
User: "How do I implement a trailing stop loss?"
Bot: "I don't have that in my Mudrex docs. @DecentralizedJM might know?"
```

**After** (helpful):
```
User: "How do I implement a trailing stop loss?"
Bot: "This isn't in my Mudrex docs, but here's a generic pattern you can adapt:

```python
class TrailingStop:
    def __init__(self, initial_price, trail_percent):
        self.highest_price = initial_price
        self.trail_percent = trail_percent
    
    def update(self, current_price):
        if current_price > self.highest_price:
            self.highest_price = current_price
        stop_price = self.highest_price * (1 - self.trail_percent)
        return stop_price

# Use with Mudrex API to update stop loss orders
```

For Mudrex-specific implementation, check if they support trailing stops in the API docs, or @DecentralizedJM can help."
```
