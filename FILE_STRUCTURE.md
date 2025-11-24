# Mudrex API Bot - File Structure

```
mudrex-api-bot/
│
├── 📁 .github/
│   └── copilot-instructions.md      # GitHub Copilot workspace config
│
├── 📁 src/                          # Main source code
│   ├── __init__.py
│   │
│   ├── 📁 bot/                      # Telegram bot logic
│   │   ├── __init__.py
│   │   └── telegram_bot.py          # Bot handlers, commands, message processing
│   │
│   ├── 📁 config/                   # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py              # Environment variables, config loading
│   │
│   └── 📁 rag/                      # RAG pipeline components
│       ├── __init__.py
│       ├── pipeline.py              # Main RAG orchestration
│       ├── vector_store.py          # Vector database (sklearn-based)
│       ├── gemini_client.py         # Google Gemini AI integration
│       └── document_loader.py       # Document ingestion & chunking
│
├── 📁 scripts/                      # Utility scripts
│   ├── __init__.py
│   └── ingest_docs.py               # Documentation ingestion script
│
├── 📁 docs/                         # API documentation files
│   ├── README.md                    # Documentation guidelines
│   ├── getting-started.md           # Sample: Getting started guide
│   └── orders.md                    # Sample: Order management docs
│
├── 📁 venv/                         # Python virtual environment (auto-generated)
│
├── 📁 data/                         # Runtime data (created when running)
│   └── chroma/                      # Vector database storage
│       └── vectors.pkl              # Serialized vectors & docs
│
├── 📄 main.py                       # Application entry point
├── 📄 test_setup.py                 # Setup verification script
│
├── 📄 requirements.txt              # Python dependencies
├── 📄 .env.example                  # Environment template
├── 📄 .env                          # Your API keys (git-ignored)
├── 📄 .gitignore                    # Git ignore rules
│
├── 📄 README.md                     # Complete documentation
├── 📄 SETUP.md                      # Quick setup guide
├── 📄 PROJECT_SUMMARY.md            # This summary
├── 📄 LICENSE                       # MIT License
│
└── 📄 bot.log                       # Runtime logs (created when running)
```

## 🎯 Key Files Explained

### Entry Points
- **`main.py`** - Start the bot with `python main.py`
- **`scripts/ingest_docs.py`** - Load docs with `python scripts/ingest_docs.py`
- **`test_setup.py`** - Verify setup with `python test_setup.py`

### Core Logic
- **`src/bot/telegram_bot.py`** - Handles all Telegram interactions
- **`src/rag/pipeline.py`** - Coordinates the RAG workflow
- **`src/rag/vector_store.py`** - Manages document embeddings
- **`src/rag/gemini_client.py`** - Generates AI responses

### Configuration
- **`.env`** - Your API keys and settings
- **`src/config/settings.py`** - Loads and validates config

### Documentation
- **`docs/`** - Place your Mudrex API docs here
- **`README.md`** - Complete project documentation
- **`SETUP.md`** - Quick start instructions

## 📊 File Count

- **Python files**: 11
- **Documentation**: 6  
- **Configuration**: 3
- **Total project files**: 20+

## 🔐 Files to Protect

Never commit to public repos:
- `.env` (contains API keys)
- `data/` (vector database)
- `bot.log` (runtime logs)
- `venv/` (virtual environment)

All protected by `.gitignore` ✅

## 📝 Files to Customize

1. **`.env`** - Add your API keys
2. **`docs/*.md`** - Add your API documentation  
3. **`src/rag/gemini_client.py`** - Customize bot personality
4. **`src/bot/telegram_bot.py`** - Add custom commands

## 🚀 Workflow

```
1. Add docs → docs/*.md
2. Ingest → python scripts/ingest_docs.py
3. Run → python main.py
4. Chat → Telegram bot answers questions
```

---

**Total Lines of Code**: ~1,500 lines of production-ready Python!
