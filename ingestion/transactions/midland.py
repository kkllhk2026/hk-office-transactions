"""
Midland IC&I transaction scraper.

⚠️  Same caveat as Centaline — verify selectors against current HTML.
"""
from __future__ import annotations

from typing import List, Dict, Any

from bs4 import BeautifulSoup

from ingestion.base_scraper import BaseScraper
from config.settings import TRANSACTION_SITES
from utils.logger import logger
from utils.helpers import parse_money_hkd, parse_area_sqft, parse_date_flexible


class MidlandScraper(BaseScraper):
    name = "midland"

    def __init__(self) -> None:
        super().__init__()
        cfg = TRANSACTION_SITES.get("midland_ici", {})
        self.base_url = cfg.get("base_url", "https://www.midlandici.com.hk")
        self.listing_url = cfg.get("listing_url",
                                   f"{self.base_url}/ics/property/transaction/list/en")
        self.row_selector = cfg.get("row_selector", "table tr")
        self.enabled = cfg.get("enabled", True)

    def fetch_listings(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []

        out: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            url = f"{self.listing_url}?page={page}"
            logger.info(f"[{self.name}] Fetching {url}")
            r = self.get(url)
            if r is None:
                break
            soup = BeautifulSoup(r.text, "lxml")
            rows = soup.select(self.row_selector)
            if len(rows) <= 1:
                logger.warning(f"[{self.name}] no rows; stopping")
                break

            for row in rows[1:]:                       # skip header
                rec = self._parse_row(row)
                if rec:
                    out.append(rec)

        logger.info(f"[{self.name}] parsed {len(out)} transactions")
        return out

    def _parse_row(self, row) -> Dict[str, Any] | None:
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 5:
            return None
        try:
            tx_date = parse_date_flexible(cells[0])
            if not tx_date:
                return None

            building = cells[1] if len(cells) > 1 else None
            address = cells[2] if len(cells) > 2 else None
            floor_raw = cells[3] if len(cells) > 3 else None
            area_raw = cells[4] if len(cells) > 4 else None
            price_raw = cells[5] if len(cells) > 5 else None
            tx_type = "Lease" if any(
                k in " ".join(cells).lower()
                for k in ("lease", "rent", "let")
            ) else "Sale"

            link_el = row.select_one("a[href]")
            source_url = None
            if link_el and link_el.get("href"):
                href = link_el["href"]
                source_url = href if href.startswith("http") else self.base_url + href

            rec: Dict[str, Any] = {
                "source": self.name,
                "source_url": source_url,
                "transaction_date": tx_date,
                "building_name_raw": building,
                "address_raw": address,
                "floor_raw": floor_raw,
                "area_sqft_gross": parse_area_sqft(area_raw),
                "transaction_type": tx_type,
                "raw_payload": " | ".join(cells)[:2000],
            }
            money = parse_money_hkd(price_raw) if price_raw else None
            if tx_type == "Sale":
                rec["price_hkd"] = money
            else:
                rec["rent_hkd_monthly"] = money
            return rec
        except Exception as e:
            logger.debug(f"[{self.name}] row parse failed: {e}")
            return None
