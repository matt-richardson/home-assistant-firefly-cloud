"""Tests for Firefly due date helpers."""

from datetime import date

import pytest

from custom_components.firefly_cloud.dates import local_midnight, parse_due_date


def test_parse_naive_is_calendar_date(melbourne):
    """A due date without a timezone is that calendar date."""
    assert parse_due_date("2026-11-20T00:00:00") == date(2026, 11, 20)


def test_parse_naive_ignores_ha_timezone(new_york):
    """A naive due date never shifts, whatever HA's timezone is."""
    assert parse_due_date("2026-11-20T00:00:00") == date(2026, 11, 20)


def test_parse_aware_converts_to_local_date(melbourne):
    """A due date with an explicit offset is converted to HA's timezone first."""
    assert parse_due_date("2026-11-19T13:00:00Z") == date(2026, 11, 20)
    assert parse_due_date("2026-11-19T12:59:00+00:00") == date(2026, 11, 19)


@pytest.mark.parametrize("value", [None, "", "not-a-date"])
def test_parse_invalid_returns_none(value):
    """Missing or junk due dates give None rather than raising."""
    assert parse_due_date(value) is None


def test_local_midnight(melbourne):
    """local_midnight is the start of that day in HA's timezone."""
    assert local_midnight(date(2026, 11, 20)).isoformat() == "2026-11-20T00:00:00+11:00"
