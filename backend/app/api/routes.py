"""API endpoints."""
import json
from datetime import date
from typing import Annotated
 
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
 
from app.config import HISTORY_START, SENSITIVITY_HOURS, WINDOW_END, WINDOW_START
from app.data import Dataset, get_dataset
from app.services.forecast import (
    DEFAULT_BIAS_LAG_DAYS,
    DEFAULT_BIAS_WINDOW_DAYS,
    DEFAULT_CUTOFF_HOUR,
    apply_bias_correction,
    compare,
    daily_mean_error,
    error_metrics,
    estimate_bias,
    evaluate_bias_correction,
    select_latest_forecast,
)
 
router = APIRouter(prefix="/api")
 
CutoffHour = Annotated[
    float,
    Query(ge=0, le=24, description="Cutoff hour (UTC) of the day before delivery"),
]
WindowDays = Annotated[
    int,
    Query(ge=1, le=28, description="Days of past errors used to estimate the bias"),
]
 
 
def to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> list of JSON-safe dicts (ISO dates, NaN -> null)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))
 
 
def _history_comparison(ds: Dataset, cutoff_hour: float) -> pd.DataFrame:
    """Forecast vs actual from the first day of actuals (history for the correction)."""
    selected = select_latest_forecast(
        ds.forecasts, cutoff_hour, start=HISTORY_START, end=WINDOW_END
    )
    return compare(selected, ds.actuals_hourly)
 
 
def _corrected_window(ds: Dataset, cutoff_hour: float, window_days: int) -> pd.DataFrame:
    corrected = apply_bias_correction(
        _history_comparison(ds, cutoff_hour), window_days, DEFAULT_BIAS_LAG_DAYS
    )
    return corrected[
        (corrected["startTime"] >= WINDOW_START) & (corrected["startTime"] < WINDOW_END)
    ]
 
 
def _window_selection(ds: Dataset, cutoff_hour: float) -> pd.DataFrame:
    return select_latest_forecast(
        ds.forecasts, cutoff_hour, start=WINDOW_START, end=WINDOW_END
    )
 
 
@router.get("/forecast/latest")
def latest_forecast(
    delivery_date: date,
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
    ds: Dataset = Depends(get_dataset),
):
    """Latest forecast (and the actual, if it exists) of each hour of a delivery day."""
    day = pd.Timestamp(delivery_date, tz="UTC")
    selected = select_latest_forecast(
        ds.forecasts, cutoff_hour, start=day, end=day + pd.Timedelta(days=1)
    )
    if selected.empty:
        raise HTTPException(404, "No forecast available at the cutoff for that day")
    points = selected.merge(ds.actuals_hourly, on="startTime", how="left")
    cutoff_time = day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    return {
        "delivery_date": delivery_date.isoformat(),
        "cutoff_hour": cutoff_hour,
        "cutoff_time": cutoff_time.isoformat(),
        "points": to_records(points),
    }
 
 
@router.get("/forecast/corrected")
def corrected_forecast(
    delivery_date: date,
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
    window_days: WindowDays = DEFAULT_BIAS_WINDOW_DAYS,
    ds: Dataset = Depends(get_dataset),
):
    """Latest forecast of a delivery day minus the bias learned from past days.
 
    Only errors known at decision time are used (see `estimate_bias`).
    """
    day = pd.Timestamp(delivery_date, tz="UTC")
    selected = select_latest_forecast(
        ds.forecasts, cutoff_hour, start=day, end=day + pd.Timedelta(days=1)
    )
    if selected.empty:
        raise HTTPException(404, "No forecast available at the cutoff for that day")
    bias = estimate_bias(
        daily_mean_error(_history_comparison(ds, cutoff_hour)),
        day,
        window_days,
        DEFAULT_BIAS_LAG_DAYS,
    )
    if bias is None:
        raise HTTPException(
            422, f"Not enough error history ({window_days} full days) before that day"
        )
    points = selected.merge(ds.actuals_hourly, on="startTime", how="left")
    points["bias_estimate"] = bias
    points["forecast_corrected"] = points["forecast"] - bias
    return {
        "delivery_date": delivery_date.isoformat(),
        "cutoff_hour": cutoff_hour,
        "window_days": window_days,
        "lag_days": DEFAULT_BIAS_LAG_DAYS,
        "bias_estimate": bias,
        "points": to_records(points),
    }
 
 
@router.get("/accuracy/summary")
def accuracy_summary(
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
    ds: Dataset = Depends(get_dataset),
):
    """Error metrics for the whole of January with the given cutoff."""
    cmp = compare(_window_selection(ds, cutoff_hour), ds.actuals_hourly)
    return {
        "cutoff_hour": cutoff_hour,
        "window": {"start": WINDOW_START.isoformat(), "end": WINDOW_END.isoformat()},
        "metrics": error_metrics(cmp),
    }
 
 
@router.get("/accuracy/timeseries")
def accuracy_timeseries(
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
    ds: Dataset = Depends(get_dataset),
):
    """Hourly forecast vs actual and error, for charts."""
    cmp = compare(_window_selection(ds, cutoff_hour), ds.actuals_hourly)
    cols = ["startTime", "publishTime", "forecast", "actual", "error", "horizon_h"]
    return {"cutoff_hour": cutoff_hour, "points": to_records(cmp[cols])}
 
 
@router.get("/accuracy/cutoff-sensitivity")
def cutoff_sensitivity(
    hours: Annotated[list[float] | None, Query()] = None,
    ds: Dataset = Depends(get_dataset),
):
    """How the error changes with the cutoff hour (i.e. which publication is used)."""
    results = []
    for h in hours or SENSITIVITY_HOURS:
        cmp = compare(_window_selection(ds, h), ds.actuals_hourly)
        results.append({"cutoff_hour": h, "metrics": error_metrics(cmp)})
    return {"results": results}
 
 
@router.get("/accuracy/bias-correction")
def bias_correction_summary(
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
    window_days: WindowDays = DEFAULT_BIAS_WINDOW_DAYS,
    ds: Dataset = Depends(get_dataset),
):
    """Raw vs bias-corrected metrics over the days with a complete history window."""
    corrected = _corrected_window(ds, cutoff_hour, window_days)
    return {
        "cutoff_hour": cutoff_hour,
        "window_days": window_days,
        "lag_days": DEFAULT_BIAS_LAG_DAYS,
        **evaluate_bias_correction(corrected),
    }
 
 
@router.get("/accuracy/bias-correction/timeseries")
def bias_correction_timeseries(
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
    window_days: WindowDays = DEFAULT_BIAS_WINDOW_DAYS,
    ds: Dataset = Depends(get_dataset),
):
    """Hourly raw and corrected forecast vs actual, for charts."""
    corrected = _corrected_window(ds, cutoff_hour, window_days)
    cols = [
        "startTime", "forecast", "forecast_corrected", "actual",
        "error", "error_corrected", "bias_estimate",
    ]
    return {"cutoff_hour": cutoff_hour, "window_days": window_days,
            "points": to_records(corrected[cols])}