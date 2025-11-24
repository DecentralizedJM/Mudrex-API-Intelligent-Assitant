# 🚀 Quick Reference Card

**Mudrex API Intelligent Assistant**  
**Author:** [DecentralizedJM](https://github.com/DecentralizedJM)

---

## Essential Commands

```bash
# Setup
cp .env.example .env           # Create config
nano .env                      # Add API keys

# Install & Activate
source venv/bin/activate       # Activate environment

# Verify Setup
python test_setup.py           # Check everything

# Ingest Documentation
python scripts/ingest_docs.py  # Load docs into vector DB

# Run Bot
python main.py                 # Start the bot
```

## Required API Keys

| Key | Where to Get | In .env as |
|-----|--------------|-----------|
| Telegram Bot Token | [@BotFather](https://t.me/botfather) | `TELEGRAM_BOT_TOKEN` |
| Gemini API Key | [Google AI Studio](https://makersuite.google.com/app/apikey) | `GEMINI_API_KEY` |

## Telegram Bot Commands

```
/start  - Welcome message
/help   - Show help
/stats  - Bot statistics
```

## Example Questions (for testing)

```
"How do I authenticate with the API?"
"What's the endpoint for creating orders?"
"Error 401 - what does it mean?"
"Show me an example of making a request"
```

## File Locations

| What | Where |
|------|-------|
| API Documentation | `docs/*.md` |
| Configuration | `.env` |
| Bot Code | `src/bot/telegram_bot.py` |
| RAG Logic | `src/rag/pipeline.py` |
| Logs | `bot.log` |
| Vector DB | `data/chroma/vectors.pkl` |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Import errors | `source venv/bin/activate` |
| Bot doesn't respond | Check `.env` has correct tokens |
| No documents found | Run `python scripts/ingest_docs.py` |
| Poor answers | Add more docs to `docs/` |

## Configuration Quick Tweaks

```bash
# In .env file:

# Make responses more creative
GEMINI_TEMPERATURE=0.7

# Retrieve more context
TOP_K_RESULTS=10

# Lower quality threshold
SIMILARITY_THRESHOLD=0.4

# Restrict to specific chat
ALLOWED_CHAT_IDS=-1001234567890
```

## Development Workflow

1. **Add documentation** → Place `.md` files in `docs/`
2. **Ingest** → `python scripts/ingest_docs.py`
3. **Test** → `python main.py` and ask questions
4. **Iterate** → Adjust settings in `.env`
5. **Deploy** → Keep running in background

## Project Stats

- **Lines of Code**: ~1,200 Python LOC
- **Files**: 20+ project files
- **Dependencies**: 6 main packages
- **License**: MIT

## Need Help?

1. Run `python test_setup.py`
2. Check `bot.log`
3. Read `README.md`
4. See `SETUP.md`

## Architecture in 30 Seconds

```
User asks question in Telegram
    ↓
Bot detects if API-related
    ↓
Search vector DB for relevant docs
    ↓
Send docs + question to Gemini
    ↓
Return intelligent answer to user
```

---

**Built with ❤️ by [DecentralizedJM](https://github.com/DecentralizedJM)**

Ready to help your users 24/7! 🤖
