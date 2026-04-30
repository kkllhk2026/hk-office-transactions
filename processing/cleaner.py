"""
Standardize Hong Kong addresses, district names, and building names so we can
match transactions and news to the same building.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from config.settings import HK_DISTRICTS, TRACKED_BUILDINGS


# Common abbreviations / variants
_DISTRICT_ALIASES = {
    "tst": "Tsim Sha Tsui",
    "csw": "Cheung Sha Wan",
    "tko": "Tseung Kwan O",
    "kt": "Kwun Tong",
    "wch": "Wan Chai",
    "cwb": "Causeway Bay",
    "tsw": "Tsuen Wan",
    "shw": "Sheung Wan",
    "kb": "Kowloon Bay",
    "ne": "North Point",
    "qb": "Quarry Bay",
    "tk": "Taikoo",
    "tai koo": "Taikoo",
    "ki": "Kowloon",
}

_BUILDING_ALIASES = {
    "icc": "International Commerce Centre",
    "international commerce centre": "International Commerce Centre",
    "two ifc": "Two IFC",
    "2ifc": "Two IFC",
    "one ifc": "One IFC",
    "1ifc": "One IFC",
    "boc tower": "Bank of China Tower",
    "ck centre": "Cheung Kong Center",
    "exchange sq": "Exchange Square",
    "the hkri": "HKRI Taikoo Hui",
    "k11 atelier king's road": "K11 Atelier King's Road",
}


def _strip_punct(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\-_,./()]+", " ", s)).strip()


def normalize_district(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = _strip_punct(raw).lower()
    if s in _DISTRICT_ALIASES:
        return _DISTRICT_ALIASES[s]
    # exact-ish match against canonical list
    for d in HK_DISTRICTS:
        if d.lower() in s:
            # collapse Tai Koo / Taikoo
            return "Taikoo" if d.lower() in {"taikoo", "tai koo"} else d
    return raw.title()


def normalize_building_name(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = _strip_punct(raw).lower()
    s = re.sub(r"^the\s+", "", s)
    if s in _BUILDING_ALIASES:
        return _BUILDING_ALIASES[s]
    # Try to match against tracked list (case-insensitive substring)
    for b in TRACKED_BUILDINGS:
        if b.lower() in s or s in b.lower():
            return b
    # Title-case fallback, preserving acronyms like IFC, ICC, AIA, IBM, BOC
    acronyms = {"IFC", "ICC", "AIA", "BOC", "PCCW", "ICBC", "K11", "HKRI", "PMQ"}
    out = []
    for w in raw.split():
        wu = re.sub(r"[^A-Za-z0-9]", "", w).upper()
        out.append(w.upper() if wu in acronyms else w.capitalize())
    return " ".join(out)


def split_address(raw: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Heuristic split into (building, street, district).
    HK addresses are messy; this returns best-effort guesses.
    """
    if not raw:
        return None, None, None
    parts = [p.strip() for p in re.split(r",|·|，", raw) if p.strip()]

    district = None
    for p in parts:
        nd = normalize_district(p)
        if nd and nd in HK_DISTRICTS + ["Taikoo"]:
            district = nd
            break

    building = None
    street = None
    if parts:
        building = normalize_building_name(parts[0])
        if len(parts) > 1:
            street = parts[1] if parts[1] != district else (parts[2] if len(parts) > 2 else None)
    return building, street, district


def normalize_grade(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = raw.strip().upper()
    if "A" in s:
        return "A"
    if "B" in s:
        return "B"
    if "C" in s:
        return "C"
    return None
