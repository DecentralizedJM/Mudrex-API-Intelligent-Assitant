# Mudrex API Copilot — Product Documentation

**Version:** 1.0  
**Last Updated:** January 2026  
**Author:** DecentralizedJM  
**Status:** Production (Staging Branch)

---

## 1. Executive Summary

The **Mudrex API Copilot** is an AI-powered Telegram assistant designed to help developers integrate with the Mudrex Futures API. It functions like GitHub Copilot but specialized for Mudrex — providing code examples, debugging assistance, and API onboarding support.

### Key Value Propositions

| For | Value |
|-----|-------|
| **New Developers** | Quick onboarding with code snippets and authentication guidance |
| **Active Traders** | Real-time answers about API endpoints, error codes, and rate limits |
| **Community** | 24/7 support without manual intervention |
| **Mudrex Team** | Reduced support load, consistent documentation delivery |

---

## 2. Product Overview

### 2.1 What It Does

- Answers API questions with working code examples
- Debugs integration errors (analyzes logs, HTTP codes)
- Explains authentication and endpoint usage
- Fetches live market data (500+ futures pairs)
- Provides official documentation links
- Recommends community tools (SDK, broadcasters)

### 2.2 What It Doesn't Do

- Give trading advice or signals
- Execute trades on behalf of users
- Respond to off-topic conversations
- Auto-reply to keyword detection (reactive only)

### 2.3 Target Users

| User Type | Use Case |
|-----------|----------|
| API Developers | Integration help, code examples |
| Algo Traders | Debugging, endpoint clarification |
| Community Admins | Assist users by tagging the bot |
| Support Team | Escalation via @DecentralizedJM tag |

---

## 3. Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         TELEGRAM                                 │
│                    (Group Messages)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      TELEGRAM BOT                                │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │   Message    │    │   Command    │    │   Response   │      │
│   │   Handler    │───▶│   Router     │───▶│   Manager    │      │
│   └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      RAG PIPELINE                                │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │    Query     │    │   Document   │    │   Response   │      │
│   │ Transformer  │───▶│  Retriever   │───▶│  Generator   │      │
│   └──────────────┘    └──────────────┘    └──────────────┘      │
│          │                   │                   │               │
│          ▼                   ▼                   ▼               │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │   Gemini     │    │   Vector     │    │   Redis      │      │
│   │   Flash      │    │   Store      │    │   Cache      │      │
│   └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│                                                                  │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│   │   Mudrex     │    │   Gemini     │    │   Station    │      │
│   │   MCP API    │    │   AI API     │    │   Master     │      │
│   └──────────────┘    └──────────────┘    └──────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Descriptions

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Telegram Bot** | Message handling, command routing | python-telegram-bot |
| **RAG Pipeline** | Document retrieval and response generation | Custom implementation |
| **Vector Store** | Semantic search over documentation | NumPy, scikit-learn |
| **Gemini AI** | LLM for response generation and embeddings | google-genai SDK |
| **MCP Client** | Live market data from Mudrex | REST API calls |
| **Redis Cache** | Response caching, session management | redis-py |
| **Station Master** | Centralized error reporting | HTTP webhooks |

### 3.3 Data Flow

```
User Message
     │
     ▼
┌─────────────────┐
│ Is bot engaged? │──No──▶ Ignore
│ (@mention/reply)│
└────────┬────────┘
         │Yes
         ▼
┌─────────────────┐
│ Check Redis     │──Hit──▶ Return cached response
│ Cache           │
└────────┬────────┘
         │Miss
         ▼
┌─────────────────┐
│ Query           │
│ Transformation  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vector Search   │
│ (Embeddings)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Document        │
│ Validation      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Reranking   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response        │
│ Generation      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cache & Send    │
└─────────────────┘
```

---

## 4. Core Features

### 4.1 Response Triggers

The bot operates in **reactive mode** only. It responds when:

| Trigger | Description | Example |
|---------|-------------|---------|
| **Direct Mention** | User tags @BotName in message | "Hey @API_Copilot how do I place an order?" |
| **Reply to Bot** | User replies to bot's previous message | Continuing a conversation thread |
| **Quote + Mention** | User quotes someone else and tags the bot | Admin helping another user by tagging bot |

### 4.2 Bot Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/help` | All | Usage guide and examples |
| `/endpoints` | All | API endpoints with documentation links |
| `/listfutures` | All | Count of available futures pairs |
| `/tools` | All | MCP server tools list |
| `/mcp` | All | MCP setup instructions |
| `/stats` | Admin | Bot usage statistics |
| `/learn <text>` | Admin | Teach bot new information |
| `/set_fact KEY value` | Admin | Set a strict fact |
| `/delete_fact KEY` | Admin | Remove a fact |

### 4.3 Response Types

| Type | When Used | Example |
|------|-----------|---------|
| **Code Example** | "How to" questions | Python/JS snippet with authentication |
| **Error Debug** | Error logs or codes | Analysis + fix |
| **Documentation Link** | Feature inquiry | Link to relevant docs section |
| **Template Response** | Known limitations | Webhooks, TradingView, etc. |
| **Fallback** | Unknown topics | "Couldn't find that. Docs: [link] — @DecentralizedJM can help" |

---

## 5. RAG Pipeline

### 5.1 Overview

The Retrieval-Augmented Generation (RAG) pipeline ensures accurate, documentation-grounded responses.

### 5.2 Pipeline Stages

| Stage | Purpose | Technique |
|-------|---------|-----------|
| **1. Query Transformation** | Improve search query | Step-back prompting, query expansion |
| **2. Initial Retrieval** | Find relevant documents | Vector similarity (cosine) |
| **3. Iterative Retrieval** | Retry with modified query | Max 2 iterations |
| **4. Relevancy Validation** | Filter irrelevant docs | LLM scoring (threshold: 0.6) |
| **5. Reranking** | Order by relevance | LLM-based reranking |
| **6. Response Generation** | Create final answer | Context-grounded LLM call |

### 5.3 Hallucination Prevention

| Mechanism | Description |
|-----------|-------------|
| **Document Validation** | LLM verifies if retrieved docs answer the query |
| **No Web Search** | Responses use only Mudrex documentation |
| **Template Responses** | Known gaps have pre-written answers |
| **Honest Fallback** | "Couldn't find that" instead of guessing |

### 5.4 Thresholds & Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Similarity Threshold | 0.45 | Minimum cosine similarity for retrieval |
| Context Threshold | 0.30 | Lower threshold for broader context |
| Relevancy Threshold | 0.6 | Minimum validation score to use a doc |
| Rerank Top K | 5 | Number of docs after reranking |
| Max Iterations | 2 | Query transformation retry limit |

---

## 6. MCP Integration

### 6.1 What is MCP?

Model Context Protocol (MCP) allows AI assistants to interact with external services. Mudrex provides an MCP server for futures trading operations.

### 6.2 Available Tools

#### Read-Only (Safe)

| Tool | Description |
|------|-------------|
| `list_futures` | List all futures contracts (500+ pairs) |
| `get_future` | Details for a specific contract |
| `get_orders` | All open orders |
| `get_order` | Specific order by ID |
| `get_order_history` | Historical orders |
| `get_positions` | All open positions |
| `get_position_history` | Historical positions |
| `get_leverage` | Current leverage for a contract |
| `get_liquidation_price` | Liquidation price calculation |
| `get_available_funds` | Available trading balance |
| `get_fee_history` | Trading fee history |

#### Write Operations (Confirmation Required)

| Tool | Description |
|------|-------------|
| `place_order` | Place LONG/SHORT order |
| `amend_order` | Modify existing order |
| `cancel_order` | Cancel an order |
| `close_position` | Close at market |
| `reverse_position` | Flip long ↔ short |
| `place_risk_order` | Set SL/TP |
| `amend_risk_order` | Modify SL/TP |
| `set_leverage` | Change leverage |
| `add_margin` | Add margin to position |

### 6.3 Bot Usage of MCP

The Telegram bot uses MCP for:
- Listing available futures contracts (`/listfutures`)
- Fetching contract details for user queries
- Displaying available tools (`/tools`)

**Note:** The bot does NOT execute trades. Write operations require user confirmation via Claude Desktop + MCP.

---

## 7. Scheduled Tasks

### 7.1 Changelog Watcher

| Property | Value |
|----------|-------|
| **Frequency** | Daily |
| **Source** | Mudrex API changelog |
| **Action** | Broadcast updates to group |
| **Purpose** | Keep community informed of API changes |

### 7.2 Futures Listing Watcher

| Property | Value |
|----------|-------|
| **Frequency** | Daily |
| **Action** | Compare current vs previous futures list |
| **Output** | Announce new listings and delistings |
| **Storage** | Persists previous state for comparison |

---

## 8. Caching Strategy

### 8.1 Redis Cache Layers

| Cache Type | TTL | Purpose |
|------------|-----|---------|
| Query Response | 1 hour | Identical question caching |
| Embeddings | 24 hours | Reduce embedding API calls |
| Relevancy Validation | 1 hour | Skip re-validation |
| Reranking Results | 1 hour | Skip re-ranking |
| Transformed Queries | 1 hour | Skip query transformation |

### 8.2 Cache Keys

Caches use SHA256 hashes of input data for keys, ensuring:
- Consistent key generation
- No collision with similar queries
- Privacy (queries not stored as plaintext)

---

## 9. Error Handling

### 9.1 Error Reporting

All errors are reported to **Station Master** for centralized monitoring:

| Error Type | Handling |
|------------|----------|
| API Timeout | Retry with exponential backoff |
| Rate Limit | Queue and retry after delay |
| Auth Error | Log and notify admin |
| Gemini 503 | Retry up to 3 times |
| Unhandled Exception | Report to Station Master + generic user message |

### 9.2 User-Facing Errors

Users see friendly messages, not stack traces:

| Internal Error | User Message |
|----------------|--------------|
| Gemini timeout | "Taking longer than usual. Try again?" |
| No docs found | "Couldn't find that. Docs: [link]" |
| MCP failure | "Can't fetch live data right now." |

---

## 10. Security

### 10.1 Access Control

| Layer | Control |
|-------|---------|
| **Group Only** | Bot ignores DMs |
| **Admin Commands** | `/stats`, `/learn` restricted by user ID |
| **Allowed Chats** | Optional whitelist via `ALLOWED_CHAT_IDS` |

### 10.2 API Key Safety

| Key | Storage | Usage |
|-----|---------|-------|
| Telegram Token | Environment variable | Bot authentication |
| Gemini API Key | Environment variable | LLM calls |
| Mudrex Secret | Environment variable | MCP read-only data |

### 10.3 Data Privacy

- No user messages stored permanently
- Conversation context cleared after session
- Redis cache auto-expires (TTL)
- No PII in logs

---

## 11. Deployment

### 11.1 Requirements

| Component | Specification |
|-----------|---------------|
| Python | 3.10+ |
| Memory | 512MB minimum |
| Redis | Optional (for caching) |
| Network | Outbound HTTPS |

### 11.2 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Telegram bot token |
| `GEMINI_API_KEY` | Yes | Google AI API key |
| `MUDREX_API_SECRET` | No | For live market data |
| `REDIS_URL` | No | Redis connection string |
| `ADMIN_USER_IDS` | No | Admin Telegram IDs |
| `ALLOWED_CHAT_IDS` | No | Whitelisted group IDs |

### 11.3 Deployment Options

| Platform | Notes |
|----------|-------|
| **Railway** | Recommended. Add Redis service for caching. |
| **Heroku** | Works with Redis add-on. |
| **VPS** | Docker or systemd service. |
| **Local** | For development only. |

---

## 12. Monitoring

### 12.1 Health Indicators

| Metric | Healthy | Warning |
|--------|---------|---------|
| Response Time | < 5s | > 10s |
| Cache Hit Rate | > 50% | < 20% |
| Error Rate | < 1% | > 5% |
| Gemini Latency | < 3s | > 8s |

### 12.2 Logging

| Level | Content |
|-------|---------|
| INFO | Message received, response sent |
| DEBUG | RAG pipeline steps, cache operations |
| WARNING | Rate limits, retries |
| ERROR | API failures, exceptions |

---

## 13. Community Resources

| Resource | URL | Description |
|----------|-----|-------------|
| **Python SDK** | github.com/DecentralizedJM/mudrex-api-trading-python-sdk | Symbol-first trading, 500+ pairs |
| **TIA Broadcaster** | github.com/DecentralizedJM/TIA-Service-Broadcaster | WebSocket signal streaming |
| **API Docs** | docs.trade.mudrex.com | Official documentation |
| **MCP Docs** | docs.trade.mudrex.com/docs/mcp | MCP setup guide |

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **RAG** | Retrieval-Augmented Generation — combining document search with LLM |
| **MCP** | Model Context Protocol — standard for AI-to-service communication |
| **Embeddings** | Vector representations of text for semantic search |
| **Reranking** | Re-ordering search results by relevance using LLM |
| **Hallucination** | LLM generating false information not in source docs |
| **Station Master** | Centralized error reporting service |

---

## 15. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 2026 | Initial release — reactive mode, RAG pipeline, MCP integration |

---

## Appendix A: File Structure

```
mudrex-api-copilot/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
│
├── src/
│   ├── bot/
│   │   └── telegram_bot.py    # Message handling, commands
│   │
│   ├── rag/
│   │   ├── pipeline.py        # RAG orchestration
│   │   ├── vector_store.py    # Embedding storage & search
│   │   ├── gemini_client.py   # LLM client & persona
│   │   ├── document_loader.py # Doc ingestion
│   │   ├── cache.py           # Redis caching
│   │   ├── context_manager.py # Conversation context
│   │   └── semantic_memory.py # Long-term facts
│   │
│   ├── mcp/
│   │   ├── client.py          # MCP API client
│   │   └── tools.py           # Tool definitions
│   │
│   ├── tasks/
│   │   ├── scheduler.py       # Job scheduling
│   │   ├── changelog_watcher.py
│   │   └── futures_listing_watcher.py
│   │
│   ├── lib/
│   │   └── error_reporter.py  # Station Master integration
│   │
│   └── config/
│       └── settings.py        # Configuration dataclass
│
├── docs/                      # RAG knowledge base (markdown)
├── data/                      # Vector store persistence
└── scripts/
    ├── ingest_docs.py         # Build vector store
    └── scrape_docs.py         # Fetch latest docs
```

---

## Appendix B: API Quick Reference

### Authentication

All Mudrex API calls use a single header:

```
X-Authentication: <your-api-secret>
```

No HMAC signing. No timestamps.

### Base URL

```
https://trade.mudrex.com/fapi/v1
```

### Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| -1121 | Invalid symbol | Use format `BTCUSDT` not `BTC-USDT` |
| -1022 | Auth failed | Check API secret |
| -1015 | Rate limited | Max 2 requests/second |

### Dashboard URL

```
https://www.mudrex.com/pro-trading
```

---

*Document generated for Confluence. Copy sections as needed.*
