"""Download actual wind generation (FUELHH) and forecasts (WINDFOR) from Elexon BMRS.
 
Use:
    pip install requests pandas pyarrow
    python fetch_data.py
 
Saves data/raw/actuals.parquet and data/raw/forecasts.parquet, and prints a summary.
NOTE: Parameter names follow the BMRS v1 API; if any endpoint
returns a 400 error, check the documentation page and adjust PARAMS below.
"""
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
 
import pandas as pd
import requests
 
BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = Path("data/raw")
 
# Decisions made in January 2026 -> deliveries from January 2 to February 1.
ACTUALS_FROM, ACTUALS_TO = date(2026, 1, 1), date(2026, 2, 2)
# Forecasts published a few days in advance (in case the time horizon is long).
FORECASTS_FROM, FORECASTS_TO = date(2025, 12, 24), date(2026, 2, 1)
 
 
def chunks(start: date, end: date, days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt
 
 
def get_json(url: str, params: dict, retries: int = 3):
    for attempt in range(1, retries + 1):
        resp = requests.get(
            url, params=params, headers={"Accept": "application/json"}, timeout=60
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  try {attempt}: HTTP {resp.status_code} -> {resp.text[:200]}")
        time.sleep(2 * attempt)
    raise RuntimeError(f"Falló {url} con {params}")
 
 
def fetch_actuals() -> pd.DataFrame:
    rows = []
    for a, b in chunks(ACTUALS_FROM, ACTUALS_TO, 7):
        print(f"FUELHH {a} -> {b}")
        rows += get_json(
            f"{BASE}/FUELHH/stream",
            {"settlementDateFrom": a.isoformat(), "settlementDateTo": b.isoformat(),
             "fuelType": "WIND"},
        )
    return pd.DataFrame(rows)
 
 
def fetch_forecasts() -> pd.DataFrame:
    rows = []
    for a, b in chunks(FORECASTS_FROM, FORECASTS_TO, 2):
        print(f"WINDFOR {a} -> {b}")
        rows += get_json(
            f"{BASE}/WINDFOR/stream",
            {"publishDateTimeFrom": f"{a.isoformat()}T00:00:00Z",
             "publishDateTimeTo": f"{b.isoformat()}T00:00:00Z"},
        )
    return pd.DataFrame(rows)
 
 
def summarize(name: str, df: pd.DataFrame):
    print(f"\n== {name}: {len(df)} filas ==")
    print("columns:", list(df.columns))
    for col in ("startTime", "publishTime"):
        if col in df:
            print(f"{col}: {df[col].min()} -> {df[col].max()}")
    print(df.head(3).to_string())
 
 
if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    actuals = fetch_actuals()
    forecasts = fetch_forecasts()
    for df in (actuals, forecasts):
        for col in ("startTime", "publishTime"):
            if col in df:
                df[col] = pd.to_datetime(df[col], utc=True)
    actuals = actuals.sort_values("publishTime").drop_duplicates("startTime", keep="last")
    actuals.to_parquet(OUT / "actuals.parquet", index=False)
    forecasts.to_parquet(OUT / "forecasts.parquet", index=False)
    summarize("actuals", actuals)
    summarize("forecasts", forecasts)
    print(f"\nReady ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)")