from datetime import datetime, timezone
from typing import Any


class TimeParseError(ValueError):
    pass


def format_api_datetime(moment: datetime) -> str:
    """Official NESO path format: YYYY-MM-DDThh:mmZ."""
    utc = moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%MZ")


def parse_utc_datetime(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TimeParseError("Missing UTC timestamp.")

    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise TimeParseError(f"Could not parse timestamp '{value}' as UTC ISO-8601.") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_utc_iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()
