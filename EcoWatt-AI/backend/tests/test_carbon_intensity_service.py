from datetime import datetime, timezone

import httpx
import pytest

from app.services.carbon_intensity import (
    CarbonIntensityResponseError,
    CarbonIntensityService,
    CarbonIntensityUnavailableError,
    UnsupportedRegionError,
    format_api_datetime,
)

FROM_TIME = datetime(2018, 1, 20, 12, 0, tzinfo=timezone.utc)

NATIONAL_PAYLOAD = {
    "data": [
        {
            "from": "2018-01-20T12:00Z",
            "to": "2018-01-20T12:30Z",
            "intensity": {"forecast": 266, "actual": 263, "index": "moderate"},
        },
        {
            "from": "2018-01-20T12:30Z",
            "to": "2018-01-20T13:00Z",
            "intensity": {"forecast": 250, "actual": None, "index": "moderate"},
        },
    ]
}

LONDON_PAYLOAD = {
    "data": [
        {
            "regionid": 13,
            "dnoregion": "UKPN London",
            "shortname": "London",
            "data": [
                {
                    "from": "2018-01-20T12:00Z",
                    "to": "2018-01-20T12:30Z",
                    "intensity": {"forecast": 180, "index": "moderate"},
                }
            ],
        }
    ]
}


def service_with(handler: object) -> CarbonIntensityService:
    return CarbonIntensityService(transport=httpx.MockTransport(handler))


def test_format_api_datetime_uses_official_utc_path_format() -> None:
    assert format_api_datetime(FROM_TIME) == "2018-01-20T12:00Z"


def test_national_forecast_normalizes_official_schema() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://api.carbonintensity.org.uk/intensity/2018-01-20T12:00Z/fw48h"
        )
        assert request.headers["Accept"] == "application/json"
        return httpx.Response(200, json=NATIONAL_PAYLOAD)

    result = service_with(handler).get_forecast("gb", from_time=FROM_TIME)

    assert result["region"] == "GB"
    assert result["forecast_type"] == "national"
    assert result["units"] == "gCO2/kWh"
    assert result["data_source"] == "National Energy System Operator Carbon Intensity API"
    assert len(result["periods"]) == 2
    assert result["periods"][0] == {
        "start_time": "2018-01-20T12:00:00+00:00",
        "end_time": "2018-01-20T12:30:00+00:00",
        "carbon_intensity": 266,
        "units": "gCO2/kWh",
        "region": "GB",
        "data_source": "National Energy System Operator Carbon Intensity API",
        "forecast_type": "national",
    }


def test_london_forecast_uses_official_region_id_13() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == (
            "https://api.carbonintensity.org.uk/regional/intensity/"
            "2018-01-20T12:00Z/fw48h/regionid/13"
        )
        return httpx.Response(200, json=LONDON_PAYLOAD)

    result = service_with(handler).get_forecast("london", from_time=FROM_TIME)

    assert result["region"] == "London"
    assert result["forecast_type"] == "regional"
    assert result["periods"][0]["carbon_intensity"] == 180
    assert result["periods"][0]["start_time"] == "2018-01-20T12:00:00+00:00"
    assert result["periods"][0]["region"] == "London"


def test_missing_forecast_is_omitted_and_actual_is_not_used() -> None:
    payload = {
        "data": [
            {
                "from": "2018-01-20T12:00Z",
                "to": "2018-01-20T12:30Z",
                "intensity": {"forecast": None, "actual": 999, "index": "high"},
            },
            {
                "from": "2018-01-20T12:30Z",
                "to": "2018-01-20T13:00Z",
                "intensity": {"forecast": 111, "actual": 999, "index": "low"},
            },
        ]
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    result = service_with(handler).get_forecast("gb", from_time=FROM_TIME)

    assert len(result["periods"]) == 1
    assert result["periods"][0]["carbon_intensity"] == 111


def test_all_missing_forecasts_raise_without_fabricating_values() -> None:
    payload = {
        "data": [
            {
                "from": "2018-01-20T12:00Z",
                "to": "2018-01-20T12:30Z",
                "intensity": {"forecast": None, "actual": 50},
            }
        ]
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    with pytest.raises(CarbonIntensityResponseError, match="no usable forecast"):
        service_with(handler).get_forecast("gb", from_time=FROM_TIME)


def test_unexpected_payload_raises() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    with pytest.raises(CarbonIntensityResponseError, match="official Intensity schema"):
        service_with(handler).get_forecast("gb", from_time=FROM_TIME)


def test_network_failure_is_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(CarbonIntensityUnavailableError, match="Could not reach"):
        service_with(handler).get_forecast("gb", from_time=FROM_TIME)


def test_upstream_server_error_is_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"code": "500", "message": "fail"}})

    with pytest.raises(CarbonIntensityUnavailableError, match="HTTP 500"):
        service_with(handler).get_forecast("gb", from_time=FROM_TIME)


def test_unsupported_region() -> None:
    with pytest.raises(UnsupportedRegionError):
        CarbonIntensityService().get_forecast("paris")
