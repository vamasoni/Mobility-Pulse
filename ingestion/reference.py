from __future__ import annotations
import io
import zipfile
import requests
from config import RAW_DIR

CSV_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
ZIP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"

def main() -> None:
    out = RAW_DIR.parent / "reference"
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "taxi_zone_lookup.csv"
    if not csv_path.exists():
        response = requests.get(CSV_URL, timeout=90)
        response.raise_for_status()
        csv_path.write_bytes(response.content)
    zip_path = out / "taxi_zones.zip"
    if not zip_path.exists():
        response = requests.get(ZIP_URL, timeout=90)
        response.raise_for_status()
        zip_path.write_bytes(response.content)
    extract_dir = out / "taxi_zones"
    if not extract_dir.exists():
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_path.read_bytes())) as archive:
            archive.extractall(extract_dir)
    print(f"Taxi-zone reference ready: {csv_path}")

if __name__ == "__main__":
    main()
