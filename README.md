# Wind forecast accuracy for day-ahead buying

A web app for a UK energy utility's day-ahead buying team. It answers two questions about
national wind generation in Great Britain, using Elexon BMRS data for January 2026:

1. **What was the latest wind forecast available when the buying decision had to be made?**
2. **How accurate are those forecasts, in numbers?**

On top of that it shows how the error changes with the decision cutoff, and whether a simple
bias correction (using only information known at decision time) reduces the error.

- **Live app:** REPLACE-WITH-FRONTEND-URL
- **API docs:** REPLACE-WITH-BACKEND-URL/docs
- **Video demo:** REPLACE-WITH-YOUTUBE-URL

## How the analysis works

**Data** (Elexon BMRS, national level, wind only):

- Actuals: `FUELHH` with `fuelType = WIND` (30-minute resolution), averaged to hourly values.
- Forecasts: `WINDFOR` (hourly values, published several times a day).

**Forecast available at decision time.** For every target hour, the app picks the most recent
forecast published at or before the cutoff of the previous day. The cutoff is a parameter:
by default **09:00 UTC on the day before delivery** (UK time equals UTC in January). Without a
cutoff rule, "the latest forecast" would use information the buyer did not have.

**Error metrics.** Error = forecast − actual, so a positive error means the forecast was above
the actual generation. Reported: MAE, RMSE, bias, MAPE (only where the actual is not zero),
percentiles of the absolute error (P50/P90/P95) and the 5th/95th percentiles of the signed
error, which show the under- and over-forecast tails separately.

**Bias correction.** The forecast of delivery day D is shifted by the mean error of the days
D-8 … D-2 (7 days by default). Actuals of D-1 are not known yet at the cutoff, so the window
never uses them. Days without a complete window are left out of the comparison, so the
corrected and raw columns always cover the same hours (24 of the 31 days with the defaults).

### Main findings (January 2026, cutoff 09:00 UTC)

- The forecast is above the actual on average: bias of about **+1.7 GW** (about 15 % of the
  mean actual generation), positive on 27 of the 31 delivery days, but very variable from day
  to day.
- Waiting for a more recent publication helps only a little between the 03:00 and 10:00
  cutoffs (about 3 % lower MAE).
- Over the 24 days with a full 7-day history, the bias correction lowers MAE from about
  **2,083 to 1,625 MW (−22 %)** and the 95th percentile of the absolute error from about
  5,430 to 4,185 MW.
- The correction shrinks the over-forecast tail but enlarges the under-forecast tail (5th
  percentile of the error goes from about −1,080 to −2,760 MW), so both tails are shown.

### Limitations

- The data is a **snapshot** of one month (January 2026), downloaded once and stored in the
  repo, not a live connection to Elexon.
- The default cutoff (09:00 UTC) is an assumption. The real day-ahead market deadline was not
  verified, so the cutoff is adjustable. Later cutoffs only help if they fall before the
  decision deadline.
- The cause of the persistent over-forecast was **not established** with the information in
  these two datasets (for example, whether both series cover exactly the same wind
  generation). The correction reduces the effect; it does not explain it.
- One month of data is not enough to claim the correction works in other seasons.

## Project structure

```
.
├── docker-compose.yml            Runs backend + frontend together
├── backend/                      Python (FastAPI)
│   ├── Dockerfile
│   ├── index.py                  Vercel entrypoint (exposes the FastAPI app)
│   ├── requirements.txt          Runtime dependencies
│   ├── requirements-dev.txt      + pytest, httpx, requests
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py               Creates the FastAPI app (CORS, routes, /health)
│   │   ├── config.py             Paths, analysis window, settings
│   │   ├── data.py               Loads the parquet files once
│   │   ├── api/routes.py         HTTP endpoints
│   │   └── services/forecast.py  Core logic: forecast selection, metrics, bias correction
│   ├── data/raw/                 Elexon snapshot: actuals.parquet, forecasts.parquet
│   ├── scripts/
│   │   ├── fetch_data.py         Downloads the data from Elexon
│   │   ├── explore.py            Data checks (duplicates, horizon, coverage)
│   │   └── analyze_bias.py       Bias diagnostics
│   └── tests/                    30 tests (logic and API)
└── frontend/                     React + Vite + Recharts
    ├── Dockerfile                Builds the app and serves it with nginx
    ├── nginx.conf                Serves the files and proxies /api to the backend
    ├── vercel.json               Rewrites /api to the deployed backend
    ├── package.json
    ├── vite.config.js            React plugin and dev proxy to the backend
    ├── index.html
    └── src/
        ├── main.jsx, App.jsx     Entry point and page layout
        ├── api.js, hooks.js      API client and data-fetching hook
        ├── format.js             Number and date formatting
        ├── chartTheme.js         Chart colors and shared chart props
        ├── styles.css
        └── components/           Accuracy, DeliveryDay, BiasCorrection, CutoffSensitivity,
                                  Section, Status, WindowDaysInput
```

## Run it

### With Docker (recommended)

```bash
docker compose up --build
```

- App: http://localhost:8080
- API and interactive docs: http://localhost:8000/docs

Stop it with `Ctrl + C` and `docker compose down`.

### Without Docker

Backend (Python 3.12 or newer):

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1      macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Frontend (Node 20 or newer), in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. In development Vite proxies `/api` to http://localhost:8000.

### Tests

```bash
cd backend
python -m pytest -q
```

They cover the selection of the forecast at the cutoff (including boundary cases), hourly
aggregation, the metrics, the bias correction (including a test that it never uses
information from after the decision time) and the API endpoints.

### Refresh the data

```bash
cd backend
python scripts/fetch_data.py
```

Downloads January 2026 from Elexon and rewrites `data/raw/*.parquet`. To analyse another
period, change the date constants at the top of the script and the window in `app/config.py`.

## API

| Endpoint | Description |
|---|---|
| `GET /api/forecast/latest?delivery_date=&cutoff_hour=` | Forecast available at the cutoff for each hour of a delivery day, with the actual when it exists |
| `GET /api/forecast/corrected?delivery_date=&cutoff_hour=&window_days=` | The same, with the bias-corrected forecast and the estimated bias |
| `GET /api/accuracy/summary?cutoff_hour=` | Error metrics for the whole of January |
| `GET /api/accuracy/timeseries?cutoff_hour=` | Hourly forecast, actual and error |
| `GET /api/accuracy/cutoff-sensitivity` | Metrics for different cutoff hours |
| `GET /api/accuracy/bias-correction?cutoff_hour=&window_days=` | Raw vs corrected metrics |
| `GET /api/accuracy/bias-correction/timeseries` | Hourly raw and corrected forecast vs actual |
| `GET /health` | Health check |

`cutoff_hour` is the UTC hour of the day before delivery (0 to 24). `window_days` is 1 to 28.

## Deployment (Vercel)

The repo is deployed as two Vercel projects, both importing this repository:

1. **Backend:** Root Directory `backend`. Vercel detects the FastAPI app through `index.py`.
2. **Frontend:** Root Directory `frontend`. `vercel.json` rewrites `/api/*` to the backend
   URL, mirroring what nginx does in Docker, so the frontend code is identical in every
   environment.

## AI assistance

This project was built with the help of **Claude (Anthropic)**, used as a coding assistant for
architecture discussions, code and test generation, debugging and documentation.