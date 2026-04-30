"""
Shared base scraper: UA rotation, retries with exponential backoff,
polite rate limiting, robots.txt respect.

USAGE:
    class MyScraper(BaseScraper):
        def fetch_listings(self) -> list[dict]: ...
"""
from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import (
    USER_AGENT_ROTATION, REQUEST_TIMEOUT, REQUEST_DELAY_MIN,
    REQUEST_DELAY_MAX, MAX_RETRIES,
)
from utils.logger import logger


_USER_AGENTS = [
    # A small static pool — fake-useragent can be flaky offline
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class BaseScraper(ABC):
    """Subclass and implement fetch_listings()."""

    name: str = "base"
    base_url: str = ""
    respect_robots: bool = True

    def __init__(self) -> None:
        self.session = requests.Session()
        self._robots_cache: Dict[str, RobotFileParser] = {}

    # -------- HTTP helpers --------
    def _headers(self) -> Dict[str, str]:
        ua = random.choice(_USER_AGENTS) if USER_AGENT_ROTATION else _USER_AGENTS[0]
        return {
            "User-Agent": ua,
            "Accept-Language": "en-HK,en;q=0.9,zh-HK;q=0.8,zh;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    def _can_fetch(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        try:
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            rp = self._robots_cache.get(base)
            if rp is None:
                rp = RobotFileParser()
                rp.set_url(f"{base}/robots.txt")
                rp.read()
                self._robots_cache[base] = rp
            return rp.can_fetch(self._headers()["User-Agent"], url)
        except Exception as e:
            logger.debug(f"robots.txt check failed for {url}: {e}; allowing")
            return True

    def _polite_delay(self) -> None:
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=2, min=2, max=20),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def get(self, url: str, **kwargs: Any) -> Optional[requests.Response]:
        if not self._can_fetch(url):
            logger.warning(f"[{self.name}] Blocked by robots.txt: {url}")
            return None
        self._polite_delay()
        try:
            r = self.session.get(
                url, headers=self._headers(),
                timeout=REQUEST_TIMEOUT, **kwargs,
            )
            r.raise_for_status()
            return r
        except requests.HTTPError as e:
            # 4xx not retried; 5xx retried by tenacity above
            if 400 <= e.response.status_code < 500:
                logger.warning(f"[{self.name}] {e.response.status_code} on {url}")
                return None
            raise

    # -------- Required interface --------
    @abstractmethod
    def fetch_listings(self) -> list[dict]:
        """Return a list of normalized transaction or news dicts."""
        raise NotImplementedError
