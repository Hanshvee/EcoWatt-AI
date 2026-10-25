from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, carbon_intensity_service
from app.models.schedule import ScheduleRequest
from app.services.scheduler import (
    ScheduleError,
    build_schedule,
    modeled_emissions_g,
    parse_forecast_periods,
)

client = TestClient(app)
UTC = timezone.utc
START = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_transport() -> None:
    original = carbon_intensity_service.transport
    yield
    carbon_intensity_service.transport = original


def period(start: datetime, intensity: float, minutes: int = 30) -> dict:
    end = start + timedelta(minutes=minutes)
    return {
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "carbon_intensity": intensity,
        "units": "gCO2/kWh",
        "region": "GB",
        "data_source": "National Energy System Operator Carbon Intensity API",
        "forecast_type": "national",
    }


def forecast_from_intensities(intensities: list[float], start: datetime = START, gap_after: int | None = None) -> dict:
    periods = []
    cursor = start
    for index, intensity in enumerate(intensities):
        if gap_after is not None and index == gap_after:
            cursor += timedelta(minutes=30)
        periods.append(period(cursor, intensity))
        cursor += timedelta(minutes=30)
    return {
        "region": "GB",
        "units": "gCO2/kWh",
        "data_source": "National Energy System Operator Carbon Intensity API",
        "forecast_type": "national",
        "upstream_endpoint": "https://api.carbonintensity.org.uk/intensity/2026-10-25T12:00Z/fw48h",
        "periods": periods,
    }


def official_payload(intensities: list[float], start: datetime = START, gap_after: int | None = None) -> dict:
    data = []
    cursor = start
    for index, intensity in enumerate(intensities):
        if gap_after is not None and index == gap_after:
            cursor += timedelta(minutes=30)
        end = cursor + timedelta(minutes=30)
        data.append(
            {
                "from": cursor.strftime("%Y-%m-%dT%H:%MZ"),
                "to": end.strftime("%Y-%m-%dT%H:%MZ"),
                "intensity": {"forecast": intensity, "actual": None, "index": "moderate"},
            }
        )
        cursor = end
    return {"data": data}


def request_body(
    *,
    region: str = "gb",
    appliance: str = "dishwasher",
    earliest: datetime = START,
    latest: datetime | None = None,
    duration_minutes: float = 60,
    energy_kwh: float = 1.0,
) -> dict:
    return {
        "region": region,
        "appliance": appliance,
        "earliest_start": earliest.isoformat(),
        "latest_finish": (latest or earliest + timedelta(hours=2)).isoformat(),
        "duration_minutes": duration_minutes,
        "energy_kwh": energy_kwh,
    }


def schedule_request(**kwargs) -> ScheduleRequest:
    body = request_body(**kwargs)
    return ScheduleRequest.model_validate(body)


def mock_forecast(intensities: list[float], start: datetime = START, gap_after: int | None = None):
    payload = official_payload(intensities, start=start, gap_after=gap_after)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    carbon_intensity_service.transport = httpx.MockTransport(handler)
    carbon_intensity_service.base_url = "https://api.carbonintensity.org.uk"


def test_selects_lowest_emissions_window() -> None:
    forecast = forecast_from_intensities([200, 200, 50, 50])
    result = build_schedule(
        schedule_request(duration_minutes=60, energy_kwh=1.0, latest=START + timedelta(hours=2)),
        forecast,
    )

    assert result.recommended_start == (START + timedelta(hours=1)).isoformat()
    assert result.recommended_finish == (START + timedelta(hours=2)).isoformat()
    assert result.estimated_emissions_gco2 == 50.0
    assert result.baseline.start == START.isoformat()
    assert result.baseline.estimated_emissions_gco2 == 200.0
    assert result.estimated_emissions_difference_gco2 == 150.0


def test_equal_emissions_prefers_earliest_start() -> None:
    forecast = forecast_from_intensities([100, 100, 100, 100])
    result = build_schedule(
        schedule_request(duration_minutes=60, energy_kwh=1.0),
        forecast,
    )

    assert result.recommended_start == START.isoformat()
    assert result.baseline.start == START.isoformat()
    assert result.estimated_emissions_difference_gco2 == 0.0


def test_earliest_start_and_deadline_constraints() -> None:
    forecast = forecast_from_intensities([10, 10, 200, 200])
    result = build_schedule(
        schedule_request(
            earliest=START + timedelta(minutes=30),
            latest=START + timedelta(hours=2),
            duration_minutes=60,
            energy_kwh=1.0,
        ),
        forecast,
    )

    assert result.recommended_start == (START + timedelta(minutes=30)).isoformat()
    assert result.recommended_finish == (START + timedelta(minutes=90)).isoformat()
    assert result.baseline.start == result.recommended_start


def test_infeasible_when_duration_does_not_fit_deadline() -> None:
    response = client.post(
        "/api/schedule",
        json=request_body(duration_minutes=180, latest=START + timedelta(hours=1)),
    )
    assert response.status_code == 422


def test_missing_forecast_interval_is_rejected() -> None:
    forecast = forecast_from_intensities([80, 80, 10, 10], gap_after=2)
    with pytest.raises(ScheduleError) as exc_info:
        build_schedule(
            schedule_request(duration_minutes=90, energy_kwh=1.0, latest=START + timedelta(hours=3)),
            forecast,
        )
    assert exc_info.value.code == "insufficient_forecast_coverage"


def test_emissions_weight_partial_half_hours() -> None:
    periods = parse_forecast_periods(forecast_from_intensities([100, 40]))
    start = START + timedelta(minutes=15)
    finish = start + timedelta(minutes=45)
    # 15 min at 100 and 30 min at 40, uniform 1 kWh over 45 min.
    # energy = 1 * (15/45)=1/3 at 100, 2/3 at 40 => 100/3 + 80/3 = 60
    assert modeled_emissions_g(start, finish, 1.0, periods) == 60.0


def test_invalid_region() -> None:
    mock_forecast([100, 100])
    response = client.post("/api/schedule", json=request_body(region="paris"))
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_region"


def test_invalid_duration() -> None:
    response = client.post("/api/schedule", json=request_body(duration_minutes=0))
    assert response.status_code == 422


def test_invalid_energy_consumption() -> None:
    response = client.post("/api/schedule", json=request_body(energy_kwh=-1))
    assert response.status_code == 422


def test_invalid_appliance() -> None:
    body = request_body()
    body["appliance"] = "toaster"
    response = client.post("/api/schedule", json=body)
    assert response.status_code == 422


def test_upstream_neso_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    carbon_intensity_service.transport = httpx.MockTransport(handler)
    response = client.post("/api/schedule", json=request_body())
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "upstream_unavailable"


def test_api_schedule_returns_baseline_and_disclaimer() -> None:
    mock_forecast([180, 180, 60, 60])
    response = client.post(
        "/api/schedule",
        json=request_body(appliance="ev_charging", duration_minutes=60, energy_kwh=7.0),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["appliance"] == "EV charging"
    assert payload["recommended_start"] == (START + timedelta(hours=1)).isoformat()
    assert payload["baseline"]["start"] == START.isoformat()
    assert payload["estimated_emissions_gco2"] == 420.0
    assert payload["baseline"]["estimated_emissions_gco2"] == 1260.0
    assert payload["estimated_emissions_difference_gco2"] == 840.0
    assert payload["data_source"].startswith("National Energy System Operator")
    assert "uniform" in " ".join(payload["assumptions"]).lower()
    assert "not a verified reduction" in payload["disclaimer"].lower()
    assert payload["recommended_start"].endswith("+00:00")


def test_naive_timestamp_is_rejected() -> None:
    body = request_body()
    body["earliest_start"] = "2026-10-25T12:00:00"
    body["latest_finish"] = "2026-10-25T14:00:00"
    response = client.post("/api/schedule", json=body)
    assert response.status_code == 422


def test_health_and_forecast_still_work() -> None:
    mock_forecast([90])
    health = client.get("/api/health")
    forecast = client.get("/api/carbon-forecast")
    assert health.status_code == 200
    assert forecast.status_code == 200
    assert forecast.json()["periods"][0]["carbon_intensity"] == 90
