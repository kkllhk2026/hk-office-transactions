"""
RSS feed reader. Feedparser is forgiving about malformed XML so this is
the most reliable news ingestion path.
"""
from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime, timezone

import feedparser

from config.settings import RSS_FEEDS
from utils.logger import logger


def fetch_all_feeds() -> List[Dict[str, Any]]:
    """Pull every configured RSS feed and return raw entries."""
    out: List[Dict[str, Any]] = []
    for feed in RSS_FEEDS:
        url = feed.get("url")
        if not url:
            continue
        logger.info(f"[rss] {feed['name']} → {url}")
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                logger.warning(f"[rss] {feed['name']} returned no entries "
                               f"(bozo: {parsed.bozo_exception})")
                continue
            for entry in parsed.entries:
                out.append(_normalize_entry(entry, feed))
        except Exception as e:
            logger.error(f"[rss] failed {feed['name']}: {e}")
    logger.info(f"[rss] total entries: {len(out)}")
    return out


def _normalize_entry(entry, feed) -> Dict[str, Any]:
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or "").strip()
    summary = entry.get("summary") or entry.get("description") or ""

    pub = None
    for k in ("published_parsed", "updated_parsed", "created_parsed"):
        if entry.get(k):
            try:
                pub = datetime(*entry[k][:6], tzinfo=timezone.utc)
                break
            except Exception:
                pass

    return {
        "title": title,
        "url": link,
        "raw_text": summary,
        "source": feed.get("name", "rss"),
        "region": feed.get("region", "local"),
        "language": feed.get("language", "en"),
        "published_at": pub,
    }
