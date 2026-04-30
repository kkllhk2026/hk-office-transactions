"""Central configuration loaded from env + sources.yaml."""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# ---------- Paths ----------
DATA_DIR = ROOT / "data"
LOGS_DIR = ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ---------- Database ----------
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'hk_office.db'}")

# ---------- Scraping ----------
USER_AGENT_ROTATION = os.getenv("USER_AGENT_ROTATION", "true").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "1.5"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "4.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# ---------- Alerts ----------
ALERT_PRICE_HKD = float(os.getenv("ALERT_PRICE_HKD", "100000000"))
ALERT_AREA_SQFT = float(os.getenv("ALERT_AREA_SQFT", "10000"))

# ---------- NLP ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ENABLE_TRANSLATION = os.getenv("ENABLE_TRANSLATION", "false").lower() == "true"

# ---------- Scheduler ----------
RUN_DAILY_AT = os.getenv("RUN_DAILY_AT", "06:00")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Hong_Kong")

# ---------- Keywords for relevance filtering ----------
RELEVANCE_KEYWORDS_EN = [
    "office floor", "whole floor", "whole-floor", "partial floor",
    "office transaction", "office lease", "office leasing", "office sale",
    "Grade A office", "grade-a office", "office tower", "office building",
    "office space", "commercial property", "office rent", "office rental",
    "psf", "per sq ft", "per square foot", "leasing deal", "office deal",
    "en bloc", "office acquisition", "office investment",
]

RELEVANCE_KEYWORDS_ZH = [
    "寫字樓", "辦公樓", "甲級寫字樓", "全層", "半層", "整層",
    "寫字樓租務", "寫字樓買賣", "寫字樓交易", "商廈",
    "尺租", "尺價", "全幢",
]

HK_DISTRICTS = [
    # Hong Kong Island
    "Central", "Admiralty", "Sheung Wan", "Wan Chai", "Causeway Bay",
    "North Point", "Quarry Bay", "Taikoo", "Tai Koo", "Wong Chuk Hang",
    "Island East",
    # Kowloon
    "Tsim Sha Tsui", "TST", "Mong Kok", "Hung Hom", "Kowloon Bay",
    "Kwun Tong", "Kowloon East", "Kai Tak", "Cheung Sha Wan",
    "Lai Chi Kok", "San Po Kong",
    # New Territories
    "Tsuen Wan", "Tseung Kwan O", "Sha Tin", "Kwai Chung", "Kwai Fong",
    "Tai Po", "Fo Tan",
]

# Buildings we particularly care about (extend freely)
TRACKED_BUILDINGS = [
    "The Center", "Two IFC", "One IFC", "IFC Mall", "Cheung Kong Center",
    "Chater House", "Exchange Square", "Jardine House", "ICBC Tower",
    "Lippo Centre", "Pacific Place", "Hopewell Centre", "Three Pacific Place",
    "One Island East", "Taikoo Place", "PCCW Tower", "Citibank Tower",
    "Bank of China Tower", "Bank of America Tower", "AIA Central",
    "Henderson Centre", "Cosco Tower", "World-Wide House", "Times Square",
    "Hysan Place", "Lee Garden", "Lee Theatre", "Manulife Plaza",
    "K11 Atelier", "Harbour City", "ICC", "International Commerce Centre",
    "The Henderson", "Two Taikoo Place",
]

# ---------- Source definitions ----------
def _load_sources() -> Dict[str, Any]:
    path = ROOT / "config" / "sources.yaml"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

SOURCES: Dict[str, Any] = _load_sources()

# Convenience accessors
RSS_FEEDS: List[Dict[str, str]] = SOURCES.get("rss_feeds", [])
NEWS_SITES: List[Dict[str, str]] = SOURCES.get("news_sites", [])
TRANSACTION_SITES: Dict[str, Any] = SOURCES.get("transaction_sites", {})
