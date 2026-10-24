from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, carbon_intensity_service
from app.services.carbon_intensity import (
    CarbonIntensityUnavailableError,
    CarbonIntensityService,
)

client = TestClient(app)

FROM_TIME = datetime(2018, 1, 20, 12, 0, tzinfo=timezone.utc)

NATIONAL_PAYLOAD = {
    "data": [
        {
            "from": "2018-01-20T12:00Z",
            "to": "2018-01-20T12:30Z",
            "intensity": {"forecast": 266, "actual": 263, "index": "moderate"},
        }
    ]
}


@pytest.fixture(autouse=True)
def reset_transport() -> None:
    original = carbon_intensity_service.transport
    yield
    carbon_intensity_service.transport = original


def test_health_endpoint_still_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_carbon_forecast_route_returns_normalized_national_data() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=NATIONAL_PAYLOAD)

    carbon_intensity_service.transport = httpx.MockTransport(handler)
    carbon_intensity_service.base_url = "https://api.carbonintensity.org.uk"

    response = client.get("/api/carbon-forecast")

    assert response.status_code == 200
    payload = response.json()
    assert payload["region"] == "GB"
    assert payload["periods"][0]["carbon_intensity"] == 266
    assert payload["periods"][0]["units"] == "gCO2/kWh"


def test_carbon_forecast_route_accepts_london_region() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "regionid/13" in str(request.url)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "regionid": 13,
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
            },
        )

    carbon_intensity_service.transport = httpx.MockTransport(handler)

    response = client.get("/api/carbon-forecast", params={"region": "london"})

    assert response.status_code == 200
    assert response.json()["region"] == "London"


def test_carbon_forecast_invalid_region() -> None:
    response = client.get("/api/carbon-forecast", params={"region": "paris"})
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_region"


def test_carbon_forecast_upstream_unavailable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    carbon_intensity_service.transport = httpx.MockTransport(handler)
    response = client.get("/api/carbon-forecast")

    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "upstream_unavailable"


@pytest.mark.integration
def test_live_national_forecast_when_api_available() -> None:
    try:
        result = CarbonIntensityService().get_forecast("gb", from_time=FROM_TIME)
    except CarbonIntensityUnavailableError:
        pytest.skip("Carbon Intensity API is unavailable")

    assert result["periods"]
    first = result["periods"][0]
    assert first["units"] == "gCO2/kWh"
    assert first["forecast_type"] == "national"
    assert first["start_time"].endswith("+00:00")
    assert first["carbon_intensity"] is not None


@pytest.mark.integration
def test_live_london_forecast_when_api_available() -> None:
    try:
        result = CarbonIntensityService().get_forecast("london")
    except CarbonIntensityUnavailableError:
        pytest.skip("Carbon Intensity API is unavailable")

    assert result["forecast_type"] == "regional"
    assert result["periods"]
    assert "regionid/13" in result["upstream_endpoint"]
    assert result["periods"][0]["carbon_intensity"] is not None
