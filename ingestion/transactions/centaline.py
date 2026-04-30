"""
Centaline Commercial (oir.centanet.com) transaction scraper.

⚠️  HTML SELECTORS WILL DRIFT. Verify with browser DevTools and update
the selectors block below. The shape returned by fetch_listings() is the
contract the ETL relies on — don't change keys without updating etl.py.
"""
from __future__ import annotations

from typing import List, Dict, Any
from datetime import date

from bs4 import BeautifulSoup

from ingestion.base_scraper import BaseScraper
from config.settings import TRANSACTION_SITES
from utils.logger import logger
from utils.helpers import parse_money_hkd, parse_area_sqft, parse_date_flexible


class CentalineScraper(BaseScraper):
    name = "centaline"

    def __init__(self) -> None:
        super().__init__()
        cfg = TRANSACTION_SITES.get("centaline_commercial", {})
        self.base_url = cfg.get("base_url", "https://oir.centanet.com")
        self.listing_url = cfg.get("listing_url", f"{self.base_url}/en/transaction")
        self.row_selector = cfg.get("row_selector", "div.transaction-row")
        self.enabled = cfg.get("enabled", True)

    def fetch_listings(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        if not self.enabled:
            logger.info(f"[{self.name}] disabled in config")
            return []

        records: List[Dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            url = f"{self.listing_url}?page={page}"
            logger.info(f"[{self.name}] Fetching {url}")
            r = self.get(url)
            if r is None:
                break

            soup = BeautifulSoup(r.text, "lxml")
            rows = soup.select(self.row_selector)
            if not rows:
                # try generic table rows as fallback
                rows = soup.select("table tr")[1:]
            if not rows:
                logger.warning(f"[{self.name}] No rows found on page {page}; stopping")
                break

            for row in rows:
                rec = self._parse_row(row)
                if rec:
                    records.append(rec)

        logger.info(f"[{self.name}] parsed {len(records)} transactions")
        return records

    # ----- private -----
    def _parse_row(self, row) -> Dict[str, Any] | None:
        try:
            text = row.get_text(" | ", strip=True)
            cells = [c.strip() for c in text.split("|") if c.strip()]
            if len(cells) < 4:
                return None

            # Centaline rows historically: Date | Building | Floor/Unit | Area | Price | psf | Type
            tx_date = parse_date_flexible(cells[0])
            if not tx_date:
                return None

            building = cells[1] if len(cells) > 1 else None
            floor_raw = cells[2] if len(cells) > 2 else None
            area_raw = cells[3] if len(cells) > 3 else None
            price_raw = cells[4] if len(cells) > 4 else None

            # Type detection
            tx_type = "Sale"
            joined = text.lower()
            if any(k in joined for k in ["lease", "rent", "let", "monthly", "/month"]):
                tx_type = "Lease"

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
                "floor_raw": floor_raw,
                "area_sqft_gross": parse_area_sqft(area_raw),
                "transaction_type": tx_type,
                "raw_payload": text[:2000],
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
