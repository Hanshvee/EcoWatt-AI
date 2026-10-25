from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator, model_validator

APPLIANCE_NAMES: dict[str, str] = {
    "dishwasher": "Dishwasher",
    "washing_machine": "Washing machine",
    "dryer": "Dryer",
    "ev_charging": "EV charging",
}

APPLIANCE_ALIASES: dict[str, str] = {
    "dishwasher": "dishwasher",
    "washing_machine": "washing_machine",
    "washing-machine": "washing_machine",
    "washer": "washing_machine",
    "dryer": "dryer",
    "tumble_dryer": "dryer",
    "ev_charging": "ev_charging",
    "ev-charging": "ev_charging",
    "ev": "ev_charging",
}


def normalize_appliance(value: str) -> str:
    key = value.strip().lower().replace(" ", "_")
    if key not in APPLIANCE_ALIASES:
        raise ValueError(
            "Unsupported appliance. Use dishwasher, washing_machine, dryer, or ev_charging."
        )
    return APPLIANCE_ALIASES[key]


def require_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Timestamps must include a timezone offset, for example +00:00 or Z.")
    return value.astimezone(timezone.utc)


class ScheduleRequest(BaseModel):
    region: str = Field(min_length=1, examples=["gb", "london"])
    appliance: str = Field(examples=["dishwasher"])
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
    def validate_timezone(cls, value: datetime) -> datetime:
        return require_aware_utc(value)

    @model_validator(mode="after")
    def validate_window(self) -> "ScheduleRequest":
        if self.latest_finish <= self.earliest_start:
            raise ValueError("latest_finish must be after earliest_start.")
        runtime = self.latest_finish - self.earliest_start
        needed = self.duration_minutes * 60
        if runtime.total_seconds() < needed:
            raise ValueError(
                "duration_minutes does not fit between earliest_start and latest_finish."
            )
        return self


class ScheduleWindow(BaseModel):
    start: str
    finish: str
    estimated_emissions_gco2: float


class ScheduleResponse(BaseModel):
    appliance: str
    appliance_type: str
    region: str
    recommended_start: str
    recommended_finish: str
    duration_minutes: float
    energy_kwh: float
    estimated_emissions_gco2: float
    baseline: ScheduleWindow
    estimated_emissions_difference_gco2: float
    data_source: str
    assumptions: list[str]
    disclaimer: str
    upstream_endpoint: str | None = None
