import json, time
from pathlib import Path
import requests

def get_json(url, params=None, headers=None, retries=5, timeout=60):
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise last

def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), default=str) + "\n")
    tmp.replace(path)
