import argparse, os
from datetime import date, timedelta
from ingestion.utils import get_json, write_jsonl
from config import RAW_DIR, BOROUGH, START_DATE, END_DATE

URL = os.getenv("DOT_ENDPOINT", "https://data.cityofnewyork.us/resource/i4gi-tjb9.json")

def fetch_day(day, borough=BOROUGH):
    rows, offset, limit = [], 0, 50000
    headers = {"X-App-Token": os.getenv("DOT_APP_TOKEN")} if os.getenv("DOT_APP_TOKEN") else {}
    while True:
        params = {
            "$limit": limit, "$offset": offset, "$order": "data_as_of,id",
            "$where": f"data_as_of >= '{day}T00:00:00' AND data_as_of < '{day + timedelta(days=1)}T00:00:00' AND borough='{borough}'"
        }
        batch = get_json(URL, params=params, headers=headers)
        rows.extend(batch)
        if len(batch) < limit:
            return rows
        offset += limit

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default=START_DATE)
    p.add_argument("--end", default=END_DATE)
    args = p.parse_args()
    d, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    while d <= end:
        out = RAW_DIR / "dot_traffic" / f"date={d.isoformat()}" / "manhattan.jsonl"
        if not out.exists():
            rows = fetch_day(d)
            write_jsonl(out, rows)
            print(d, len(rows))
        else:
            print("skip", d)
        d += timedelta(days=1)

if __name__ == "__main__":
    main()
