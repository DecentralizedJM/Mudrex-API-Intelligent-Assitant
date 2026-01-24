"""
Daily scheduler: changelog watcher, docs scrape, RAG ingest, and broadcast to groups.

Copyright (c) 2025 DecentralizedJM
Licensed under MIT License
"""
import asyncio
import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import config

logger = logging.getLogger(__name__)
_job_lock = asyncio.Lock()


async def _run_daily_docs_and_changelog(bot, rag_pipeline, docs_dir: Path):
    """Daily job: changelog check, broadcast if changed, scrape, ingest."""
    if not getattr(config, "ENABLE_CHANGELOG_WATCHER", True):
        logger.debug("Changelog watcher disabled; skipping daily job")
        return
    async with _job_lock:
        try:
            # 1) Changelog watcher (sync)
            from scripts.changelog_watcher import run as changelog_run
            changed, summary = await asyncio.to_thread(changelog_run)
            if changed and summary and config.ALLOWED_CHAT_IDS:
                for cid in config.ALLOWED_CHAT_IDS:
                    try:
                        await bot.app.bot.send_message(chat_id=cid, text=summary)
                    except Exception as e:
                        logger.warning(f"Changelog broadcast to {cid} failed: {e}")
            elif changed and (not config.ALLOWED_CHAT_IDS or len(config.ALLOWED_CHAT_IDS) == 0):
                logger.info("Changelog changed but ALLOWED_CHAT_IDS not set; skipping broadcast")

            # 2) Scrape docs (sync)
            from scripts import scrape_api_docs
            await asyncio.to_thread(scrape_api_docs.scrape_docs)

            # 3) Ingest: clear and re-ingest docs (sync, can block briefly)
            def _ingest():
                rag_pipeline.vector_store.clear()
                return rag_pipeline.ingest_documents(str(docs_dir))
            n = await asyncio.to_thread(_ingest)
            logger.info(f"Daily ingest: {n} chunks")
        except Exception as e:
            logger.error(f"Daily job error: {e}", exc_info=True)


def setup_scheduler(bot, rag_pipeline, docs_dir: Path) -> AsyncIOScheduler:
    """Create and add the daily job. Call start() after setup."""
    scheduler = AsyncIOScheduler()
    hour = getattr(config, "CHANGELOG_CRON_HOUR", 2)
    minute = getattr(config, "CHANGELOG_CRON_MINUTE", 0)
    scheduler.add_job(
        _run_daily_docs_and_changelog,
        "cron",
        hour=hour,
        minute=minute,
        args=[bot, rag_pipeline, docs_dir],
    )
    logger.info(f"Daily job scheduled at {hour:02d}:{minute:02d} UTC")
    return scheduler
