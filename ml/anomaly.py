from __future__ import annotations
import pandas as pd
from sklearn.ensemble import IsolationForest
from db import connect, executemany

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT segment_id,ts,speed,congestion_index FROM analytics.fact_traffic_hourly ORDER BY segment_id,ts", conn)
    if df.empty:
        print("No hourly traffic rows; run analytics first.")
        return
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    grouped = df.groupby("segment_id")["speed"]
    df["flatline"] = grouped.transform(lambda s: s.rolling(6, min_periods=6).std().lt(0.01))
    df["sudden_change"] = grouped.transform(lambda s: s.diff().abs().gt(25))
    df["physical_limit"] = ~df["speed"].between(0, 120)
    valid = df[["speed", "congestion_index"]].replace([float("inf"), float("-inf")], float("nan")).fillna(0)
    if len(df) >= 10:
        detector = IsolationForest(n_estimators=150, contamination=0.01, random_state=42)
        df["iso"] = detector.fit_predict(valid)
    else:
        df["iso"] = 1
    rows = []
    for row in df.itertuples(index=False):
        types = []
        if bool(row.flatline): types.append("sensor_flatline")
        if bool(row.sudden_change): types.append("sudden_change")
        if bool(row.physical_limit): types.append("physical_limit")
        if row.iso == -1: types.append("isolation_forest")
        for kind in types:
            score = -1.0 if kind != "isolation_forest" else 1.0
            rows.append((int(row.segment_id), row.ts.to_pydatetime(), float(row.speed), None if pd.isna(row.congestion_index) else float(row.congestion_index), kind, score))
    with connect() as conn:
        conn.execute("TRUNCATE analytics.ml_anomalies")
        if rows:
            executemany(conn, "INSERT INTO analytics.ml_anomalies(segment_id,ts,speed,congestion_index,anomaly_type,anomaly_score) VALUES (%s,%s,%s,%s,%s,%s)", rows)
    print(f"Anomaly records: {len(rows):,}")

if __name__ == "__main__":
    main()
