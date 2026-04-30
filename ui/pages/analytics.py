"""Analytics & insights page: time-series, leasing vs sales, news correlation."""
from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from ui.components import load_transactions, load_news, date_range_picker


def render() -> None:
    st.title("Analytics & Insights")

    start, end = date_range_picker("Period", default_preset="Last 3 years")
    df = load_transactions(start, end)
    news = load_news(start, end, region=None, only_relevant=True)

    if df.empty:
        st.info("No transaction data yet.")
        return

    df["d"] = pd.to_datetime(df["date"])

    # Pick an aggregation grain that matches the selected window:
    #   ≤ 90 days → weekly
    #   ≤ 2 years → monthly
    #   > 2 years → quarterly
    span_days = (end - start).days
    if span_days <= 90:
        grain, grain_label = "W", "weekly"
    elif span_days <= 730:
        grain, grain_label = "M", "monthly"
    else:
        grain, grain_label = "Q", "quarterly"

    st.caption(f"Showing **{grain_label}** aggregation across "
               f"{span_days:,} days of data ({len(df):,} transactions).")

    # ---- psf trends ----
    st.subheader("Price/rent psf trends")
    monthly = (
        df.assign(m=df["d"].dt.to_period(grain).dt.to_timestamp())
          .groupby(["m", "type"])
          .agg(price_psf=("price_psf", "mean"),
               rent_psf=("rent_psf", "mean"),
               deals=("id", "count"))
          .reset_index()
    )
    sale_m = monthly[monthly["type"] == "Sale"]
    lease_m = monthly[monthly["type"] == "Lease"]

    col1, col2 = st.columns(2)
    with col1:
        if not sale_m.empty and sale_m["price_psf"].notna().any():
            fig = px.line(sale_m, x="m", y="price_psf", markers=True, height=320,
                          title="Avg sale price psf (HKD)")
            fig.update_layout(margin=dict(t=40, b=10), xaxis_title="", yaxis_title="HKD/sqft")
            st.plotly_chart(fig, use_container_width=True)
    with col2:
        if not lease_m.empty and lease_m["rent_psf"].notna().any():
            fig = px.line(lease_m, x="m", y="rent_psf", markers=True, height=320,
                          title="Avg rent psf/month (HKD)", color_discrete_sequence=["#ff7f0e"])
            fig.update_layout(margin=dict(t=40, b=10), xaxis_title="", yaxis_title="HKD/sqft/mo")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---- leasing vs sales volume ----
    st.subheader("Leasing vs Sales volume")
    vol = (
        df.assign(m=df["d"].dt.to_period(grain).dt.to_timestamp())
          .groupby(["m", "type"]).size().reset_index(name="deals")
    )
    fig = px.bar(vol, x="m", y="deals", color="type", barmode="group", height=320,
                 color_discrete_map={"Sale": "#1f77b4", "Lease": "#ff7f0e"})
    fig.update_layout(margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Deals")
    st.plotly_chart(fig, use_container_width=True)

    # ---- floor band distribution ----
    st.subheader("Distribution by floor band")
    from processing.floor_parser import floor_band
    df["band"] = df.apply(lambda r: floor_band(r["floor_low"], r["floor_high"]), axis=1)
    band_summary = (
        df.groupby(["band", "type"]).size().reset_index(name="count")
    )
    band_order = ["Low (≤10F)", "Mid (11–30F)", "High (31–60F)", "Super-high (>60F)", "Unknown"]
    fig = px.bar(band_summary, x="band", y="count", color="type",
                 category_orders={"band": band_order},
                 height=320, barmode="stack")
    fig.update_layout(margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Deals")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---- news correlation ----
    st.subheader("News volume vs transaction volume")
    if not news.empty and news["published"].notna().any():
        n_daily = (
            news.assign(d=pd.to_datetime(news["published"]).dt.to_period(grain).dt.to_timestamp())
                .groupby("d").size().reset_index(name="news_count")
        )
        t_daily = (
            df.assign(d=df["d"].dt.to_period(grain).dt.to_timestamp())
              .groupby("d").size().reset_index(name="tx_count")
        )
        merged = pd.merge(n_daily, t_daily, on="d", how="outer").fillna(0).sort_values("d")
        fig = px.line(merged, x="d", y=["news_count", "tx_count"], height=320,
                      labels={"value": "Count", "variable": ""})
        fig.update_layout(margin=dict(t=10, b=10), xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        if len(merged) > 4:
            corr = merged[["news_count", "tx_count"]].corr().iloc[0, 1]
            st.caption(f"Pearson correlation ({grain_label}): **{corr:.2f}**")
    else:
        st.info("Not enough news data for correlation analysis.")
