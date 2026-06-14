"""Date helpers for Meta insights time ranges."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def yesterday_utc() -> date:
    return (datetime.now(timezone.utc) - timedelta(days=1)).date()


def date_range_for_day(day: date) -> dict[str, str]:
    """Return Meta API time_range dict for a single UTC calendar day."""
    day_str = day.isoformat()
    return {"since": day_str, "until": day_str}
