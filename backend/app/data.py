"""Data loading: Parquet files are read only once and then reused."""
from dataclasses import dataclass
from functools import lru_cache
 
import pandas as pd
 
from app.config import DATA_DIR
from app.services.forecast import hourly_actuals
 
 
@dataclass(frozen=True)
class Dataset:
    forecasts: pd.DataFrame      # publishTime, startTime, generation
    actuals_hourly: pd.DataFrame  # startTime, current (hourly average)
 
 
@lru_cache(maxsize=1)
def load_dataset() -> Dataset:
    forecasts = pd.read_parquet(DATA_DIR / "forecasts.parquet").drop_duplicates(
        ["publishTime", "startTime"]
    )
    actuals = pd.read_parquet(DATA_DIR / "actuals.parquet")
    return Dataset(forecasts=forecasts, actuals_hourly=hourly_actuals(actuals))
 
 
def get_dataset() -> Dataset:
    """FastAPI dependency (overridden by tests with synthetic data)."""
    return load_dataset()