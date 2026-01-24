# Mudrex API Bot Troubleshooting Guide

This guide covers common errors encountered when running the Mudrex API trading bots or SDKs.

## Telegram API Errors

### Error 409: Conflict
**Full Error**: `telegram.error.Conflict: Terminated by other getUpdates request; make sure that only one bot instance is running`
**Cause**: You are running **two instances** of the same bot simultaneously.
- Example: You have one instance running on your laptop and another on a server (Railway/Heroku).
- Example: You opened two terminal windows and ran `python main.py` in both.
**Solution**:
1. Stop ALL running instances of the bot.
2. Check your task manager or `ps aux | grep python` to kill hidden processes.
3. Start ONLY one instance.

### Error 401: Unauthorized
**Cause**: The Telegram Bot Token in your `.env` file is incorrect.
**Solution**:
1. Open `@BotFather` on Telegram.
2. Send `/token` to get a new token.
3. Update `TELEGRAM_BOT_TOKEN` in your `.env`.

## Mudrex API Errors

### Rate Limited (429)
**Log**: `[WARNING] mudrex.client: Rate limited, retrying in 1.0s...`
**Cause**: You are making too many requests too fast.
- Public Limit: ~2 requests per second.
- Private Limit: Varies by endpoint.
**Solution**:
- The SDK automatically retries.
- If it persists, increase your `poll_interval` or sleep time between requests.

### Error -1121: Invalid Symbol
**Cause**: The trading pair symbol is formatted incorrectly or does not exist.
**Solution**:
- Use `BTCUSDT` (no hyphen).
- Do NOT use `BTC-USDT` or `BTC/USDT` for API calls.
- Check valid symbols with `list_futures`.

### Error -1022: Signature Mismatch / 401 Unauthorized
**Cause**: Your `MUDREX_API_SECRET` is wrong, or the timestamp is out of sync.
**Solution**:
- Regenerate your API Secret in the Mudrex Dashboard.
- Ensure your system clock is synced (use `ntp`).
- Verify you are sending the `X-Authentication` header correctly.
