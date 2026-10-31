"""Core analysis: the forecast available at decision time and its error metrics.
 
All functions are pure (they take and return DataFrames), so they can be tested
without touching the network or the disk.
 
Time zone: everything is UTC. In January the UK uses GMT (= UTC); for other
months the cutoff hour would have to be converted from local time.
"""
from __future__ import annotations
 
import numpy as np
import pandas as pd
 
DEFAULT_CUTOFF_HOUR = 9.0  # UTC hour of the day before delivery (configurable)
DEFAULT_BIAS_WINDOW_DAYS = 7  # days of history used to estimate the bias
DEFAULT_BIAS_LAG_DAYS = 2  # at decision time (D-1) actuals are only known up to D-2
 
 
def select_latest_forecast(
    forecasts: pd.DataFrame,
    cutoff_hour: float = DEFAULT_CUTOFF_HOUR,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """For each target hour, the latest forecast published before the cutoff.
 
    The cutoff is "the day before delivery at `cutoff_hour` UTC" (inclusive).
    `start`/`end` limit the target hours (end exclusive).
    Returns: startTime, publishTime, forecast, horizon_h.
    """
    df = forecasts[["publishTime", "startTime", "generation"]].copy()
    if start is not None:
        df = df[df["startTime"] >= start]
    if end is not None:
        df = df[df["startTime"] < end]
 
    cutoff = (
        df["startTime"].dt.normalize()
        - pd.Timedelta(days=1)
        + pd.Timedelta(hours=cutoff_hour)
    )
    df = df[df["publishTime"] <= cutoff]
 
    latest = (
        df.sort_values("publishTime")
        .groupby("startTime", as_index=False)
        .tail(1)
        .sort_values("startTime")
        .rename(columns={"generation": "forecast"})
    )
    latest["horizon_h"] = (
        latest["startTime"] - latest["publishTime"]
    ).dt.total_seconds() / 3600
    return latest[["startTime", "publishTime", "forecast", "horizon_h"]].reset_index(
        drop=True
    )
 
 
def hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Average the two 30-minute periods of each hour (NaN if one is missing)."""
    series = actuals.drop_duplicates("startTime").set_index("startTime")["generation"]
    resampled = series.sort_index().resample("1h")
    hourly = resampled.mean().where(resampled.count() == 2)
    return hourly.rename("actual").reset_index()
 
 
def compare(selected: pd.DataFrame, actuals_hourly: pd.DataFrame) -> pd.DataFrame:
    """Join the selected forecast and the actual by hour; error = forecast - actual."""
    df = selected.merge(actuals_hourly, on="startTime", how="inner").dropna(
        subset=["actual", "forecast"]
    )
    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()
    return df
 
 
def error_metrics(df: pd.DataFrame) -> dict:
    """Error metrics. A positive error means the forecast was HIGHER than the actual."""
    if df.empty:
        return {"n": 0}
    err, abs_err = df["error"], df["abs_error"]
    positive = df[df["actual"] > 0]  # MAPE only where the actual is not zero
    return {
        "n": int(len(df)),
        "mae": float(abs_err.mean()),
        "rmse": float(np.sqrt((err**2).mean())),
        "bias": float(err.mean()),
        "mape_pct": float((positive["abs_error"] / positive["actual"]).mean() * 100)
        if len(positive)
        else None,
        "abs_error_p50": float(abs_err.quantile(0.50)),
        "abs_error_p90": float(abs_err.quantile(0.90)),
        "abs_error_p95": float(abs_err.quantile(0.95)),
        "error_p05": float(err.quantile(0.05)),
        "error_p95": float(err.quantile(0.95)),
    }
 
 
# ---------------------------------------------------------------------------
# Bias correction (uses only information available at decision time)
# ---------------------------------------------------------------------------
 
 
def daily_mean_error(compared: pd.DataFrame) -> pd.Series:
    """Mean forecast error of each delivery day (UTC).
 
    Days with fewer than 24 compared hours are set to NaN so that a partial day
    never produces a noisy bias estimate.
    """
    grouped = compared.assign(day=compared["startTime"].dt.normalize()).groupby("day")["error"]
    return grouped.mean().where(grouped.size() == 24)
 
 
def estimate_bias(
    daily_errors: pd.Series,
    day: pd.Timestamp,
    window_days: int = DEFAULT_BIAS_WINDOW_DAYS,
    lag_days: int = DEFAULT_BIAS_LAG_DAYS,
) -> float | None:
    """Bias estimate for delivery `day`: mean of the daily errors of the
    `window_days` days ending `lag_days` days before it.
 
    With the defaults (7, 2) the window for delivery day D is D-8 ... D-2: at the
    decision time (D-1, before delivery D-1 has finished) the actuals of D-1 and D
    are not known yet. Returns None unless the whole window is available.
    """
    first = day - pd.Timedelta(days=lag_days + window_days - 1)
    last = day - pd.Timedelta(days=lag_days)
    history = daily_errors.reindex(pd.date_range(first, last, freq="D"))
    if history.isna().any():
        return None
    return float(history.mean())
 
 
def apply_bias_correction(
    compared: pd.DataFrame,
    window_days: int = DEFAULT_BIAS_WINDOW_DAYS,
    lag_days: int = DEFAULT_BIAS_LAG_DAYS,
) -> pd.DataFrame:
    """Subtract the estimated bias from each forecast.
 
    `compared` is the output of `compare()` and must include the history needed
    for the first days. Days without a complete history window are dropped, so the
    result only contains days where the correction could really be computed.
    Adds: bias_estimate, forecast_corrected, error_corrected, abs_error_corrected.
    """
    daily = daily_mean_error(compared)
    df = compared.copy()
    df["day"] = df["startTime"].dt.normalize()
    estimates = {}
    for day in df["day"].unique():
        value = estimate_bias(daily, day, window_days, lag_days)
        estimates[day] = np.nan if value is None else value
    df["bias_estimate"] = df["day"].map(estimates).astype(float)
    df = df.dropna(subset=["bias_estimate"]).copy()
    df["forecast_corrected"] = df["forecast"] - df["bias_estimate"]
    df["error_corrected"] = df["forecast_corrected"] - df["actual"]
    df["abs_error_corrected"] = df["error_corrected"].abs()
    return df.drop(columns="day").reset_index(drop=True)
 
 
def evaluate_bias_correction(corrected: pd.DataFrame) -> dict:
    """Raw vs corrected metrics over exactly the same hours."""
    fixed = corrected.assign(
        error=corrected["error_corrected"], abs_error=corrected["abs_error_corrected"]
    )
    return {
        "days_evaluated": int(corrected["startTime"].dt.normalize().nunique()),
        "raw": error_metrics(corrected),
        "corrected": error_metrics(fixed),
    }