"""
Test script to verify the setup
"""
import sys
from pathlib import Path

def test_imports():
    """Test if all required packages are installed"""
    print("Testing imports...")
    try:
        import telegram
        print("✓ python-telegram-bot")
    except ImportError as e:
        print(f"✗ python-telegram-bot: {e}")
        return False
    
    try:
        import google.generativeai as genai
        print("✓ google-generativeai")
    except ImportError as e:
        print(f"✗ google-generativeai: {e}")
        return False
    
    try:
        import numpy as np
        print("✓ numpy")
    except ImportError as e:
        print(f"✗ numpy: {e}")
        return False
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        print("✓ scikit-learn")
    except ImportError as e:
        print(f"✗ scikit-learn: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv")
    except ImportError as e:
        print(f"✗ python-dotenv: {e}")
        return False
    
    return True


def test_env_file():
    """Check if .env file exists"""
    print("\nChecking environment configuration...")
    env_path = Path(".env")
    
    if not env_path.exists():
        print("✗ .env file not found")
        print("  → Run: cp .env.example .env")
        return False
    
    print("✓ .env file exists")
    
    # Check if keys are set
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    
    if not telegram_token or telegram_token == "your_telegram_bot_token_here":
        print("✗ TELEGRAM_BOT_TOKEN not configured")
        print("  → Add your bot token to .env")
        return False
    print("✓ TELEGRAM_BOT_TOKEN is set")
    
    if not gemini_key or gemini_key == "your_gemini_api_key_here":
        print("✗ GEMINI_API_KEY not configured")
        print("  → Add your Gemini API key to .env")
        return False
    print("✓ GEMINI_API_KEY is set")
    
    return True


def test_docs_directory():
    """Check if docs directory has files"""
    print("\nChecking documentation...")
    docs_path = Path("docs")
    
    if not docs_path.exists():
        print("✗ docs/ directory not found")
        return False
    
    doc_files = list(docs_path.rglob("*.md")) + list(docs_path.rglob("*.txt"))
    doc_files = [f for f in doc_files if f.name != "README.md"]
    
    if not doc_files:
        print("⚠ No documentation files found in docs/")
        print("  → Add your API docs to docs/ directory")
        print("  → Sample files were created for testing")
        return True
    
    print(f"✓ Found {len(doc_files)} documentation file(s)")
    for doc in doc_files[:3]:
        print(f"  - {doc.name}")
    
    return True


def test_vector_store():
    """Check if vector database exists"""
    print("\nChecking vector database...")
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    db_path = Path(os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"))
    db_file = db_path / "vectors.pkl"
    
    if not db_file.exists():
        print("⚠ Vector database not initialized")
        print("  → Run: python scripts/ingest_docs.py")
        return True
    
    print("✓ Vector database exists")
    return True


def main():
    """Run all tests"""
    print("=" * 50)
    print("Mudrex API Bot - Setup Verification")
    print("=" * 50)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_env_file()
    all_passed &= test_docs_directory()
    all_passed &= test_vector_store()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ Setup verification complete!")
        print("\nNext steps:")
        print("1. If you haven't already: python scripts/ingest_docs.py")
        print("2. Run the bot: python main.py")
    else:
        print("✗ Setup incomplete - please fix the issues above")
        sys.exit(1)
    print("=" * 50)


if __name__ == "__main__":
    main()
