# Railway Shell Deployment Guide

## 🚀 How to Deploy in Railway Shell

After Railway deploys your bot, you need to ingest the documentation to create the RAG knowledge base.

### Step 1: Access Railway Shell

1. Go to [railway.app](https://railway.app)
2. Open your project
3. Click on your service (the bot)
4. Go to **"Deployments"** tab
5. Click on the latest deployment
6. Click **"Shell"** button (or "Open Shell")

### Step 2: Run Documentation Ingestion

In the Railway Shell, run:

```bash
python3 scripts/ingest_docs.py
```

This will:
- Load all documentation files from `docs/` folder
- Create embeddings using Gemini
- Save to `./data/chroma/vectors.pkl`
- Show progress and chunk count

### Step 3: Verify

Check the output - you should see:
```
✓ Loaded 10 documents
✓ Created 29 chunks
✓ Successfully ingested 29 chunks
```

### Step 4: Restart Service (if needed)

After ingestion, restart the service:
- Go to Railway dashboard
- Click **"Redeploy"** or the service will auto-restart
- Check logs to verify bot started with docs loaded

---

## 🔄 Alternative: One-Time Setup Script

You can also add this to Railway as a one-time setup:

### Option A: Add to Dockerfile (Recommended)

Update Dockerfile to auto-ingest on first run:

```dockerfile
# Add after COPY . .
RUN if [ ! -f data/chroma/vectors.pkl ]; then \
    python3 scripts/ingest_docs.py; \
    fi
```

### Option B: Railway Build Command

In Railway → Settings → Build:
- Add post-build command: `python3 scripts/ingest_docs.py`

---

## 📋 Complete Shell Commands

```bash
# 1. Check you're in the right directory
pwd
# Should show: /app

# 2. Check if docs exist
ls -la docs/
# Should show 10 .md files

# 3. Ingest documentation
python3 scripts/ingest_docs.py

# 4. Verify vector store was created
ls -la data/chroma/
# Should show: vectors.pkl

# 5. Check bot logs
# Go to Railway → Logs tab
```

---

## 🆘 Troubleshooting

**Problem**: "No such file or directory: docs/"
- **Solution**: Check you're in `/app` directory
- Run: `cd /app && python3 scripts/ingest_docs.py`

**Problem**: "GEMINI_API_KEY not set"
- **Solution**: Set `GEMINI_API_KEY` in Railway Variables
- Then re-run ingestion

**Problem**: "Permission denied"
- **Solution**: Railway shell has permissions, try again
- Or check if `data/` directory exists: `mkdir -p data/chroma`

**Problem**: Vector store not persisting
- **Solution**: Railway volumes persist data
- Check Railway → Settings → Volumes
- Ensure `./data` is mounted

---

## ✅ Quick Checklist

- [ ] Railway service deployed successfully
- [ ] Environment variables set (TELEGRAM_BOT_TOKEN, GEMINI_API_KEY)
- [ ] Opened Railway Shell
- [ ] Ran `python3 scripts/ingest_docs.py`
- [ ] Verified output shows "X chunks ingested"
- [ ] Checked bot logs show "Loaded X document chunks"
- [ ] Bot responding to questions in Telegram group

---

## 🎯 Summary

**After Railway deploys:**
1. Open Shell in Railway dashboard
2. Run: `python3 scripts/ingest_docs.py`
3. Wait for "Successfully ingested X chunks"
4. Bot is ready!

That's it! The bot will now have all API knowledge loaded.
