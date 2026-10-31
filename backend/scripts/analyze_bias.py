"""Diagnose the forecast bias: is it constant, proportional, or concentrated in a few days?
 
Run from the backend folder:  python scripts\analyze_bias.py
"""
import sys
from pathlib import Path
 
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
 
import pandas as pd
 
from app.services.forecast import compare, hourly_actuals, select_latest_forecast
 
CUTOFF = 9.0
HIST_START = pd.Timestamp("2026-01-01", tz="UTC")  # to have an error history
START = pd.Timestamp("2026-01-02", tz="UTC")
END = pd.Timestamp("2026-02-02", tz="UTC")
 
fc = pd.read_parquet("data/raw/forecasts.parquet").drop_duplicates(
    ["publishTime", "startTime"]
)
actuals = hourly_actuals(pd.read_parquet("data/raw/actuals.parquet"))
sel = select_latest_forecast(fc, CUTOFF, start=HIST_START, end=END)
df = compare(sel, actuals)
df["day"] = df["startTime"].dt.normalize()
df["hour"] = df["startTime"].dt.hour
win = df[df["startTime"] >= START]
 
print(f"Cutoff used: {CUTOFF}:00 UTC, hours analysed: {len(win)}")
 
print("\n== 1. Overall level (MW) ==")
print(f"mean actual: {win['actual'].mean():.0f}   mean forecast: {win['forecast'].mean():.0f}")
print(f"mean bias: {win['error'].mean():.0f} MW "
      f"({win['error'].mean() / win['actual'].mean() * 100:.1f}% of mean actual)")
print(f"sum of forecast / sum of actual: {win['forecast'].sum() / win['actual'].sum():.3f}")
 
print("\n== 2. Bias by actual generation level (quartiles) ==")
win = win.assign(level=pd.qcut(win["actual"], 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"]))
by_level = win.groupby("level", observed=True).agg(
    mean_actual=("actual", "mean"), bias=("error", "mean"), hours=("error", "size")
)
by_level["bias_pct_of_actual"] = by_level["bias"] / by_level["mean_actual"] * 100
print(by_level.round(0).to_string())
 
print("\n== 3. Daily bias (mean error of each delivery day, MW) ==")
daily = win.groupby("day")["error"].mean()
print(daily.describe().round(0).to_string())
print(f"days with positive bias: {(daily > 0).sum()} of {len(daily)}")
 
print("\n== 4. Bias by hour of day (UTC, MW) ==")
print(win.groupby("hour")["error"].mean().round(0).to_string())
 
print("\n== 5. Bias correction WITHOUT using the future ==")
print("(at 09:00 on D-1 only actuals up to day D-2 are known)")
daily_all = df.groupby("day")["error"].mean()
parts = []
for day, g in win.groupby("day"):
    hist = daily_all[
        (daily_all.index >= day - pd.Timedelta(days=8))
        & (daily_all.index <= day - pd.Timedelta(days=2))
    ]
    if len(hist) < 7:
        continue
    corrected_error = (g["forecast"] - hist.mean()) - g["actual"]
    parts.append(pd.DataFrame({"raw": g["abs_error"], "corrected": corrected_error.abs(),
                               "err_corr": corrected_error}))
res = pd.concat(parts)
print(f"days evaluated: {res.shape[0] // 24} (7-day history window)")
print(f"MAE uncorrected: {res['raw'].mean():.0f}   corrected: {res['corrected'].mean():.0f}")
print(f"P95 absolute error uncorrected: {res['raw'].quantile(0.95):.0f}   "
      f"corrected: {res['corrected'].quantile(0.95):.0f}")
print(f"residual bias after correction: {res['err_corr'].mean():.0f}")