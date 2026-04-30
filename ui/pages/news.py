"""Dedicated news page with local/foreign filter and AI summaries."""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from ui.components import load_news, date_range_picker


def render() -> None:
    st.title("News & Insights")

    start, end = date_range_picker("Period", default_preset="Last 30 days")
    c1, c2, c3 = st.columns(3)
    region = c1.selectbox("Region", ["All", "Local", "Foreign"])
    only_relevant = c2.checkbox("Only HK office-relevant", value=True)
    sort = c3.selectbox("Sort", ["Newest", "Most relevant", "Most linked"])

    df = load_news(start, end, region=region, only_relevant=only_relevant)
    if df.empty:
        st.info("No news in this window. Run news ingestion to populate.")
        return

    if sort == "Most relevant":
        df = df.sort_values("score", ascending=False)
    elif sort == "Most linked":
        df = df.sort_values("tx_count", ascending=False)

    # ---- top metrics ----
    col1, col2, col3 = st.columns(3)
    col1.metric("Articles", f"{len(df):,}")
    col2.metric("Local 🇭🇰", f"{(df['region'] == 'local').sum():,}")
    col3.metric("Foreign 🌏", f"{(df['region'] == 'foreign').sum():,}")

    # ---- volume chart ----
    if df["published"].notna().any():
        ts = (
            df.assign(d=pd.to_datetime(df["published"]).dt.date)
              .groupby(["d", "region"]).size().reset_index(name="n")
        )
        fig = px.bar(ts, x="d", y="n", color="region", height=260,
                     color_discrete_map={"local": "#d62728", "foreign": "#2ca02c"})
        fig.update_layout(margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Articles")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---- article list ----
    for _, row in df.head(80).iterrows():
        badge = "🌏" if row["region"] == "foreign" else "🇭🇰"
        date_str = row["published"].strftime("%Y-%m-%d") if pd.notna(row["published"]) else "—"
        score_str = f" · score {row['score']:.2f}" if pd.notna(row.get("score")) else ""
        with st.container(border=True):
            st.markdown(f"{badge} **{row['title']}**")
            st.caption(f"{row['source']} · {date_str}{score_str} · "
                       f"[Read full article ↗]({row['url']})")
            if row.get("summary"):
                st.write(row["summary"])
            tags = []
            if row.get("buildings"):
                tags.append(f"🏢 {row['buildings']}")
            if row.get("districts"):
                tags.append(f"📍 {row['districts']}")
            if row.get("amounts"):
                tags.append(f"💰 {row['amounts']}")
            if row.get("tx_count"):
                tags.append(f"🔗 {row['tx_count']} linked deals")
            if tags:
                st.markdown(" · ".join(f"`{t}`" for t in tags))
