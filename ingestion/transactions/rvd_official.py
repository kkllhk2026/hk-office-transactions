"""
Official-data ingester for RVD Property Market Statistics, Land Registry,
and data.gov.hk CSV downloads.

Strategy:
  - RVD publishes monthly Excel and PDF tables. We download the latest CSV
    when one is exposed; otherwise we provide a manifest so a human can
    upload via csv_uploader.
  - Land Registry monthly summary CSVs (sometimes redistributed via
    data.gov.hk) can be parsed for office property aggregate stats.
"""
from __future__ import annotations

from typing import List, Dict, Any
from pathlib import Path
from datetime import date

import pandas as pd

from ingestion.base_scraper import BaseScraper
from config.settings import TRANSACTION_SITES, DATA_DIR
from utils.logger import logger
from utils.helpers import parse_date_flexible


class RVDScraper(BaseScraper):
    """Tries to download the most recent RVD office stats spreadsheet."""
    name = "rvd"

    def __init__(self) -> None:
        super().__init__()
        cfg = TRANSACTION_SITES.get("rvd", {})
        self.base_url = cfg.get("base_url", "https://www.rvd.gov.hk")
        self.listing_url = cfg.get("listing_url",
                                   f"{self.base_url}/en/publications/property_market_statistics.html")
        self.enabled = cfg.get("enabled", True)
        self.download_dir = DATA_DIR / "rvd"
        self.download_dir.mkdir(exist_ok=True)

    def fetch_listings(self) -> List[Dict[str, Any]]:
        """RVD data is aggregate-level; we treat each row as a market data point,
        not an individual transaction. Stored separately or shown as context."""
        if not self.enabled:
            return []

        logger.info(f"[{self.name}] RVD ingestion is aggregate-level. "
                    f"Place latest RVD office tables at {self.download_dir} as CSV.")

        out: List[Dict[str, Any]] = []
        for csv_path in self.download_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_path)
                logger.info(f"[{self.name}] loaded {csv_path.name} ({len(df)} rows)")
                for _, row in df.iterrows():
                    rec = self._row_to_dict(row)
                    if rec:
                        out.append(rec)
            except Exception as e:
                logger.error(f"[{self.name}] failed to read {csv_path}: {e}")

        return out

    def _row_to_dict(self, row: pd.Series) -> Dict[str, Any] | None:
        # Expecting columns like: Date, District, Avg Rent, Avg Price, Vacancy
        try:
            tx_date = None
            for k in ("Date", "Month", "Period"):
                if k in row and pd.notna(row[k]):
                    tx_date = parse_date_flexible(str(row[k]))
                    break
            if not tx_date:
                return None
            return {
                "source": self.name,
                "transaction_date": tx_date,
                "district": str(row.get("District", "")) or None,
                "raw_payload": row.to_json(),
                "transaction_type": "MarketStat",  # special non-transaction type
            }
        except Exception:
            return None
