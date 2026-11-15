"""Date and time helpers.

Firefly due dates are calendar dates local to Home Assistant. Code that needs the
current time calls ``dates.get_offset_time()`` through the module (not a
``from`` import), so tests can patch it in one place.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.util import dt as dt_util

# Shift "now" for testing against historical data; both 0 in normal operation.
# Negative values go back in time, e.g. TIME_OFFSET_DAYS = -6 is six days ago, and
# TIME_OFFSET_DAYS = -1, TIME_OFFSET_HOURS = -2 is yesterday, two hours earlier.
TIME_OFFSET_DAYS = 0
TIME_OFFSET_HOURS = 0  # can be fractional


def get_offset_time() -> datetime:
    """Return Home Assistant's current local time, shifted by the offsets above."""
    now = dt_util.now()
    if TIME_OFFSET_DAYS == 0 and TIME_OFFSET_HOURS == 0:
        return now
    return now + timedelta(days=TIME_OFFSET_DAYS, hours=TIME_OFFSET_HOURS)


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
