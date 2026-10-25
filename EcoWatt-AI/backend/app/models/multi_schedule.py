from datetime import datetime, timedelta

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.schedule import normalize_appliance, require_aware_utc

GRID_MINUTES = 30


def _on_half_hour(value: datetime) -> datetime:
    moment = require_aware_utc(value)
    if moment.minute not in (0, 30) or moment.second != 0 or moment.microsecond != 0:
        raise ValueError(
            "Timestamps must fall on a 30-minute UTC boundary (minute 00 or 30)."
        )
    return moment


def _multiple_of_grid(minutes: float) -> float:
    if minutes <= 0:
        raise ValueError("duration_minutes must be greater than zero.")
    stepped = minutes / GRID_MINUTES
    if abs(stepped - round(stepped)) > 1e-9:
        raise ValueError("duration_minutes must be a multiple of 30 for this MVP.")
    return float(int(round(stepped)) * GRID_MINUTES)


class MultiApplianceRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    appliance: str
    earliest_start: datetime
    latest_finish: datetime
    duration_minutes: float = Field(gt=0, le=2880)
    energy_kwh: float = Field(gt=0, le=200)

    @field_validator("appliance")
    @classmethod
    def validate_appliance(cls, value: str) -> str:
        return normalize_appliance(value)

    @field_validator("earliest_start", "latest_finish")
    @classmethod
    def validate_grid_time(cls, value: datetime) -> datetime:
        return _on_half_hour(value)

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: float) -> float:
        return _multiple_of_grid(value)

    @model_validator(mode="after")
    def validate_window(self) -> "MultiApplianceRequest":
        if self.latest_finish <= self.earliest_start:
            raise ValueError(f"Appliance '{self.id}': latest_finish must be after earliest_start.")
        needed = timedelta(minutes=self.duration_minutes)
        if self.latest_finish - self.earliest_start < needed:
            raise ValueError(
                f"Appliance '{self.id}': duration does not fit between earliest_start and latest_finish."
            )
        return self


class MultiScheduleRequest(BaseModel):
    region: str = Field(min_length=1, examples=["gb", "london"])
    household_max_power_kw: float = Field(gt=0, le=100)
    appliances: list[MultiApplianceRequest] = Field(min_length=2, max_length=6)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> "MultiScheduleRequest":
        ids = [item.id for item in self.appliances]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            raise ValueError(f"Duplicate appliance IDs are not allowed: {', '.join(duplicates)}.")
        return self


class MultiApplianceAssignment(BaseModel):
    id: str
    appliance: str
    appliance_type: str
    start: str
    finish: str
    duration_minutes: float
    energy_kwh: float
    average_power_kw: float
    estimated_emissions_gco2: float


class MultiBaselineResponse(BaseModel):
    available: bool
    appliances: list[MultiApplianceAssignment] | None = None
    total_estimated_emissions_gco2: float | None = None
    estimated_emissions_difference_gco2: float | None = None
    estimated_emissions_difference_percent: float | None = None
    reason: str | None = None


class MultiSolverInfo(BaseModel):
    status: str
    proven_optimal: bool
    wall_time_seconds: float
    power_scale: int
    emissions_scale: int
    precision: str


class MultiScheduleResponse(BaseModel):
    region: str
    solver_status: str
    household_max_power_kw: float
    appliances: list[MultiApplianceAssignment]
    total_estimated_emissions_gco2: float
    baseline: MultiBaselineResponse
    data_source: str
    assumptions: list[str]
    disclaimer: str
    solver: MultiSolverInfo
    upstream_endpoint: str | None = None
