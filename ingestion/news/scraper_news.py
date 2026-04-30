"""
Full-article extraction. Uses trafilatura (actively maintained, Python 3.13
compatible) with a BeautifulSoup fallback so a missing dependency or
JS-rendered page doesn't kill the run.

Trafilatura replaced the original newspaper3k integration in April 2026
because newspaper3k is abandoned (last release 2020) and breaks on
Python 3.13 due to lxml's removal of `html.clean`.
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ingestion.base_scraper import BaseScraper
from config.settings import NEWS_SITES
from utils.logger import logger


def fetch_full_article(url: str) -> Optional[str]:
    """Return cleaned article body text, or None on failure."""
    if not url:
        return None

    # Primary: trafilatura. Better extraction than newspaper3k anyway.
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                favor_recall=True,    # prefer slightly noisier output to losing the article
            )
            if text and len(text) > 200:
                return text
    except Exception as e:
        logger.debug(f"trafilatura failed for {url}: {e}")

    # Fallback: requests + BeautifulSoup paragraph extraction
    try:
        scraper = _GenericFetcher()
        r = scraper.get(url)
        if not r:
            return None
        soup = BeautifulSoup(r.text, "lxml")
        for tag in soup(["script", "style", "nav", "aside", "footer", "header"]):
            tag.decompose()
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        body = "\n\n".join(p for p in paras if len(p) > 40)
        return body if len(body) > 200 else None
    except Exception as e:
        logger.debug(f"fallback extractor failed for {url}: {e}")
        return None


def fetch_news_site_links() -> List[Dict[str, Any]]:
    """For sites without RSS, fetch the index page and return article stubs
    (title + url) that can be hydrated later by fetch_full_article."""
    fetcher = _GenericFetcher()
    out: List[Dict[str, Any]] = []
    for site in NEWS_SITES:
        url = site.get("url")
        if not url:
            continue
        logger.info(f"[news-index] {site['name']} → {url}")
        r = fetcher.get(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "lxml")
        sel = site.get("article_selector", "a")
        for a in soup.select(sel):
            href = a.get("href")
            title = a.get_text(" ", strip=True)
            if not href or len(title) < 12:
                continue
            full = href if href.startswith("http") else urljoin(url, href)
            out.append({
                "title": title,
                "url": full,
                "source": site["name"],
                "region": site.get("region", "local"),
                "language": site.get("language", "en"),
                "raw_text": "",
                "published_at": None,
            })
    logger.info(f"[news-index] total stubs: {len(out)}")
    return out


class _GenericFetcher(BaseScraper):
    name = "news_fetcher"

    def fetch_listings(self):    # not used
        return []
