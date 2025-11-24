# Quick Setup Guide

## Complete Setup Steps

### 1. Configure Environment Variables

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Add your API keys:
```
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
GEMINI_API_KEY=your_gemini_api_key
```

### 2. Add Your API Documentation

Place your Mudrex API documentation files in the `docs/` directory:

```bash
# Example: Copy your documentation
cp /path/to/your/api-docs/*.md docs/
```

Supported formats: `.md`, `.txt`, `.rst`

### 3. Ingest Documentation

Load your documentation into the vector database:

```bash
source venv/bin/activate
python scripts/ingest_docs.py
```

You should see output like:
```
INFO - Starting document ingestion...
INFO - Loaded: getting-started.md
INFO - Loaded: orders.md
INFO - Created 15 chunks from 2 documents
INFO - ✓ Successfully ingested 15 chunks
```

### 4. Run the Bot

```bash
python main.py
```

You should see:
```
INFO - Starting Mudrex API Documentation Bot
INFO - Initialized vector store with 15 documents
INFO - Bot is ready! Starting polling...
```

### 5. Test in Telegram

1. Open Telegram and find your bot (search for the bot name you created)
2. Send `/start` to begin
3. Ask a question like: "How do I authenticate with the API?"

## Getting API Keys

### Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Follow the instructions to create your bot
4. Copy the token provided

### Google Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key

## Troubleshooting

### Bot doesn't start

Check your `.env` file:
```bash
cat .env
```

Ensure both `TELEGRAM_BOT_TOKEN` and `GEMINI_API_KEY` are set.

### No documents found

Run the ingestion script:
```bash
python scripts/ingest_docs.py
```

### Import errors

Reinstall dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

## Optional: Restrict to Specific Chat

To only respond in your private API users group:

1. Add your bot to the Telegram group
2. Get the chat ID (you can use [@userinfobot](https://t.me/userinfobot))
3. Add to `.env`:
```
ALLOWED_CHAT_IDS=-1001234567890
```

For multiple chats, use comma-separated values:
```
ALLOWED_CHAT_IDS=-1001234567890,-1009876543210
```

## Next Steps

- Customize bot responses by editing `src/rag/gemini_client.py`
- Adjust similarity thresholds in `.env`
- Add more documentation files as your API evolves
- Monitor logs in `bot.log`

---

Need help? Check the main [README.md](README.md) or open an issue.
