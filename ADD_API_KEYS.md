# 🎯 FINAL SETUP - ADD YOUR API KEYS NOW

## ✅ Everything is Ready!

Your bot is configured and documentation is loaded. Now add your API keys to activate it.

---

## 📝 Step 1: Open the .env File

```bash
cd /Users/jm/mudrex-api-bot
code .env
# or
nano .env
```

---

## 🔑 Step 2: Add Your API Keys

### A. Get Telegram Bot Token (5 minutes)

1. Open Telegram
2. Search for: `@BotFather`
3. Send: `/newbot`
4. Follow prompts:
   - Bot name: `Mudrex API Assistant` (or your choice)
   - Username: `mudrex_api_bot` (must end with 'bot')
5. Copy the token (looks like: `7234567890:AAH...`)

**Add to .env:**
```bash
TELEGRAM_BOT_TOKEN=7234567890:AAHxxxxxxxxxxxxxxxxxxxxxxx
```

### B. Get Gemini API Key (2 minutes)

1. Visit: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Select a Google Cloud project (or create new)
4. Copy the key (looks like: `AIzaSy...`)

**Add to .env:**
```bash
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Your .env Should Look Like:

```bash
# Environment Configuration for Mudrex API Bot

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=7234567890:AAHxxxxxxxxxxxxxxxxxxxxxxx

# Gemini AI Configuration
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-3-pro-preview
GEMINI_TEMPERATURE=0.3
GEMINI_MAX_TOKENS=1024

# (rest stays as is)
```

**Save the file!** (Ctrl+O in nano, or Cmd+S in VS Code)

---

## 🚀 Step 3: Re-Ingest Documentation (With Real API Key)

Now that you have a real Gemini key, re-ingest the docs to create proper embeddings:

```bash
cd /Users/jm/mudrex-api-bot
source venv/bin/activate
python scripts/ingest_docs.py
```

**Expected output:**
```
Starting document ingestion...
Loaded: mudrex-api-documentation.md
Loaded: getting-started.md
Loaded: orders.md
Created 11 chunks from 4 documents
Generating embeddings for 11 documents...
✓ Successfully ingested 11 chunks from 4 documents
✓ Vector database: ./data/chroma
```

(No more API_KEY_INVALID errors!)

---

## ▶️ Step 4: Run the Bot

```bash
python main.py
```

**You should see:**
```
==================================================
Starting Mudrex API Documentation Bot
==================================================
Initializing RAG pipeline...
Loaded 11 document chunks
Initializing Telegram bot...
Bot is ready! Starting polling...
```

**Bot is now running!** ✅

---

## 📱 Step 5: Test in Telegram

1. Open Telegram on your phone/desktop
2. Search for your bot: `@mudrex_api_bot` (or whatever username you chose)
3. Click "START" or send: `/start`

**Try these questions:**
```
/start
How do I authenticate with the API?
What's the endpoint for creating orders?
What are the rate limits?
Show me an example request
```

The bot should respond with information from your Mudrex docs!

---

## 🎯 What Happens Now?

```
User asks: "How do I authenticate?"
    ↓
Bot searches vector DB for "authentication"
    ↓
Finds relevant sections from docs
    ↓
Sends to Gemini with context
    ↓
Gemini generates smart answer
    ↓
User gets accurate response!
```

---

## 🛠️ Troubleshooting

### Bot doesn't start?
```bash
# Check your .env file
cat .env | grep TOKEN
cat .env | grep GEMINI

# Make sure no spaces around the = sign
# Make sure you saved the file
```

### Bot doesn't respond in Telegram?
- Make sure bot is running (you should see "Bot is ready!")
- Try `/start` command first
- Check bot username is correct

### API key errors?
- Gemini: Make sure it's from https://makersuite.google.com/app/apikey
- Telegram: Make sure it's from @BotFather
- Both should have no spaces or extra characters

---

## ✨ Next Steps (After Bot Works)

Once your bot is responding:

### 1. Add to Your Telegram Group
- Add the bot to your Mudrex API users group
- Bot will auto-respond to API questions

### 2. Improve Documentation
```bash
# Fetch more comprehensive docs
python scripts/fetch_mudrex_docs.py

# Or manually add more .md files to docs/
# Then re-ingest:
python scripts/ingest_docs.py
```

### 3. Customize Bot Behavior
Edit `.env` to tune:
```bash
GEMINI_TEMPERATURE=0.5  # More creative (0.0-1.0)
TOP_K_RESULTS=10        # Retrieve more context
```

### 4. Restrict to Specific Chat (Optional)
```bash
# Get your group chat ID
# Add to .env:
ALLOWED_CHAT_IDS=-1001234567890
```

---

## 📊 Quick Status Check

Run this to verify everything:
```bash
cd /Users/jm/mudrex-api-bot
source venv/bin/activate
python test_setup.py
```

Should show all ✓ checks!

---

## 🎊 You're Done!

Your Mudrex API Intelligent Assistant is ready to:
- Answer API questions 24/7
- Reduce support burden on devs
- Help your community succeed

**Add your keys and let's go!** 🚀

---

## Need Help?

- Check logs: `cat bot.log`
- Test ingestion: `python scripts/ingest_docs.py`
- Verify setup: `python test_setup.py`
- Review docs: `cat docs/mudrex-api-documentation.md`

**Everything is configured. Just add your API keys!** 🔑
