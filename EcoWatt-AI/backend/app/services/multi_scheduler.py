"""Household multi-appliance scheduler using Google OR-Tools CP-SAT.

MVP rules
---------
- One continuous, non-interruptible run per appliance.
- Starts and durations sit on the NESO 30-minute grid.
- Average power = energy_kwh / duration_hours.
- Objective uses forecast-weighted modeled emissions, not marginal CO2.

Integer scaling
---------------
- Power is stored as milliwatts of kW: value * 1000, rounded up for
  appliances and down for household capacity (0.001 kW precision).
- Emissions are stored as thousandths of a gram: value * 1000, nearest
  (0.001 gCO2 precision).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import ceil
from typing import Any

from ortools.sat.python import cp_model

from app.models.multi_schedule import (
    MultiApplianceAssignment,
    MultiApplianceRequest,
    MultiBaselineResponse,
    MultiScheduleRequest,
    MultiScheduleResponse,
    MultiSolverInfo,
)
from app.models.schedule import APPLIANCE_NAMES
from app.services.carbon_intensity import DATA_SOURCE
from app.services.scheduler import (
    PERIOD,
    ScheduleError,
    ForecastPeriod,
    modeled_emissions_g,
    parse_forecast_periods,
)

POWER_SCALE = 1000
EMISSIONS_SCALE = 1000
SOLVER_TIME_LIMIT_SECONDS = 10.0
SOLVER_SEED = 42

ASSUMPTIONS = [
    "Each appliance runs once, continuously, and cannot be paused.",
    "Starts and durations are restricted to the NESO 30-minute settlement grid.",
    "Average power is modeled as energy_kwh / duration_hours and is uniform during the run.",
    "Household capacity is enforced in every occupied 30-minute slot.",
    "The objective uses NESO forecast average carbon intensity, not marginal emissions.",
    "CP-SAT power units are kW * 1000 (appliance values rounded up, household cap rounded down).",
    "CP-SAT emission units are gCO2 * 1000, rounded to the nearest 0.001 g.",
    "A FEASIBLE solver status is a bounded-time solution, not a proven optimum.",
    "The earliest-start baseline is a greedy capacity-feasible packing, not an optimized schedule.",
]

DISCLAIMER = (
    "Modeled emissions differences use NESO forecast average carbon intensity. "
    "They are not verified avoided emissions and do not guarantee a real reduction "
    "in grid CO2. A FEASIBLE result is not proven optimal."
)


@dataclass(frozen=True)
class PreparedAppliance:
    spec: MultiApplianceRequest
    power_kw: float
    power_units: int
    duration_slots: int
    starts: list[datetime]


def average_power_kw(energy_kwh: float, duration_minutes: float) -> float:
    hours = duration_minutes / 60.0
    if hours <= 0:
        raise ScheduleError("Duration must be greater than zero.", code="invalid_duration")
    return energy_kwh / hours


def scale_power_up(power_kw: float) -> int:
    return int(ceil(power_kw * POWER_SCALE - 1e-9))


def scale_capacity_down(power_kw: float) -> int:
    return int(power_kw * POWER_SCALE)


def scale_emissions(emissions_g: float) -> int:
    return int(round(emissions_g * EMISSIONS_SCALE))


def slot_range(start: datetime, duration_slots: int) -> list[datetime]:
    return [start + (index * PERIOD) for index in range(duration_slots)]


def period_map(periods: list[ForecastPeriod]) -> dict[datetime, ForecastPeriod]:
    return {period.start: period for period in periods}


def covering_periods(
    start: datetime,
    duration_slots: int,
    lookup: dict[datetime, ForecastPeriod],
) -> list[ForecastPeriod] | None:
    covered: list[ForecastPeriod] = []
    for slot in slot_range(start, duration_slots):
        period = lookup.get(slot)
        if period is None:
            return None
        if covered and period.start != covered[-1].end:
            return None
        covered.append(period)
    return covered


def feasible_starts(
    appliance: MultiApplianceRequest,
    lookup: dict[datetime, ForecastPeriod],
) -> list[datetime]:
    duration_slots = int(round(appliance.duration_minutes / 30))
    latest_start = appliance.latest_finish - timedelta(minutes=appliance.duration_minutes)
    starts: list[datetime] = []
    cursor = appliance.earliest_start
    while cursor <= latest_start:
        if covering_periods(cursor, duration_slots, lookup) is not None:
            starts.append(cursor)
        cursor += PERIOD
    return starts


def prepare_appliances(
    request: MultiScheduleRequest,
    periods: list[ForecastPeriod],
) -> list[PreparedAppliance]:
    lookup = period_map(periods)
    household_units = scale_capacity_down(request.household_max_power_kw)
    prepared: list[PreparedAppliance] = []

    for spec in request.appliances:
        power_kw = average_power_kw(spec.energy_kwh, spec.duration_minutes)
        power_units = scale_power_up(power_kw)
        if power_units > household_units:
            raise ScheduleError(
                f"Appliance '{spec.id}' requires {power_kw:.3f} kW, "
                f"which exceeds the household limit of {request.household_max_power_kw} kW.",
                code="exceeds_household_power",
            )
        starts = feasible_starts(spec, lookup)
        if not starts:
            raise ScheduleError(
                f"Appliance '{spec.id}' has no continuous 30-minute NESO forecast coverage "
                "between its earliest start and deadline.",
                code="insufficient_forecast_coverage",
            )
        prepared.append(
            PreparedAppliance(
                spec=spec,
                power_kw=power_kw,
                power_units=power_units,
                duration_slots=int(round(spec.duration_minutes / 30)),
                starts=starts,
            )
        )
    return prepared


def assignment_from_start(
    prepared: PreparedAppliance,
    start: datetime,
    periods: list[ForecastPeriod],
) -> MultiApplianceAssignment:
    finish = start + timedelta(minutes=prepared.spec.duration_minutes)
    emissions = modeled_emissions_g(start, finish, prepared.spec.energy_kwh, periods)
    return MultiApplianceAssignment(
        id=prepared.spec.id,
        appliance=APPLIANCE_NAMES[prepared.spec.appliance],
        appliance_type=prepared.spec.appliance,
        start=start.isoformat(),
        finish=finish.isoformat(),
        duration_minutes=prepared.spec.duration_minutes,
        energy_kwh=prepared.spec.energy_kwh,
        average_power_kw=round(prepared.power_kw, 3),
        estimated_emissions_gco2=emissions,
    )


def earliest_start_baseline(
    prepared: list[PreparedAppliance],
    periods: list[ForecastPeriod],
    household_max_power_kw: float,
) -> MultiBaselineResponse:
    capacity = scale_capacity_down(household_max_power_kw)
    remaining: dict[datetime, int] = {period.start: capacity for period in periods}
    chosen: dict[str, datetime] = {}

    ordered = sorted(
        prepared,
        key=lambda item: (item.spec.earliest_start, item.spec.latest_finish, item.spec.id),
    )
    for item in ordered:
        placed = False
        for start in item.starts:
            slots = slot_range(start, item.duration_slots)
            if all(remaining.get(slot, -1) >= item.power_units for slot in slots):
                for slot in slots:
                    remaining[slot] -= item.power_units
                chosen[item.spec.id] = start
                placed = True
                break
        if not placed:
            return MultiBaselineResponse(
                available=False,
                reason=(
                    "No earliest-start packing honors every appliance deadline "
                    "and the household power limit. Baseline emissions were not invented."
                ),
            )

    by_id = {item.spec.id: item for item in prepared}
    assignments = [
        assignment_from_start(by_id[item.spec.id], chosen[item.spec.id], periods)
        for item in prepared
    ]
    total = round(sum(row.estimated_emissions_gco2 for row in assignments), 3)
    return MultiBaselineResponse(
        available=True,
        appliances=assignments,
        total_estimated_emissions_gco2=total,
    )


def solve_schedule(
    prepared: list[PreparedAppliance],
    periods: list[ForecastPeriod],
    household_max_power_kw: float,
) -> tuple[dict[str, datetime], MultiSolverInfo]:
    model = cp_model.CpModel()
    starts: dict[tuple[str, datetime], cp_model.IntVar] = {}

    for item in prepared:
        for start in item.starts:
            starts[(item.spec.id, start)] = model.NewBoolVar(f"start_{item.spec.id}_{start.isoformat()}")
        model.Add(sum(starts[(item.spec.id, start)] for start in item.starts) == 1)

    occupancy: dict[datetime, list[tuple[cp_model.IntVar, int]]] = {}
    for item in prepared:
        for start in item.starts:
            var = starts[(item.spec.id, start)]
            for slot in slot_range(start, item.duration_slots):
                occupancy.setdefault(slot, []).append((var, item.power_units))

    capacity = scale_capacity_down(household_max_power_kw)
    for slot, loads in occupancy.items():
        model.Add(sum(var * power for var, power in loads) <= capacity)

    slot_index = {period.start: index for index, period in enumerate(periods)}
    emission_terms: list[cp_model.LinearExpr] = []
    tie_terms: list[cp_model.LinearExpr] = []
    for item in prepared:
        for start in item.starts:
            finish = start + timedelta(minutes=item.spec.duration_minutes)
            cost = scale_emissions(modeled_emissions_g(start, finish, item.spec.energy_kwh, periods))
            var = starts[(item.spec.id, start)]
            emission_terms.append(var * cost)
            tie_terms.append(var * slot_index.get(start, 0))

    max_tie = max(len(periods) * len(prepared), 1) + 1
    model.Minimize(sum(emission_terms) * max_tie + sum(tie_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
    solver.parameters.random_seed = SOLVER_SEED
    solver.parameters.num_search_workers = 1
    status_code = solver.Solve(model)

    if status_code == cp_model.OPTIMAL:
        status = "OPTIMAL"
        proven = True
    elif status_code == cp_model.FEASIBLE:
        status = "FEASIBLE"
        proven = False
    elif status_code == cp_model.INFEASIBLE:
        raise ScheduleError(
            "No household schedule satisfies every appliance window and the power limit.",
            code="infeasible_schedule",
        )
    else:
        raise ScheduleError(
            "The scheduler did not find a feasible assignment within the time limit.",
            code="solver_unsolved",
            status_code=503,
        )

    chosen: dict[str, datetime] = {}
    for item in prepared:
        for start in item.starts:
            if solver.Value(starts[(item.spec.id, start)]) == 1:
                chosen[item.spec.id] = start
                break
        if item.spec.id not in chosen:
            raise ScheduleError(
                "The solver returned an incomplete assignment.",
                code="solver_unsolved",
                status_code=503,
            )

    info = MultiSolverInfo(
        status=status,
        proven_optimal=proven,
        wall_time_seconds=round(solver.WallTime(), 4),
        power_scale=POWER_SCALE,
        emissions_scale=EMISSIONS_SCALE,
        precision=(
            "Power is integer millikilowatts (kW * 1000). "
            "Emissions are integer milligrams of modeled CO2 (gCO2 * 1000)."
        ),
    )
    return chosen, info


def attach_baseline_delta(
    baseline: MultiBaselineResponse,
    optimized_total: float,
) -> MultiBaselineResponse:
    if not baseline.available or baseline.total_estimated_emissions_gco2 is None:
        return baseline
    difference = round(baseline.total_estimated_emissions_gco2 - optimized_total, 3)
    percent = None
    if baseline.total_estimated_emissions_gco2 > 0:
        percent = round(100.0 * difference / baseline.total_estimated_emissions_gco2, 3)
    return baseline.model_copy(
        update={
            "estimated_emissions_difference_gco2": difference,
            "estimated_emissions_difference_percent": percent,
        }
    )


def build_multi_schedule(request: MultiScheduleRequest, forecast: dict[str, Any]) -> MultiScheduleResponse:
    periods = parse_forecast_periods(forecast)
    prepared = prepare_appliances(request, periods)
    chosen, solver_info = solve_schedule(prepared, periods, request.household_max_power_kw)
    assignments = [
        assignment_from_start(item, chosen[item.spec.id], periods)
        for item in prepared
    ]
    total = round(sum(row.estimated_emissions_gco2 for row in assignments), 3)
    baseline = attach_baseline_delta(
        earliest_start_baseline(prepared, periods, request.household_max_power_kw),
        total,
    )

    return MultiScheduleResponse(
        region=str(forecast.get("region") or request.region),
        solver_status=solver_info.status,
        household_max_power_kw=request.household_max_power_kw,
        appliances=assignments,
        total_estimated_emissions_gco2=total,
        baseline=baseline,
        data_source=str(forecast.get("data_source") or DATA_SOURCE),
        assumptions=list(ASSUMPTIONS),
        disclaimer=DISCLAIMER,
        solver=solver_info,
        upstream_endpoint=forecast.get("upstream_endpoint"),
    )


def request_from_time(request: MultiScheduleRequest) -> datetime:
    return min(item.earliest_start for item in request.appliances)
