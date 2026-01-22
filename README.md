# Mudrex API Bot 🤖

A **GROUP-ONLY** generic Telegram bot for private API traders community. Helps developers with Mudrex API documentation, coding questions, error debugging, and general API help.

> ⚠️ **GROUP-ONLY**: This bot only works in Telegram groups. It does NOT respond to DMs.
> 
> ⚠️ **SERVICE ACCOUNT MODEL**: This bot uses a read-only service account key to fetch PUBLIC data (prices, market info). It cannot access individual user accounts (positions, orders, balance).

## Features

- **RAG-Powered Answers**: Uses Gemini AI with retrieval-augmented generation for accurate API documentation responses
- **MCP Integration**: Can access public/general information (like listing futures contracts)
- **Group-Only Mode**: Only responds when mentioned/tagged in groups, rejects DMs
- **Community Focus**: Designed for API traders group discussions - feedback, coding help, errors
- **Smart Filtering**: Only responds to API-related questions, ignores off-topic chat
- **Code Examples**: Provides working Python/JavaScript code snippets
- **Error Debugging**: Helps troubleshoot API errors and integration issues

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/DecentralizedJM/Mudrex-API-Intelligent-Assitant-.git
cd Mudrex-API-Intelligent-Assitant-

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy example config
cp .env.example .env

# Edit with your keys
nano .env  # or use any editor
```

Required settings:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

Optional (for public data access):
```env
MUDREX_API_SECRET=your_service_account_read_only_key
```

**Important**: Use your **personal API secret** from Mudrex. The bot uses this to fetch public market data (prices, contracts, status). The bot code is configured to block personal account queries - even though it has your key, it won't fetch user balances, orders, or positions. Users asking for personal data will get a message directing them to use Claude Desktop with MCP or the Mudrex dashboard.

### 3. Ingest Documentation

```bash
# Create/update documentation
python3 scripts/scrape_docs.py

# Ingest into vector store
python3 scripts/ingest_docs.py
```

### 4. Run

```bash
python3 main.py
```

## Bot Commands (Group-Only)

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/stats` | Bot statistics |
| `/tools` | Available MCP tools |
| `/mcp` | MCP setup guide |
| `/futures` | List futures contracts (public info) |

**Usage**: 
- Just ask your API question - bot automatically detects and responds
- Or tag with `@botname` to get attention
- Bot ignores off-topic messages when not tagged

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Bot                         │
│  (Junior Dev + Community Admin personality)             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  RAG Pipeline│    │  MCP Client  │    │  Gemini   │  │
│  │  (Docs Query)│    │  (Live Data) │    │  (AI)     │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│         │                   │                 │         │
│         ▼                   ▼                 │         │
│  ┌──────────────┐    ┌──────────────┐         │         │
│  │ Vector Store │    │ Mudrex API   │◄────────┘         │
│  │ (Embeddings) │    │ (Read-Only)  │                   │
│  └──────────────┘    └──────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── main.py                 # Entry point
├── src/
│   ├── bot/               # Telegram bot handlers
│   │   └── telegram_bot.py
│   ├── rag/               # RAG pipeline
│   │   ├── pipeline.py
│   │   ├── vector_store.py
│   │   ├── gemini_client.py
│   │   └── document_loader.py
│   ├── mcp/               # MCP integration
│   │   ├── client.py
│   │   └── tools.py
│   └── config/            # Configuration
│       └── settings.py
├── scripts/
│   ├── ingest_docs.py     # Document ingestion
│   └── scrape_docs.py     # Documentation scraper
├── docs/                  # API documentation files
├── data/                  # Vector store data
├── requirements.txt
└── .env.example
```

## MCP Integration

The bot integrates with Mudrex's MCP (Model Context Protocol) server for live data:

```python
# Safe endpoints (read-only)
- get_market_price
- get_ticker_24hr
- get_orderbook
- get_klines
- get_account_balance
- get_positions
- get_open_orders

# Blocked endpoints (safety)
- place_order
- cancel_order
- modify_order
- close_position
```

## Bot Personality

The bot acts as a **Junior Dev + Community Admin**:

✅ **Does:**
- Answers API questions directly
- Provides working code examples
- Debugs integration issues
- Asks clarifying questions when needed
- Tags @DecentralizedJM for escalations

❌ **Doesn't:**
- Engage in off-topic chat
- Give trading advice
- Execute order placement
- Mention competitor exchanges

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Telegram bot token |
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `MUDREX_API_SECRET` | No | - | Mudrex API key (read-only) |
| `GEMINI_MODEL` | No | gemini-2.5-flash-preview-05-20 | Gemini model |
| `MCP_ENABLED` | No | true | Enable MCP integration |
| `ALLOWED_CHAT_IDS` | No | - | Restrict to specific chats |

## Development

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python3 main.py

# Update documentation
python3 scripts/scrape_docs.py
python3 scripts/ingest_docs.py

# Test MCP connection
python3 -c "
import asyncio
from src.mcp import MudrexMCPClient
async def test():
    client = MudrexMCPClient()
    await client.connect()
    print(client.get_available_tools())
asyncio.run(test())
"
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Author

**DecentralizedJM** - [GitHub](https://github.com/DecentralizedJM)

---

*Built with ❤️ for the Mudrex developer community*
