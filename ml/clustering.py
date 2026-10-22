from __future__ import annotations
import pandas as pd
from sklearn.cluster import KMeans
from db import connect
from config import PROCESSED_DIR

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT segment_id,ts,speed FROM analytics.fact_traffic_hourly", conn)
    if df.empty:
        print("No hourly traffic rows; run analytics first.")
        return
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df["hour"] = df["ts"].dt.hour
    wide = df.pivot_table(index="segment_id", columns="hour", values="speed", aggfunc="mean")
    wide = wide.dropna(axis=1, how="all")
    wide = wide.fillna(wide.median()).fillna(0)
    if len(wide) < 2:
        print(f"Need at least two segments with complete hourly profiles; found {len(wide)}.")
        return
    k = min(4, len(wide))
    model = KMeans(n_clusters=k, n_init=20, random_state=42)
    result = pd.DataFrame({"segment_id": wide.index.astype(int), "cluster": model.fit_predict(wide)})
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(PROCESSED_DIR / "segment_clusters.csv", index=False)
    print("Segments per cluster:")
    print(result.groupby("cluster").size().to_string())

if __name__ == "__main__":
    main()
