"""
LeasingHub.com office transactions scraper.
"""
from __future__ import annotations

from typing import List, Dict, Any
from bs4 import BeautifulSoup

from ingestion.base_scraper import BaseScraper
from config.settings import TRANSACTION_SITES
from utils.logger import logger
from utils.helpers import parse_money_hkd, parse_area_sqft, parse_date_flexible


class LeasingHubScraper(BaseScraper):
    name = "leasinghub"

    def __init__(self) -> None:
        super().__init__()
        cfg = TRANSACTION_SITES.get("leasinghub", {})
        self.base_url = cfg.get("base_url", "https://www.leasinghub.com")
        self.listing_url = cfg.get("listing_url", f"{self.base_url}/transactions")
        self.row_selector = cfg.get("row_selector", "div.transaction-card")
        self.enabled = cfg.get("enabled", True)

    def fetch_listings(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        out: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            url = f"{self.listing_url}?page={page}"
            logger.info(f"[{self.name}] fetching {url}")
            r = self.get(url)
            if r is None:
                break
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select(self.row_selector)
            if not cards:
                cards = soup.select("article, div.card, li.tx")
            if not cards:
                logger.warning(f"[{self.name}] no cards; stopping")
                break

            for card in cards:
                rec = self._parse_card(card)
                if rec:
                    out.append(rec)

        logger.info(f"[{self.name}] parsed {len(out)} transactions")
        return out

    def _parse_card(self, card) -> Dict[str, Any] | None:
        try:
            # Pull labelled fields by data-attr or by text proximity
            def field(label: str) -> str | None:
                el = card.find(string=lambda t: t and label.lower() in t.lower())
                if el and el.parent:
                    nxt = el.parent.find_next_sibling()
                    if nxt:
                        return nxt.get_text(" ", strip=True)
                return None

            building = field("Building") or (card.select_one(".building, .title")
                                              and card.select_one(".building, .title").get_text(" ", strip=True))
            tx_date = parse_date_flexible(field("Date") or "")
            floor_raw = field("Floor") or field("Unit")
            area = parse_area_sqft(field("Area") or "")
            price = parse_money_hkd(field("Price") or field("Rent") or "")
            tx_type = "Lease" if field("Rent") else "Sale"

            link = card.select_one("a[href]")
            source_url = None
            if link and link.get("href"):
                source_url = link["href"] if link["href"].startswith("http") else self.base_url + link["href"]

            if not building or not tx_date:
                return None

            rec: Dict[str, Any] = {
                "source": self.name,
                "source_url": source_url,
                "transaction_date": tx_date,
                "building_name_raw": building,
                "floor_raw": floor_raw,
                "area_sqft_gross": area,
                "transaction_type": tx_type,
                "raw_payload": card.get_text(" | ", strip=True)[:2000],
            }
            if tx_type == "Sale":
                rec["price_hkd"] = price
            else:
                rec["rent_hkd_monthly"] = price
            return rec
        except Exception as e:
            logger.debug(f"[{self.name}] card parse failed: {e}")
            return None
