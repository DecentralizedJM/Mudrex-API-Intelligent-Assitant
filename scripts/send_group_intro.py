#!/usr/bin/env python3
"""Send the group intro message once. Uses TELEGRAM_GROUP_CHAT_ID from .env (or Railway)."""
import asyncio
import sys

# Import from the canonical source to avoid duplication
from src.bot.telegram_bot import GROUP_INTRO_MESSAGE


async def main():
    # Load from .env (run from repo root: python3 scripts/send_group_intro.py)
    from dotenv import load_dotenv
    load_dotenv()
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    group_chat = os.getenv("TELEGRAM_GROUP_CHAT_ID")
    try:
        chat_id = int(group_chat.strip()) if group_chat and group_chat.strip() else None
    except ValueError:
        chat_id = None

    config = type("Config", (), {"TELEGRAM_BOT_TOKEN": token, "TELEGRAM_GROUP_CHAT_ID": chat_id})()

    if not config.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if config.TELEGRAM_GROUP_CHAT_ID is None:
        print("TELEGRAM_GROUP_CHAT_ID not set. Add your Telegram group chat ID to .env (e.g. -1001234567890)")
        sys.exit(1)

    from telegram import Bot
    from telegram.constants import ParseMode

    chat_id = config.TELEGRAM_GROUP_CHAT_ID
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=GROUP_INTRO_MESSAGE,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
        print(f"Sent intro to chat_id={chat_id}")
    except Exception as e:
        print(f"Failed to send: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
