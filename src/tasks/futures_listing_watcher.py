"""
Futures Listing Watcher

Fetches active futures via GET /fapi/v1/futures (REST), diffs vs last snapshot,
and detects newly listed and delisted. Used for /listfutures count and daily
broadcast to ALLOWED_CHAT_IDS.

Copyright (c) 2025 DecentralizedJM
Licensed under MIT License
"""
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Set

import aiohttp

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "futures_snapshot.json"


def _ensure_data_dir() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _normalize_symbol(s: str) -> str:
    """Normalize to comparable symbol: uppercase, ensure USDT suffix for consistency."""
    if not s or not isinstance(s, str):
        return ""
    s = str(s).strip().upper()
    # If it looks like BASEUSDT or BASE/USDT, normalize to BASEUSDT
    s = s.replace("/", "")
    if not s.endswith("USDT") and len(s) >= 2:
        s = s + "USDT"
    return s if len(s) > 2 else ""


def _extract_from_list(items: Any) -> Set[str]:
    symbols: Set[str] = set()
    if not isinstance(items, list):
        return symbols
    for it in items:
        if isinstance(it, dict):
            for key in ("symbol", "id", "asset_id", "ticker", "asset"):
                v = it.get(key)
                if isinstance(v, str) and v:
                    n = _normalize_symbol(v)
                    if n:
                        symbols.add(n)
            # Also try first few string values that look like symbols
            for v in it.values():
                if isinstance(v, str) and re.match(r"^[A-Z0-9]{2,12}(?:USDT)?$", v.upper()):
                    n = _normalize_symbol(v)
                    if n:
                        symbols.add(n)
        elif isinstance(it, str):
            n = _normalize_symbol(it)
            if n:
                symbols.add(n)
    return symbols


def _extract_symbols(data: Any) -> Set[str]:
    """
    Extract a set of normalized symbols from MCP list_futures response.

    Handles: list of dicts; {data,futures,results: [...]}; {content:[{type,text}]}.
    """
    symbols: Set[str] = set()
    if data is None:
        return symbols

    # Direct list
    if isinstance(data, list):
        return _extract_from_list(data)

    if not isinstance(data, dict):
        return symbols

    # data.data, data.futures, data.results
    for key in ("data", "futures", "results", "contracts", "assets"):
        arr = data.get(key)
        if isinstance(arr, list):
            symbols |= _extract_from_list(arr)

    # MCP content: [{ "type": "text", "text": "..." }] — text may be JSON
    for c in data.get("content") or []:
        if not isinstance(c, dict) or c.get("type") != "text":
            continue
        text = c.get("text") or ""
        if not isinstance(text, str):
            continue
        try:
            parsed = json.loads(text)
            symbols |= _extract_symbols(parsed)
        except json.JSONDecodeError:
            # Grep symbol-like tokens: BASEUSDT, BASE/USDT, "symbol":"X"
            for m in re.finditer(r'"(?:symbol|id|asset_id|ticker)"\s*:\s*"([A-Za-z0-9/]+)"', text):
                n = _normalize_symbol(m.group(1))
                if n:
                    symbols.add(n)
            for m in re.finditer(r"\b([A-Z]{2,10})/?(?:USDT)?\b", text):
                n = _normalize_symbol(m.group(1))
                if n:
                    symbols.add(n)

    return symbols


# Page size for GET /fapi/v1/futures. Paginate until the API returns fewer items.
_LIST_FUTURES_PAGE_SIZE = 500
_LIST_FUTURES_MAX_ITEMS = 5000

# REST: GET /fapi/v1/futures — https://docs.trade.mudrex.com/docs/get-asset-listing
_FUTURES_REST_URL = "https://trade.mudrex.com/fapi/v1/futures"


async def fetch_all_futures_symbols_via_rest(api_secret: str) -> Set[str]:
    """
    Fetch all active futures symbols via GET /fapi/v1/futures (paginated).
    Uses limit and offset; response shape: { "success": true, "data": [ {"symbol": "BTCUSDT", ...}, ... ] }.
    """
    if not api_secret:
        return set()
    headers = {"X-Authentication": api_secret}
    all_symbols: Set[str] = set()
    offset = 0
    limit = _LIST_FUTURES_PAGE_SIZE
    max_items = _LIST_FUTURES_MAX_ITEMS
    async with aiohttp.ClientSession() as session:
        while offset < max_items:
            url = f"{_FUTURES_REST_URL}?limit={limit}&offset={offset}"
            try:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
            except (aiohttp.ClientError, ValueError) as e:
                logger.warning(f"REST GET /fapi/v1/futures error: {e}")
                break
            if not isinstance(data, dict) or not data.get("success") or "data" not in data:
                break
            arr = data["data"]
            if not isinstance(arr, list):
                break
            before = len(all_symbols)
            # Use only "symbol" — id/asset_id are UUIDs and would inflate the count
            syms = set()
            for o in arr:
                if isinstance(o, dict):
                    s = o.get("symbol")
                    if isinstance(s, str) and s:
                        n = _normalize_symbol(s)
                        if n:
                            syms.add(n)
            all_symbols |= syms
            n = len(arr)
            if n == 0:
                break
            if n > 0 and len(all_symbols) == before:
                break
            offset += n
            if n < limit:
                break
    return all_symbols


async def fetch_all_futures_symbols(mcp_client) -> Set[str]:
    """
    Fetch all futures symbols via MCP list_futures with pagination.

    - Requests up to _LIST_FUTURES_PAGE_SIZE (500) per call to limit round-trips
      while staying under typical API limits.
    - Pages using offset until the API returns 0 items, so the total can be 540, 1000, etc.
    - If the first parameterized call fails, falls back to list_futures with {}.
    """
    all_symbols: Set[str] = set()
    offset = 0
    limit = _LIST_FUTURES_PAGE_SIZE
    max_items = _LIST_FUTURES_MAX_ITEMS

    while offset < max_items:
        res = await mcp_client.call_tool("list_futures", {"limit": limit, "offset": offset})
        if not res.get("success"):
            if offset == 0:
                res = await mcp_client.call_tool("list_futures", {})
                if res.get("success"):
                    return _extract_symbols(res.get("data"))
            return all_symbols
        syms = _extract_symbols(res.get("data"))
        n = len(syms)
        if n == 0:
            break
        before = len(all_symbols)
        all_symbols |= syms
        # If we got only duplicates (server may not support offset), stop.
        if n > 0 and len(all_symbols) == before:
            break
        offset += n
    return all_symbols


async def run(mcp_client=None, api_secret=None) -> tuple[bool, str]:
    """
    Fetch current futures via GET /fapi/v1/futures (REST) or MCP list_futures,
    diff vs last snapshot, persist state. Prefers REST when api_secret is set.

    Returns:
        (changed: bool, summary: str)
    """
    api_secret = api_secret or (getattr(mcp_client, "api_secret", None) if mcp_client else None)
    if not api_secret and not (mcp_client and getattr(mcp_client, "is_authenticated", lambda: False)()):
        logger.debug("Futures listing watcher: no api_secret or MCP; skipping")
        return False, ""

    if api_secret:
        current = await fetch_all_futures_symbols_via_rest(api_secret)
    else:
        current = await fetch_all_futures_symbols(mcp_client)
    if not current:
        logger.warning("Futures listing watcher: no symbols extracted")

    _ensure_data_dir()
    previous: Set[str] = set()
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                obj = json.load(f)
                previous = set(obj.get("symbols") or [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Futures listing watcher: state read error: {e}")

    now = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"symbols": sorted(current), "updated": now}, f, indent=2)

    # First run: no previous snapshot — do not report everything as "new"
    if not previous:
        logger.info("Futures listing watcher: initial snapshot saved; no diff")
        return False, ""

    new = sorted(current - previous)
    delisted = sorted(previous - current)

    if not new and not delisted:
        return False, ""

    parts = ["Futures listing update:"]
    if new:
        parts.append("Newly listed: " + ", ".join(new[:20]))
        if len(new) > 20:
            parts.append(f"… and {len(new) - 20} more")
    if delisted:
        parts.append("Delisted: " + ", ".join(delisted[:20]))
        if len(delisted) > 20:
            parts.append(f"… and {len(delisted) - 20} more")
    summary = "\n".join(parts)
    logger.info(f"Futures listing watcher: {summary}")
    return True, summary
