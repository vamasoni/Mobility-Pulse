
from __future__ import annotations

import hashlib
import json
import pandas as pd
from psycopg.types.json import Jsonb

from db import connect, executemany
from config import RAW_DIR

TLC_MAP = {
    "pickup_ts": ["pickup_ts", "tpep_pickup_datetime"],
    "dropoff_ts": ["dropoff_ts", "tpep_dropoff_datetime"],
    "passenger_count": ["passenger_count"],
    "trip_distance": ["trip_distance"],
    "ratecode_id": ["ratecode_id", "RatecodeID"],
    "store_and_fwd_flag": ["store_and_fwd_flag", "store_and_fwd"],
    "pu_location_id": ["pu_location_id", "PULocationID"],
    "do_location_id": ["do_location_id", "DOLocationID"],
    "payment_type": ["payment_type"],
    "fare_amount": ["fare_amount"],
    "extra": ["extra"],
    "mta_tax": ["mta_tax"],
    "tip_amount": ["tip_amount"],
    "tolls_amount": ["tolls_amount"],
    "improvement_surcharge": ["improvement_surcharge"],
    "total_amount": ["total_amount"],
    "congestion_surcharge": ["congestion_surcharge"],
    "airport_fee": ["airport_fee", "Airport_fee"],
    "cbd_congestion_fee": ["cbd_congestion_fee", "cbd_congestion_fee"],
}

TLC_FIELDS = list(TLC_MAP)


def nullable(value):
    if value is None:
        return None
    if not isinstance(value, (dict, list)):
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
    if hasattr(value, "item"):
        return value.item()
    return value


def load_dot() -> int:
    count = 0
    with connect() as conn:
        conn.execute("TRUNCATE raw.dot_traffic")
        batch = []

        for path in sorted(RAW_DIR.glob("dot_traffic/date=*/manhattan.jsonl")):
            day = path.parent.name.split("=", 1)[1]
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    batch.append((day, Jsonb(json.loads(line))))
                    if len(batch) >= 2000:
                        executemany(
                            conn,
                            "INSERT INTO raw.dot_traffic(source_date,payload) VALUES (%s,%s)",
                            batch,
                        )
                        count += len(batch)
                        batch.clear()

        if batch:
            executemany(
                conn,
                "INSERT INTO raw.dot_traffic(source_date,payload) VALUES (%s,%s)",
                batch,
            )
            count += len(batch)

    print(f"DOT raw rows loaded: {count:,}")
    return count


def load_taxi_zones() -> int:
    path = RAW_DIR.parent / "reference" / "taxi_zone_lookup.csv"
    if not path.exists():
        print("Taxi-zone lookup not found; skipping.")
        return 0

    df = pd.read_csv(path)
    rows = [
        (
            int(row["LocationID"]),
            nullable(row.get("Borough")),
            nullable(row.get("Zone")),
            nullable(row.get("service_zone")),
        )
        for _, row in df.iterrows()
    ]

    with connect() as conn:
        conn.execute("TRUNCATE raw.taxi_zone_lookup")
        if rows:
            executemany(
                conn,
                "INSERT INTO raw.taxi_zone_lookup(location_id,borough,zone,service_zone) VALUES (%s,%s,%s,%s)",
                rows,
            )

    print(f"Taxi-zone reference rows loaded: {len(rows):,}")
    return len(rows)


def load_tlc() -> int:
    paths = sorted((RAW_DIR / "tlc" / "filtered").glob("yellow_tripdata_*.parquet"))
    total = 0

    with connect() as conn:
        conn.execute("TRUNCATE raw.tlc_yellow")

        for path in paths:
            month = path.stem.replace("yellow_tripdata_", "")
            df = pd.read_parquet(path)
            selected = {}

            for target, candidates in TLC_MAP.items():
                source = next((c for c in candidates if c in df.columns), None)
                selected[target] = df[source] if source else None

            frame = pd.DataFrame(selected)
            frame["source_month"] = f"{month}-01"

            for start in range(0, len(frame), 2000):
                chunk = frame.iloc[start:start + 2000]
                rows = []

                for record in chunk[TLC_FIELDS + ["source_month"]].itertuples(
                    index=False, name=None
                ):
                    values = list(record)
                    for i in (0, 1):
                        if values[i] is not None and hasattr(values[i], "isoformat"):
                            values[i] = values[i].isoformat(sep=" ")

                    values = [nullable(v) for v in values]
                    digest = hashlib.sha1(
                        "|".join("" if v is None else str(v) for v in values[:-1])
                        .encode("utf-8")
                    ).hexdigest()
                    row_hash = int(digest[:15], 16)
                    rows.append(tuple(values + [row_hash]))

                if rows:
                    columns = TLC_FIELDS + ["source_month", "row_hash"]
                    placeholders = ",".join(["%s"] * len(columns))
                    executemany(
                        conn,
                        f"INSERT INTO raw.tlc_yellow ({','.join(columns)}) VALUES ({placeholders})",
                        rows,
                    )
                    total += len(rows)

            print(f"Loaded TLC {month}: {len(df):,} rows")

    print(f"TLC raw rows loaded: {total:,}")
    return total


def load_weather() -> int:
    path = RAW_DIR / "weather" / "manhattan_hourly.json"
    if not path.exists():
        print("Weather file not found; skipping.")
        return 0

    hourly = json.loads(path.read_text(encoding="utf-8"))["hourly"]
    fields = [
        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
        "precipitation", "rain", "snowfall", "weather_code", "cloud_cover",
        "wind_speed_10m", "wind_gusts_10m",
    ]

    rows = []
    for i, timestamp in enumerate(hourly["time"]):
        rows.append(
            (timestamp,) + tuple(
                nullable(hourly.get(field, [None] * len(hourly["time"]))[i])
                for field in fields
            )
        )

    with connect() as conn:
        conn.execute("TRUNCATE raw.weather")
        if rows:
            executemany(
                conn,
                "INSERT INTO raw.weather(ts_local,temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,snowfall,weather_code,cloud_cover,wind_speed_10m,wind_gusts_10m) VALUES ("
                + ",".join(["%s"] * 11) + ")",
                rows,
            )

    print(f"Weather raw rows loaded: {len(rows):,}")
    return len(rows)


def load_collisions() -> int:
    rows_by_id = {}

    for path in sorted(RAW_DIR.glob("collisions/date=*/manhattan.jsonl")):
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                obj = json.loads(line)
                collision_id = obj.get("collision_id", obj.get("COLLISION_ID"))
                if collision_id is None:
                    continue
                rows_by_id[str(collision_id)] = obj

    rows = []
    for collision_id, obj in rows_by_id.items():
        rows.append((
            collision_id,
            obj.get("crash_date", obj.get("CRASH DATE")),
            obj.get("crash_time", obj.get("CRASH TIME")),
            obj.get("borough", obj.get("BOROUGH")),
            nullable(obj.get("latitude", obj.get("LATITUDE"))),
            nullable(obj.get("longitude", obj.get("LONGITUDE"))),
            nullable(obj.get("persons_injured", obj.get("NUMBER OF PERSONS INJURED"))),
            nullable(obj.get("persons_killed", obj.get("NUMBER OF PERSONS KILLED"))),
            Jsonb(obj),
        ))

    with connect() as conn:
        conn.execute("TRUNCATE raw.collisions")
        if rows:
            executemany(
                conn,
                "INSERT INTO raw.collisions(collision_id,crash_date,crash_time,borough,latitude,longitude,persons_injured,persons_killed,raw_payload) VALUES ("
                + ",".join(["%s"] * 9) + ")",
                rows,
            )

    print(f"Collision raw rows loaded: {len(rows):,}")
    return len(rows)


def main() -> None:
    print("Loading source data...")
    load_taxi_zones()
    load_dot()
    load_tlc()
    load_weather()
    load_collisions()
    print("Source loading complete.")


if __name__ == "__main__":
    main()
