from __future__ import annotations
import argparse
import os
import pandas as pd
import requests
from config import RAW_DIR, START_DATE, END_DATE

BASE = os.getenv("TLC_YELLOW_BASE", "https://d37ci6vzurychx.cloudfront.net/trip-data")
ZONE_CSV = os.getenv("TLC_ZONES_CSV", "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv")
RENAME = {
    "tpep_pickup_datetime": "pickup_ts", "tpep_dropoff_datetime": "dropoff_ts",
    "passenger_count": "passenger_count", "trip_distance": "trip_distance",
    "RatecodeID": "ratecode_id", "store_and_fwd_flag": "store_and_fwd_flag",
    "PULocationID": "pu_location_id", "DOLocationID": "do_location_id",
    "payment_type": "payment_type", "fare_amount": "fare_amount", "extra": "extra",
    "mta_tax": "mta_tax", "tip_amount": "tip_amount", "tolls_amount": "tolls_amount",
    "improvement_surcharge": "improvement_surcharge", "total_amount": "total_amount",
    "congestion_surcharge": "congestion_surcharge", "Airport_fee": "airport_fee",
    "cbd_congestion_fee": "cbd_congestion_fee",
}

def get_zone_lookup() -> pd.DataFrame:
    path = RAW_DIR.parent / "reference" / "taxi_zone_lookup.csv"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(ZONE_CSV, timeout=90); response.raise_for_status()
        path.write_bytes(response.content)
    return pd.read_csv(path)

def download_month(period: str) -> Path:
    out = RAW_DIR / "tlc" / "downloads" / f"yellow_tripdata_{period}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        response = requests.get(f"{BASE}/yellow_tripdata_{period}.parquet", timeout=240)
        response.raise_for_status()
        out.write_bytes(response.content)
    return out

def filter_manhattan(path: Path, period: str, zones: pd.DataFrame) -> None:
    # Stream Parquet row groups/batches so a multi-million-row TLC month does not
    # need to fit in RAM. Only columns consumed by the warehouse are retained.
    import pyarrow as pa
    import pyarrow.parquet as pq

    required = ["pickup_ts", "dropoff_ts", "passenger_count", "trip_distance", "ratecode_id", "store_and_fwd_flag", "pu_location_id", "do_location_id", "payment_type", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee", "cbd_congestion_fee"]
    numeric_float = ["passenger_count", "trip_distance", "ratecode_id", "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee", "cbd_congestion_fee"]
    integer_cols = ["pu_location_id", "do_location_id", "payment_type"]
    schema_fields = [pa.field("pickup_ts", pa.string()), pa.field("dropoff_ts", pa.string()),
                     pa.field("passenger_count", pa.float64()), pa.field("trip_distance", pa.float64()),
                     pa.field("ratecode_id", pa.float64()), pa.field("store_and_fwd_flag", pa.string()),
                     pa.field("pu_location_id", pa.int64()), pa.field("do_location_id", pa.int64()),
                     pa.field("payment_type", pa.int64()), pa.field("fare_amount", pa.float64()),
                     pa.field("extra", pa.float64()), pa.field("mta_tax", pa.float64()),
                     pa.field("tip_amount", pa.float64()), pa.field("tolls_amount", pa.float64()),
                     pa.field("improvement_surcharge", pa.float64()), pa.field("total_amount", pa.float64()),
                     pa.field("congestion_surcharge", pa.float64()), pa.field("airport_fee", pa.float64()),
                     pa.field("cbd_congestion_fee", pa.float64())]
    schema = pa.schema(schema_fields)
    manhattan = set(pd.to_numeric(zones.loc[zones["Borough"].eq("Manhattan"), "LocationID"], errors="coerce").dropna().astype(int))
    month_start = pd.Timestamp(period + "-01")
    month_end = month_start + pd.offsets.MonthBegin(1)
    out = RAW_DIR / "tlc" / "filtered" / f"yellow_tripdata_{period}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    kept = 0
    parquet = pq.ParquetFile(path)
    try:
        for batch in parquet.iter_batches(batch_size=200_000):
            df = batch.to_pandas().rename(columns=RENAME)
            for col in required:
                if col not in df.columns:
                    df[col] = None
            pu = pd.to_numeric(df["pu_location_id"], errors="coerce")
            do = pd.to_numeric(df["do_location_id"], errors="coerce")
            pickup = pd.to_datetime(df["pickup_ts"], errors="coerce")
            mask = (pu.isin(manhattan) | do.isin(manhattan)) & (pickup >= month_start) & (pickup < month_end)
            filtered = df.loc[mask, required].copy()
            if filtered.empty:
                continue
            filtered["pickup_ts"] = pd.to_datetime(filtered["pickup_ts"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            filtered["dropoff_ts"] = pd.to_datetime(filtered["dropoff_ts"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
            for col in numeric_float:
                filtered[col] = pd.to_numeric(filtered[col], errors="coerce")
            for col in integer_cols:
                filtered[col] = pd.to_numeric(filtered[col], errors="coerce").round().astype("Int64")
            table = pa.Table.from_pandas(filtered, schema=schema, preserve_index=False, safe=False)
            if writer is None:
                writer = pq.ParquetWriter(out, schema)
            writer.write_table(table, row_group_size=100_000)
            kept += len(filtered)
    finally:
        if writer is not None:
            writer.close()
    if writer is None:
        empty = pa.Table.from_pandas(pd.DataFrame({col: pd.Series(dtype="object") for col in required}), schema=schema, preserve_index=False, safe=False)
        pq.write_table(empty, out)
    print(f"TLC {period}: {kept:,} Manhattan-related trips -> {out}")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=START_DATE[:7])
    parser.add_argument("--end", default=END_DATE[:7])
    args = parser.parse_args()
    zones = get_zone_lookup()
    for period in pd.period_range(args.start, args.end, freq="M"):
        month = str(period)
        download = download_month(month)
        filtered = RAW_DIR / "tlc" / "filtered" / f"yellow_tripdata_{month}.parquet"
        if filtered.exists():
            print(f"TLC {month}: already filtered, skip")
            continue
        filter_manhattan(download, month, zones)

if __name__ == "__main__":
    main()
