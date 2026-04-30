"""Small reusable helpers: hashing, dedup, money parsing, date parsing."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, date
from typing import Optional


def stable_hash(*parts: str) -> str:
    """Stable hash for deduping news/transactions across runs."""
    joined = "||".join((p or "").strip().lower() for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()


def parse_money_hkd(text: str) -> Optional[float]:
    """
    Parse strings like 'HK$1.2B', '$850M', 'HKD 95,000,000', '$3,200/month'.
    Returns numeric HKD value or None.
    """
    if not text:
        return None
    s = text.replace(",", "").replace("HK$", "").replace("HKD", "").replace("$", "")
    s = s.strip()

    multiplier = 1.0
    m = re.search(r"([\d.]+)\s*(B|bn|billion|M|mn|million|K|thousand)?", s, re.IGNORECASE)
    if not m:
        return None
    try:
        val = float(m.group(1))
    except ValueError:
        return None

    suffix = (m.group(2) or "").lower()
    if suffix in {"b", "bn", "billion"}:
        multiplier = 1e9
    elif suffix in {"m", "mn", "million"}:
        multiplier = 1e6
    elif suffix in {"k", "thousand"}:
        multiplier = 1e3
    return val * multiplier


def parse_area_sqft(text: str) -> Optional[float]:
    """Parse '12,500 sq ft', '1,200 sqm', returns sqft."""
    if not text:
        return None
    s = text.replace(",", "").lower()

    m_sqft = re.search(r"([\d.]+)\s*(sq\s*ft|sqft|sf)", s)
    if m_sqft:
        try:
            return float(m_sqft.group(1))
        except ValueError:
            pass

    m_sqm = re.search(r"([\d.]+)\s*(sq\s*m|sqm|m2|m²)", s)
    if m_sqm:
        try:
            return float(m_sqm.group(1)) * 10.7639
        except ValueError:
            pass

    m_plain = re.search(r"([\d.]+)", s)
    if m_plain:
        try:
            return float(m_plain.group(1))
        except ValueError:
            pass
    return None


def parse_date_flexible(text: str) -> Optional[date]:
    """Try several common HK date formats."""
    if not text:
        return None
    text = text.strip()
    fmts = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y",
        "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y",
    ]
    for f in fmts:
        try:
            return datetime.strptime(text, f).date()
        except ValueError:
            continue
    # ISO datetime
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except Exception:
        return None


def truncate(text: Optional[str], n: int = 280) -> str:
    if not text:
        return ""
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"
