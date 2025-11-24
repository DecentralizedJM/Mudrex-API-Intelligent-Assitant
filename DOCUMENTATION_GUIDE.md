# 📚 Adding Mudrex API Documentation

## Your Documentation Source

**URL:** https://docs.trade.mudrex.com

You have **3 options** to add this documentation to your bot:

---

## ✅ Option 1: Automatic Fetch (Easiest - Try This First)

Run the automatic fetcher script:

```bash
cd /Users/jm/mudrex-api-bot
source venv/bin/activate
python scripts/fetch_mudrex_docs.py
```

**What it does:**
- Fetches content from https://docs.trade.mudrex.com
- Extracts the text content
- Saves to `docs/mudrex-api-documentation.md`

**Check the result:**
```bash
cat docs/mudrex-api-documentation.md | head -100
```

**If it looks good** → Proceed to ingest (see bottom)  
**If it looks incomplete** → Try Option 2

---

## ✅ Option 2: Manual Copy-Paste (Most Reliable)

If automatic fetching doesn't capture everything:

### Step 1: Generate Template
```bash
python scripts/fetch_mudrex_docs.py
# This creates docs/mudrex-api-MANUAL.md
```

### Step 2: Fill the Template

1. Open the template:
   ```bash
   code docs/mudrex-api-MANUAL.md
   # or
   nano docs/mudrex-api-MANUAL.md
   ```

2. Visit: https://docs.trade.mudrex.com

3. **Copy ALL sections:**
   - Overview
   - Authentication (API keys, headers)
   - All Endpoints (Wallet, Futures, Orders, Positions)
   - Request/Response examples
   - Error codes
   - Rate limits
   - Code examples

4. Paste into the template file

5. Save the file

---

## ✅ Option 3: Structured Sections (Best Quality)

Create multiple organized files for better retrieval:

```bash
cd /Users/jm/mudrex-api-bot/docs

# Create individual documentation files
touch authentication.md
touch wallet-api.md
touch futures-api.md
touch orders-api.md
touch positions-api.md
touch error-codes.md
touch rate-limits.md
touch examples.md
```

Then fill each file with its relevant section from https://docs.trade.mudrex.com

**Benefits:**
- Better organized
- Easier to update specific sections
- More accurate search results

---

## 📋 What to Include (Checklist)

When copying documentation, make sure you include:

### ✅ Authentication
- How to get API keys
- Required headers (X-Authentication, X-Time, etc.)
- Authentication examples

### ✅ Base URLs
- API base URL
- Version information

### ✅ All Endpoints
For each endpoint, include:
- Method (GET, POST, PUT, DELETE)
- Path (/fapi/v1/...)
- Description
- Parameters (required/optional)
- Request example
- Response example

### ✅ Data Types
- How numbers are handled
- Date/time format
- Decimal precision

### ✅ Error Codes
- All possible error codes
- What each error means
- How to fix common errors

### ✅ Rate Limits
- Requests per second/minute
- What happens when exceeded

### ✅ Code Examples
- Python examples
- cURL examples
- Any language examples available

---

## 🚀 After Adding Documentation

Once you have the documentation in `docs/` folder:

### Step 1: Verify Files
```bash
ls -lh docs/
```

You should see your documentation files.

### Step 2: Ingest into Vector Database
```bash
cd /Users/jm/mudrex-api-bot
source venv/bin/activate
python scripts/ingest_docs.py
```

**Expected output:**
```
Starting document ingestion...
Loaded: mudrex-api-documentation.md
Generating embeddings for X documents...
✓ Successfully ingested X chunks from Y documents
✓ Vector database: ./data/chroma
```

### Step 3: Test the Bot
```bash
python main.py
```

In Telegram, ask:
- "How do I authenticate?"
- "What's the endpoint for creating orders?"
- "What are the rate limits?"

---

## 💡 Format Examples

### Good Documentation Format:

```markdown
# Authentication

## API Keys

Get your API keys from Settings > API in your Mudrex account.

## Required Headers

Every request must include:
- `X-Authentication`: Your API secret
- `X-Time`: Millisecond timestamp

## Example Request

\`\`\`bash
curl -X GET https://trade.mudrex.com/fapi/v1/wallet \\
  -H "X-Authentication: your_api_secret" \\
  -H "X-Time: 1635789012000"
\`\`\`

## Response

\`\`\`json
{
  "success": true,
  "data": {
    "balance": "1000.50"
  }
}
\`\`\`
```

### Avoid This:

```
auth
keys needed
X-Auth header
```

(Too minimal - bot needs context!)

---

## 🎯 Quick Start Recommendation

**For fastest results:**

1. **Run automatic fetch:**
   ```bash
   python scripts/fetch_mudrex_docs.py
   ```

2. **Check the output:**
   ```bash
   cat docs/mudrex-api-documentation.md
   ```

3. **If it looks incomplete:**
   - Visit https://docs.trade.mudrex.com
   - Copy ALL text content
   - Paste into `docs/mudrex-api-manual.md`

4. **Ingest:**
   ```bash
   python scripts/ingest_docs.py
   ```

5. **Run bot:**
   ```bash
   python main.py
   ```

---

## ❓ FAQ

**Q: How much documentation do I need?**  
A: More is better! Include everything from the docs site.

**Q: What format should it be?**  
A: Markdown (.md) or plain text (.txt) works fine.

**Q: Can I add multiple files?**  
A: Yes! All files in `docs/` are processed.

**Q: Can I update docs later?**  
A: Yes! Just update files in `docs/` and re-run `python scripts/ingest_docs.py`

**Q: Does the bot need internet to answer?**  
A: Yes, it needs internet to call Gemini API. But your docs are stored locally.

---

**Choose the option that works best for you and let's get your documentation loaded!** 📚
