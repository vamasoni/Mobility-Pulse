from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

POSTGRES = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "mobilitypulse"),
    "user": os.getenv("POSTGRES_USER", "mobility"),
    "password": os.getenv("POSTGRES_PASSWORD", "mobilitypulse_dev"),
}

RAW_DIR = ROOT / os.getenv("RAW_DIR", "data/raw")
PROCESSED_DIR = ROOT / os.getenv("PROCESSED_DIR", "data/processed")
MODEL_DIR = ROOT / os.getenv("MODEL_DIR", "models")
CITY_TIMEZONE = os.getenv("CITY_TIMEZONE", "America/New_York")
BOROUGH = os.getenv("BOROUGH", "Manhattan")
START_DATE = os.getenv("START_DATE", "2026-01-01")
END_DATE = os.getenv("END_DATE", "2026-05-31")

for p in (RAW_DIR, PROCESSED_DIR, MODEL_DIR):
    p.mkdir(parents=True, exist_ok=True)
