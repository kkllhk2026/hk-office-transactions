"""Reusable UI components for Streamlit pages."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple, Optional

import pandas as pd
import streamlit as st
from sqlalchemy import select, func

from database import session_scope
from database.models import Transaction, NewsArticle, IngestionRun


# ---------- Data loaders (cached) ----------
@st.cache_data(ttl=300, show_spinner=False)
def load_transactions(
    start: date, end: date,
    districts: Optional[list[str]] = None,
    types: Optional[list[str]] = None,
) -> pd.DataFrame:
    with session_scope() as s:
        q = s.query(Transaction).filter(
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
        if districts:
            q = q.filter(Transaction.district.in_(districts))
        if types:
            q = q.filter(Transaction.transaction_type.in_(types))
        rows = q.order_by(Transaction.transaction_date.desc()).all()
        data = [{
            "id": r.id,
            "date": r.transaction_date,
            "district": r.district,
            "building": r.building.name if r.building else r.building_name_raw,
            "tenure_model": r.building.tenure_model if r.building else "unknown",
            "owner": r.building.owner if r.building else None,
            "floor": r.floor_raw,
            "floor_low": r.floor_low,
            "floor_high": r.floor_high,
            "zone": r.floor_zone,
            "whole_floor": r.is_whole_floor,
            "unit": r.unit,
            "area_sqft": r.area_sqft_gross or r.area_sqft_saleable,
            "type": r.transaction_type,
            "price_hkd": r.price_hkd,
            "price_psf": r.price_psf,
            "rent_monthly": r.rent_hkd_monthly,
            "rent_psf": r.rent_psf_monthly,
            "buyer": r.buyer,
            "seller": r.seller,
            "tenant": r.tenant,
            "landlord": r.landlord,
            "grade": r.grade,
            "source": r.source,
            "source_url": r.source_url,
            "is_alert": r.is_alert,
            "tenure_mismatch": r.tenure_mismatch,
            "review_notes": r.review_notes,
        } for r in rows]
    return pd.DataFrame(data)


@st.cache_data(ttl=300, show_spinner=False)
def load_news(
    start: date, end: date,
    region: Optional[str] = None,
    only_relevant: bool = True,
) -> pd.DataFrame:
    with session_scope() as s:
        q = s.query(NewsArticle).filter(
            NewsArticle.published_at.isnot(None),
            NewsArticle.published_at >= pd.Timestamp(start),
            NewsArticle.published_at <= pd.Timestamp(end) + pd.Timedelta(days=1),
        )
        if region and region != "All":
            q = q.filter(NewsArticle.region == region.lower())
        if only_relevant:
            q = q.filter(NewsArticle.is_relevant.is_(True))
        rows = q.order_by(NewsArticle.published_at.desc()).limit(500).all()
        data = [{
            "id": r.id,
            "published": r.published_at,
            "title": r.title,
            "source": r.source,
            "region": r.region,
            "language": r.language,
            "summary": r.summary,
            "buildings": r.mentioned_buildings,
            "districts": r.mentioned_districts,
            "amounts": r.mentioned_amounts,
            "url": r.url,
            "score": r.relevance_score,
            "tx_count": len(r.transactions),
        } for r in rows]
    return pd.DataFrame(data)


@st.cache_data(ttl=300, show_spinner=False)
def get_last_update() -> Optional[pd.Timestamp]:
    with session_scope() as s:
        last = s.query(func.max(IngestionRun.finished_at)).scalar()
    return last


# ---------- Reusable widgets ----------
def date_range_picker(
    label: str = "Date range",
    default_preset: str = "Last 90 days",
    location: str = "main",            # "main" or "sidebar"
) -> Tuple[date, date]:
    """
    Two-mode date selector with HK-relevant presets and a custom-range fallback.

    Presets cover the typical analyst workflow:
      • Short windows (7d / 30d / 90d) for activity tracking
      • YTD / Last year for reporting
      • Multi-year (1Y / 3Y / 5Y / 10Y / All) for trend analysis

    Returns (start, end) inclusive.
    """
    container = st.sidebar if location == "sidebar" else st

    today = date.today()
    presets: dict[str, Tuple[date, date]] = {
        "Last 7 days":   (today - timedelta(days=7),   today),
        "Last 30 days":  (today - timedelta(days=30),  today),
        "Last 90 days":  (today - timedelta(days=90),  today),
        "Year to date":  (date(today.year, 1, 1),      today),
        "Last 12 months":(today - timedelta(days=365), today),
        "Last 3 years":  (today - timedelta(days=365 * 3),  today),
        "Last 5 years":  (today - timedelta(days=365 * 5),  today),
        "Last 10 years": (today - timedelta(days=365 * 10), today),
        "All time":      (date(2000, 1, 1),            today),
        "Custom…":       (None, None),                            # type: ignore
    }

    options = list(presets.keys())
    default_idx = options.index(default_preset) if default_preset in options else 2

    cols = container.columns([2, 3] if location == "main" else [1])
    with cols[0]:
        choice = st.selectbox(
            label, options, index=default_idx, key=f"preset_{label}",
        )

    if choice == "Custom…":
        # Two date inputs side by side for clarity
        with cols[1] if location == "main" else container:
            c1, c2 = st.columns(2)
            start = c1.date_input(
                "From",
                value=today - timedelta(days=365),
                min_value=date(1990, 1, 1),
                max_value=today,
                key=f"custom_from_{label}",
            )
            end = c2.date_input(
                "To",
                value=today,
                min_value=start,
                max_value=today,
                key=f"custom_to_{label}",
            )
        if start > end:
            start, end = end, start
        return start, end

    return presets[choice]


def metric_card(col, title: str, value: str, delta: Optional[str] = None) -> None:
    with col:
        st.metric(title, value, delta=delta if delta else None)


def alert_banner(df: pd.DataFrame) -> None:
    if df.empty:
        return
    alerts = df[df["is_alert"] == True]    # noqa: E712
    if alerts.empty:
        return
    n = len(alerts)
    top = alerts.head(3)
    with st.expander(f"⚠️  {n} alert-worthy deals in current view", expanded=False):
        for _, row in top.iterrows():
            price = f"HK${row['price_hkd']:,.0f}" if row.get("price_hkd") else \
                f"HK${row['rent_monthly']:,.0f}/mo"
            st.markdown(
                f"**{row['date']}** — {row['building']} · "
                f"{row['floor'] or '?'} · {row['area_sqft'] or '?'} sqft · {price}"
            )


def format_hkd(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    if v >= 1e9:
        return f"HK${v / 1e9:.2f}B"
    if v >= 1e6:
        return f"HK${v / 1e6:.1f}M"
    if v >= 1e3:
        return f"HK${v / 1e3:.0f}K"
    return f"HK${v:,.0f}"
