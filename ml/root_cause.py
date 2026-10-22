from __future__ import annotations
import pandas as pd
from db import connect
from config import CITY_TIMEZONE

def main() -> None:
    with connect() as conn:
        df = pd.read_sql("SELECT ts,speed,congestion_index,trip_count,incident_count,temperature_2m,precipitation FROM analytics.hourly_traffic_enriched", conn)
    if df.empty:
        print("No enriched traffic data; run analytics first.")
        return
    df["ts"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(CITY_TIMEZONE)
    df["date"] = df["ts"].dt.date
    daily = df.groupby("date").agg(speed=("speed", "mean"), congestion=("congestion_index", "mean"), trips=("trip_count", "mean"), incidents=("incident_count", "mean"), temperature=("temperature_2m", "mean"), precipitation=("precipitation", "mean")).reset_index()
    event = daily.sort_values("congestion", ascending=False).iloc[0]
    day = pd.Timestamp(event["date"])
    previous = daily[(daily["date"] < event["date"]) & (pd.to_datetime(daily["date"]).dt.dayofweek == day.dayofweek)].tail(4)
    baseline = previous.mean(numeric_only=True) if not previous.empty else daily[daily["date"] != event["date"]].mean(numeric_only=True)
    print("Highest-congestion date:", event["date"])
    print("Observed metrics:", event.drop(labels=["date"]).to_dict())
    print("Historical baseline:", baseline.to_dict())
    if not baseline.empty:
        print("Difference from baseline:", (event.drop(labels=["date"]).astype(float) - baseline).to_dict())

if __name__ == "__main__":
    main()
