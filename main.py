"""
Mudrex API Bot - Main Entry Point
A helpful junior dev + community admin bot for Mudrex API support

Copyright (c) 2025 DecentralizedJM (https://github.com/DecentralizedJM)
Licensed under MIT License
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Ensure we're in the right directory
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)

from src.config import config
from src.rag import RAGPipeline
from src.bot import MudrexBot
from src.mcp import MudrexMCPClient
from src.tasks.scheduler import setup_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

# SECURITY: Suppress verbose httpx logs to prevent token exposure
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def validate_config():
    """Validate required configuration"""
    errors = config.validate()
    
    if errors:
        logger.error("Configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.error("\nPlease check your .env file. See .env.example for reference.")
        sys.exit(1)


async def async_main():
    """Async main application entry point"""
    logger.info("=" * 60)
    logger.info("  Mudrex API Bot - Starting Up")
    logger.info("=" * 60)
    
    # Validate configuration
    validate_config()
    logger.info("Configuration validated")
    
    # Initialize RAG pipeline
    logger.info("Initializing RAG pipeline...")
    rag_pipeline = RAGPipeline()
    
    # Check document count
    stats = rag_pipeline.get_stats()
    if stats['total_documents'] == 0:
        logger.warning("No documents in vector store!")
        logger.info("Attempting to auto-ingest documentation...")
        
        # Try to ingest docs automatically
        docs_dir = Path(__file__).parent / "docs"
        if docs_dir.exists() and any(docs_dir.glob("*.md")):
            logger.info(f"Found docs directory with {len(list(docs_dir.glob('*.md')))} files")
            try:
                num_chunks = rag_pipeline.ingest_documents(str(docs_dir))
                if num_chunks > 0:
                    logger.info(f"✓ Successfully auto-ingested {num_chunks} chunks")
                    stats = rag_pipeline.get_stats()
                    logger.info(f"✓ Vector store now has {stats['total_documents']} documents")
                else:
                    logger.warning("Ingestion returned 0 chunks. Check docs directory.")
            except Exception as e:
                logger.error(f"Failed to auto-ingest docs: {e}")
                logger.info("Run manually: python3 scripts/ingest_docs.py")
        else:
            logger.warning(f"Docs directory not found or empty: {docs_dir}")
            logger.info("Run: python3 scripts/scrape_docs.py && python3 scripts/ingest_docs.py")
    else:
        logger.info(f"Loaded {stats['total_documents']} document chunks")
    
    # Initialize MCP client with service account (read-only key for public data)
    mcp_client = None
    if config.MCP_ENABLED:
        logger.info("Initializing MCP client (service account mode)...")
        mcp_client = MudrexMCPClient(api_secret=config.MUDREX_API_SECRET)
        try:
            await mcp_client.connect()
            if mcp_client.is_authenticated():
                tools = mcp_client.get_safe_tools()
                logger.info(f"MCP connected with service account - {len(tools)} public tools available")
            else:
                logger.warning("MCP service account key not configured - public data features disabled")
                logger.info("Set MUDREX_API_SECRET in .env with a read-only service account key")
        except Exception as e:
            logger.warning(f"MCP connection failed: {e}")
            logger.info("Bot will work without MCP features")
    
    # Initialize bot
    logger.info("Initializing Telegram bot...")
    bot = MudrexBot(rag_pipeline, mcp_client)
    
    # Scheduler for daily changelog scrape + ingest + broadcast
    scheduler = None
    if config.ENABLE_CHANGELOG_WATCHER:
        docs_dir = Path(__file__).parent / "docs"
        scheduler = setup_scheduler(bot, rag_pipeline, docs_dir)
        scheduler.start()
    
    try:
        # Start the bot
        logger.info("Starting bot...")
        await bot.start_async()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("  Bot is LIVE! Press Ctrl+C to stop.")
        logger.info("=" * 60)
        logger.info("")
        
        # Keep running until interrupted
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down...")
        
        if scheduler:
            scheduler.shutdown(wait=False)
        await bot.stop()
        
        if mcp_client:
            await mcp_client.close()
        
        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Goodbye!")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
