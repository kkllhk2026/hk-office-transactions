"""
HK Office Floor Transactions Dashboard — main Streamlit app.

Run:
    streamlit run app.py
"""
from __future__ import annotations

from datetime import datetime

import streamlit as st

from database import init_db
from ui.components import get_last_update
from ui.pages import overview, feed, news, analytics, building
from pipeline.etl import run_full_pipeline, run_news_ingestion
from ingestion.csv_uploader import parse_upload
from pipeline.etl import _persist_transactions
from utils.logger import logger


st.set_page_config(
    page_title="HK Office Transactions",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS — restrained, dashboard-y, theme-aware
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }
    [data-testid="stMetric"] {
        background: rgba(127,127,127,0.06);
        padding: 14px 18px;
        border-radius: 10px;
        border: 1px solid rgba(127,127,127,0.15);
    }
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 600; }
    h1 { font-weight: 700; letter-spacing: -0.02em; }
    h2, h3 { font-weight: 600; letter-spacing: -0.01em; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def _ensure_db_ready():
    init_db()
    return True


_ensure_db_ready()


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🏢 HK Office Tracker")

    last = get_last_update()
    if last:
        st.caption(f"Last updated: **{last.strftime('%Y-%m-%d %H:%M UTC')}**")
    else:
        st.caption("Not yet ingested. Use Settings → Run pipeline.")

    page = st.radio(
        "Navigate",
        ["Overview", "Feed", "News", "Analytics", "Building", "Settings"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("v0.1 · Data accuracy depends on source-site stability. "
               "Verify large deals against the original source.")


# ---------- Page router ----------
if page == "Overview":
    overview.render()

elif page == "Feed":
    feed.render()

elif page == "News":
    news.render()

elif page == "Analytics":
    analytics.render()

elif page == "Building":
    building.render()

elif page == "Settings":
    st.title("Settings")

    st.subheader("Run pipeline now")
    c1, c2, c3 = st.columns(3)
    if c1.button("🔄 Refresh news only", use_container_width=True):
        with st.spinner("Pulling RSS feeds & news pages…"):
            try:
                totals = run_news_ingestion(hydrate_full_text=True)
                st.success(f"News refresh complete: {totals}")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"News refresh failed: {e}")

    if c2.button("⛓️ Run full ETL", use_container_width=True):
        with st.spinner("Running full pipeline (this can take several minutes)…"):
            try:
                totals = run_full_pipeline()
                st.success(f"Pipeline complete: {totals}")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Pipeline failed: {e}")

    if c3.button("🗑 Clear UI cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared.")

    st.divider()
    st.subheader("Manual CSV / Excel upload")
    st.write("Use this when scrapers are blocked or you have agency report data. "
             "Required columns: `transaction_date, building_name, transaction_type`. "
             "Optional: `district, address, floor, area_sqft, price_hkd, "
             "rent_hkd_monthly, buyer, seller, tenant, landlord, grade, source, source_url`.")
    upload = st.file_uploader("Upload .csv or .xlsx", type=["csv", "xlsx", "xls"])
    if upload:
        try:
            records = parse_upload(upload.read(), upload.name)
            st.write(f"Parsed **{len(records)}** rows. Preview:")
            st.dataframe(records[:10])
            if st.button(f"✅ Insert {len(records)} into database"):
                inserted = _persist_transactions(records)
                st.success(f"Inserted {inserted} new transactions "
                           f"({len(records) - inserted} duplicates skipped).")
                st.cache_data.clear()
        except Exception as e:
            st.error(f"Upload failed: {e}")

    st.divider()
    st.subheader("Diagnostics")
    from database import session_scope
    from database.models import Transaction, NewsArticle, IngestionRun
    from sqlalchemy import func
    with session_scope() as s:
        n_tx = s.query(func.count(Transaction.id)).scalar()
        n_news = s.query(func.count(NewsArticle.id)).scalar()
        n_runs = s.query(func.count(IngestionRun.id)).scalar()
        recent_runs = (
            s.query(IngestionRun)
             .order_by(IngestionRun.started_at.desc())
             .limit(10).all()
        )
        recent_data = [{
            "started": r.started_at,
            "source": r.source,
            "status": r.status,
            "fetched": r.items_fetched,
            "inserted": r.items_inserted,
            "error": (r.error_message or "")[:120],
        } for r in recent_runs]

    c1, c2, c3 = st.columns(3)
    c1.metric("Transactions", f"{n_tx:,}")
    c2.metric("News articles", f"{n_news:,}")
    c3.metric("Pipeline runs", f"{n_runs:,}")

    if recent_data:
        st.write("**Recent ingestion runs**")
        st.dataframe(recent_data, hide_index=True, use_container_width=True)
