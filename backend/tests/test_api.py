import pandas as pd
import pytest
from fastapi.testclient import TestClient
 
from app.data import Dataset, get_dataset
from app.main import app
from app.services.forecast import hourly_actuals
 
 
def ts(s):
    return pd.Timestamp(s, tz="UTC")
 
 
@pytest.fixture
def client():
    hours = pd.date_range("2026-01-05", periods=24, freq="h", tz="UTC")
    forecasts = pd.concat([
        pd.DataFrame({"publishTime": ts("2026-01-04 07:30"), "startTime": hours, "generation": 100}),
        pd.DataFrame({"publishTime": ts("2026-01-04 09:30"), "startTime": hours, "generation": 999}),
    ])
    half_hours = pd.date_range("2026-01-05", periods=48, freq="30min", tz="UTC")
    actuals = pd.DataFrame({"startTime": half_hours, "generation": 110})
    ds = Dataset(forecasts=forecasts, actuals_hourly=hourly_actuals(actuals))
    app.dependency_overrides[get_dataset] = lambda: ds
    yield TestClient(app)
    app.dependency_overrides.clear()
 
 
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
 
 
def test_latest_forecast_uses_publication_before_cutoff(client):
    r = client.get("/api/forecast/latest", params={"delivery_date": "2026-01-05"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) == 24
    assert {p["forecast"] for p in body["points"]} == {100}
    assert body["points"][0]["actual"] == 110
    assert body["cutoff_time"].startswith("2026-01-04T09:00:00")
 
 
def test_later_cutoff_changes_selected_forecast(client):
    r = client.get(
        "/api/forecast/latest", params={"delivery_date": "2026-01-05", "cutoff_hour": 10}
    )
    assert {p["forecast"] for p in r.json()["points"]} == {999}
 
 
def test_latest_forecast_404_when_nothing_available(client):
    r = client.get("/api/forecast/latest", params={"delivery_date": "2026-01-20"})
    assert r.status_code == 404
 
 
def test_invalid_cutoff_is_rejected(client):
    r = client.get("/api/accuracy/summary", params={"cutoff_hour": 30})
    assert r.status_code == 422
 
 
def test_summary_metrics(client):
    m = client.get("/api/accuracy/summary").json()["metrics"]
    assert m["n"] == 24
    assert m["bias"] == pytest.approx(-10)
    assert m["mae"] == pytest.approx(10)
 
 
def test_timeseries_has_no_nan_and_iso_dates(client):
    pts = client.get("/api/accuracy/timeseries").json()["points"]
    assert len(pts) == 24
    assert pts[0]["startTime"].endswith("Z")
    assert pts[0]["error"] == -10
 
 
def test_cutoff_sensitivity(client):
    r = client.get("/api/accuracy/cutoff-sensitivity", params=[("hours", 9), ("hours", 10)])
    by_hour = {x["cutoff_hour"]: x["metrics"] for x in r.json()["results"]}
    assert by_hour[9.0]["bias"] == pytest.approx(-10)
    assert by_hour[10.0]["bias"] == pytest.approx(889)