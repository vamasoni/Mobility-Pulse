from __future__ import annotations
import pandas as pd
import holidays
from db import connect, executemany
from config import PROCESSED_DIR, CITY_TIMEZONE

FEATURE_COLUMNS = ["segment_id", "ts", "speed", "congestion_index", "trip_count", "incident_count", "temperature_2m", "precipitation", "wind_speed_10m", "hour", "dow", "is_holiday", "lag_1", "lag_24", "lag_168", "rolling_6", "target_speed"]

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT * FROM analytics.hourly_traffic_enriched ORDER BY segment_id, ts", conn)
    if df.empty:
        print("No enriched traffic rows. Run ingestion, load_sources, and build_analytics first.")
        return
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(CITY_TIMEZONE)
    df["hour"] = df["ts"].dt.hour
    df["dow"] = df["ts"].dt.dayofweek
    years = sorted(set(df["ts"].dt.year.tolist()))
    holiday_calendar = holidays.US(years=years)
    df["is_holiday"] = df["ts"].dt.date.map(lambda day: int(day in holiday_calendar))
    grouped = df.groupby("segment_id", group_keys=False)["speed"]
    df["lag_1"] = grouped.shift(1)
    df["lag_24"] = grouped.shift(24)
    df["lag_168"] = grouped.shift(168)
    df["rolling_6"] = grouped.transform(lambda values: values.shift(1).rolling(6, min_periods=2).mean())
    df["target_speed"] = grouped.shift(-1)
    features = df[FEATURE_COLUMNS].replace([float("inf"), float("-inf")], float("nan")).dropna().copy()
    if features.empty:
        print("No rows remain after lag/target construction; a longer time range may be required.")
        return
    features["ts"] = pd.to_datetime(features["ts"], utc=True)
    with connect() as conn:
        conn.execute("TRUNCATE analytics.ml_features")
        executemany(conn, 
            "INSERT INTO analytics.ml_features(segment_id,ts,speed,congestion_index,trip_count,incident_count,temperature_2m,precipitation,wind_speed_10m,hour,dow,is_holiday,lag_1,lag_24,lag_168,rolling_6,target_speed) VALUES (" + ",".join(["%s"] * 17) + ")",
            [tuple(None if pd.isna(v) else (v.item() if hasattr(v, "item") else v) for v in row) for row in features.itertuples(index=False, name=None)],
        )
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    features.to_parquet(PROCESSED_DIR / "ml_features.parquet", index=False)
    print(f"Feature rows: {len(features):,}; segments: {features.segment_id.nunique():,}")

if __name__ == "__main__":
    main()
