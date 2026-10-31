import numpy as np
import pandas as pd
import pytest
 
from app.services.forecast import (
    compare,
    error_metrics,
    hourly_actuals,
    select_latest_forecast,
)
 
 
def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")
 
 
def make_forecasts(rows):
    return pd.DataFrame(
        [{"publishTime": ts(p), "startTime": ts(s), "generation": g} for p, s, g in rows]
    )
 
 
def test_picks_latest_publication_before_cutoff():
    fc = make_forecasts([
        ("2026-01-09 02:30", "2026-01-10 12:00", 100),
        ("2026-01-09 07:30", "2026-01-10 12:00", 200),  # the last one before 09:00
        ("2026-01-09 09:30", "2026-01-10 12:00", 300),  # posterior al corte
    ])
    out = select_latest_forecast(fc, cutoff_hour=9)
    assert len(out) == 1
    assert out.loc[0, "forecast"] == 200
    assert out.loc[0, "publishTime"] == ts("2026-01-09 07:30")
 
 
def test_cutoff_is_inclusive():
    fc = make_forecasts([("2026-01-09 09:00", "2026-01-10 00:00", 50)])
    assert len(select_latest_forecast(fc, cutoff_hour=9)) == 1
 
 
def test_target_with_only_late_forecast_is_dropped():
    fc = make_forecasts([("2026-01-09 09:30", "2026-01-10 00:00", 50)])
    assert select_latest_forecast(fc, cutoff_hour=9).empty
 
 
def test_later_cutoff_selects_later_publication():
    fc = make_forecasts([
        ("2026-01-09 07:30", "2026-01-10 12:00", 200),
        ("2026-01-09 09:30", "2026-01-10 12:00", 300),
    ])
    assert select_latest_forecast(fc, cutoff_hour=10).loc[0, "forecast"] == 300
 
 
def test_start_end_filter_and_horizon():
    fc = make_forecasts([
        ("2026-01-09 07:30", "2026-01-10 12:00", 1),
        ("2026-01-10 07:30", "2026-01-11 12:00", 2),
    ])
    out = select_latest_forecast(
        fc, start=ts("2026-01-11"), end=ts("2026-01-12")
    )
    assert list(out["forecast"]) == [2]
    assert out.loc[0, "horizon_h"] == pytest.approx(28.5)
 
 
def test_hourly_actuals_average_and_incomplete_hour():
    act = pd.DataFrame({
        "startTime": [ts("2026-01-01 00:00"), ts("2026-01-01 00:30"), ts("2026-01-01 01:00")],
        "generation": [100, 200, 300],
    })
    out = hourly_actuals(act).set_index("startTime")["actual"]
    assert out[ts("2026-01-01 00:00")] == 150
    assert np.isnan(out[ts("2026-01-01 01:00")])  # It only includes a 30-minute period.
 
 
def test_error_metrics_known_values():
    df = pd.DataFrame({"forecast": [110, 90, 120, 80], "actual": [100, 100, 100, 100]})
    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()
    m = error_metrics(df)
    assert m["n"] == 4
    assert m["mae"] == pytest.approx(15)
    assert m["rmse"] == pytest.approx(np.sqrt(250))
    assert m["bias"] == pytest.approx(0)
    assert m["mape_pct"] == pytest.approx(15)
 
 
def test_mape_ignores_zero_actuals():
    df = pd.DataFrame({"forecast": [10, 50], "actual": [0, 100]})
    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()
    assert error_metrics(df)["mape_pct"] == pytest.approx(50)
 
 
def test_compare_inner_join_and_error_sign():
    sel = pd.DataFrame({
        "startTime": [ts("2026-01-01 00:00")],
        "publishTime": [ts("2025-12-31 07:30")],
        "forecast": [120.0],
        "horizon_h": [16.5],
    })
    act = pd.DataFrame({"startTime": [ts("2026-01-01 00:00")], "actual": [100.0]})
    out = compare(sel, act)
    assert out.loc[0, "error"] == 20  # made an overly optimistic forecast