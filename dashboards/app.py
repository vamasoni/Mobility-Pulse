from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
from db import connect

st.set_page_config(page_title="MobilityPulse | NYC Traffic Intelligence", layout="wide")
st.title("MobilityPulse")
st.caption("NYC traffic, taxi demand, weather, collisions and next-hour forecasts")

@st.cache_data(ttl=60, show_spinner=False)
def query(sql: str) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql(sql, conn)

# The dashboard must render even before ingestion/analytics have run.
try:
    health = query("""SELECT to_regclass('analytics.v_kpis') AS kpis,
                            to_regclass('analytics.v_congestion_by_hour') AS hourly""")
    if health.empty or pd.isna(health.iloc[0]["kpis"]):
        st.warning("Warehouse schema is not initialized. Run the pipeline initialization stage.")
        st.stop()
    kpis = query("SELECT * FROM analytics.v_kpis")
except Exception as exc:
    st.error("Cannot connect to the MobilityPulse warehouse.")
    st.code(str(exc))
    st.info("Check PostgreSQL health and database credentials, then initialize the schema.")
    st.stop()

if kpis.empty:
    st.info("Analytics views exist, but no traffic data has been loaded yet.")
    row = {"segments": 0, "hourly_rows": 0, "avg_speed": None, "avg_congestion": None}
else:
    row = kpis.iloc[0].to_dict()

c = st.columns(4)
c[0].metric("Traffic segments", f"{int(row.get('segments') or 0):,}")
c[1].metric("Hourly observations", f"{int(row.get('hourly_rows') or 0):,}")
c[2].metric("Average speed", "—" if pd.isna(row.get('avg_speed')) else f"{row['avg_speed']:.1f} km/h")
c[3].metric("Average congestion", "—" if pd.isna(row.get('avg_congestion')) else f"{row['avg_congestion']:.1%}")

st.divider()
st.subheader("Traffic patterns")
try:
    hourly = query("SELECT * FROM analytics.v_congestion_by_hour ORDER BY hour_of_day")
    if not hourly.empty:
        st.plotly_chart(px.line(hourly, x="hour_of_day", y="avg_congestion", markers=True,
                                labels={"hour_of_day":"Hour (New York)","avg_congestion":"Mean congestion"}), use_container_width=True)
    else:
        st.info("No hourly traffic aggregates yet.")
except Exception as exc:
    st.warning(f"Hourly traffic view unavailable: {exc}")

left, right = st.columns(2)
with left:
    st.subheader("Most congested segments")
    try:
        top = query("""SELECT t.segment_id, COALESCE(s.link_name, 'Segment ' || t.segment_id::text) AS segment,
                             t.avg_congestion, t.avg_speed, t.observations
                      FROM analytics.v_top_congested_segments t
                      LEFT JOIN clean.dim_segment s USING(segment_id)
                      ORDER BY t.avg_congestion DESC LIMIT 20""")
        st.dataframe(top, use_container_width=True, hide_index=True) if not top.empty else st.info("No segment rankings yet.")
    except Exception as exc: st.info(f"Segment analytics not available yet: {exc}")
with right:
    st.subheader("Taxi origin–destination flows")
    try:
        od = query("""SELECT f.pickup_zone_id, COALESCE(p.zone, 'Zone '||f.pickup_zone_id::text) pickup_zone,
                            f.dropoff_zone_id, COALESCE(d.zone, 'Zone '||f.dropoff_zone_id::text) dropoff_zone, f.trips
                     FROM analytics.v_od_flows f
                     LEFT JOIN clean.dim_zone p ON p.location_id=f.pickup_zone_id
                     LEFT JOIN clean.dim_zone d ON d.location_id=f.dropoff_zone_id
                     LIMIT 25""")
        st.dataframe(od, use_container_width=True, hide_index=True) if not od.empty else st.info("No taxi flows yet.")
    except Exception as exc: st.info(f"Taxi-flow view not available yet: {exc}")

st.divider()
st.subheader("Forecast evaluation")
try:
    segments = query("SELECT DISTINCT segment_id FROM analytics.ml_predictions ORDER BY segment_id")
    if segments.empty:
        st.info("No model predictions yet. Forecasts appear after feature engineering and model training.")
    else:
        sid = st.selectbox("Traffic segment", segments.segment_id.astype(int).tolist())
        pred = query("SELECT forecast_ts, actual_speed, predicted_speed FROM analytics.ml_predictions WHERE segment_id = " + str(int(sid)) + " ORDER BY forecast_ts")
        if not pred.empty:
            st.plotly_chart(px.line(pred, x="forecast_ts", y=["actual_speed","predicted_speed"],
                                    labels={"forecast_ts":"Forecast time","value":"Speed (km/h)","variable":"Series"}), use_container_width=True)
            mae = (pred.actual_speed-pred.predicted_speed).abs().mean()
            st.metric("Selected segment MAE", f"{mae:.2f} km/h")
except Exception as exc:
    st.info(f"Forecast evaluation is not available yet: {exc}")

st.divider()
st.subheader("Operational status")
for table, label in [("raw.dot_traffic","DOT raw"),("raw.tlc_yellow","TLC raw"),("raw.weather","Weather raw"),("raw.collisions","Collision raw"),("analytics.fact_traffic_hourly","Hourly traffic"),("analytics.ml_anomalies","Detected anomalies")]:
    try:
        count = query(f"SELECT count(*) AS n FROM {table}").iloc[0]["n"]
        st.write(f"{label}: **{int(count):,}** rows")
    except Exception:
        st.write(f"{label}: schema/table not initialized")
