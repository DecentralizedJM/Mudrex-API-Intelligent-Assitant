"""
Changelog Watcher for docs.trade.mudrex.com
Fetches changelog page, hashes content, and detects changes.
Used by the daily scheduler to broadcast when changelog is updated.

Copyright (c) 2025 DecentralizedJM
Licensed under MIT License
"""
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CHANGELOG_URL = "https://docs.trade.mudrex.com/docs/changelogs"
STATE_FILE = Path(__file__).resolve().parent.parent / "data" / "changelog_state.json"


def _ensure_data_dir():
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _fetch_and_normalize(url: str) -> str:
    """Fetch page and return normalized text from main content."""
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning(f"Changelog fetch failed: {e}")
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body
    if not main:
        return ""
    for el in main.find_all(["script", "style", "nav"]):
        el.decompose()
    text = main.get_text(separator="\n", strip=True)
    # Normalize: collapse whitespace, single newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_summary(text: str) -> str:
    """Try to extract a one-line summary (e.g. newest version). If brittle, return generic."""
    # Look for "Changelog — v1.0.X" or "Release Summary" / version table
    m = re.search(r"Changelog\s*—\s*(v[\d.]+)", text, re.I)
    if m:
        return f"New: {m.group(1)}. See: {CHANGELOG_URL}"
    return f"Mudrex API changelog was updated. See: {CHANGELOG_URL}"


def run() -> tuple[bool, str]:
    """
    Check changelog for updates.
    Returns:
        (changed: bool, summary: str)
        If changed, summary is a short message for the broadcast. Otherwise "".
    """
    _ensure_data_dir()
    text = _fetch_and_normalize(CHANGELOG_URL)
    if not text:
        logger.warning("Changelog: no content extracted")
        return False, ""

    new_hash = _hash_content(text)
    prev_hash = None
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                prev_hash = data.get("last_hash")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Changelog state read error: {e}")

    # Persist new state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_hash": new_hash, "last_check": datetime.now(timezone.utc).isoformat()}, f, indent=2)

    if prev_hash is not None and new_hash != prev_hash:
        summary = _parse_summary(text)
        logger.info(f"Changelog changed: {summary}")
        return True, summary
    return False, ""
