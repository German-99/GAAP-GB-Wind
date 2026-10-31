"""Central configuration (can be overridden with environment variables)."""
import os
from pathlib import Path
 
import pandas as pd
 
DATA_DIR = Path(os.getenv("DATA_DIR", "data/raw"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
 
# Delivery days whose decisions are made in January 2026: 2 Jan to 1 Feb (end exclusive).
WINDOW_START = pd.Timestamp("2026-01-02", tz="UTC")
WINDOW_END = pd.Timestamp("2026-02-02", tz="UTC")
# The error history for the bias correction starts with the first day of actuals.
HISTORY_START = pd.Timestamp("2026-01-01", tz="UTC")
 
# Cutoff hours (UTC, previous day) just after each observed publication.
SENSITIVITY_HOURS = [3.0, 5.0, 8.0, 10.0, 12.0, 13.0, 16.0, 19.0, 23.0]