"""
Mudrex API Bot - Telegram Handler
GROUP-ONLY bot for private API traders community
Responds only when mentioned/tagged in groups

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
import re
from typing import Optional, Dict, Tuple
from collections import defaultdict
import time

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode, ChatAction, ChatType

from ..config import config
from ..rag import RAGPipeline
from ..mcp import MudrexMCPClient, MudrexTools
from ..tasks.futures_listing_watcher import fetch_all_futures_symbols, fetch_all_futures_symbols_via_rest

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for group messages"""
    
    def __init__(self, max_messages: int = 50, window_seconds: int = 60):
        self.max_messages = max_messages
        self.window = window_seconds
        self.group_messages: Dict[int, list] = defaultdict(list)  # Per group
    
    def is_allowed(self, chat_id: int) -> bool:
        """Check if group is within rate limit"""
        now = time.time()
        self.group_messages[chat_id] = [
            t for t in self.group_messages[chat_id] 
            if now - t < self.window
        ]
        
        if len(self.group_messages[chat_id]) >= self.max_messages:
            return False
        
        self.group_messages[chat_id].append(now)
        return True


class MudrexBot:
    """
    AI co-pilot for the Mudrex API community. Uses MCP whenever needed for live data.
    GROUP-ONLY: Responds in groups when mentioned or when the message is API-related.
    """
    
    def __init__(self, rag_pipeline: RAGPipeline, mcp_client: Optional[MudrexMCPClient] = None):
        self.rag_pipeline = rag_pipeline
        self.mcp_client = mcp_client
        self.rate_limiter = RateLimiter(
            max_messages=config.RATE_LIMIT_MESSAGES,
            window_seconds=config.RATE_LIMIT_WINDOW
        )
        
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        self._register_handlers()
        
        logger.info("MudrexBot initialized (AI co-pilot, GROUP-ONLY)")
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Commands - Available in Groups AND DMs
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("tools", self.cmd_tools))
        self.app.add_handler(CommandHandler("mcp", self.cmd_mcp))
        
        # Futures Tools
        self.app.add_handler(CommandHandler("futures", self.cmd_futures))
        self.app.add_handler(CommandHandler("listfutures", self.cmd_futures))  # Alias
        self.app.add_handler(CommandHandler("endpoints", self.cmd_endpoints))
        
        # Admin Commands (Work in Groups & DM for admins ideally, but keeping group-only filter for consistency unless DM needed)
        # Actually, let's allow admins to teach in DMs too! 
        # But wait, self.reject_dm blocks DMs. Let's keep it simple: Admin commands work in GROUPS for now.
        self.app.add_handler(CommandHandler("learn", self.cmd_learn)) # Removed ChatType filter to allow flexibility if we open DMs later
        self.app.add_handler(CommandHandler("set_fact", self.cmd_set_fact))
        self.app.add_handler(CommandHandler("delete_fact", self.cmd_delete_fact))
        
        # Message handler - ONLY in groups, only when mentioned/tagged
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
                self.handle_message
            )
        )
        
        # Reject DMs
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & filters.ChatType.PRIVATE,
                self.handle_dm
            )
        )
        
        # Document Handler (File Uploads)
        self.app.add_handler(
            MessageHandler(
                filters.Document.ALL & filters.ChatType.PRIVATE,
                self.handle_document
            )
        )
        
        self.app.add_error_handler(self.error_handler)
        logger.info("Handlers registered (GROUP-ONLY)")
    
    async def handle_dm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle Direct Messages
        - Admins: Teacher Mode active (can teach via natural language)
        - Users: Rejected (Bot is group-only)
        """
        user_id = update.effective_user.id
        
        # 1. ADMIN LOGIC (Teacher Mode)
        if self._is_admin(user_id):
            message = update.message.text
            if not message:
                return

            await update.message.chat.send_action(ChatAction.TYPING)
            
            # Analyze intent for teaching
            intent = self.rag_pipeline.gemini_client.parse_learning_instruction(message)
            
            if intent.get('action') == 'SET_FACT':
                key = intent.get('key')
                value = intent.get('value')
                if key and value:
                    self.rag_pipeline.set_fact(key, value)
                    await update.message.reply_text(f"Got it — I'll remember **{key}** as {value}.", parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text("I couldn't parse a clear key/value. Try: \"X is Y\" or \"/set_fact KEY value\".")
                return
            
            elif intent.get('action') == 'LEARN':
                content = intent.get('content') or message
                self.rag_pipeline.learn_text(content)
                await update.message.reply_text("Noted. I've added that to my knowledge — I'll use it when it's relevant.", parse_mode=ParseMode.MARKDOWN)
                return
            
            # If no teaching intent, normal RAG query (for testing)
            result = self.rag_pipeline.query(message)
            await self._send_response(update, result['answer'])
            return

        # 2. NON-ADMIN LOGIC (Reject)
        if update.message:
            await update.message.reply_text(
                "👋 Hi! I'm the **AI co-pilot** for the Mudrex API group.\n\n"
                "I only work in groups where API traders discuss:\n"
                "• API integration questions\n"
                "• Coding help and debugging\n"
                "• Error troubleshooting\n"
                "• Feedback and suggestions\n\n"
                "Join the group and tag me with @ to ask questions!",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle File Uploads (Admin Only)
        Allows bulk learning from files (.txt, .md, .json, .py)
        """
        user_id = update.effective_user.id
        
        # 1. Access Control
        if not self._is_admin(user_id):
            await update.message.reply_text(f"🚫 Admin only. Your ID: `{user_id}`", parse_mode=ParseMode.MARKDOWN)
            return

        doc = update.message.document
        file_name = doc.file_name or "document"
        
        # 2. File Type Validation
        allowed_extensions = {'.txt', '.md', '.json', '.py', '.yaml', '.yml', '.rst'}
        is_valid = any(file_name.lower().endswith(ext) for ext in allowed_extensions)
        
        if not is_valid:
            await update.message.reply_text("⚠️ Supported formats: .txt, .md, .json, .py, .yaml")
            return

        # 3. Process File
        status_msg = await update.message.reply_text("📥 Processing file...")
        try:
            # Download file
            new_file = await doc.get_file()
            file_content = await new_file.download_as_bytearray()
            text_content = file_content.decode('utf-8')
            
            # Learn Text (prepend filename; pass metadata)
            knowledge = f"file: {file_name}\n\n{text_content}"
            self.rag_pipeline.learn_text(knowledge, metadata={"source": "admin_upload", "filename": file_name})
            
            await status_msg.edit_text(f"Got it — I've added **{file_name}** to my knowledge. I'll use it when it's relevant.", parse_mode=ParseMode.MARKDOWN)
            
        except UnicodeDecodeError:
            await status_msg.edit_text("❌ Error: File must be text-based (UTF-8).")
        except Exception as e:
            logger.error(f"File upload error: {e}")
            await status_msg.edit_text("❌ Error processing file.")

    async def setup_commands(self):
        """Set up bot commands menu"""
        commands = [
            BotCommand("help", "Show help"),
            BotCommand("tools", "MCP server tools list"),
            BotCommand("mcp", "MCP setup guide"),
            BotCommand("listfutures", "List futures contracts (count)"),
            BotCommand("endpoints", "API endpoints"),

            BotCommand("stats", "Bot statistics"),
        ]
        await self.app.bot.set_my_commands(commands)
    
    # ==================== Commands ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome = """Hey! I'm **MudrexBot** — your **AI co-pilot** for the Mudrex API.

*I help with:*
- API integration, auth, endpoints
- Code debugging and fixes
- Error troubleshooting
- **Live data via MCP** (futures list, contract details) when you ask
- MCP server setup

*How to use:*
Ask your API question or tag me with @. I use the MCP server whenever your question needs live data (e.g. "list futures", "BTC contract details").

*Commands:*
/help - Full help
/tools - MCP server tools list
/mcp - MCP setup
/listfutures - List futures (count)
/endpoints - API endpoints (names only)

I'm your co-pilot for the Mudrex API. 🚀"""
        
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """*Mudrex API — AI co-pilot help*

*What I do:*
I'm an **AI co-pilot**: I use the **MCP server** whenever your question needs live data (e.g. list futures, contract details for BTC/ETH). I also use docs and RAG for how‑tos and errors.

*I help with:*
- API auth (X-Authentication only, no HMAC)
- Endpoints, code examples (Python/JS)
- Error debugging
- **Live futures/contract data** via MCP when you ask

*Example questions:*
"List available futures" → I call MCP
"Get BTC contract details" → I call MCP
"How do I authenticate?" / "Error -1121?" → I use docs

*Commands:*
/tools - MCP server tools list
/mcp - MCP setup
/listfutures - List futures (count)
/endpoints - API endpoints (names only)
/stats - Bot info

*MCP:* docs.trade.mudrex.com/docs/mcp

For *personal* account data (positions, orders, balance), use Claude Desktop with MCP and your own API key."""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command — admin only"""
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text(f"🚫 Admin only. Your ID: `{user_id}`", parse_mode=ParseMode.MARKDOWN)
            return
        stats = self.rag_pipeline.get_stats()
        
        mcp_status = "Connected" if self.mcp_client and self.mcp_client.is_connected() else "Not connected"
        
        auth_status = "Service Account" if self.mcp_client and self.mcp_client.is_authenticated() else "Not configured"
        
        stats_text = f"""*Bot Stats (AI co-pilot)*

Model: {stats['model']}
Docs: {stats['total_documents']} chunks
MCP: {mcp_status} (used when you ask for futures/contracts)
Auth: {auth_status}
Mode: Group-only

_AI co-pilot for the Mudrex API_"""
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_tools(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tools command — MCP server tools list. Plain text to avoid Telegram Markdown parse errors."""
        tools_text = MudrexTools.get_tools_summary()
        tools_text += "\n\nFor personal account data, use Claude Desktop with MCP.\n/mcp — MCP setup"
        await update.message.reply_text(tools_text)
    
    async def cmd_mcp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /mcp command"""
        mcp_text = """*Mudrex MCP Setup Guide*

*What is MCP?*
MCP lets AI assistants like Claude interact with your Mudrex account.

*Setup with Claude Desktop:*

1. Install Node.js from nodejs.org
2. Open Claude Desktop Settings > Developer > Edit Config
3. Add this config:
```
{
  "mcpServers": {
    "mcp-futures-trading": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mudrex.com/mcp", "--header", "X-Authentication:${API_SECRET}"],
      "env": {"API_SECRET": "<your-api-secret>"}
    }
  }
}
```
4. Get API secret from trade.mudrex.com
5. Restart Claude Desktop

*Full docs:* docs.trade.mudrex.com/docs/mcp"""
        
        await update.message.reply_text(mcp_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_futures(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /futures and /listfutures — count via GET /fapi/v1/futures (REST) or MCP fallback."""
        await update.message.chat.send_action(ChatAction.TYPING)
        doc_url = "https://docs.trade.mudrex.com/docs/get-asset-listing"
        msg_tail = f"To see the full list: GET /fapi/v1/futures — {doc_url}"

        if config.MUDREX_API_SECRET:
            symbols = await fetch_all_futures_symbols_via_rest(config.MUDREX_API_SECRET)
        elif self.mcp_client:
            symbols = await fetch_all_futures_symbols(self.mcp_client)
        else:
            await update.message.reply_text(
                f"*List futures*\n\n{msg_tail}\n\nSet MUDREX_API_SECRET in .env to show the count here.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        n = len(symbols)
        await update.message.reply_text(
            f"There are **{n}** futures pairs listed. {msg_tail}",
            parse_mode=ParseMode.MARKDOWN
        )

    # (name, method, path, doc_slug) — doc_slug → https://docs.trade.mudrex.com/docs/{slug}
    _API_ENDPOINTS = [
        ("Get spot funds", "GET", "/fapi/v1/wallet/funds", "get-spot-funds"),
        ("Transfer funds (spot ↔ futures)", "POST", "/fapi/v1/wallet/futures/transfer", "post-transfer-funds"),
        ("Get futures funds", "GET", "/fapi/v1/futures/funds", "get-available-funds-futures"),
        ("Get asset listing", "GET", "/fapi/v1/futures", "get-asset-listing"),
        ("Get asset by id", "GET", "/fapi/v1/futures/:asset_id", "get"),
        ("Get leverage", "GET", "/fapi/v1/futures/:asset_id/leverage", "get-leverage-by-asset-id"),
        ("Set leverage", "POST", "/fapi/v1/futures/:asset_id/leverage", "set"),
        ("Place order", "POST", "/fapi/v1/futures/:asset_id/order", "post-market-order"),
        ("Get open orders", "GET", "/fapi/v1/futures/orders", "get-open-orders"),
        ("Get order by id", "GET", "/fapi/v1/futures/orders/:order_id", "get-order-by-id"),
        ("Amend order", "PATCH", "/fapi/v1/futures/orders/:order_id", "orders"),
        ("Cancel order", "DELETE", "/fapi/v1/futures/orders/:order_id", "delete-order"),
        ("Get order history", "GET", "/fapi/v1/futures/orders/history", "get-order-history"),
        ("Get open positions", "GET", "/fapi/v1/futures/positions", "get-open-positions"),
        ("Get liquidation price", "GET", "/fapi/v1/futures/positions/:position_id/liq-price", "get-liquidation-price"),
        ("Add margin", "POST", "/fapi/v1/futures/positions/:position_id/add-margin", "add-margin"),
        ("Place risk order", "POST", "/fapi/v1/futures/positions/:position_id/riskorder", "set-sl-tp"),
        ("Amend risk order", "PATCH", "/fapi/v1/futures/positions/:position_id/riskorder", "edit-sl-tp"),
        ("Reverse position", "POST", "/fapi/v1/futures/positions/:position_id/reverse", "reverse"),
        ("Partial close position", "POST", "/fapi/v1/futures/positions/:position_id/close/partial", "partial-close"),
        ("Close position", "POST", "/fapi/v1/futures/positions/:position_id/close", "square-off"),
        ("Get position history", "GET", "/fapi/v1/futures/positions/history", "get-position-history"),
        ("Get fee history", "GET", "/fapi/v1/futures/fee/history", "fees"),
    ]

    async def cmd_endpoints(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /endpoints — paths and doc links"""
        base = "https://docs.trade.mudrex.com/docs"
        lines = ["*Mudrex API — Endpoints*\n_Base: https://trade.mudrex.com_ · Auth: X-Authentication\n"]
        for name, method, path, slug in self._API_ENDPOINTS:
            url = f"{base}/{slug}"
            lines.append(f"• {name} — `{method} {path}` · [doc]({url})")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    
    # ==================== Admin Commands (Teacher Mode) ====================
    
    def _is_admin(self, user_id: int) -> bool:
        """Check if user is an admin"""
        if not config.ADMIN_USER_IDS:
            return False
        return user_id in config.ADMIN_USER_IDS
    
    async def cmd_learn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /learn <text>
        Ingest new knowledge into the vector store immediately.
        """
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text(f"🚫 Admin only. Your ID: `{user_id}`", parse_mode=ParseMode.MARKDOWN)
            return

        text = " ".join(context.args)
        if not text:
            await update.message.reply_text("Usage: `/learn The new rate limit is 50 requests per minute.`", parse_mode=ParseMode.MARKDOWN)
            return

        try:
            self.rag_pipeline.learn_text(text)
            await update.message.reply_text("Noted. I've added that to my knowledge — I'll use it when it's relevant.", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Error learning: {e}")

    async def cmd_set_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /set_fact <key> <value>
        Set a strict fact (Key-Value) that overrides RAG.
        """
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text(f"🚫 Admin only. Your ID: `{user_id}`", parse_mode=ParseMode.MARKDOWN)
            return

        if len(context.args) < 2:
            await update.message.reply_text("Usage: `/set_fact LATENCY 200ms`", parse_mode=ParseMode.MARKDOWN)
            return

        key = context.args[0].upper()
        value = " ".join(context.args[1:])
        
        try:
            self.rag_pipeline.set_fact(key, value)
            await update.message.reply_text(f"✅ Fact Set: **{key}** = `{value}`", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await update.message.reply_text(f"❌ Error setting fact: {e}")

    async def cmd_delete_fact(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /delete_fact <key>
        Delete a strict fact.
        """
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text(f"🚫 Admin only. Your ID: `{user_id}`", parse_mode=ParseMode.MARKDOWN)
            return

        if not context.args:
            await update.message.reply_text("Usage: `/delete_fact LATENCY`", parse_mode=ParseMode.MARKDOWN)
            return

        key = context.args[0].upper()
        
        if self.rag_pipeline.delete_fact(key):
            await update.message.reply_text(f"✅ Fact **{key}** deleted.", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(f"⚠️ Fact **{key}** not found.", parse_mode=ParseMode.MARKDOWN)

    # ==================== MCP (AI co-pilot: use whenever needed) ====================
    
    def _resolve_mcp_call(self, message: str) -> Optional[Tuple[str, dict]]:
        """If the message should be answered with MCP, return (tool_name, params). Else None."""
        low = message.lower().strip()
        # list_futures: list/available/show futures or contracts
        if re.search(r'\b(list|show|available|all|what)\s+(futures|contracts?)\b', low):
            return ("list_futures", {})
        if re.search(r'\b(futures|contracts?)\s+(list|available)\b', low):
            return ("list_futures", {})
        # get_future: contract details for a symbol
        sym_map = {"btc": "BTCUSDT", "eth": "ETHUSDT", "xrp": "XRPUSDT", "sol": "SOLUSDT", "bnb": "BNBUSDT", "doge": "DOGEUSDT"}
        m = re.search(r'\b(btc|eth|xrp|sol|bnb|doge|ada|avax|link|dot|matic)\b', low)
        if m:
            base = m.group(1).upper()
            sym = sym_map.get(m.group(1).lower(), base + "USDT")
            if re.search(r'\b(get|detail|info|spec|future|contract)\b', low):
                return ("get_future", {"symbol": sym})
        # Explicit symbol: BTC/USDT or similar
        m = re.search(r'\b([A-Z]{2,6})/?(?:USDT)?\b', message, re.I)
        if m and re.search(r'\b(get|detail|info|spec|future|contract)\b', low):
            s = m.group(1).upper().replace("/", "")
            if not s.endswith("USDT"):
                s = s + "USDT"
            return ("get_future", {"symbol": s})
        return None

    def _format_mcp_for_context(self, result: dict) -> str:
        """Format MCP call result for the LLM context. Truncate if large."""
        if not result.get("success"):
            return ""
        data = result.get("data")
        if not data:
            return ""
        # MCP often returns { "content": [ {"type":"text", "text": "..."} ] }
        if isinstance(data, dict) and "content" in data:
            parts = [c.get("text", "") for c in data["content"] if isinstance(c, dict) and c.get("type") == "text"]
            raw = "\n".join(parts) if parts else str(data)
        elif isinstance(data, str):
            raw = data
        else:
            raw = str(data)
        return (raw[:3200] + "\n... (truncated)") if len(raw) > 3200 else raw

    # ==================== Message Handler ====================
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle incoming messages in groups
        Responds when:
        1. Bot is mentioned/tagged (always)
        2. Message is clearly API-related (smart detection)
        Ignores off-topic messages when not tagged
        """
        if not update.message or not update.message.text:
            return
        
        # Ensure we're in a group
        if update.effective_chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
            logger.debug(f"Ignored non-group message from {update.effective_chat.type}")
            return
        
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name
        message = update.message.text
        
        # Check if bot is mentioned/tagged
        bot_mentioned = self._is_bot_mentioned(update)
        
        # Check if message is API-related
        is_api_related = self.rag_pipeline.gemini_client.is_api_related_query(message)
        

        
        # Respond if:
        # 1. Bot is mentioned/tagged (always respond)
        # 2. Message is clearly API-related (smart detection)
        # Otherwise, silently ignore
        if not bot_mentioned and not is_api_related:
            logger.debug(f"Not mentioned and not API-related, ignoring message from {user_name}")
            return
        
        # Access control (if configured)
        if config.ALLOWED_CHAT_IDS and chat_id not in config.ALLOWED_CHAT_IDS:
            logger.warning(f"Unauthorized group: {chat_id}")
            return
        
        # Rate limiting (per group)
        if not self.rate_limiter.is_allowed(chat_id):
            await update.message.reply_text(
                "Slow down! Too many requests from this group. Try again in a minute."
            )
            return
        
        logger.info(f"Group message from {user_name} in {chat_id}: {message[:50]}... | mentioned={bot_mentioned} | api_related={is_api_related}")
        
        # If tagged but not API-related, short redirect
        if bot_mentioned and not is_api_related:
            await update.message.reply_text(
                "I'm here for API and REST help. What would you like to know?"
            )
            return
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            history_key = f"history_{chat_id}"
            chat_history = context.chat_data.get(history_key, [])
            
            # AI co-pilot: live data via REST (GET /fapi/v1/futures) or MCP
            mcp_context = None
            mcp_info = self._resolve_mcp_call(message)
            # list_futures: REST (preferred) or MCP, reply with count and GET /fapi/v1/futures doc
            if mcp_info and mcp_info[0] == "list_futures" and (config.MUDREX_API_SECRET or (self.mcp_client and self.mcp_client.is_authenticated())):
                symbols = await fetch_all_futures_symbols_via_rest(config.MUDREX_API_SECRET) if config.MUDREX_API_SECRET else await fetch_all_futures_symbols(self.mcp_client)
                n = len(symbols)
                doc_url = "https://docs.trade.mudrex.com/docs/get-asset-listing"
                await update.message.reply_text(
                    f"There are **{n}** futures pairs listed. To see the full list: GET /fapi/v1/futures — {doc_url}",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            if self.mcp_client and self.mcp_client.is_authenticated() and mcp_info:
                tool_name, params = mcp_info
                res = await self.mcp_client.call_tool(tool_name, params)
                if res.get("success") and res.get("data"):
                    mcp_context = self._format_mcp_for_context(res)
                    logger.info(f"MCP co-pilot: {tool_name} -> {len(mcp_context or '')} chars")
            
            result = self.rag_pipeline.query(message, chat_history=chat_history, mcp_context=mcp_context)
            
            # Update history
            chat_history.append({'role': 'user', 'content': message})
            chat_history.append({'role': 'assistant', 'content': result['answer']})
            context.chat_data[history_key] = chat_history[-6:]  # Keep last 6 per group
            
            # Send response
            await self._send_response(update, result['answer'])
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(
                "Hit a snag there. Mind rephrasing your question?"
            )
    
    def _is_bot_mentioned(self, update: Update) -> bool:
        """
        Check if bot is mentioned/tagged in the message
        Returns True if:
        - Bot is @mentioned
        - Message is a reply to bot's message
        - Bot username is in the message
        """
        if not update.message:
            return False
        
        # Check if replying to bot
        if update.message.reply_to_message:
            if update.message.reply_to_message.from_user and update.message.reply_to_message.from_user.is_bot:
                return True
        
        # Check for @mentions
        if update.message.entities:
            bot_username = self.app.bot.username.lower() if self.app.bot.username else None
            for entity in update.message.entities:
                if entity.type == "mention":
                    # Extract mentioned username
                    mention = update.message.text[entity.offset:entity.offset + entity.length].lower()
                    if bot_username and bot_username in mention:
                        return True
                elif entity.type == "text_mention":
                    # Direct user mention
                    if entity.user and entity.user.is_bot:
                        return True
        
        # Check if bot username appears in text (case-insensitive)
        if self.app.bot.username:
            if f"@{self.app.bot.username.lower()}" in update.message.text.lower():
                return True
        
        return False
    
    async def _send_response(self, update: Update, response: str):
        """Send response with markdown fallback"""
        try:
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        except Exception:
            # Strip markdown if parsing fails
            plain = response.replace('*', '').replace('_', '').replace('`', '')
            await update.message.reply_text(plain, disable_web_page_preview=True)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error: {context.error}", exc_info=context.error)
        if update and update.message:
            await update.message.reply_text("Something went wrong. Try again?")
    
    def run(self):
        """Start the bot (blocking)"""
        logger.info("Starting MudrexBot (GROUP-ONLY)...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def start_async(self):
        """Start the bot (async)"""
        await self.app.initialize()
        await self.setup_commands()
        await self.app.start()
        await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info("MudrexBot started (GROUP-ONLY mode)")
    
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping MudrexBot...")
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
