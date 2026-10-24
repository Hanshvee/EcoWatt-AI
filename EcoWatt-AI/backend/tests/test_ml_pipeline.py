from datetime import datetime, timedelta, timezone

import httpx
import numpy as np
import pandas as pd
import pytest

from ml.acquire import (
    AcquisitionError,
    clean_observations,
    download_history,
    iter_request_windows,
    parse_national_payload,
    parse_national_period,
)
from ml.features import FEATURE_COLUMNS, PERIOD, add_lag_features, assert_no_target_leakage, build_feature_table, split_xy
from ml.paths import CLEANED_CSV, TARGET_COLUMN
from ml.timeutils import format_api_datetime, parse_utc_datetime
from ml.train import chronological_splits, fit_xgboost, predict

UTC = timezone.utc


def official_period(start: datetime, actual, forecast=None) -> dict:
    end = start + timedelta(minutes=30)
    return {
        "from": start.strftime("%Y-%m-%dT%H:%MZ"),
        "to": end.strftime("%Y-%m-%dT%H:%MZ"),
        "intensity": {"forecast": forecast, "actual": actual, "index": "moderate"},
    }


def test_parse_utc_and_official_path_format() -> None:
    moment = datetime(2018, 1, 20, 12, 0, tzinfo=UTC)
    assert format_api_datetime(moment) == "2018-01-20T12:00Z"
    parsed = parse_utc_datetime("2018-01-20T12:00Z")
    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)
    assert parsed == moment


def test_parse_official_national_schema() -> None:
    payload = {
        "data": [
            official_period(datetime(2018, 1, 20, 12, 0, tzinfo=UTC), actual=263, forecast=266)
        ]
    }
    rows = parse_national_payload(payload)
    assert len(rows) == 1
    assert rows[0]["actual_gco2_per_kwh"] == 263
    assert rows[0]["start_time"] == "2018-01-20T12:00:00+00:00"
    assert rows[0]["units"] == "gCO2/kWh"
    assert rows[0]["region"] == "GB"


def test_missing_actual_is_kept_null_then_dropped() -> None:
    start = datetime(2018, 1, 20, 12, 0, tzinfo=UTC)
    rows = [
        parse_national_period(official_period(start, actual=None, forecast=400)),
        parse_national_period(official_period(start + timedelta(minutes=30), actual=120)),
    ]
    cleaned = clean_observations(rows)
    assert len(cleaned) == 1
    assert cleaned.iloc[0][TARGET_COLUMN] == 120
    assert 400 not in set(cleaned[TARGET_COLUMN])


def test_duplicate_timestamps_keep_last() -> None:
    start = datetime(2018, 1, 20, 12, 0, tzinfo=UTC)
    first = parse_national_period(official_period(start, actual=10))
    second = parse_national_period(official_period(start, actual=22))
    cleaned = clean_observations([first, second])
    assert len(cleaned) == 1
    assert cleaned.iloc[0][TARGET_COLUMN] == 22


def test_non_30_minute_periods_are_dropped() -> None:
    row = parse_national_period(official_period(datetime(2018, 1, 20, 12, 0, tzinfo=UTC), actual=80))
    assert row is not None
    row["end_time"] = "2018-01-20T13:00:00+00:00"
    with pytest.raises(AcquisitionError, match="No estimated actual"):
        clean_observations([row])


def test_request_windows_respect_14_day_limit() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 10, tzinfo=UTC)
    windows = list(iter_request_windows(start, end, max_days=14))
    assert windows[0][0] == start
    assert all((stop - begin) <= timedelta(days=14) for begin, stop in windows)
    assert windows[-1][1] == end


def test_http_failure_does_not_invent_data() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    with pytest.raises(AcquisitionError, match="Could not reach"):
        download_history(
            lookback_days=14,
            end=datetime(2018, 2, 1, tzinfo=UTC),
            transport=httpx.MockTransport(handler),
        )


def test_unexpected_schema_raises() -> None:
    with pytest.raises(AcquisitionError, match="official national Intensity schema"):
        parse_national_payload({"unexpected": True})


def make_series(periods: int, start: datetime | None = None) -> pd.DataFrame:
    origin = start or datetime(2018, 1, 1, 0, 0, tzinfo=UTC)
    rows = []
    for index in range(periods):
        moment = origin + timedelta(minutes=30 * index)
        # Deterministic fixture for leakage/lag tests only. Not used to train
        # the reported NESO model.
        actual = 100 + index
        rows.append(
            {
                "start_time": moment,
                "end_time": moment + timedelta(minutes=30),
                TARGET_COLUMN: float(actual),
                "official_forecast_gco2_per_kwh": float(actual + 5),
                "region": "GB",
                "units": "gCO2/kWh",
            }
        )
    return pd.DataFrame(rows)


def expected_time_lag(frame: pd.DataFrame, start_times: pd.Series, lag: int) -> pd.Series:
    lookup = frame.set_index(pd.to_datetime(frame["start_time"], utc=True))[TARGET_COLUMN]
    historical = pd.to_datetime(start_times, utc=True) - (lag * PERIOD)
    return historical.map(lookup)


def test_lag_features_use_only_past_actuals() -> None:
    frame = make_series(10)
    lagged = add_lag_features(frame)
    assert lagged.loc[3, "lag_1"] == lagged.loc[2, TARGET_COLUMN]
    assert lagged.loc[3, "lag_2"] == lagged.loc[1, TARGET_COLUMN]
    assert lagged.loc[3, "lag_1"] != lagged.loc[3, TARGET_COLUMN]
    assert lagged.loc[3, "lag_1"] == expected_time_lag(frame, lagged.loc[[3], "start_time"], 1).iloc[0]


def test_no_future_data_in_model_features() -> None:
    source = make_series(400)
    featured = build_feature_table(source)
    x_features, y_target = split_xy(featured)
    assert_no_target_leakage(x_features)
    assert TARGET_COLUMN not in x_features.columns
    assert list(x_features.columns) == FEATURE_COLUMNS

    for offset, column in ((1, "lag_1"), (2, "lag_2"), (48, "lag_48"), (336, "lag_336")):
        expected = expected_time_lag(source, featured["start_time"], offset)
        assert featured[column].reset_index(drop=True).equals(expected.reset_index(drop=True))

    assert (featured["lag_1"] != featured[TARGET_COLUMN]).all()
    assert y_target.name == TARGET_COLUMN


def test_gappy_lags_do_not_use_previous_kept_row() -> None:
    frame = make_series(12)
    gap_idx = 4
    gappy = frame.drop(index=gap_idx).reset_index(drop=True)
    lagged = add_lag_features(gappy)

    gap_time = pd.Timestamp(frame.loc[gap_idx, "start_time"])
    next_time = gap_time + PERIOD
    previous_kept = frame.loc[gap_idx - 1, TARGET_COLUMN]
    next_row = lagged.loc[lagged["start_time"] == next_time].iloc[0]

    assert pd.isna(next_row["lag_1"])
    assert next_row["lag_1"] != previous_kept
    assert next_row["lag_2"] == previous_kept


def test_gappy_feature_table_drops_rows_with_missing_timestamps() -> None:
    frame = make_series(400)
    gap_idx = 350
    gappy = frame.drop(index=gap_idx).reset_index(drop=True)
    featured = build_feature_table(gappy)

    gap_time = pd.Timestamp(frame.loc[gap_idx, "start_time"])
    featured_starts = set(pd.to_datetime(featured["start_time"], utc=True))

    assert gap_time + PERIOD not in featured_starts
    assert gap_time + (2 * PERIOD) not in featured_starts
    assert gap_time + (3 * PERIOD) in featured_starts

    recovered = featured.loc[featured["start_time"] == gap_time + (3 * PERIOD)].iloc[0]
    assert recovered["lag_1"] == frame.loc[gap_idx + 2, TARGET_COLUMN]
    assert recovered["lag_2"] == frame.loc[gap_idx + 1, TARGET_COLUMN]
    assert recovered["lag_1"] != frame.loc[gap_idx - 1, TARGET_COLUMN]


def test_gapless_cleaned_dataset_keeps_expected_counts_and_time_lags() -> None:
    if not CLEANED_CSV.exists():
        pytest.skip("Cleaned NESO dataset is not present.")

    cleaned = pd.read_csv(CLEANED_CSV)
    cleaned["start_time"] = pd.to_datetime(cleaned["start_time"], utc=True)
    featured = build_feature_table(cleaned)

    assert len(cleaned) == 8641
    assert len(featured) == 8305
    assert featured["start_time"].min() == cleaned["start_time"].min() + (336 * PERIOD)

    expected_lag_1 = expected_time_lag(cleaned, featured["start_time"], 1)
    np.testing.assert_array_equal(
        featured["lag_1"].to_numpy(dtype=float),
        expected_lag_1.to_numpy(dtype=float),
    )


def test_calendar_features_are_utc() -> None:
    featured = build_feature_table(make_series(400))
    first = featured.iloc[0]
    start = pd.Timestamp(first["start_time"])
    assert start.tz is not None
    assert first["hour"] == start.hour
    assert first["day_of_week"] == start.day_of_week
    assert first["month"] == start.month


def test_chronological_splits_do_not_overlap() -> None:
    featured = build_feature_table(make_series(48 * 50))
    train, val, test = chronological_splits(featured, val_days=7, test_days=7)
    assert train["start_time"].max() < val["start_time"].min()
    assert val["start_time"].max() < test["start_time"].min()


def test_model_inference_on_fixture_series() -> None:
    featured = build_feature_table(make_series(48 * 40))
    train, val, test = chronological_splits(featured, val_days=5, test_days=5)
    model = fit_xgboost(train, val)
    preds = predict(model, test)
    assert len(preds) == len(test)
    assert preds.dtype == float
    assert preds.tolist()
    assert all(pred == pred for pred in preds)


def test_existing_health_route_untouched() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
