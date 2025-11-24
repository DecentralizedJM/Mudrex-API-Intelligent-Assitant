# Mudrex API Documentation Bot

An intelligent Telegram bot that answers Mudrex API questions using RAG (Retrieval-Augmented Generation) with Google Gemini 3.0 Pro Preview.

**Author:** [DecentralizedJM](https://github.com/DecentralizedJM)  
**License:** MIT (with attribution required)  
**Copyright:** © 2025 DecentralizedJM

---

## Features

- 🤖 **Automatic Query Detection**: Identifies API-related questions
- 📚 **Documentation RAG**: Uses vector search to find relevant docs
- 🔒 **Focused Responses**: Only answers API-related queries
- 💬 **Context Aware**: Maintains conversation history
- ⚡ **Fast & Accurate**: Powered by Gemini 3.0 Pro Preview
- 🔐 **Secure**: Optional chat ID restrictions

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
│   (Handler)     │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  RAG Pipeline   │◄────►│  Vector Store │
│                 │      │ (sklearn-based)│
└──────┬──────────┘      └──────────────┘
       │
       ▼
┌─────────────────┐
│  Gemini 3.0     │
│  Pro Preview    │
└─────────────────┘
```
│                 │      │ Vector Store │
└──────┬──────────┘      └──────────────┘
       │
       ▼
┌─────────────────┐
│  Gemini 2.0     │
│  Flash API      │
└─────────────────┘
```

## Tech Stack

- Python 3.10+
- python-telegram-bot for Telegram integration
- Scikit-learn for vector similarity search
- Google Gemini 3.0 Pro Preview API for LLM
- FastAPI for optional webhook server

## Setup

### 1. Prerequisites

- Python 3.10 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Google Gemini API Key

### 2. Installation

```bash
# Clone or navigate to project
cd mudrex-api-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Required:
# - TELEGRAM_BOT_TOKEN
# - GEMINI_API_KEY
```

### 4. Add Documentation

Place your Mudrex API documentation files in the `docs/` directory:

```bash
mkdir -p docs
# Add your .md, .txt, or .rst files here
```

### 5. Ingest Documentation

```bash
# Load documentation into vector database
python scripts/ingest_docs.py
```

### 6. Run the Bot

```bash
python main.py
```

## Usage

### Telegram Commands

- `/start` - Welcome message and introduction
- `/help` - Show available commands and tips
- `/stats` - Display bot statistics

### Example Questions

```
User: How do I authenticate with the API?
Bot: To authenticate with the Mudrex API, you need to...

User: What's the endpoint for creating orders?
Bot: The order creation endpoint is POST /v1/orders...

User: Error 401 Unauthorized
Bot: A 401 error indicates authentication issues...
```

## Configuration Options

Edit `.env` to customize behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_MODEL` | Gemini model to use | `gemini-3-pro-preview` |
| `GEMINI_TEMPERATURE` | Response creativity (0-1) | `0.3` |
| `TOP_K_RESULTS` | Documents to retrieve | `5` |
| `SIMILARITY_THRESHOLD` | Minimum similarity score | `0.6` |
| `ALLOWED_CHAT_IDS` | Restrict to specific chats | None (all allowed) |

## Project Structure

```
mudrex-api-bot/
├── src/
│   ├── bot/              # Telegram bot handlers
│   ├── rag/              # RAG pipeline & vector store
│   └── config/           # Configuration management
├── scripts/
│   └── ingest_docs.py    # Documentation ingestion
├── docs/                 # API documentation files
├── data/                 # Vector database (auto-created)
├── main.py               # Entry point
├── requirements.txt      # Python dependencies
└── .env                  # Environment variables
```

## Development

### Adding New Documentation

1. Add files to `docs/` directory
2. Run ingestion: `python scripts/ingest_docs.py`
3. Restart bot

### Changing LLM Provider

The architecture supports easy LLM swapping. To use OpenAI/Claude:

1. Update `src/rag/gemini_client.py`
2. Change API client initialization
3. Update environment variables

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests (when available)
pytest tests/
```

## Deployment

### Docker (Coming Soon)

```bash
docker build -t mudrex-api-bot .
docker run -d --env-file .env mudrex-api-bot
```

### Production Considerations

- Use webhook mode instead of polling for better performance
- Set `ALLOWED_CHAT_IDS` to restrict access
- Monitor logs: `tail -f bot.log`
- Regularly update documentation via re-ingestion

## Troubleshooting

### Bot doesn't respond
- Check `TELEGRAM_BOT_TOKEN` is correct
- Verify bot has no other instances running
- Check chat ID isn't restricted

### Poor answer quality
- Increase `TOP_K_RESULTS` to retrieve more context
- Lower `SIMILARITY_THRESHOLD` for more results
- Add more comprehensive documentation

### Import errors
- Ensure virtual environment is activated
- Reinstall: `pip install -r requirements.txt --force-reinstall`

## License

MIT License - Copyright © 2025 [DecentralizedJM](https://github.com/DecentralizedJM)

This is original work. While open-source under MIT, proper attribution is required for any derivative works. See [LICENSE](LICENSE) file for full details.

## Support

For issues or questions:
- Open an issue on GitHub
- Contact the development team
- Check logs in `bot.log`

---

Built with ❤️ by [DecentralizedJM](https://github.com/DecentralizedJM) for the Mudrex API community
