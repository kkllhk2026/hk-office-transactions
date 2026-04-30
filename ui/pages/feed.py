"""Unified feed: transactions and relevant news, advanced filters."""
from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st

from ui.components import (
    load_transactions, load_news, date_range_picker, format_hkd,
)
from config.settings import HK_DISTRICTS


def render() -> None:
    st.title("Transaction & News Feed")

    # ---- filters ----
    start, end = date_range_picker("Period", default_preset="Last 90 days")

    c1, c2, c3 = st.columns(3)
    types = c1.multiselect("Type", ["Sale", "Lease"], default=["Sale", "Lease"])
    districts = c2.multiselect("District", HK_DISTRICTS)
    region = c3.selectbox("News region", ["All", "Local", "Foreign"])

    c4, c5, c6 = st.columns(3)
    floor_min = c4.number_input("Min floor", min_value=0, max_value=120, value=0)
    floor_max = c5.number_input("Max floor", min_value=0, max_value=120, value=120)
    min_area = c6.number_input("Min area (sqft)", min_value=0, value=0, step=500)

    c7, c8, c9 = st.columns(3)
    min_price = c7.number_input("Min price/rent (HKD)", min_value=0, value=0, step=1_000_000)
    only_alerts = c8.checkbox("Alerts only", value=False)
    tenure_filter = c9.selectbox(
        "Tenure model",
        ["All", "Single-landlord (leases only)", "Strata (sales + leases)", "Unknown"],
        help=(
            "Single-landlord buildings (e.g. Two IFC, Chater House, Pacific Place) "
            "shouldn't have sale transactions in real life — any that appear are "
            "flagged for review. Strata buildings (e.g. The Center, Lippo Centre) "
            "have both sales and leases legitimately."
        ),
    )

    search_q = st.text_input("🔎 Search building / buyer / tenant",
                             placeholder="e.g. Two IFC, JPMorgan…")

    # ---- transaction view ----
    tx = load_transactions(start, end, districts or None, types or None)
    if not tx.empty:
        if floor_min > 0 or floor_max < 120:
            tx = tx[(tx["floor_low"].fillna(0) >= floor_min) &
                    (tx["floor_high"].fillna(120) <= floor_max)]
        if min_area > 0:
            tx = tx[tx["area_sqft"].fillna(0) >= min_area]
        if min_price > 0:
            tx = tx[
                (tx["price_hkd"].fillna(0) >= min_price)
                | (tx["rent_monthly"].fillna(0) * 12 >= min_price)
            ]
        if only_alerts:
            tx = tx[tx["is_alert"] == True]            # noqa: E712
        if tenure_filter == "Single-landlord (leases only)":
            tx = tx[tx["tenure_model"] == "single-landlord"]
        elif tenure_filter == "Strata (sales + leases)":
            tx = tx[tx["tenure_model"] == "strata"]
        elif tenure_filter == "Unknown":
            tx = tx[tx["tenure_model"].isin([None, "unknown", ""])]
        if search_q:
            mask = (
                tx["building"].astype(str).str.contains(search_q, case=False, na=False)
                | tx["buyer"].astype(str).str.contains(search_q, case=False, na=False)
                | tx["tenant"].astype(str).str.contains(search_q, case=False, na=False)
                | tx["seller"].astype(str).str.contains(search_q, case=False, na=False)
            )
            tx = tx[mask]

    st.subheader(f"Transactions ({len(tx)})")
    if tx.empty:
        st.info("No matches.")
    else:
        # Surface tenure mismatches up front — these are "Sale" rows on
        # buildings that in real life only do leasing.
        mismatches = tx[tx["tenure_mismatch"] == True]    # noqa: E712
        if not mismatches.empty:
            st.warning(
                f"⚠️ {len(mismatches)} transaction(s) flagged as **tenure mismatch** "
                f"— sales recorded on single-landlord buildings (e.g. Two IFC, "
                f"Chater House). These are likely source-side misclassifications "
                f"and should be verified manually before reporting."
            )
        display = tx.assign(
            Price=tx.apply(
                lambda r: format_hkd(r["price_hkd"]) if r["type"] == "Sale"
                else f"{format_hkd(r['rent_monthly'])}/mo", axis=1),
            psf=tx.apply(
                lambda r: f"${r['price_psf']:,.0f}" if r["type"] == "Sale" and pd.notna(r["price_psf"])
                else (f"${r['rent_psf']:,.1f}" if pd.notna(r['rent_psf']) else "—"),
                axis=1),
        )[[
            "date", "district", "building", "floor", "area_sqft",
            "type", "Price", "psf", "source", "is_alert", "source_url",
        ]].rename(columns={
            "date": "Date", "district": "District", "building": "Building",
            "floor": "Floor", "area_sqft": "Area (sqft)", "type": "Type",
            "source": "Source", "is_alert": "Alert", "source_url": "Link",
        })
        st.dataframe(
            display, hide_index=True, use_container_width=True,
            column_config={
                "Link": st.column_config.LinkColumn("Link"),
                "Alert": st.column_config.CheckboxColumn("Alert"),
            },
        )

        # exports
        csv = tx.to_csv(index=False).encode()
        st.download_button("⬇ Download CSV", csv, file_name="hk_transactions.csv")

        excel_buf = BytesIO()
        with pd.ExcelWriter(excel_buf, engine="openpyxl") as w:
            tx.to_excel(w, index=False, sheet_name="Transactions")
        st.download_button(
            "⬇ Download Excel", excel_buf.getvalue(),
            file_name="hk_transactions.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ---- news view ----
    st.divider()
    news = load_news(start, end, region=region)
    if not news.empty and search_q:
        mask = (
            news["title"].astype(str).str.contains(search_q, case=False, na=False)
            | news["buildings"].astype(str).str.contains(search_q, case=False, na=False)
            | news["summary"].astype(str).str.contains(search_q, case=False, na=False)
        )
        news = news[mask]

    st.subheader(f"News mentions ({len(news)})")
    if news.empty:
        st.info("No matching news.")
    else:
        for _, row in news.head(50).iterrows():
            badge = "🌏" if row["region"] == "foreign" else "🇭🇰"
            link = f"[{row['source']}]({row['url']})"
            buildings = f" · 🏢 {row['buildings']}" if row.get("buildings") else ""
            tx_badge = f" · 🔗 {row['tx_count']} linked" if row.get("tx_count") else ""
            st.markdown(
                f"{badge} **{row['title']}** — {link}"
                f"{buildings}{tx_badge}"
            )
            if row.get("summary"):
                st.caption(row["summary"])
