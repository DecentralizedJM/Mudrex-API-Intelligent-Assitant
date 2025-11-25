# Mudrex API Intelligent Assistant 🤖

A focused, concise Telegram bot for Mudrex API support using RAG (Retrieval-Augmented Generation) with Google Gemini 2.5 Flash. The bot provides brief, helpful answers about API integration, authentication, orders, and debugging.

**Bot:** [@API_Assistant_V2_bot](https://t.me/API_Assistant_V2_bot)  
**Author:** [DecentralizedJM](https://github.com/DecentralizedJM)  
**License:** MIT (with attribution required)  
**Copyright:** © 2025 DecentralizedJM

---

## Features

- 🎯 **Focused on API**: Only responds to API-related questions, avoids casual chitchat
- 📏 **Concise Responses**: Brief, to-the-point answers (2-4 sentences for simple questions)
- 💬 **Always Responds When Tagged**: If @mentioned, always engages - asks clarifying questions if needed
- 📚 **RAG-Powered**: Vector search across Mudrex API documentation for accurate answers
- 🤝 **Humble & Helpful**: Natural, conversational tone without unnecessary bragging or formatting
- ⚡ **Fast**: Powered by Gemini 2.5 Flash with optimized prompts
- 🔐 **Secure**: Optional chat ID restrictions for controlled access
- 📖 **Auto-Documentation**: Pulls latest docs from https://docs.trade.mudrex.com
- 🛡️ **Critical Guardrails**: Never says Mudrex is "not an exchange", escalates tough questions to @DecentralizedJM

## Bot Behavior

### ✅ Responds To:
- **API Questions**: "How do I authenticate?", "What's the order endpoint?"
- **Code Review**: Share code with errors, get fixes and explanations
- **Debugging**: "Getting 401 error", "Order placement failing"
- **@Mentions**: Always responds when tagged, asks follow-ups if unclear

### ❌ Ignores:
- **Casual Chat**: "hello", "how are you", "nice weather"
- **Non-API Topics**: General conversation, unrelated questions

### 💡 Response Style:
- **Brief**: 2-4 sentences for simple questions
- **Natural**: Conversational paragraphs, not excessive bullet points
- **Helpful**: Code examples when relevant, always brief
- **Humble**: No bragging about IQ or being "part of the team"

## Architecture

```
┌─────────────┐
│  Telegram   │
│    User     │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Telegram Bot   │
│   (Handler)     │  ✓ Silent filtering
│                 │  ✓ @mention detection
│                 │  ✓ Always respond when tagged
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  RAG Pipeline   │◄────►│  Vector Store   │
│                 │      │ (sklearn-based) │
│  • Query detect │      │  22 documents   │
│  • Context ret. │      │  embeddings     │
└──────┬──────────┘      └─────────────────┘
       │
       ▼
┌─────────────────┐
│  Gemini 2.5     │
│  Flash API      │  ✓ Concise responses
│                 │  ✓ Humble persona
│                 │  ✓ Critical guardrails
└─────────────────┘
```

## Tech Stack

- **Python 3.14** - Latest Python runtime
- **python-telegram-bot 21.0** - Async Telegram integration
- **Scikit-learn** - Vector similarity search with cosine distance
- **Google Gemini 2.5 Flash** - Fast, efficient LLM with extended context
- **BeautifulSoup4** - Documentation auto-fetching from web

## Setup

### 1. Prerequisites

- Python 3.10 or higher (tested on Python 3.14)
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- Google Gemini API Key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/DecentralizedJM/Mudrex-API-Intelligent-Assitant-.git
cd Mudrex-API-Intelligent-Assitant-

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the project root:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.3
GEMINI_MAX_TOKENS=2048

# Optional: Restrict to specific chat IDs (comma-separated)
# ALLOWED_CHAT_IDS=123456789,-987654321
```

**⚠️ Security Note:** Never commit your `.env` file to version control. It's already in `.gitignore`.

### 4. Fetch & Ingest Documentation

The bot automatically fetches Mudrex API documentation:

```bash
# Auto-fetch from docs.trade.mudrex.com and ingest
python scripts/ingest_docs.py
```

This creates vector embeddings from 22 documentation chunks.

### 5. Run the Bot

```bash
python main.py
```

You should see:
```
==================================================
Starting Mudrex API Documentation Bot
==================================================
Initialized vector store with 22 documents
Initialized Gemini client with model: gemini-2.5-flash
Bot is now running. Press Ctrl+C to stop.
```

## Usage

### Telegram Commands

- `/start` - Welcome message and bot introduction
- `/help` - Show usage tips and features
- `/stats` - Display bot statistics (documents loaded, model info)

### Example Interactions

```
User: How do I authenticate with the Mudrex API?
Bot: Use the X-Authentication header with your API secret. Here's a quick example:
     [code snippet]
     Keep your API secret secure and never commit it to code.

User: hello
Bot: [silently ignores - not API-related]

User: I want to start API trading. How
Bot: Create API keys from your Mudrex dashboard, then use the authentication header 
     in your requests. Check the docs at docs.trade.mudrex.com for full setup steps.

User: @API_Assistant_V2_bot hi
Bot: I'm here to help with the Mudrex API. What would you like to know?

User: @API_Assistant_V2_bot unclear question
Bot: What specifically would you like help with regarding the Mudrex API?

User: Is Mudrex using Bybit API keys?
Bot: [Redirects] Let me get @DecentralizedJM to provide more details on this.
```

## Configuration Options

Edit `.env` to customize behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | *Required* |
| `GEMINI_API_KEY` | Google Gemini API key | *Required* |
| `GEMINI_MODEL` | Gemini model to use | `gemini-2.5-flash` |
| `GEMINI_TEMPERATURE` | Response creativity (0-1) | `0.3` |
| `GEMINI_MAX_TOKENS` | Maximum response length | `2048` |
| `EMBEDDING_MODEL` | Model for embeddings | `models/text-embedding-004` |
| `TOP_K_RESULTS` | Documents to retrieve | `5` |
| `SIMILARITY_THRESHOLD` | Minimum similarity score | `0.6` |
| `ALLOWED_CHAT_IDS` | Restrict to specific chats | None (all allowed) |
| `AUTO_DETECT_QUERIES` | Enable smart filtering | `true` |

## Project Structure

```
mudrex-api-bot/
├── src/
│   ├── bot/
│   │   ├── telegram_bot.py      # Telegram handlers, @mention detection
│   │   └── __init__.py
│   ├── rag/
│   │   ├── pipeline.py          # RAG orchestration
│   │   ├── vector_store.py      # sklearn-based vector search
│   │   ├── gemini_client.py     # Gemini API client with concise persona
│   │   └── __init__.py
│   ├── config/
│   │   ├── settings.py          # Configuration management
│   │   └── __init__.py
│   └── utils/
│       └── document_loader.py   # Auto-fetch from docs.trade.mudrex.com
├── scripts/
│   └── ingest_docs.py           # Documentation ingestion script
├── data/
│   └── chroma/
│       └── vectors.pkl          # Serialized vector embeddings
├── docs/
│   └── mudrex-api-documentation.md  # Auto-fetched documentation
├── main.py                      # Entry point
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in repo)
├── .gitignore                   # Git ignore rules
├── LICENSE                      # MIT License
└── README.md                    # This file
```

## Development

### Adding/Updating Documentation

The bot automatically fetches documentation from https://docs.trade.mudrex.com:

```bash
# Re-fetch and re-ingest latest documentation
python scripts/ingest_docs.py

# Restart bot to reload
python main.py
```

### Customizing Bot Personality

Edit `src/rag/gemini_client.py` to modify the system prompt:

```python
# Current persona: Helpful, concise, humble API assistant
# Modify the system_instruction in _create_prompt() method
```

Key personality traits (defined in system prompt):
- **Stay Focused**: Only API-related questions
- **Be Concise**: 2-4 sentences for simple answers
- **Be Humble**: No bragging or unnecessary formatting
- **Always Respond When Tagged**: Engage even if unclear, ask follow-ups
- **Write Naturally**: Conversational paragraphs, not excessive bullets

### Critical Guardrails (Hard-coded)

The bot has strict rules to protect Mudrex's brand:

- ⛔ **Never say** Mudrex is "not an exchange" or "wrapper around exchanges"
- 🚨 **Escalate** tough/confrontational questions to @DecentralizedJM
- 🚫 **Never mention** competitor exchanges (Binance, Bybit, etc.)
- ✅ **Position** Mudrex as full-featured exchange with FIU regulation

These are defined in `src/rag/gemini_client.py` system prompt.

### Testing

```bash
# Test documentation ingestion
python scripts/ingest_docs.py

# Test bot locally
python main.py
# Send test messages on Telegram
```

## Deployment

### Running in Production

```bash
# Use nohup to run in background
nohup python main.py > bot.log 2>&1 &

# Or use screen/tmux
screen -S mudrex-bot
python main.py
# Ctrl+A, D to detach
```

### Production Best Practices

- ✅ Set `ALLOWED_CHAT_IDS` to restrict access to authorized users
- ✅ Monitor logs: `tail -f bot.log`
- ✅ Set up log rotation for `bot.log`
- ✅ Regularly update documentation via re-ingestion
- ✅ Keep API keys secure and rotate regularly
- ✅ Only one bot instance per token (Telegram limitation)

## Troubleshooting

### Bot doesn't respond to messages
- ✅ Check `TELEGRAM_BOT_TOKEN` is correct
- ✅ Verify message is API-related or bot is @mentioned
- ✅ Look for "Silently ignoring non-API message" in logs
- ✅ Try @mentioning: `@API_Assistant_V2_bot your question`

### "Conflict: terminated by other getUpdates request"
- Multiple bot instances are running
- Kill all instances: `pkill -9 python`
- Wait 5-10 seconds before restarting
- Or create a new bot with new token via @BotFather

### Bot gives long responses
- This was fixed in latest version (commit e2e2fbb)
- System prompt emphasizes brevity: "2-4 sentences for simple questions"
- Responses are concise and natural paragraphs, not excessive bullets

### Bot responds to casual chat
- Fixed in latest version - ignores "hello", "hi", etc. unless @mentioned
- Check logs for "Silently ignoring non-API message"
- API keywords required: api, endpoint, authentication, order, error, etc.

### Bot doesn't respond when @mentioned
- This should always work - check logs for errors
- System rule: "When tagged, ALWAYS respond"
- If unclear, bot asks follow-up questions

## Recent Updates (Nov 2025)

**v2.0 - Concise & Focused Release**
- ✅ Made responses much more concise (2-4 sentences)
- ✅ Removed excessive bullet points and formatting
- ✅ Humble personality - no bragging about IQ or team membership
- ✅ Always responds when @mentioned, asks follow-ups if needed
- ✅ Avoids casual chitchat - focused on API help only
- ✅ Natural conversational tone, not corporate or robotic
- ✅ Maintained critical guardrails (never say "not an exchange")

**Commits:**
- `e2e2fbb`: Concise, focused, humble bot behavior
- `c74f6c5`: Allow greetings when @mentioned
- `c938fc2`: Improved error messages
- `f161515`: Added critical guardrails and USPs
- `2dbd141`: Code correction feature

## Features Roadmap

- [x] RAG-based question answering
- [x] Gemini 2.5 Flash integration
- [x] Silent non-API message filtering
- [x] @Mention detection and always-respond
- [x] Auto-documentation fetching
- [x] Concise, humble responses
- [x] Code review and debugging help
- [x] Critical brand guardrails
- [ ] Multi-language support
- [ ] Conversation history tracking
- [ ] Analytics dashboard

## Contributing

Contributions are welcome! This project is open-source under MIT license with attribution requirement.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

**Attribution Required:** When forking or creating derivative works, please maintain attribution to [DecentralizedJM](https://github.com/DecentralizedJM) as per MIT license.

## License

MIT License - Copyright © 2025 [DecentralizedJM](https://github.com/DecentralizedJM)

This is original work. While open-source under MIT, proper attribution is required for any derivative works. See [LICENSE](LICENSE) file for full details.

## Support & Contact

- 🐛 **Issues:** [GitHub Issues](https://github.com/DecentralizedJM/Mudrex-API-Intelligent-Assitant-/issues)
- 📧 **Contact:** Open an issue for questions or support
- 📝 **Logs:** Check `bot.log` for debugging
- 🤖 **Live Bot:** [@API_Assistant_V2_bot](https://t.me/API_Assistant_V2_bot) on Telegram

---

**Built with ❤️ by [DecentralizedJM](https://github.com/DecentralizedJM)**  
*Empowering the Mudrex API community with intelligent assistance*
