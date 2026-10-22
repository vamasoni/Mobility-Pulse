from pathlib import Path
from db import connect

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    sql = (ROOT / "sql" / "00_init.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.execute(sql)
    print("Warehouse initialized.")

if __name__ == "__main__":
    main()
