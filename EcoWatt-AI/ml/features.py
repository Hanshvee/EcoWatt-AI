"""Leakage-safe features for 1-step-ahead national intensity prediction.

Prediction task
---------------
At the start of half-hour period t we predict the NESO estimated actual
national average intensity for that same period (gCO2/kWh).

Known at prediction time
- Calendar fields of period t (hour, weekday, month).
- Estimated actuals from earlier completed periods only.

Not used
- actual[t] or any later actual.
- Official NESO forecast[t] (kept in the cleaned file as metadata only).

Lags are joined on exact UTC timestamps, not CSV row position:
- lag_1: start_time - 30 minutes
- lag_2: start_time - 60 minutes
- lag_48: start_time - 24 hours
- lag_336: start_time - 7 days

If a required historical timestamp is absent, that lag is left missing.
Rows with any missing lag are dropped. Earlier available rows are never
used as a substitute.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.paths import TARGET_COLUMN

LAGS = (1, 2, 48, 336)
PERIOD = pd.Timedelta(minutes=30)
FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "month",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
    "lag_1",
    "lag_2",
    "lag_48",
    "lag_336",
]


def add_calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    start = pd.to_datetime(out["start_time"], utc=True)
    out["hour"] = start.dt.hour
    out["day_of_week"] = start.dt.day_of_week
    out["month"] = start.dt.month
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24)
    out["dow_sin"] = np.sin(2 * np.pi * out["day_of_week"] / 7)
    out["dow_cos"] = np.cos(2 * np.pi * out["day_of_week"] / 7)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)
    return out


def add_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["start_time"] = pd.to_datetime(out["start_time"], utc=True)
    out = out.sort_values("start_time")
    if not out["start_time"].is_unique:
        raise ValueError("Lag features require unique start_time values.")

    lookup = out.set_index("start_time")[TARGET_COLUMN]
    for lag in LAGS:
        historical_time = out["start_time"] - (lag * PERIOD)
        out[f"lag_{lag}"] = historical_time.map(lookup)
    return out


def build_feature_table(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"start_time", TARGET_COLUMN}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Feature table is missing columns: {sorted(missing)}")

    featured = add_calendar_features(frame)
    featured = add_lag_features(featured)
    featured = featured.dropna(subset=[f"lag_{lag}" for lag in LAGS]).reset_index(drop=True)
    return featured


def split_xy(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    return frame.loc[:, FEATURE_COLUMNS], frame[TARGET_COLUMN]


def assert_no_target_leakage(feature_frame: pd.DataFrame) -> None:
    if TARGET_COLUMN in feature_frame.columns:
        raise ValueError("Target column leaked into model features.")
    unexpected = {"actual", "official_forecast_gco2_per_kwh"}
    leaked = unexpected.intersection(feature_frame.columns)
    if leaked:
        raise ValueError(f"Disallowed columns present in features: {sorted(leaked)}")
