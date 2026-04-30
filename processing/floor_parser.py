"""
Parse Hong Kong office floor notations into structured fields.

Examples handled:
  "15/F"                -> low=15, high=15, partial=False, whole=True (assumed)
  "15/F Unit A"         -> low=15, high=15, partial=True (unit specified)
  "8-10/F"              -> low=8, high=10, multi-floor lease
  "8/F – 10/F"          -> same
  "High Zone 35/F"      -> low=35, high=35, zone=High
  "Mid Zone, 21/F"      -> zone=Mid, low=21, high=21
  "Low Zone Office"     -> zone=Low (no exact floor)
  "Whole 12/F"          -> whole=True, low=12, high=12
  "12-15/F (whole)"     -> whole=True, low=12, high=15
  "G/F"                 -> low=0, high=0
  "B1/F"                -> low=-1, high=-1
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class FloorInfo:
    raw: str
    floor_low: Optional[int] = None
    floor_high: Optional[int] = None
    floor_zone: Optional[str] = None       # Low / Mid / High
    is_whole_floor: bool = False
    is_partial_floor: bool = False
    unit: Optional[str] = None


_ZONE_PATTERNS = {
    "Low": re.compile(r"\b(low\s*zone|low[-\s]*level|low\s*flr|低層)\b", re.IGNORECASE),
    "Mid": re.compile(r"\b(mid\s*zone|mid[-\s]*level|mid\s*flr|中層)\b", re.IGNORECASE),
    "High": re.compile(r"\b(high\s*zone|high[-\s]*level|high\s*flr|高層)\b", re.IGNORECASE),
}

_UNIT_PATTERN = re.compile(
    r"\b(?:unit|suite|room|rm|flat|室)\s*([A-Z0-9\-]+)", re.IGNORECASE
)

_WHOLE_PATTERN = re.compile(
    r"\b(whole\s*(?:floor|flr)|entire\s*floor|full\s*floor|整層|全層)\b", re.IGNORECASE
)

_PARTIAL_PATTERN = re.compile(
    r"\b(part(?:ial)?\s*floor|half\s*floor|半層)\b", re.IGNORECASE
)

# Range like "8-10/F", "8/F-10/F", "8 to 10/F"
_RANGE_PATTERN = re.compile(
    r"(\d{1,3})\s*(?:/F|F)?\s*[-–to]+\s*(\d{1,3})\s*/?F", re.IGNORECASE
)
# Single floor "15/F" or "15F"
_SINGLE_PATTERN = re.compile(r"(\d{1,3})\s*/?F\b", re.IGNORECASE)

# Special: G/F, UG/F, LG/F, B1/F, B2/F, M/F, R/F
_SPECIAL_FLOORS = {
    "G/F": 0, "GF": 0, "GROUND": 0,
    "UG/F": 1, "UGF": 1,
    "LG/F": -1, "LGF": -1,
    "B1/F": -1, "B1": -1,
    "B2/F": -2, "B2": -2,
    "B3/F": -3, "B3": -3,
    "M/F": 0,                  # mezzanine treated as 0 for sort order
    "R/F": 999,                # roof
}


def parse_floor(raw: Optional[str]) -> FloorInfo:
    info = FloorInfo(raw=(raw or "").strip())
    if not raw:
        return info

    text = raw.strip()
    upper = text.upper()

    # --- Special floor codes ---
    for code, num in _SPECIAL_FLOORS.items():
        if re.search(rf"\b{re.escape(code)}\b", upper):
            info.floor_low = num
            info.floor_high = num
            break

    # --- Zone detection ---
    for zone, pat in _ZONE_PATTERNS.items():
        if pat.search(text):
            info.floor_zone = zone
            break

    # --- Unit detection ---
    m_unit = _UNIT_PATTERN.search(text)
    if m_unit:
        info.unit = m_unit.group(1).upper()
        info.is_partial_floor = True

    # --- Whole / partial keywords ---
    if _WHOLE_PATTERN.search(text):
        info.is_whole_floor = True
        info.is_partial_floor = False
    if _PARTIAL_PATTERN.search(text):
        info.is_partial_floor = True
        info.is_whole_floor = False

    # --- Floor numbers (range first, then single) ---
    if info.floor_low is None:
        m_range = _RANGE_PATTERN.search(text)
        if m_range:
            try:
                lo = int(m_range.group(1))
                hi = int(m_range.group(2))
                info.floor_low = min(lo, hi)
                info.floor_high = max(lo, hi)
                if hi > lo:
                    # multi-floor block: assume whole-floor unless unit specified
                    if not info.is_partial_floor:
                        info.is_whole_floor = True
            except ValueError:
                pass
        else:
            m_single = _SINGLE_PATTERN.search(text)
            if m_single:
                try:
                    n = int(m_single.group(1))
                    info.floor_low = n
                    info.floor_high = n
                except ValueError:
                    pass

    # If we have a floor and no unit and no explicit "partial", default to whole
    if (info.floor_low is not None
            and not info.is_partial_floor
            and not info.is_whole_floor
            and info.unit is None):
        info.is_whole_floor = True

    return info


def floor_band(low: Optional[int], high: Optional[int]) -> str:
    """Categorize a floor into Low/Mid/High band for charting."""
    if low is None:
        return "Unknown"
    avg = (low + (high or low)) / 2
    if avg <= 10:
        return "Low (≤10F)"
    if avg <= 30:
        return "Mid (11–30F)"
    if avg <= 60:
        return "High (31–60F)"
    return "Super-high (>60F)"
