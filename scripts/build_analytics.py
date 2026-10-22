from pathlib import Path
from db import connect

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    transform = (ROOT / "sql" / "01_transform.sql").read_text(encoding="utf-8")
    metrics = (ROOT / "sql" / "02_metrics.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.execute(transform)
        conn.execute(metrics)
    print("Transformations and KPI views completed.")
    with connect() as conn:
        for table in ("raw.dot_traffic", "raw.tlc_yellow", "raw.weather", "raw.collisions", "analytics.fact_traffic_hourly", "analytics.hourly_traffic_enriched"):
            schema, name = table.split(".")
            n = conn.execute("SELECT count(*) FROM " + schema + "." + name).fetchone()[0]
            print(f"{table}: {n:,} rows")

if __name__ == "__main__":
    main()
