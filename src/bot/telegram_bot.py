"""
Telegram Bot handlers and logic

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License - See LICENSE file for details.
"""
import logging
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from ..config import config
from ..rag import RAGPipeline

logger = logging.getLogger(__name__)


class MudrexBot:
    """Telegram bot for Mudrex API documentation"""
    
    def __init__(self, rag_pipeline: RAGPipeline):
        """
        Initialize the bot
        
        Args:
            rag_pipeline: RAG pipeline instance
        """
        self.rag_pipeline = rag_pipeline
        self.app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Mudrex bot initialized")
    
    def _register_handlers(self):
        """Register command and message handlers"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("stats", self.stats_command))
        
        # Message handler for questions
        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            )
        )
        
        logger.info("Handlers registered")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """I'm here to help with the Mudrex API.

*I can help you with:*
• API integration and authentication
• Code review and debugging
• Working code examples
• Best practices

Ask me anything about the Mudrex API or share code for review."""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """*Commands:*
/start - Welcome message
/help - This help
/stats - Bot info

*I help with:*
• API authentication and integration
• Code debugging and fixes
• Working examples in Python/JavaScript
• Best practices

*Example questions:*
"How do I authenticate?"
"Fix this code: ```python...```"
"Show me how to place an order"

Tag me with @ in groups or just send your question."""
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.rag_pipeline.get_stats()
        
        stats_message = f"""*Bot Stats*

AI Model: {stats['model']}
Docs Loaded: {stats['total_documents']} chunks
Status: Online

Helping developers integrate the Mudrex API."""
        await update.message.reply_text(stats_message, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        if not update.message or not update.message.text:
            return
        
        # Check if chat is allowed (if restrictions are enabled)
        if config.ALLOWED_CHAT_IDS:
            if update.effective_chat.id not in config.ALLOWED_CHAT_IDS:
                logger.warning(f"Unauthorized chat: {update.effective_chat.id}")
                return
        
        user_message = update.message.text
        user_name = update.effective_user.first_name
        
        # Check if bot is mentioned (@username or reply)
        bot_mentioned = False
        if update.message.reply_to_message and update.message.reply_to_message.from_user.is_bot:
            bot_mentioned = True
        elif update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention" or entity.type == "text_mention":
                    bot_mentioned = True
                    break
        
        logger.info(f"Message from {user_name}: {user_message[:50]}, mentioned={bot_mentioned}")
        
        # If bot is mentioned, ALWAYS respond - even if unclear, ask for clarification
        if bot_mentioned:
            # Let all messages through when tagged
            pass
        else:
            # Check if message is API-related when not mentioned
            is_api_related = self.rag_pipeline.gemini_client.is_api_related_query(user_message)
            if not is_api_related:
                logger.info(f"Silently ignoring non-API message: {user_message[:50]}")
                return  # Silently ignore non-API messages
        
        # Show typing indicator
        await update.message.chat.send_action("typing")
        
        try:
            # Get chat history (last few messages from context)
            chat_history = context.user_data.get('history', [])
            
            # Query the RAG pipeline
            result = self.rag_pipeline.query(
                user_message,
                chat_history=chat_history
            )
            
            # Update chat history
            chat_history.append({'role': 'user', 'content': user_message})
            chat_history.append({'role': 'assistant', 'content': result['answer']})
            
            # Keep only last 6 messages (3 exchanges)
            context.user_data['history'] = chat_history[-6:]
            
            # Send response (NO sources - we're confident!)
            response = result['answer']
            
            # Try to send with Markdown, fallback to plain text if it fails
            try:
                await update.message.reply_text(
                    response,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            except Exception as parse_error:
                logger.warning(f"Markdown parse error, sending as plain text: {parse_error}")
                # Remove markdown formatting and send as plain text
                plain_response = response.replace('*', '').replace('_', '').replace('`', '')
                await update.message.reply_text(
                    plain_response,
                    disable_web_page_preview=True
                )
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(
                "Hmm, ran into an issue there. Mind rephrasing your question?"
            )
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Mudrex API bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping bot...")
        await self.app.stop()
