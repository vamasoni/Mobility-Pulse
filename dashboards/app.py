from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
from db import connect

st.set_page_config(page_title="MobilityPulse", layout="wide")
st.title("MobilityPulse — NYC Mobility Analytics")
st.caption("Manhattan traffic, taxi trips, weather, incidents, and next-hour forecasts")

try:
    with connect() as conn:
        kpis = pd.read_sql("SELECT * FROM analytics.v_kpis", conn)
        hourly = pd.read_sql("SELECT * FROM analytics.v_congestion_by_hour", conn)
        top = pd.read_sql("SELECT * FROM analytics.v_top_congested_segments", conn)
        od = pd.read_sql("SELECT * FROM analytics.v_od_flows LIMIT 100", conn)
except Exception as exc:
    st.error(f"Could not read analytics views: {exc}")
    st.info("Run `python -m scripts.init_db`, `python -m scripts.load_sources`, and `python -m scripts.build_analytics` first.")
    st.stop()

if kpis.empty or int(kpis.iloc[0]["hourly_rows"] or 0) == 0:
    st.warning("The analytics tables are empty. Run ingestion, load source files, and build analytics first.")
    st.stop()

row = kpis.iloc[0]
columns = st.columns(4)
columns[0].metric("Segments", f"{int(row['segments'] or 0):,}")
columns[1].metric("Hourly rows", f"{int(row['hourly_rows'] or 0):,}")
columns[2].metric("Average speed", "N/A" if pd.isna(row["avg_speed"]) else f"{row['avg_speed']:.1f}")
columns[3].metric("Average congestion", "N/A" if pd.isna(row["avg_congestion"]) else f"{row['avg_congestion']:.1%}")

st.subheader("Average congestion by hour")
if not hourly.empty:
    st.plotly_chart(px.line(hourly, x="hour", y="avg_congestion", markers=True), use_container_width=True)
else:
    st.info("No hourly congestion data available yet.")

left, right = st.columns(2)
with left:
    st.subheader("Most congested segments")
    st.dataframe(top, use_container_width=True, hide_index=True)
with right:
    st.subheader("Taxi origin-destination flows")
    st.dataframe(od, use_container_width=True, hide_index=True)

try:
    with connect() as conn:
        predictions = pd.read_sql("SELECT ts, actual_speed, predicted_speed FROM analytics.ml_predictions ORDER BY ts LIMIT 20000", conn)
    if not predictions.empty:
        st.subheader("Forecast versus actual speed")
        st.plotly_chart(px.line(predictions, x="ts", y=["actual_speed", "predicted_speed"]), use_container_width=True)
    else:
        st.info("Forecasts not available yet. Run `python -m ml.build_features` and `python -m ml.forecast`.")
except Exception:
    st.info("Forecast table is not available yet. Run the ML pipeline after analytics has been built.")
