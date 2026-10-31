import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
 
from app.data import Dataset, get_dataset
from app.main import app
from app.services.forecast import (
    apply_bias_correction,
    daily_mean_error,
    estimate_bias,
    evaluate_bias_correction,
    hourly_actuals,
)
 
 
def ts(s):
    return pd.Timestamp(s, tz="UTC")
 
 
def daily_series(values, start="2026-01-01"):
    idx = pd.date_range(start, periods=len(values), freq="D", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)
 
 
def make_compared(days, error=100.0, start="2026-01-01"):
    hours = pd.date_range(start, periods=24 * days, freq="h", tz="UTC")
    return pd.DataFrame({
        "startTime": hours,
        "forecast": 1000.0 + error,
        "actual": 1000.0,
        "error": error,
        "abs_error": abs(error),
    })
 
 
# --- estimate_bias ---------------------------------------------------------
 
def test_estimate_uses_exactly_days_d_minus_8_to_d_minus_2():
    daily = daily_series([100 + i for i in range(12)])  # day i has error 100 + i
    day10 = daily.index[10]
    # window = days 2..8 -> values 102..108 -> mean 105
    assert estimate_bias(daily, day10) == pytest.approx(105)
 
 
def test_estimate_never_uses_the_future():
    daily = daily_series([100 + i for i in range(12)])
    day10 = daily.index[10]
    baseline = estimate_bias(daily, day10)
    tampered = daily.copy()
    tampered.iloc[9:] = 1_000_000  # D-1, D and later: unknown at decision time
    assert estimate_bias(tampered, day10) == baseline
 
 
def test_estimate_is_none_without_complete_history():
    daily = daily_series([100.0] * 12)
    assert estimate_bias(daily, daily.index[5]) is None  # needs days -3 .. 3
    missing = daily.copy()
    missing.iloc[4] = np.nan  # a hole inside the window of day 10
    assert estimate_bias(missing, daily.index[10]) is None
 
 
def test_estimate_respects_custom_window():
    daily = daily_series([100 + i for i in range(12)])
    # window_days=3, lag 2 for day 10 -> days 6..8 -> 106, 107, 108
    assert estimate_bias(daily, daily.index[10], window_days=3) == pytest.approx(107)
 
 
# --- daily_mean_error ------------------------------------------------------
 
def test_daily_mean_error_ignores_partial_days():
    full = make_compared(1, error=50.0)
    partial = make_compared(1, error=999.0, start="2026-01-02").iloc[:10]
    out = daily_mean_error(pd.concat([full, partial]))
    assert out[ts("2026-01-01")] == 50
    assert np.isnan(out[ts("2026-01-02")])
 
 
# --- apply / evaluate ------------------------------------------------------
 
def test_correction_removes_constant_bias_and_drops_days_without_history():
    corrected = apply_bias_correction(make_compared(12, error=100.0))
    # delivery day 8 (Jan 9) is the first with a full window: D-8 = Jan 1
    assert corrected["startTime"].dt.normalize().nunique() == 4
    assert corrected["startTime"].min() == ts("2026-01-09")
    assert np.allclose(corrected["error_corrected"], 0)
    assert np.allclose(corrected["forecast_corrected"], 1000)
 
 
def test_evaluate_reports_raw_and_corrected_on_same_hours():
    result = evaluate_bias_correction(apply_bias_correction(make_compared(12, error=100.0)))
    assert result["days_evaluated"] == 4
    assert result["raw"]["n"] == result["corrected"]["n"] == 96
    assert result["raw"]["mae"] == pytest.approx(100)
    assert result["corrected"]["mae"] == pytest.approx(0)
 
 
def test_evaluate_with_no_history_is_empty():
    result = evaluate_bias_correction(apply_bias_correction(make_compared(5)))
    assert result["days_evaluated"] == 0
    assert result["raw"] == {"n": 0}
 
 
# --- API -------------------------------------------------------------------
 
@pytest.fixture
def client():
    hours = pd.date_range("2026-01-01", periods=24 * 12, freq="h", tz="UTC")
    forecasts = pd.DataFrame({
        "publishTime": hours.normalize() - pd.Timedelta(hours=16, minutes=30),  # D-1 07:30
        "startTime": hours,
        "generation": 1100,
    })
    half = pd.date_range("2026-01-01", periods=48 * 12, freq="30min", tz="UTC")
    actuals = pd.DataFrame({"startTime": half, "generation": 1000})
    ds = Dataset(forecasts=forecasts, actuals_hourly=hourly_actuals(actuals))
    app.dependency_overrides[get_dataset] = lambda: ds
    yield TestClient(app)
    app.dependency_overrides.clear()
 
 
def test_api_bias_correction_summary(client):
    body = client.get("/api/accuracy/bias-correction").json()
    assert body["days_evaluated"] == 4
    assert body["window_days"] == 7 and body["lag_days"] == 2
    assert body["raw"]["mae"] == pytest.approx(100)
    assert body["corrected"]["mae"] == pytest.approx(0, abs=1e-9)
 
 
def test_api_corrected_forecast_for_a_day(client):
    body = client.get("/api/forecast/corrected", params={"delivery_date": "2026-01-10"}).json()
    assert body["bias_estimate"] == pytest.approx(100)
    assert len(body["points"]) == 24
    assert body["points"][0]["forecast"] == 1100
    assert body["points"][0]["forecast_corrected"] == pytest.approx(1000)
 
 
def test_api_corrected_forecast_needs_history(client):
    r = client.get("/api/forecast/corrected", params={"delivery_date": "2026-01-05"})
    assert r.status_code == 422
 
 
def test_api_corrected_timeseries(client):
    pts = client.get("/api/accuracy/bias-correction/timeseries").json()["points"]
    assert len(pts) == 96
    assert pts[0]["error_corrected"] == pytest.approx(0, abs=1e-9)
    assert pts[0]["startTime"].endswith("Z")
 
 
def test_api_rejects_invalid_window(client):
    assert client.get("/api/accuracy/bias-correction", params={"window_days": 0}).status_code == 422
    assert client.get("/api/accuracy/bias-correction", params={"window_days": 99}).status_code == 422