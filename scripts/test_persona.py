
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import RAGPipeline
from src.rag.gemini_client import GeminiClient

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_persona():
    print("Initializing RAG Pipeline with new Persona...")
    rag = RAGPipeline()
    client = rag.gemini_client
    
    # Test Log Detection Logic
    print("\n1. Testing Log Detection Logic:")
    log_message = """
    bot_log.txt:4944:2026-01-14 18:36:10 [ERROR] AsyncBot: ❌ Telegram API Error: 409
    bot_log.txt:4945:2026-01-14 18:36:14 [WARNING] mudrex.client: Rate limited, retrying in 1.0s...
    """
    is_related = client.is_api_related_query(log_message)
    print(f"   Log Message Detected? {'✅ YES' if is_related else '❌ NO'}")
    
    # Test RAG Response to Logs
    print("\n2. Testing Response to Error Logs (409 Conflict):")
    response = rag.query(log_message)
    print("-" * 50)
    print(response['answer'])
    print("-" * 50)
    
    if "409" in response['answer'] and "two instances" in response['answer'].lower():
        print("   ✅ Bot correctly identified 409 Conflict issue")
    else:
        print("   ❌ Bot failed to identify specific 409 issue")

    # Test Persona Style
    print("\n3. Testing Persona Style (Direct vs Chatty):")
    q = "How do I authenticate?"
    response = rag.query(q)
    print(f"Q: {q}")
    print(f"A: {response['answer'][:100]}...")
    
    if "hope" in response['answer'].lower() or "please" in response['answer'].lower():
         print("   ⚠️  Bot might still be too polite/fluffy")
    else:
         print("   ✅ Bot seems direct")

    # Test Chitchat Filtering
    print("\n4. Testing Chitchat Filtering:")
    q_chat = "hi"
    is_related = client.is_api_related_query(q_chat)
    print(f"Q: '{q_chat}' -> detected? {is_related}")
    if not is_related:
        print("   ✅ Bot correctly IGNORED pure chitchat")
    else:
        print("   ⚠️  Bot might be too responsive to chitchat")

if __name__ == "__main__":
    test_persona()
