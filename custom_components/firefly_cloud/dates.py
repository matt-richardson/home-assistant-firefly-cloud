"""Due date helpers: Firefly due dates are calendar dates local to Home Assistant."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.util import dt as dt_util


def parse_due_date(value: str | None) -> date | None:
    """Return the calendar date of a Firefly due date, in Home Assistant's timezone.

    Firefly sends due dates without a timezone (e.g. ``2026-11-20T00:00:00``); those
    are taken as that calendar date. A value with an explicit offset or ``Z`` is
    converted to Home Assistant's timezone before taking the date. Missing or
    unparseable values give ``None``.
    """
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None
    if parsed.tzinfo is None:
        return parsed.date()
    return dt_util.as_local(parsed).date()


def local_midnight(day: date) -> datetime:
    """Return the start of ``day`` in Home Assistant's timezone."""
    return dt_util.start_of_local_day(day)
