"""
Mudrex API Bot - Telegram Handler
GROUP-ONLY bot for private API traders community
Responds only when mentioned/tagged in groups

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import logging
from typing import Optional, Dict
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
    Telegram bot for Mudrex API community group
    GROUP-ONLY: Only responds in groups when mentioned/tagged
    Focus: API questions, coding help, error debugging, feedback
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
        
        logger.info("MudrexBot initialized (GROUP-ONLY mode)")
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Commands - only work in groups
        self.app.add_handler(CommandHandler("start", self.cmd_start, filters.ChatType.GROUPS))
        self.app.add_handler(CommandHandler("help", self.cmd_help, filters.ChatType.GROUPS))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats, filters.ChatType.GROUPS))
        self.app.add_handler(CommandHandler("tools", self.cmd_tools, filters.ChatType.GROUPS))
        self.app.add_handler(CommandHandler("mcp", self.cmd_mcp, filters.ChatType.GROUPS))
        self.app.add_handler(CommandHandler("futures", self.cmd_futures, filters.ChatType.GROUPS))
        
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
                self.rag_pipeline.set_fact(key, value)
                await update.message.reply_text(f"✅ **Teacher Mode**: I've memorized that **{key}** is `{value}`.", parse_mode=ParseMode.MARKDOWN)
                return
            
            elif intent.get('action') == 'LEARN':
                content = intent.get('content')
                self.rag_pipeline.learn_text(content)
                await update.message.reply_text(f"✅ **Teacher Mode**: I've learned this new information:\n_{content[:100]}..._", parse_mode=ParseMode.MARKDOWN)
                return
            
            # If no teaching intent, normal RAG query (for testing)
            result = self.rag_pipeline.query(message)
            await self._send_response(update, result['answer'])
            return

        # 2. NON-ADMIN LOGIC (Reject)
        if update.message:
            await update.message.reply_text(
                "👋 Hi! I'm a community bot for the Mudrex API traders group.\n\n"
                "I only work in groups where API traders discuss:\n"
                "• API integration questions\n"
                "• Coding help and debugging\n"
                "• Error troubleshooting\n"
                "• Feedback and suggestions\n\n"
                "Join the group and tag me with @ to ask questions!"
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
            
            # Learn Text
            # Prepend filename for context
            knowledge = f"file: {file_name}\n\n{text_content}"
            self.rag_pipeline.learn_text(knowledge)
            
            await status_msg.edit_text(f"✅ Learned **{file_name}** ({len(text_content)} bytes).", parse_mode=ParseMode.MARKDOWN)
            
        except UnicodeDecodeError:
            await status_msg.edit_text("❌ Error: File must be text-based (UTF-8).")
        except Exception as e:
            logger.error(f"File upload error: {e}")
            await status_msg.edit_text("❌ Error processing file.")

    async def setup_commands(self):
        """Set up bot commands menu"""
        commands = [
            BotCommand("help", "Show help"),
            BotCommand("tools", "Available API tools"),
            BotCommand("mcp", "MCP setup guide"),
            BotCommand("futures", "List futures contracts"),
            BotCommand("stats", "Bot statistics"),
        ]
        await self.app.bot.set_my_commands(commands)
    
    # ==================== Commands ====================
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome = """Hey! I'm the Mudrex API community assistant.

*I help with:*
- API integration questions
- Code debugging and fixes
- Error troubleshooting
- MCP server setup
- General API feedback

*How to use:*
Just ask your API question! I'll automatically detect and respond.
Or tag me with @ to get my attention.

*Commands:*
/help - Full help
/tools - MCP tools list
/mcp - MCP setup guide

I'm here to help the community! 🚀"""
        
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """*Mudrex API Community Bot Help*

*How to use:*
Just ask your API question! I'll respond if it's API-related.
Or tag me with @botname to get my attention.

*I help with:*
- API authentication and headers
- API endpoints and usage
- Code examples (Python/JS)
- Error debugging
- MCP server setup
- General API questions

*Example questions:*
"How do I authenticate API requests?"
"Why am I getting error -1121?"
"Show me how to place a limit order"
"Help debug this code: ```python...```"
"How to set up MCP with Claude?"

*Note:* This is a generic community bot for API documentation and general help.
For personal account data (positions, orders, balance), use Claude Desktop with MCP.

*Commands:*
/tools - List API tools
/mcp - MCP setup guide
/futures - List futures contracts
/stats - Bot info

*MCP Docs:* docs.trade.mudrex.com/docs/mcp

I automatically detect API questions - no need to tag me!"""
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.rag_pipeline.get_stats()
        
        mcp_status = "Connected" if self.mcp_client and self.mcp_client.is_connected() else "Not connected"
        
        auth_status = "Service Account" if self.mcp_client and self.mcp_client.is_authenticated() else "Not configured"
        
        stats_text = f"""*Bot Stats*

Model: {stats['model']}
Docs: {stats['total_documents']} chunks
MCP: {mcp_status}
Auth: {auth_status}
Mode: Group-only (Community Bot)

_Helping the Mudrex API community_"""
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_tools(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tools command"""
        tools_text = """*Mudrex API Tools*

*Public/General Tools:*
- `list_futures` - List all available futures contracts
- `get_future` - Get contract details by symbol

*Note:* This bot uses a service account for public data only.
For personal account data (positions, orders, balance), use Claude Desktop with MCP (your own API key) or the Mudrex web interface.

Use /mcp for MCP setup instructions!"""
        
        await update.message.reply_text(tools_text, parse_mode=ParseMode.MARKDOWN)
    
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
        """Handle /futures command - list public futures contracts"""
        await update.message.chat.send_action(ChatAction.TYPING)
        
        if not self.mcp_client:
            await update.message.reply_text(
                "*List Futures*\n\n"
                "MCP not connected. This is a general community bot.\n\n"
                "For personal account data, use Claude Desktop with MCP:\n"
                "`List all available futures contracts on Mudrex`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Only public/general data - no authentication needed
        result = await self.mcp_client.call_tool('list_futures')
        
        if result.get('success'):
            data = result.get('data', {})
            text = str(data)[:3500]
            await update.message.reply_text(
                f"*Available Futures Contracts*\n\n```\n{text}\n```\n\n"
                "_Note: This is general information. For personal account data, use Claude Desktop with MCP._",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"Couldn't fetch contracts list. {result.get('message', 'Unknown error')}\n\n"
                "This is a community bot for general API help."
            )
    
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
            await update.message.reply_text(f"✅ Learned new knowledge:\n_{text[:100]}..._", parse_mode=ParseMode.MARKDOWN)
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
        
        # If tagged but not API-related, redirect to API topics
        if bot_mentioned and not is_api_related:
            await update.message.reply_text(
                "I'm here to help with Mudrex API questions! Ask me about:\n"
                "• API integration and authentication\n"
                "• Code debugging and errors\n"
                "• MCP server setup\n"
                "• Order/position management\n\n"
                "What would you like to know?"
            )
            return
        
        await update.message.chat.send_action(ChatAction.TYPING)
        
        try:
            # Get chat history (per group)
            history_key = f"history_{chat_id}"
            chat_history = context.chat_data.get(history_key, [])
            
            # Query RAG pipeline
            result = self.rag_pipeline.query(message, chat_history=chat_history)
            
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
