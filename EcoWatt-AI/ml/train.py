"""Train an XGBoost regressor on NESO national estimated actuals.

The target is Great Britain national average carbon intensity (gCO2/kWh),
not marginal emissions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from ml.baselines import mae, persistence_forecast, rmse, seasonal_naive_forecast
from ml.features import FEATURE_COLUMNS, assert_no_target_leakage, build_feature_table, split_xy
from ml.paths import (
    ARTIFACTS_DIR,
    CLEANED_CSV,
    DATA_SOURCE,
    FEATURE_COLUMNS_PATH,
    FEATURE_CSV,
    METADATA_PATH,
    MODEL_PATH,
    MODELS_DIR,
    PROCESSED_DIR,
    REGION,
    TARGET_COLUMN,
    UNITS,
)

VAL_DAYS = 14
TEST_DAYS = 14
RANDOM_SEED = 42


class TrainingError(RuntimeError):
    pass


def load_cleaned_dataset(path: Path = CLEANED_CSV) -> pd.DataFrame:
    if not path.exists():
        raise TrainingError(
            f"Cleaned dataset not found at {path}. Run `python -m ml.acquire` first. "
            "The trainer will not invent observations."
        )
    frame = pd.read_csv(path)
    if frame.empty:
        raise TrainingError("Cleaned dataset is empty.")
    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["end_time"] = pd.to_datetime(frame["end_time"], utc=True)
    return frame.sort_values("start_time").reset_index(drop=True)


def chronological_splits(
    frame: pd.DataFrame,
    *,
    val_days: int = VAL_DAYS,
    test_days: int = TEST_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if "start_time" not in frame.columns:
        raise TrainingError("Feature table is missing start_time.")

    ordered = frame.sort_values("start_time").reset_index(drop=True)
    last_start = ordered["start_time"].max()
    test_start = last_start - pd.Timedelta(days=test_days)
    val_start = test_start - pd.Timedelta(days=val_days)

    train = ordered.loc[ordered["start_time"] < val_start].copy()
    val = ordered.loc[(ordered["start_time"] >= val_start) & (ordered["start_time"] < test_start)].copy()
    test = ordered.loc[ordered["start_time"] >= test_start].copy()

    if train.empty or val.empty or test.empty:
        raise TrainingError(
            "Chronological split produced an empty set. Fetch a longer history window."
        )
    if train["start_time"].max() >= val["start_time"].min():
        raise TrainingError("Train/validation times overlap.")
    if val["start_time"].max() >= test["start_time"].min():
        raise TrainingError("Validation/test times overlap.")
    return train, val, test


def fit_xgboost(train: pd.DataFrame, val: pd.DataFrame) -> xgb.XGBRegressor:
    x_train, y_train = split_xy(train)
    x_val, y_val = split_xy(val)
    assert_no_target_leakage(x_train)

    model = xgb.XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=4,
        objective="reg:squarederror",
        tree_method="hist",
        n_jobs=1,
        random_state=RANDOM_SEED,
        early_stopping_rounds=30,
    )
    model.fit(
        x_train,
        y_train,
        eval_set=[(x_val, y_val)],
        verbose=False,
    )
    return model


def predict(model: xgb.XGBRegressor, frame: pd.DataFrame) -> np.ndarray:
    features, _ = split_xy(frame)
    assert_no_target_leakage(features)
    return np.asarray(model.predict(features), dtype=float)


def evaluate_split(name: str, frame: pd.DataFrame, model: xgb.XGBRegressor) -> dict[str, Any]:
    y_true = frame[TARGET_COLUMN].to_numpy(dtype=float)
    y_model = predict(model, frame)
    y_persist = persistence_forecast(frame)
    y_seasonal = seasonal_naive_forecast(frame)
    return {
        "split": name,
        "rows": int(len(frame)),
        "start_time": frame["start_time"].min().isoformat(),
        "end_time": frame["start_time"].max().isoformat(),
        "model": {"mae": mae(y_true, y_model), "rmse": rmse(y_true, y_model)},
        "baseline_persistence": {"mae": mae(y_true, y_persist), "rmse": rmse(y_true, y_persist)},
        "baseline_seasonal_naive": {"mae": mae(y_true, y_seasonal), "rmse": rmse(y_true, y_seasonal)},
    }


def save_artifacts(
    model: xgb.XGBRegressor,
    featured: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    model.save_model(MODEL_PATH)
    FEATURE_COLUMNS_PATH.write_text(json.dumps(FEATURE_COLUMNS, indent=2), encoding="utf-8")
    featured.to_csv(FEATURE_CSV, index=False)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def train() -> dict[str, Any]:
    cleaned = load_cleaned_dataset()
    featured = build_feature_table(cleaned)
    train_df, val_df, test_df = chronological_splits(featured)
    model = fit_xgboost(train_df, val_df)

    evaluation = {
        "train": evaluate_split("train", train_df, model),
        "validation": evaluate_split("validation", val_df, model),
        "test": evaluate_split("test", test_df, model),
    }

    metadata = {
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "target": TARGET_COLUMN,
        "units": UNITS,
        "region": REGION,
        "data_source": DATA_SOURCE,
        "quantity": "Great Britain national average electricity carbon intensity",
        "not_estimated": "This is not a marginal-emissions model.",
        "prediction_horizon": "1 half-hour period, using only past actuals plus calendar features",
        "feature_columns": FEATURE_COLUMNS,
        "lags": [1, 2, 48, 336],
        "cleaned_rows": int(len(cleaned)),
        "featured_rows": int(len(featured)),
        "data_start_utc": cleaned["start_time"].min().isoformat(),
        "data_end_utc": cleaned["start_time"].max().isoformat(),
        "splits": {
            "train_rows": int(len(train_df)),
            "validation_rows": int(len(val_df)),
            "test_rows": int(len(test_df)),
        },
        "evaluation": evaluation,
        "best_iteration": int(getattr(model, "best_iteration", 0) or 0),
        "model_path": str(MODEL_PATH),
        "notes": (
            "Rows with missing intensity.actual were dropped. "
            "Official forecast values were not used as features."
        ),
    }
    save_artifacts(model, featured, metadata)

    test_metrics = evaluation["test"]
    print(f"Observations (cleaned): {len(cleaned)}")
    print(f"Range: {metadata['data_start_utc']} to {metadata['data_end_utc']}")
    print(
        "Splits: "
        f"train={len(train_df)} val={len(val_df)} test={len(test_df)}"
    )
    print(
        "Test MAE/RMSE model: "
        f"{test_metrics['model']['mae']:.3f} / {test_metrics['model']['rmse']:.3f}"
    )
    print(
        "Test MAE/RMSE seasonal-naive: "
        f"{test_metrics['baseline_seasonal_naive']['mae']:.3f} / "
        f"{test_metrics['baseline_seasonal_naive']['rmse']:.3f}"
    )
    print(f"Metadata: {METADATA_PATH}")
    return metadata


if __name__ == "__main__":
    train()
