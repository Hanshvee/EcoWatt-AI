"""Persistence and seasonal-naive baselines for half-hourly intensity."""

from __future__ import annotations

import numpy as np
import pandas as pd


def persistence_forecast(frame: pd.DataFrame) -> np.ndarray:
    """Next period equals the previous completed actual (lag_1)."""
    return frame["lag_1"].to_numpy(dtype=float)


def seasonal_naive_forecast(frame: pd.DataFrame) -> np.ndarray:
    """Same half-hour yesterday (lag_48)."""
    return frame["lag_48"].to_numpy(dtype=float)


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
