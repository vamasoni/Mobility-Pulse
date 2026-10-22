from __future__ import annotations
import argparse
import os
from datetime import date, timedelta
from ingestion.utils import get_json, write_jsonl
from config import RAW_DIR, START_DATE, END_DATE

URL = os.getenv("COLLISIONS_ENDPOINT", "https://data.cityofnewyork.us/resource/h9gi-nx95.json")

def fetch_day(day: date) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    limit = 50000
    headers = {"X-App-Token": os.getenv("DOT_APP_TOKEN")} if os.getenv("DOT_APP_TOKEN") else None
    while True:
        next_day = day + timedelta(days=1)
        params = {
            "$limit": limit, "$offset": offset, "$order": "collision_id",
            "$where": f"crash_date >= '{day.isoformat()}T00:00:00' AND crash_date < '{next_day.isoformat()}T00:00:00' AND borough='MANHATTAN'",
        }
        batch = get_json(URL, params=params, headers=headers)
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return rows

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    args = parser.parse_args()
    day, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    while day <= end:
        out = RAW_DIR / "collisions" / f"date={day.isoformat()}" / "manhattan.jsonl"
        if out.exists():
            print(f"Collisions {day}: skip existing file")
        else:
            rows = fetch_day(day)
            write_jsonl(out, rows)
            print(f"Collisions {day}: {len(rows):,} rows")
        day += timedelta(days=1)

if __name__ == "__main__":
    main()
