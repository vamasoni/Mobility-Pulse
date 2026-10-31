from __future__ import annotations
import pandas as pd
import holidays
from db import connect, executemany
from config import CITY_TIMEZONE, PROCESSED_DIR

FEATURE_COLUMNS = ["segment_id","ts","speed","congestion_index","trip_count","incident_count","temperature_2m","precipitation","wind_speed_10m","hour","dow","is_holiday","lag_1","lag_24","lag_168","rolling_6","target_speed"]

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT * FROM analytics.hourly_traffic_enriched ORDER BY segment_id, ts", conn)
    if df.empty:
        raise RuntimeError("No enriched traffic rows. Run ingestion and analytics first.")
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    pieces=[]
    for sid, part in df.groupby("segment_id", sort=False):
        part=part.sort_values("ts").drop_duplicates("ts").set_index("ts")
        # Reindex each segment to a continuous hourly grid. Missing observed speeds
        # remain NaN and are not silently treated as adjacent hours.
        full_idx=pd.date_range(part.index.min().floor("h"), part.index.max().floor("h"), freq="h", tz="UTC")
        part=part.reindex(full_idx)
        part["segment_id"]=int(sid)
        part["speed"] = pd.to_numeric(part["speed"], errors="coerce")
        part["lag_1"]=part["speed"].shift(1)
        part["lag_24"]=part["speed"].shift(24)
        part["lag_168"]=part["speed"].shift(168)
        part["rolling_6"]=part["speed"].shift(1).rolling(6,min_periods=6).mean()
        part["target_speed"]=part["speed"].shift(-1)
        pieces.append(part.reset_index(names="ts"))
    feat=pd.concat(pieces,ignore_index=True)
    local=feat["ts"].dt.tz_convert(CITY_TIMEZONE)
    feat["hour"]=local.dt.hour
    feat["dow"]=local.dt.dayofweek
    years=sorted(local.dt.year.dropna().unique().tolist())
    cal=holidays.US(years=years)
    feat["is_holiday"]=local.dt.date.map(lambda d:int(d in cal))
    for col in ["congestion_index","trip_count","incident_count","temperature_2m","precipitation","wind_speed_10m"]:
        if col not in feat: feat[col]=0.0
    feat=feat[FEATURE_COLUMNS].replace([float("inf"),float("-inf")],float("nan")).dropna(subset=["speed","lag_1","lag_24","lag_168","rolling_6","target_speed"])
    if feat.empty: raise RuntimeError("No feature rows remain; at least 7 days of continuous hourly data per segment are needed.")
    feat["ts"]=pd.to_datetime(feat["ts"],utc=True)
    with connect() as conn:
        conn.execute("TRUNCATE analytics.ml_features")
        executemany(conn,"INSERT INTO analytics.ml_features("+",".join(FEATURE_COLUMNS)+") VALUES ("+",".join(["%s"]*len(FEATURE_COLUMNS))+")",[tuple(None if pd.isna(v) else (v.item() if hasattr(v,"item") else v) for v in r) for r in feat.itertuples(index=False,name=None)])
    PROCESSED_DIR.mkdir(parents=True,exist_ok=True)
    feat.to_parquet(PROCESSED_DIR/"ml_features.parquet",index=False)
    print(f"Feature rows: {len(feat):,}; segments: {feat.segment_id.nunique():,}")

if __name__ == "__main__": main()
