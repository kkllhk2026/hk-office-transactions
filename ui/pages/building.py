"""Building profile page: search building → all txns + linked news."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from database import session_scope
from database.models import Building, Transaction, NewsArticle
from ui.components import format_hkd, date_range_picker


def render() -> None:
    st.title("Building Profile")

    with session_scope() as s:
        names = [b.name for b in s.query(Building).order_by(Building.name).all()]
    if not names:
        st.info("No buildings indexed yet. Run the ETL pipeline first.")
        return

    c1, c2 = st.columns([2, 3])
    with c1:
        name = st.selectbox("Select a building", names)
    with c2:
        # Default to full history when looking at a single building — that's
        # the natural use case (Lee Garden 1's lease history since 2010, etc.)
        period_start, period_end = date_range_picker(
            "Period", default_preset="All time",
        )
    if not name:
        return

    with session_scope() as s:
        bld = s.query(Building).filter_by(name=name).first()
        if not bld:
            st.warning("Not found.")
            return

        txs = (
            s.query(Transaction)
            .filter(
                Transaction.building_id == bld.id,
                Transaction.transaction_date >= period_start,
                Transaction.transaction_date <= period_end,
            )
            .order_by(Transaction.transaction_date.desc())
            .all()
        )
        tx_df = pd.DataFrame([{
            "date": t.transaction_date,
            "floor": t.floor_raw,
            "area": t.area_sqft_gross or t.area_sqft_saleable,
            "type": t.transaction_type,
            "price": t.price_hkd,
            "rent": t.rent_hkd_monthly,
            "psf": t.price_psf or t.rent_psf_monthly,
            "buyer/tenant": t.buyer or t.tenant,
            "seller/landlord": t.seller or t.landlord,
            "source": t.source,
        } for t in txs])

        # collect linked news
        news_ids = set()
        for t in txs:
            for n in t.news_articles:
                news_ids.add(n.id)

        news_rows = (
            s.query(NewsArticle).filter(NewsArticle.id.in_(news_ids))
             .order_by(NewsArticle.published_at.desc()).all()
            if news_ids else []
        )

        # Detached for use after session close
        bld_data = {
            "name": bld.name,
            "address": bld.address,
            "district": bld.district,
            "grade": bld.grade,
            "completion_year": bld.completion_year,
            "tenure_model": bld.tenure_model,
            "owner": bld.owner,
        }
        news_data = [{
            "title": n.title, "url": n.url, "published": n.published_at,
            "source": n.source, "summary": n.summary,
        } for n in news_rows]

    # --- header ---
    st.markdown(f"### 🏢 {bld_data['name']}")
    meta = [v for v in (bld_data['district'], bld_data['address'],
                        f"Grade {bld_data['grade']}" if bld_data['grade'] else None,
                        f"Completed {bld_data['completion_year']}"
                        if bld_data['completion_year'] else None)
            if v]
    if meta:
        st.caption(" · ".join(meta))

    # Tenure banner — most useful piece of context on this page
    tenure = bld_data.get("tenure_model")
    owner = bld_data.get("owner")
    if tenure == "single-landlord":
        st.info(
            f"🏛️ **Single-landlord building.** Owner: {owner or 'unknown'}. "
            f"In real-world HK practice this building only has **leasing** "
            f"transactions. Any 'Sale' record below is almost certainly a "
            f"source-side misclassification — verify against the original."
        )
    elif tenure == "strata":
        st.warning(
            f"📑 **Strata-title building.** Owner: {owner or 'multiple owners'}. "
            f"Both sales and leases occur here at floor level — both are normal."
        )
    elif tenure in (None, "unknown", ""):
        st.caption("Tenure model not yet classified — add to "
                   "`config/buildings_registry.py` to enable the misclassification check.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total deals", f"{len(tx_df):,}")
    if not tx_df.empty:
        c2.metric("Total sales value",
                  format_hkd(tx_df["price"].sum()))
        c3.metric("Avg psf",
                  f"HK${tx_df['psf'].mean():,.0f}" if tx_df["psf"].notna().any() else "—")

    st.divider()

    # Per-year activity chart — useful for spotting when a building was
    # most active (e.g. The Center sales peaked in 2018-2019 after the
    # CK Asset strata sell-down).
    if not tx_df.empty and len(tx_df) > 1:
        st.subheader("Activity by year")
        import plotly.express as px
        yearly = (
            tx_df.assign(year=pd.to_datetime(tx_df["date"]).dt.year)
                 .groupby(["year", "type"])
                 .size()
                 .reset_index(name="deals")
        )
        fig = px.bar(
            yearly, x="year", y="deals", color="type",
            barmode="stack", height=260,
            color_discrete_map={"Sale": "#1f77b4", "Lease": "#ff7f0e"},
        )
        fig.update_layout(margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Deals")
        fig.update_xaxes(type="category")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Transaction history ({len(tx_df)})")
    if tx_df.empty:
        st.info("No transactions in this period.")
    else:
        st.dataframe(tx_df, hide_index=True, use_container_width=True)

    st.subheader("Related news")
    if not news_data:
        st.info("No news articles linked.")
    else:
        for art in news_data:
            date_str = art["published"].strftime("%Y-%m-%d") if art["published"] else "—"
            with st.container(border=True):
                st.markdown(f"**[{art['title']}]({art['url']})**")
                st.caption(f"{art['source']} · {date_str}")
                if art.get("summary"):
                    st.write(art["summary"])
