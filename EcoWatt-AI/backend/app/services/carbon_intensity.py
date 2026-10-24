"""Great Britain electricity carbon-intensity forecasts.

Uses the official National Energy System Operator Carbon Intensity API:
https://api.carbonintensity.org.uk/

Official forecast endpoints used:
- National 48-hour forecast:
  GET /intensity/{from}/fw48h
- London regional 48-hour forecast (region ID 13):
  GET /regional/intensity/{from}/fw48h/regionid/13

All official timestamps are UTC. This module keeps UTC internally and
never invents carbon-intensity values.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.carbonintensity.org.uk"
UNITS = "gCO2/kWh"
DATA_SOURCE = "National Energy System Operator Carbon Intensity API"
REQUEST_TIMEOUT_SECONDS = 10.0

# Official GB region IDs: https://carbon-intensity.github.io/api-definitions/
LONDON_REGION_ID = 13

SUPPORTED_REGIONS: dict[str, dict[str, Any]] = {
    "gb": {
        "kind": "national",
        "label": "GB",
        "forecast_type": "national",
    },
    "national": {
        "kind": "national",
        "label": "GB",
        "forecast_type": "national",
    },
    "great-britain": {
        "kind": "national",
        "label": "GB",
        "forecast_type": "national",
    },
    "london": {
        "kind": "regional",
        "label": "London",
        "forecast_type": "regional",
        "region_id": LONDON_REGION_ID,
    },
    "13": {
        "kind": "regional",
        "label": "London",
        "forecast_type": "regional",
        "region_id": LONDON_REGION_ID,
    },
}


class CarbonIntensityError(Exception):
    """Base error for carbon-intensity retrieval."""

    def __init__(self, message: str, *, code: str = "carbon_intensity_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class UnsupportedRegionError(CarbonIntensityError):
    def __init__(self, region: str) -> None:
        supported = "gb, london"
        super().__init__(
            f"Unsupported region '{region}'. Use {supported}.",
            code="unsupported_region",
        )
        self.region = region


class CarbonIntensityUnavailableError(CarbonIntensityError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="upstream_unavailable")


class CarbonIntensityResponseError(CarbonIntensityError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="upstream_invalid_response")


def normalize_region(region: str | None) -> dict[str, Any]:
    key = (region or "gb").strip().lower().replace(" ", "-")
    if key not in SUPPORTED_REGIONS:
        raise UnsupportedRegionError(region or "")
    return SUPPORTED_REGIONS[key]


def format_api_datetime(moment: datetime) -> str:
    """Official path format: YYYY-MM-DDThh:mmZ."""
    utc = moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%MZ")


def parse_utc_datetime(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise CarbonIntensityResponseError("A forecast period is missing a UTC timestamp.")

    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CarbonIntensityResponseError(
            f"Could not parse official timestamp '{value}' as UTC ISO-8601."
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _is_real_intensity(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _extract_forecast_value(intensity: Any) -> int | float | None:
    """Return the official forecast only. Never fall back to actual."""
    if not isinstance(intensity, dict):
        return None
    forecast = intensity.get("forecast")
    if _is_real_intensity(forecast):
        return forecast
    return None


def _normalize_period(
    raw_period: Any,
    *,
    region_label: str,
    forecast_type: str,
) -> dict[str, Any] | None:
    if not isinstance(raw_period, dict):
        return None

    forecast = _extract_forecast_value(raw_period.get("intensity"))
    if forecast is None:
        return None

    try:
        start = parse_utc_datetime(raw_period.get("from"))
        end = parse_utc_datetime(raw_period.get("to"))
    except CarbonIntensityResponseError:
        return None

    return {
        "start_time": to_utc_iso(start),
        "end_time": to_utc_iso(end),
        "carbon_intensity": forecast,
        "units": UNITS,
        "region": region_label,
        "data_source": DATA_SOURCE,
        "forecast_type": forecast_type,
    }


def _national_periods(payload: Any, region_label: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or "data" not in payload:
        raise CarbonIntensityResponseError(
            "National forecast response did not match the official Intensity schema."
        )

    rows = payload.get("data")
    if not isinstance(rows, list):
        raise CarbonIntensityResponseError(
            "National forecast 'data' was not a list of half-hour periods."
        )

    periods: list[dict[str, Any]] = []
    for row in rows:
        normalized = _normalize_period(
            row,
            region_label=region_label,
            forecast_type="national",
        )
        if normalized is not None:
            periods.append(normalized)
    return periods


def _regional_period_rows(payload: Any) -> tuple[list[Any], str]:
    if not isinstance(payload, dict) or "data" not in payload:
        raise CarbonIntensityResponseError(
            "Regional forecast response did not match the official Regional ID schema."
        )

    data = payload.get("data")
    region_block: Any
    if isinstance(data, list):
        if not data:
            raise CarbonIntensityResponseError("Regional forecast 'data' list was empty.")
        region_block = data[0]
    elif isinstance(data, dict):
        region_block = data
    else:
        raise CarbonIntensityResponseError(
            "Regional forecast 'data' was not an object or list."
        )

    if not isinstance(region_block, dict):
        raise CarbonIntensityResponseError("Regional forecast region block was invalid.")

    label = region_block.get("shortname")
    region_label = label if isinstance(label, str) and label.strip() else "London"

    rows = region_block.get("data")
    if not isinstance(rows, list):
        raise CarbonIntensityResponseError(
            "Regional forecast did not include a list of half-hour periods."
        )
    return rows, region_label


def _regional_periods(payload: Any, fallback_label: str) -> list[dict[str, Any]]:
    rows, region_label = _regional_period_rows(payload)
    periods: list[dict[str, Any]] = []
    for row in rows:
        normalized = _normalize_period(
            row,
            region_label=region_label or fallback_label,
            forecast_type="regional",
        )
        if normalized is not None:
            periods.append(normalized)
    return periods


def build_forecast_url(region_config: dict[str, Any], *, from_time: datetime, base_url: str) -> str:
    from_param = format_api_datetime(from_time)
    root = base_url.rstrip("/")
    if region_config["kind"] == "national":
        return f"{root}/intensity/{from_param}/fw48h"
    region_id = region_config["region_id"]
    return f"{root}/regional/intensity/{from_param}/fw48h/regionid/{region_id}"


class CarbonIntensityService:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("CARBON_INTENSITY_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def get_forecast(
        self,
        region: str | None = "gb",
        *,
        from_time: datetime | None = None,
    ) -> dict[str, Any]:
        region_config = normalize_region(region)
        moment = from_time or datetime.now(timezone.utc)
        url = build_forecast_url(region_config, from_time=moment, base_url=self.base_url)
        payload = self._fetch_json(url)

        if region_config["kind"] == "national":
            periods = _national_periods(payload, region_config["label"])
        else:
            periods = _regional_periods(payload, region_config["label"])

        if not periods:
            raise CarbonIntensityResponseError(
                "The Carbon Intensity API returned no usable forecast values. "
                "Missing measurements were not replaced with estimated data."
            )

        return {
            "region": region_config["label"],
            "units": UNITS,
            "data_source": DATA_SOURCE,
            "forecast_type": region_config["forecast_type"],
            "upstream_endpoint": url,
            "periods": periods,
        }

    def _fetch_json(self, url: str) -> Any:
        headers = {"Accept": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                response = client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise CarbonIntensityUnavailableError(
                "Timed out while requesting the Carbon Intensity API."
            ) from exc
        except httpx.RequestError as exc:
            raise CarbonIntensityUnavailableError(
                "Could not reach the Carbon Intensity API."
            ) from exc

        if response.status_code >= 500:
            raise CarbonIntensityUnavailableError(
                f"The Carbon Intensity API returned HTTP {response.status_code}."
            )
        if response.status_code >= 400:
            raise CarbonIntensityResponseError(
                f"The Carbon Intensity API rejected the request with HTTP {response.status_code}."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise CarbonIntensityResponseError(
                "The Carbon Intensity API returned a non-JSON response."
            ) from exc

        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            message = payload["error"].get("message") or "The Carbon Intensity API returned an error."
            raise CarbonIntensityResponseError(str(message))

        return payload


def get_carbon_forecast(region: str | None = "gb") -> dict[str, Any]:
    return CarbonIntensityService().get_forecast(region)
