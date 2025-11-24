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
        welcome_message = """
👋 Welcome to Mudrex API Documentation Bot!

I'm here to help you with Mudrex API questions.

🔹 Ask me about:
- API endpoints and usage
- Authentication & authorization
- Request/response formats
- Error codes and troubleshooting
- Integration examples

🔸 I can help with:
- "How do I authenticate with the API?"
- "What's the endpoint for creating orders?"
- "How to handle rate limits?"
- "Error: 401 Unauthorized - what does it mean?"

📚 Type your question and I'll search our documentation!

Use /help to see all available commands.
"""
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🤖 Mudrex API Bot - Commands

/start - Show welcome message
/help - Show this help message
/stats - Show bot statistics

💡 Tips:
- Ask clear, specific questions about the API
- Include error codes when troubleshooting
- Mention specific endpoints you're working with
- I only respond to API-related questions

Example questions:
• "How do I get my account balance using the API?"
• "What headers are required for authentication?"
• "Explain the /v1/orders endpoint"
• "What does error 403 mean?"
"""
        await update.message.reply_text(help_message)
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        stats = self.rag_pipeline.get_stats()
        
        stats_message = f"""
📊 Bot Statistics

📚 Documents indexed: {stats['total_documents']}
🤖 AI Model: {stats['model']}
✅ Status: Online

The bot has access to the complete Mudrex API documentation.
"""
        await update.message.reply_text(stats_message)
    
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
        
        logger.info(f"Message from {user_name}: {user_message[:50]}")
        
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
            
            # Send response
            response = result['answer']
            
            # Add sources if available
            if result.get('sources'):
                sources_text = "\n\n📖 Sources: " + ", ".join(
                    [s['filename'] for s in result['sources'][:2]]
                )
                # Only add if it fits in message limit
                if len(response) + len(sources_text) < config.MAX_RESPONSE_LENGTH:
                    response += sources_text
            
            await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, I encountered an error processing your question. Please try again."
            )
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Mudrex API bot...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping bot...")
        await self.app.stop()
