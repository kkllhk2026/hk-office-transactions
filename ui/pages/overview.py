"""Overview page: headline KPIs + district/grade summaries."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from ui.components import (
    load_transactions, date_range_picker, alert_banner, format_hkd,
)


def render() -> None:
    st.title("Hong Kong Office Floor Transactions — Overview")

    start, end = date_range_picker("Period", default_preset="Last 90 days")
    df = load_transactions(start, end)

    if df.empty:
        st.info("No transactions in the selected window. "
                "Run the ETL pipeline or upload a CSV via the **Settings** page.")
        return

    alert_banner(df)

    # ---- KPI row ----
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Transactions", f"{len(df):,}")
    sales = df[df["type"] == "Sale"]
    leases = df[df["type"] == "Lease"]
    col2.metric("Total sales value", format_hkd(sales["price_hkd"].sum()))
    col3.metric("Avg sale psf", f"HK${sales['price_psf'].mean():,.0f}"
                if not sales.empty else "—")
    col4.metric("Avg rent psf/mo", f"HK${leases['rent_psf'].mean():,.1f}"
                if not leases.empty else "—")

    st.divider()

    # ---- Volume by district ----
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Volume by district")
        by_dist = (
            df.groupby(["district", "type"])
              .size()
              .reset_index(name="count")
              .dropna(subset=["district"])
        )
        if not by_dist.empty:
            fig = px.bar(
                by_dist, x="district", y="count", color="type",
                barmode="group", height=380,
                color_discrete_map={"Sale": "#1f77b4", "Lease": "#ff7f0e"},
            )
            fig.update_layout(margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Deals")
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Top buildings")
        top_b = (
            df.groupby("building")
              .agg(deals=("id", "count"),
                   value=("price_hkd", "sum"),
                   area=("area_sqft", "sum"))
              .sort_values("deals", ascending=False)
              .head(10)
              .reset_index()
        )
        st.dataframe(
            top_b.rename(columns={"deals": "Deals", "value": "Value (HKD)",
                                  "area": "Area (sqft)"}),
            hide_index=True, use_container_width=True,
        )

    st.divider()

    # ---- Time series ----
    st.subheader("Daily transaction volume")
    ts = (
        df.assign(d=pd.to_datetime(df["date"]))
          .groupby([pd.Grouper(key="d", freq="D"), "type"])
          .size()
          .reset_index(name="count")
    )
    if not ts.empty:
        fig = px.line(ts, x="d", y="count", color="type", height=320,
                      color_discrete_map={"Sale": "#1f77b4", "Lease": "#ff7f0e"})
        fig.update_layout(margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Deals")
        st.plotly_chart(fig, use_container_width=True)

    # ---- Grade distribution ----
    if df["grade"].notna().any():
        st.subheader("Deals by building grade")
        by_grade = df.groupby("grade").size().reset_index(name="count")
        fig = px.pie(by_grade, names="grade", values="count", hole=0.5, height=300)
        st.plotly_chart(fig, use_container_width=True)
