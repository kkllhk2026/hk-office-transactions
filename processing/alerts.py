"""Flag transactions as alert-worthy based on size or price thresholds."""
from __future__ import annotations

from config.settings import ALERT_PRICE_HKD, ALERT_AREA_SQFT


def is_alert(tx: dict) -> bool:
    """Returns True if a transaction dict crosses alert thresholds."""
    price = tx.get("price_hkd") or 0
    area = tx.get("area_sqft_gross") or tx.get("area_sqft_saleable") or 0
    rent_psf = tx.get("rent_psf_monthly") or 0

    if price and price >= ALERT_PRICE_HKD:
        return True
    if area and area >= ALERT_AREA_SQFT:
        return True
    # Unusually high rent psf (anything > $200/mo psf is notable in 2025/26)
    if rent_psf and rent_psf >= 200:
        return True
    return False
