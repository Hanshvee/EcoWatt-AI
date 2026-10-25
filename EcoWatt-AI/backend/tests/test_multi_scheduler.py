from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, carbon_intensity_service
from app.models.multi_schedule import MultiScheduleRequest
from app.services.carbon_intensity import CarbonIntensityUnavailableError, CarbonIntensityService
from app.services.multi_scheduler import build_multi_schedule
from app.services.scheduler import ScheduleError

client = TestClient(app)
UTC = timezone.utc
START = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def reset_transport() -> None:
    original = carbon_intensity_service.transport
    yield
    carbon_intensity_service.transport = original


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


def forecast_from_intensities(intensities: list[float], start: datetime = START, gap_after: int | None = None) -> dict:
    periods = []
    cursor = start
    for index, intensity in enumerate(intensities):
        if gap_after is not None and index == gap_after:
            cursor += timedelta(minutes=30)
        end = cursor + timedelta(minutes=30)
        periods.append(
            {
                "start_time": cursor.isoformat(),
                "end_time": end.isoformat(),
                "carbon_intensity": intensity,
                "units": "gCO2/kWh",
                "region": "GB",
                "data_source": "National Energy System Operator Carbon Intensity API",
                "forecast_type": "national",
            }
        )
        cursor = end
    return {
        "region": "GB",
        "data_source": "National Energy System Operator Carbon Intensity API",
        "upstream_endpoint": "https://api.carbonintensity.org.uk/intensity/2026-10-25T12:00Z/fw48h",
        "periods": periods,
    }


def appliance(
    item_id: str,
    appliance: str = "dishwasher",
    earliest: datetime = START,
    latest: datetime | None = None,
    duration_minutes: float = 60,
    energy_kwh: float = 1.0,
) -> dict:
    return {
        "id": item_id,
        "appliance": appliance,
        "earliest_start": earliest.isoformat(),
        "latest_finish": (latest or earliest + timedelta(hours=2)).isoformat(),
        "duration_minutes": duration_minutes,
        "energy_kwh": energy_kwh,
    }


def multi_body(
    appliances: list[dict],
    *,
    region: str = "gb",
    household_max_power_kw: float = 5.0,
) -> dict:
    return {
        "region": region,
        "household_max_power_kw": household_max_power_kw,
        "appliances": appliances,
    }


def mock_forecast(intensities: list[float], gap_after: int | None = None) -> None:
    payload = official_payload(intensities, gap_after=gap_after)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    carbon_intensity_service.transport = httpx.MockTransport(handler)
    carbon_intensity_service.base_url = "https://api.carbonintensity.org.uk"


def test_two_appliances_non_overlapping_under_tight_capacity() -> None:
    forecast = forecast_from_intensities([10, 200, 10, 200])
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("a", energy_kwh=0.5, duration_minutes=30),
                appliance("b", energy_kwh=0.5, duration_minutes=30),
            ],
            household_max_power_kw=1.0,
        )
    )
    result = build_multi_schedule(request, forecast)
    starts = {row.id: row.start for row in result.appliances}
    assert starts["a"] != starts["b"]
    assert result.solver_status == "OPTIMAL"
    assert result.solver.proven_optimal is True
    assert result.total_estimated_emissions_gco2 == 10.0
    assert result.baseline.available is True
    assert result.baseline.total_estimated_emissions_gco2 == 105.0
    assert result.baseline.estimated_emissions_difference_gco2 == 95.0


def test_two_appliances_may_overlap_when_capacity_allows() -> None:
    forecast = forecast_from_intensities([10, 200, 200, 200])
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("washer", appliance="washing_machine", energy_kwh=0.5, duration_minutes=30),
                appliance("dryer", appliance="dryer", energy_kwh=0.5, duration_minutes=30),
            ],
            household_max_power_kw=3.0,
        )
    )
    result = build_multi_schedule(request, forecast)
    starts = {row.start for row in result.appliances}
    assert starts == {START.isoformat()}
    assert result.total_estimated_emissions_gco2 == 10.0
    assert result.solver_status == "OPTIMAL"


def test_capacity_violation_is_infeasible() -> None:
    forecast = forecast_from_intensities([50, 50])
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("ev1", appliance="ev_charging", duration_minutes=60, energy_kwh=6.0, latest=START + timedelta(hours=1)),
                appliance("ev2", appliance="ev_charging", duration_minutes=60, energy_kwh=6.0, latest=START + timedelta(hours=1)),
            ],
            household_max_power_kw=10.0,
        )
    )
    with pytest.raises(ScheduleError) as exc:
        build_multi_schedule(request, forecast)
    assert exc.value.code == "infeasible_schedule"


def test_single_appliance_exceeding_household_power() -> None:
    forecast = forecast_from_intensities([50, 50])
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("ev1", appliance="ev_charging", duration_minutes=60, energy_kwh=8.0),
                appliance("dish", duration_minutes=30, energy_kwh=0.3),
            ],
            household_max_power_kw=5.0,
        )
    )
    with pytest.raises(ScheduleError) as exc:
        build_multi_schedule(request, forecast)
    assert exc.value.code == "exceeds_household_power"


def test_different_deadlines_force_earlier_appliance() -> None:
    forecast = forecast_from_intensities([200, 10, 10, 200])
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("tight", duration_minutes=30, energy_kwh=0.5, latest=START + timedelta(minutes=30)),
                appliance("flex", duration_minutes=30, energy_kwh=0.5, latest=START + timedelta(hours=2)),
            ],
            household_max_power_kw=1.0,
        )
    )
    result = build_multi_schedule(request, forecast)
    by_id = {row.id: row for row in result.appliances}
    assert by_id["tight"].start == START.isoformat()
    assert by_id["flex"].start == (START + timedelta(minutes=30)).isoformat()
    assert result.solver_status == "OPTIMAL"


def test_missing_forecast_slots() -> None:
    forecast = forecast_from_intensities([80, 80, 10, 10], gap_after=2)
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("a", duration_minutes=90, energy_kwh=1.5, latest=START + timedelta(hours=3)),
                appliance("b", duration_minutes=30, energy_kwh=0.4, latest=START + timedelta(hours=3)),
            ]
        )
    )
    with pytest.raises(ScheduleError) as exc:
        build_multi_schedule(request, forecast)
    assert exc.value.code == "insufficient_forecast_coverage"


def test_baseline_matches_optimized_when_no_choice() -> None:
    forecast = forecast_from_intensities([75, 75, 75])
    request = MultiScheduleRequest.model_validate(
        multi_body(
            [
                appliance("a", duration_minutes=60, energy_kwh=1.0, latest=START + timedelta(hours=1)),
                appliance("b", duration_minutes=30, energy_kwh=0.4, earliest=START + timedelta(hours=1), latest=START + timedelta(hours=2)),
            ],
            household_max_power_kw=5.0,
        )
    )
    result = build_multi_schedule(request, forecast)
    assert result.baseline.available is True
    assert result.baseline.total_estimated_emissions_gco2 == result.total_estimated_emissions_gco2
    assert result.baseline.estimated_emissions_difference_gco2 == 0.0


def test_api_optimal_schedule_with_mocked_forecast() -> None:
    mock_forecast([10, 200, 10, 200])
    response = client.post(
        "/api/schedule/multiple",
        json=multi_body(
            [
                appliance("a", duration_minutes=30, energy_kwh=0.5),
                appliance("b", duration_minutes=30, energy_kwh=0.5),
            ],
            household_max_power_kw=1.0,
        ),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["solver_status"] == "OPTIMAL"
    assert payload["solver"]["proven_optimal"] is True
    assert payload["total_estimated_emissions_gco2"] == 10.0
    assert payload["baseline"]["available"] is True
    assert payload["disclaimer"].lower().find("not verified") >= 0
    assert payload["appliances"][0]["start"].endswith("+00:00")


def test_duplicate_ids_rejected() -> None:
    mock_forecast([50, 50])
    response = client.post(
        "/api/schedule/multiple",
        json=multi_body([appliance("same"), appliance("same")]),
    )
    assert response.status_code == 422


def test_invalid_duration_not_on_grid() -> None:
    response = client.post(
        "/api/schedule/multiple",
        json=multi_body(
            [
                appliance("a", duration_minutes=45),
                appliance("b"),
            ]
        ),
    )
    assert response.status_code == 422


def test_invalid_energy_and_unaligned_timestamp() -> None:
    bad_energy = multi_body([appliance("a", energy_kwh=0), appliance("b")])
    response = client.post("/api/schedule/multiple", json=bad_energy)
    assert response.status_code == 422

    body = multi_body([appliance("a"), appliance("b")])
    body["appliances"][0]["earliest_start"] = "2026-10-25T12:10:00+00:00"
    response = client.post("/api/schedule/multiple", json=body)
    assert response.status_code == 422


def test_invalid_region() -> None:
    response = client.post(
        "/api/schedule/multiple",
        json=multi_body([appliance("a"), appliance("b")], region="paris"),
    )
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unsupported_region"


def test_upstream_failure() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    carbon_intensity_service.transport = httpx.MockTransport(handler)
    response = client.post("/api/schedule/multiple", json=multi_body([appliance("a"), appliance("b")]))
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "upstream_unavailable"


def test_existing_single_schedule_endpoint_still_works() -> None:
    mock_forecast([180, 180, 60, 60])
    single = client.post(
        "/api/schedule",
        json={
            "region": "gb",
            "appliance": "dishwasher",
            "earliest_start": START.isoformat(),
            "latest_finish": (START + timedelta(hours=2)).isoformat(),
            "duration_minutes": 60,
            "energy_kwh": 1.0,
        },
    )
    health = client.get("/api/health")
    assert single.status_code == 200
    assert single.json()["recommended_start"] == (START + timedelta(hours=1)).isoformat()
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


@pytest.mark.integration
def test_live_neso_multi_appliance_schedule() -> None:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    minute = 0 if now.minute < 30 else 30
    start = now.replace(minute=minute) + timedelta(minutes=30)
    latest = start + timedelta(hours=8)
    try:
        CarbonIntensityService().get_forecast("gb", from_time=start)
    except CarbonIntensityUnavailableError:
        pytest.skip("Carbon Intensity API is unavailable")

    response = client.post(
        "/api/schedule/multiple",
        json=multi_body(
            [
                appliance("live-dish", earliest=start, latest=latest, duration_minutes=60, energy_kwh=1.2),
                appliance(
                    "live-wash",
                    appliance="washing_machine",
                    earliest=start,
                    latest=latest,
                    duration_minutes=60,
                    energy_kwh=0.8,
                ),
            ],
            household_max_power_kw=5.0,
        ),
    )
    if response.status_code == 422:
        pytest.skip("Live NESO window could not cover the requested household schedule")
    assert response.status_code == 200
    payload = response.json()
    assert payload["solver_status"] in {"OPTIMAL", "FEASIBLE"}
    if payload["solver_status"] == "FEASIBLE":
        assert payload["solver"]["proven_optimal"] is False
    assert len(payload["appliances"]) == 2
    assert payload["data_source"].startswith("National Energy System Operator")
