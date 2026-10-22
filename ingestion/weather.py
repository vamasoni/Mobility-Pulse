from __future__ import annotations
import json
import requests
from config import RAW_DIR, START_DATE, END_DATE, CITY_TIMEZONE

URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,snowfall,weather_code,cloud_cover,wind_speed_10m,wind_gusts_10m"

def main() -> None:
    params = {
        "latitude": 40.7831, "longitude": -73.9712,
        "start_date": START_DATE, "end_date": END_DATE,
        "hourly": HOURLY, "timezone": CITY_TIMEZONE,
    }
    response = requests.get(URL, params=params, timeout=180)
    response.raise_for_status()
    data = response.json()
    if "hourly" not in data or "time" not in data["hourly"]:
        raise RuntimeError(f"Unexpected Open-Meteo response: {list(data)}")
    out = RAW_DIR / "weather" / "manhattan_hourly.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data), encoding="utf-8")
    print(f"Weather saved: {out} ({len(data['hourly']['time'])} hourly rows)")

if __name__ == "__main__":
    main()
