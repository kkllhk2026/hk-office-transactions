"""
Manual CSV/Excel upload — used as a backup when scrapers fail or for
agency reports (CBRE/JLL/Cushman/Savills/Colliers/Knight Frank quarterly)
that don't expose machine-readable feeds.

Expected columns (case-insensitive, extras ignored):
    transaction_date, district, building_name, address, floor, area_sqft,
    transaction_type, price_hkd, rent_hkd_monthly, buyer, seller,
    tenant, landlord, grade, source, source_url
"""
from __future__ import annotations

from io import BytesIO, StringIO
from typing import List, Dict, Any
from datetime import date

import pandas as pd

from utils.helpers import parse_date_flexible
from utils.logger import logger


REQUIRED = {"transaction_date", "building_name", "transaction_type"}


def parse_upload(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    name = filename.lower()
    if name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(file_bytes))
    elif name.endswith(".csv"):
        df = pd.read_csv(BytesIO(file_bytes))
    else:
        # try CSV
        df = pd.read_csv(StringIO(file_bytes.decode("utf-8", errors="ignore")))

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError(
            f"Upload missing required columns: {sorted(missing)}. "
            f"Got: {sorted(df.columns)}"
        )

    out: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        try:
            tx_date = parse_date_flexible(str(row["transaction_date"]))
            if not tx_date:
                continue
            rec = {
                "source": str(row.get("source") or "manual_upload"),
                "source_url": row.get("source_url") or None,
                "transaction_date": tx_date,
                "building_name_raw": str(row["building_name"]),
                "address_raw": str(row.get("address") or "") or None,
                "district": str(row.get("district") or "") or None,
                "floor_raw": str(row.get("floor") or "") or None,
                "area_sqft_gross": _to_float(row.get("area_sqft")),
                "transaction_type": str(row["transaction_type"]).strip().title(),
                "price_hkd": _to_float(row.get("price_hkd")),
                "rent_hkd_monthly": _to_float(row.get("rent_hkd_monthly")),
                "buyer": row.get("buyer") or None,
                "seller": row.get("seller") or None,
                "tenant": row.get("tenant") or None,
                "landlord": row.get("landlord") or None,
                "grade": str(row.get("grade") or "") or None,
            }
            out.append(rec)
        except Exception as e:
            logger.warning(f"Row skipped: {e}")
    logger.info(f"CSV upload yielded {len(out)} rows from {filename}")
    return out


def _to_float(v) -> float | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return float(str(v).replace(",", "").replace("$", "").replace("HKD", "").strip())
    except Exception:
        return None
