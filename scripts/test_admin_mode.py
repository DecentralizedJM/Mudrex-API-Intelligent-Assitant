"""
Verification script for Admin Knowledge Engine
Tests:
1. Strict Fact Setting overrides RAG
2. Dynamic Learning adds to Vector Store
"""
import logging
from src.rag import RAGPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_admin_mode():
    logger.info("Initializing RAG Pipeline...")
    rag = RAGPipeline()
    
    print("\n=== Test 1: Strict Facts ===")
    fact_key = "TEST_LATENCY"
    fact_value = "999ms (Tested)"
    
    # Set fact
    print(f"Setting fact: {fact_key} = {fact_value}")
    rag.set_fact(fact_key, fact_value)
    
    # Query
    q = "What is the TEST_LATENCY?"
    result = rag.query(q)
    print(f"Q: {q}")
    print(f"A: {result['answer']}")
    
    if fact_value in result['answer']:
        print("✅ Fact Store Override: SUCCESS")
    else:
        print("❌ Fact Store Override: FAILED")
        
    # Clean up
    rag.delete_fact(fact_key)
    
    print("\n=== Test 2: Dynamic Learning ===")
    new_knowledge = "The Mudrex Secret Endpoint is /v3/super-secret-alpha."
    
    # Learn
    print(f"Learning text: {new_knowledge}")
    rag.learn_text(new_knowledge)
    
    # Query (Sleep briefly to ensure persistence if needed, though local is instant usually)
    import time
    time.sleep(1)
    
    q_learn = "What is the secret endpoint?"
    result = rag.query(q_learn)
    print(f"Q: {q_learn}")
    print(f"A: {result['answer']}")
    
    if "/v3/super-secret-alpha" in result['answer']:
        print("✅ Dynamic Learning: SUCCESS")
    else:
        print("❌ Dynamic Learning: FAILED")

if __name__ == "__main__":
    test_admin_mode()
