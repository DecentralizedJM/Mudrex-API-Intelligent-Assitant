# RAG Knowledge Base - Complete Guide

## ✅ Yes! All API Knowledge is in RAG

Everything except the 2 MCP tools (`list_futures`, `get_future`) is stored in the **RAG (Retrieval Augmented Generation) system**.

## 📚 What Knowledge is Stored in RAG

### Documentation Files (10 files):

1. **authentication.md** - API authentication, headers, keys
2. **market-data.md** - Market data endpoints, tickers, orderbook, klines
3. **trading.md** - Order placement, order types, order management
4. **account.md** - Account balance, positions, leverage, margin
5. **error-codes.md** - All error codes and solutions
6. **websocket.md** - WebSocket streams, real-time data
7. **getting-started.md** - Quick start guide
8. **mudrex-api-documentation.md** - General API overview
9. **orders.md** - Order management details
10. **README.md** - Additional documentation

### What RAG Contains:

- ✅ API endpoint documentation
- ✅ Authentication methods
- ✅ Request/response formats
- ✅ Code examples (Python/JavaScript)
- ✅ Error handling guides
- ✅ Rate limits and best practices
- ✅ WebSocket setup
- ✅ Order types and parameters
- ✅ Position management
- ✅ Leverage and margin info

**Total**: ~29 document chunks after processing

---

## 📍 Where RAG is Situated/Stored

### Storage Location:

```
Project Root/
├── docs/                    # Source documentation files (markdown)
│   ├── authentication.md
│   ├── market-data.md
│   ├── trading.md
│   └── ... (10 files)
│
└── data/
    └── chroma/
        └── vectors.pkl      # Vector store (embeddings + documents)
```

### Storage Details:

**Location**: `./data/chroma/vectors.pkl`

**Contains**:
- Document texts (chunked)
- Vector embeddings (from Gemini)
- Metadata (filename, source)
- Document IDs

**Storage Type**: File-based (pickle format)

**Embedding Model**: `models/gemini-embedding-001` (Gemini)

---

## 🔄 How RAG Works

### 1. **Ingestion** (One-time setup):
```bash
python3 scripts/ingest_docs.py
```

This:
- Reads all `.md` files from `docs/` folder
- Splits them into chunks (~1000 chars each)
- Generates embeddings using Gemini
- Saves to `./data/chroma/vectors.pkl`

### 2. **Query Time** (When user asks):
```
User: "How do I authenticate?"
  ↓
Bot searches vector store for similar chunks
  ↓
Retrieves top 5 most relevant chunks
  ↓
Sends to Gemini with user question
  ↓
Gemini generates answer using retrieved context
  ↓
Bot responds to user
```

---

## 🎯 Knowledge Distribution

| Source | What It Provides |
|--------|------------------|
| **RAG** | API documentation, code examples, error handling, authentication, endpoints, WebSocket, etc. |
| **MCP** | Live public data: `list_futures`, `get_future` (contract listings) |
| **Gemini** | General AI reasoning, code generation, natural language understanding |

---

## 📊 Example: What RAG Can Answer

### ✅ RAG Answers (from documentation):

**User**: "How do I authenticate API requests?"
**RAG**: Retrieves `authentication.md` → Shows X-Authentication header usage

**User**: "What error code -1121 means?"
**RAG**: Retrieves `error-codes.md` → Explains "Invalid symbol" error

**User**: "How to place a limit order?"
**RAG**: Retrieves `trading.md` → Shows endpoint, parameters, code example

**User**: "What's the rate limit?"
**RAG**: Retrieves relevant docs → Explains rate limits

**User**: "How to set up WebSocket?"
**RAG**: Retrieves `websocket.md` → Shows connection setup

### ✅ MCP Answers (live data):

**User**: "What futures contracts are available?"
**MCP**: Calls `list_futures` → Returns live list of 600+ contracts

**User**: "What are BTC/USDT contract specs?"
**MCP**: Calls `get_future` → Returns live contract details

---

## 🔧 Updating RAG Knowledge

### To Add New Documentation:

1. **Add markdown file** to `docs/` folder:
   ```bash
   # Add new file
   docs/new-endpoint.md
   ```

2. **Re-ingest documents**:
   ```bash
   python3 scripts/ingest_docs.py
   ```

3. **Bot automatically uses new knowledge!**

### To Update Existing Docs:

1. Edit files in `docs/` folder
2. Re-run ingestion script
3. Vector store updates automatically

---

## 💾 Storage Size

- **Source Docs**: ~20KB (10 markdown files)
- **Vector Store**: ~500KB-1MB (after embeddings)
- **Location**: `./data/chroma/vectors.pkl`

**Note**: Vector store is created automatically on first ingestion.

---

## 🎯 Summary

**RAG Contains**:
- ✅ All API documentation
- ✅ Code examples
- ✅ Error handling
- ✅ Authentication guides
- ✅ Endpoint details
- ✅ Best practices

**RAG Location**:
- 📁 Source: `docs/` folder (markdown files)
- 💾 Storage: `./data/chroma/vectors.pkl` (vector embeddings)

**MCP Contains**:
- ✅ Live public data only (2 tools)

**Together**: RAG (knowledge) + MCP (live data) = Complete bot!
