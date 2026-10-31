"""Exploration of the data downloaded by fetch_data.py.

Run from the backend folder: python scripts\\explore.py
"""
import pandas as pd
 
CUTOFF_HOUR = 9  # UTC time on the day before delivery (in January, UK = UTC)
START = pd.Timestamp("2026-01-02", tz="UTC")  # first day of delivery
END = pd.Timestamp("2026-02-02", tz="UTC")    # End (exclusive): deliveries until Feb 1
 
act = pd.read_parquet("data/raw/actuals.parquet")
fc = pd.read_parquet("data/raw/forecasts.parquet")
 
print("== Duplicates ==")
print("actuals repeated by startTime:", act.duplicated("startTime").sum())
print("forecasts repeated by (publishTime, startTime):",
      fc.duplicated(["publishTime", "startTime"]).sum())
act = act.sort_values("publishTime").drop_duplicates("startTime", keep="last")
fc = fc.drop_duplicates(["publishTime", "startTime"])
 
print("\n== Actuals without duplicates ==")
expected = pd.date_range("2026-01-01", "2026-02-02 23:30", freq="30min", tz="UTC")
missing = expected.difference(act["startTime"])
print(f"filas: {len(act)} (expected {len(expected)}), missing periods: {len(missing)}")
 
print("\n== Forecast horizon (startTime - publishTime, in hours) ==")
fc["horizon_h"] = (fc["startTime"] - fc["publishTime"]).dt.total_seconds() / 3600
print(fc["horizon_h"].describe().round(1).to_string())
print("rows with a negative horizon (published after the target date):",
      (fc["horizon_h"] < 0).sum())
 
print("\n== Publication pattern ==")
pubs = fc["publishTime"].drop_duplicates()
print("distinct publications:", len(pubs))
print("minutes since publication:", pubs.dt.minute.value_counts().to_dict())
print("UTC publication time:", sorted(pubs.dt.hour.unique()))
print("rows per post:")
print(fc.groupby("publishTime").size().describe().round(1).to_string())
 
print(f"\n== Coverage with a D-1 cutoff at {CUTOFF_HOUR}:00 UTC ==")
fc["cutoff"] = (fc["startTime"].dt.normalize() - pd.Timedelta(days=1)
                + pd.Timedelta(hours=CUTOFF_HOUR))
ok = fc[(fc["startTime"] >= START) & (fc["startTime"] < END)
        & (fc["publishTime"] <= fc["cutoff"])]
total_hours = int((END - START) / pd.Timedelta(hours=1))
print(f"target hours with forecast available as of the cutoff: "
      f"{ok['startTime'].nunique()} de {total_hours}")
latest = ok.sort_values("publishTime").groupby("startTime").tail(1)
lead = (latest["startTime"] - latest["publishTime"]).dt.total_seconds() / 3600
print("chosen forecast horizon (hours):")
print(lead.describe().round(1).to_string())