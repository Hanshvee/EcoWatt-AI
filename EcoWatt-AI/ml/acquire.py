"""Download historical national estimated actual carbon intensity.

Official endpoint (14-day maximum window):
  GET https://api.carbonintensity.org.uk/intensity/{from}/{to}

Target field: intensity.actual (gCO2/kWh). Missing actuals are dropped,
never imputed. HTTP failures raise and do not write simulated rows.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

import httpx
import pandas as pd

from ml.paths import (
    API_BASE_URL,
    CLEANED_CSV,
    DATA_SOURCE,
    MAX_RANGE_DAYS,
    PROCESSED_DIR,
    RAW_DIR,
    RAW_JSONL,
    REGION,
    UNITS,
)
from ml.timeutils import TimeParseError, format_api_datetime, parse_utc_datetime, to_utc_iso

LOOKBACK_DAYS = 180
REQUEST_TIMEOUT_SECONDS = 20.0
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5


class AcquisitionError(RuntimeError):
    pass


def is_real_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def iter_request_windows(
    start: datetime,
    end: datetime,
    max_days: int = MAX_RANGE_DAYS,
) -> Iterator[tuple[datetime, datetime]]:
    if start >= end:
        raise AcquisitionError("Historical window start must be before end.")

    cursor = start
    span = timedelta(days=max_days)
    while cursor < end:
        window_end = min(cursor + span, end)
        yield cursor, window_end
        cursor = window_end


def parse_national_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise AcquisitionError("Response did not match the official national Intensity schema.")

    rows: list[dict[str, Any]] = []
    for item in payload["data"]:
        parsed = parse_national_period(item)
        if parsed is not None:
            rows.append(parsed)
    return rows


def parse_national_period(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None

    intensity = item.get("intensity")
    if not isinstance(intensity, dict):
        return None

    try:
        start = parse_utc_datetime(item.get("from"))
        end = parse_utc_datetime(item.get("to"))
    except TimeParseError:
        return None

    actual = intensity.get("actual")
    forecast = intensity.get("forecast")
    index = intensity.get("index")

    return {
        "start_time": to_utc_iso(start),
        "end_time": to_utc_iso(end),
        "actual_gco2_per_kwh": actual if is_real_number(actual) else None,
        "official_forecast_gco2_per_kwh": forecast if is_real_number(forecast) else None,
        "intensity_index": index if isinstance(index, str) else None,
        "region": REGION,
        "units": UNITS,
        "data_source": DATA_SOURCE,
    }


def clean_observations(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise AcquisitionError("No parseable national intensity periods were returned.")

    frame["start_time"] = pd.to_datetime(frame["start_time"], utc=True)
    frame["end_time"] = pd.to_datetime(frame["end_time"], utc=True)
    frame = frame.sort_values("start_time")
    frame = frame.drop_duplicates(subset=["start_time"], keep="last")

    duration = frame["end_time"] - frame["start_time"]
    expected = pd.Timedelta(minutes=30)
    aligned = duration == expected
    frame = frame.loc[aligned].copy()

    usable = frame.dropna(subset=["actual_gco2_per_kwh"]).copy()
    if usable.empty:
        raise AcquisitionError(
            "No estimated actual carbon-intensity values were available. "
            "Missing actuals were not replaced with forecasts or simulated data."
        )
    return usable.reset_index(drop=True)


def fetch_window(
    client: httpx.Client,
    start: datetime,
    end: datetime,
    base_url: str = API_BASE_URL,
) -> tuple[str, dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/intensity/{format_api_datetime(start)}/{format_api_datetime(end)}"
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.get(url, headers={"Accept": "application/json"})
        except httpx.TimeoutException as exc:
            last_error = AcquisitionError("Timed out while requesting historical carbon intensity.")
            _backoff(attempt)
            continue
        except httpx.RequestError as exc:
            last_error = AcquisitionError("Could not reach the Carbon Intensity API.")
            last_error.__cause__ = exc
            _backoff(attempt)
            continue

        if response.status_code >= 500:
            last_error = AcquisitionError(
                f"Carbon Intensity API returned HTTP {response.status_code} for {url}."
            )
            _backoff(attempt)
            continue
        if response.status_code >= 400:
            raise AcquisitionError(
                f"Carbon Intensity API rejected {url} with HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise AcquisitionError(f"Non-JSON response from {url}.") from exc

        if not isinstance(payload, dict):
            raise AcquisitionError(f"Unexpected payload type from {url}.")
        if isinstance(payload.get("error"), dict):
            message = payload["error"].get("message") or "upstream error"
            raise AcquisitionError(f"Carbon Intensity API error for {url}: {message}")
        return url, payload

    raise last_error or AcquisitionError(f"Failed to download {url}.")


def _backoff(attempt: int) -> None:
    if attempt < MAX_RETRIES:
        time.sleep(RETRY_BACKOFF_SECONDS * attempt)


def download_history(
    *,
    lookback_days: int = LOOKBACK_DAYS,
    end: datetime | None = None,
    base_url: str = API_BASE_URL,
    transport: httpx.BaseTransport | None = None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    window_end = end or datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    # Leave a one-day buffer so the newest periods can publish estimated actuals.
    window_end = window_end - timedelta(days=1)
    window_start = window_end - timedelta(days=lookback_days)

    raw_records: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, transport=transport) as client:
        for start, stop in iter_request_windows(window_start, window_end):
            url, payload = fetch_window(client, start, stop, base_url=base_url)
            raw_records.append(
                {
                    "upstream_endpoint": url,
                    "requested_from": to_utc_iso(start),
                    "requested_to": to_utc_iso(stop),
                    "payload": payload,
                }
            )
            parsed_rows.extend(parse_national_payload(payload))

    cleaned = clean_observations(parsed_rows)
    return cleaned, raw_records


def save_datasets(cleaned: pd.DataFrame, raw_records: list[dict[str, Any]]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with RAW_JSONL.open("w", encoding="utf-8") as handle:
        for record in raw_records:
            handle.write(json.dumps(record) + "\n")

    cleaned.to_csv(CLEANED_CSV, index=False)


def acquire(
    *,
    lookback_days: int = LOOKBACK_DAYS,
    transport: httpx.BaseTransport | None = None,
) -> Path:
    cleaned, raw_records = download_history(lookback_days=lookback_days, transport=transport)
    save_datasets(cleaned, raw_records)
    print(
        f"Saved {len(cleaned)} national actual observations "
        f"from {cleaned['start_time'].min()} to {cleaned['start_time'].max()}"
    )
    print(f"Raw: {RAW_JSONL}")
    print(f"Cleaned: {CLEANED_CSV}")
    return CLEANED_CSV


if __name__ == "__main__":
    acquire()
