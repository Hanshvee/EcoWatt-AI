"""Single-appliance carbon-aware scheduler using NESO forecast intensity.

MVP energy model
----------------
Electricity use is treated as uniform over the appliance runtime. Each
half-hour forecast interval is weighted by the kWh that fall inside it:

    emissions_g = sum(intensity_g_per_kwh * energy_kwh_in_interval)

These are modeled emissions from forecast *average* carbon intensity.
They are not verified avoided emissions and do not guarantee a real
reduction in grid CO2.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Sequence

from app.models.schedule import APPLIANCE_NAMES, ScheduleRequest, ScheduleResponse, ScheduleWindow
from app.services.carbon_intensity import DATA_SOURCE, parse_utc_datetime

PERIOD = timedelta(minutes=30)
EMISSIONS_DECIMALS = 3

ASSUMPTIONS = [
    "Electricity use is modeled as uniform over the appliance runtime.",
    "Each NESO half-hour forecast intensity (gCO2/kWh) is weighted by energy consumed in that interval.",
    "Only continuous windows fully covered by contiguous 30-minute forecast periods are considered.",
    "The comparison baseline is the earliest feasible continuous window.",
    "Reported differences are modeled from forecast average carbon intensity, not verified avoided emissions.",
]

DISCLAIMER = (
    "The recommended window has a lower modeled emissions estimate based on NESO "
    "forecast average carbon intensity. This is not a verified reduction in actual "
    "grid emissions and does not guarantee a real-world carbon saving."
)


class ScheduleError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class ForecastPeriod:
    start: datetime
    end: datetime
    carbon_intensity: float


@dataclass(frozen=True)
class CandidateWindow:
    start: datetime
    finish: datetime
    emissions_gco2: float


def parse_forecast_periods(forecast: dict[str, Any]) -> list[ForecastPeriod]:
    raw_periods = forecast.get("periods")
    if not isinstance(raw_periods, list) or not raw_periods:
        raise ScheduleError(
            "The forecast did not include any usable half-hour periods.",
            code="insufficient_forecast_coverage",
        )

    periods: list[ForecastPeriod] = []
    seen: dict[datetime, ForecastPeriod] = {}
    for row in raw_periods:
        if not isinstance(row, dict):
            continue
        intensity = row.get("carbon_intensity")
        if not isinstance(intensity, (int, float)) or isinstance(intensity, bool):
            continue
        try:
            start = parse_utc_datetime(row.get("start_time"))
            end = parse_utc_datetime(row.get("end_time"))
        except Exception:
            continue
        if end - start != PERIOD:
            continue
        seen[start] = ForecastPeriod(start=start, end=end, carbon_intensity=float(intensity))

    periods = [seen[key] for key in sorted(seen)]
    if not periods:
        raise ScheduleError(
            "No contiguous 30-minute forecast intervals were available.",
            code="insufficient_forecast_coverage",
        )
    return periods


def contiguous_runs(periods: Sequence[ForecastPeriod]) -> list[list[ForecastPeriod]]:
    runs: list[list[ForecastPeriod]] = []
    current: list[ForecastPeriod] = []
    for period in periods:
        if not current or period.start == current[-1].end:
            current.append(period)
        else:
            runs.append(current)
            current = [period]
    if current:
        runs.append(current)
    return runs


def overlap(start: datetime, finish: datetime, period: ForecastPeriod) -> timedelta:
    latest_start = max(start, period.start)
    earliest_end = min(finish, period.end)
    if earliest_end <= latest_start:
        return timedelta(0)
    return earliest_end - latest_start


def is_fully_covered(start: datetime, finish: datetime, run: Sequence[ForecastPeriod]) -> bool:
    covered = timedelta(0)
    for period in run:
        covered += overlap(start, finish, period)
    return covered == (finish - start)


def modeled_emissions_g(
    start: datetime,
    finish: datetime,
    energy_kwh: float,
    run: Sequence[ForecastPeriod],
) -> float:
    duration_hours = (finish - start).total_seconds() / 3600
    if duration_hours <= 0:
        raise ScheduleError("Duration must be greater than zero.", code="invalid_duration")

    power_kw = energy_kwh / duration_hours
    total = 0.0
    for period in run:
        hours = overlap(start, finish, period).total_seconds() / 3600
        if hours > 0:
            total += period.carbon_intensity * (power_kw * hours)
    return round(total, EMISSIONS_DECIMALS)


def candidate_starts(
    run: Sequence[ForecastPeriod],
    *,
    earliest_start: datetime,
    latest_finish: datetime,
    duration: timedelta,
) -> list[datetime]:
    run_start = run[0].start
    run_end = run[-1].end
    window_open = max(earliest_start, run_start)
    window_close = min(latest_finish, run_end)
    latest_start = window_close - duration
    if latest_start < window_open:
        return []

    starts: set[datetime] = {window_open}
    for period in run:
        if window_open <= period.start <= latest_start:
            starts.add(period.start)
        aligned_to_end = period.end - duration
        if window_open <= aligned_to_end <= latest_start:
            starts.add(aligned_to_end)
    return sorted(starts)


def evaluate_run(
    run: Sequence[ForecastPeriod],
    *,
    earliest_start: datetime,
    latest_finish: datetime,
    duration: timedelta,
    energy_kwh: float,
) -> list[CandidateWindow]:
    windows: list[CandidateWindow] = []
    for start in candidate_starts(
        run,
        earliest_start=earliest_start,
        latest_finish=latest_finish,
        duration=duration,
    ):
        finish = start + duration
        if not is_fully_covered(start, finish, run):
            continue
        windows.append(
            CandidateWindow(
                start=start,
                finish=finish,
                emissions_gco2=modeled_emissions_g(start, finish, energy_kwh, run),
            )
        )
    return windows


def select_windows(
    periods: Sequence[ForecastPeriod],
    *,
    earliest_start: datetime,
    latest_finish: datetime,
    duration_minutes: float,
    energy_kwh: float,
) -> tuple[CandidateWindow, CandidateWindow]:
    duration = timedelta(minutes=duration_minutes)
    candidates: list[CandidateWindow] = []
    for run in contiguous_runs(periods):
        candidates.extend(
            evaluate_run(
                run,
                earliest_start=earliest_start,
                latest_finish=latest_finish,
                duration=duration,
                energy_kwh=energy_kwh,
            )
        )

    if not candidates:
        raise ScheduleError(
            "No continuous operating window is fully covered by contiguous "
            "30-minute NESO forecast intervals between the earliest start and deadline.",
            code="insufficient_forecast_coverage",
        )

    baseline = min(candidates, key=lambda window: window.start)
    recommended = min(candidates, key=lambda window: (window.emissions_gco2, window.start))
    return recommended, baseline


def build_schedule(request: ScheduleRequest, forecast: dict[str, Any]) -> ScheduleResponse:
    periods = parse_forecast_periods(forecast)
    recommended, baseline = select_windows(
        periods,
        earliest_start=request.earliest_start,
        latest_finish=request.latest_finish,
        duration_minutes=request.duration_minutes,
        energy_kwh=request.energy_kwh,
    )
    difference = round(baseline.emissions_gco2 - recommended.emissions_gco2, EMISSIONS_DECIMALS)

    return ScheduleResponse(
        appliance=APPLIANCE_NAMES[request.appliance],
        appliance_type=request.appliance,
        region=str(forecast.get("region") or request.region),
        recommended_start=_iso(recommended.start),
        recommended_finish=_iso(recommended.finish),
        duration_minutes=request.duration_minutes,
        energy_kwh=request.energy_kwh,
        estimated_emissions_gco2=recommended.emissions_gco2,
        baseline=ScheduleWindow(
            start=_iso(baseline.start),
            finish=_iso(baseline.finish),
            estimated_emissions_gco2=baseline.emissions_gco2,
        ),
        estimated_emissions_difference_gco2=difference,
        data_source=str(forecast.get("data_source") or DATA_SOURCE),
        assumptions=list(ASSUMPTIONS),
        disclaimer=DISCLAIMER,
        upstream_endpoint=forecast.get("upstream_endpoint"),
    )


def _iso(moment: datetime) -> str:
    return moment.astimezone(moment.tzinfo).isoformat()
