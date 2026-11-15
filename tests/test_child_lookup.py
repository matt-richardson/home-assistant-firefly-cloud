"""Tests for finding which child a Firefly tasks list belongs to."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.firefly_cloud.child_lookup import firefly_todo_child, resolve_child
from custom_components.firefly_cloud.const import DOMAIN

ENTITY = "todo.example_school_tasks_alex"
CHILD = "child-guid-1"
ENTRY = "entry-1"


@pytest.fixture
def fake_hass():
    """A hass whose entity registry knows a few entities, with the Firefly entry loaded."""
    entries = {
        ENTITY: MagicMock(platform=DOMAIN, domain="todo", config_entry_id=ENTRY, unique_id=f"{ENTRY}_todo_{CHILD}"),
        "sensor.other": MagicMock(platform="other", domain="sensor", config_entry_id="x", unique_id="y"),
        "todo.weird": MagicMock(platform=DOMAIN, domain="todo", config_entry_id=ENTRY, unique_id="no-marker"),
        "todo.no_entry": MagicMock(platform=DOMAIN, domain="todo", config_entry_id=None, unique_id=f"x_todo_{CHILD}"),
    }
    registry = MagicMock()
    registry.async_get.side_effect = entries.get
    hass = MagicMock()
    hass.data = {DOMAIN: {ENTRY: MagicMock(change_store=MagicMock())}}
    with patch("custom_components.firefly_cloud.child_lookup.er.async_get", return_value=registry):
        yield hass


def test_firefly_todo_child(fake_hass):
    """A Firefly tasks list maps to its config entry and child, whether or not the entry is loaded."""
    assert firefly_todo_child(fake_hass, ENTITY) == (ENTRY, CHILD)
    fake_hass.data[DOMAIN].clear()
    assert firefly_todo_child(fake_hass, ENTITY) == (ENTRY, CHILD)


@pytest.mark.parametrize("entity_id", ["todo.missing", "sensor.other", "todo.weird", "todo.no_entry"])
def test_firefly_todo_child_rejects_other_entities(fake_hass, entity_id):
    """Anything that isn't a Firefly tasks list isn't matched."""
    assert firefly_todo_child(fake_hass, entity_id) is None


def test_resolve_child(fake_hass):
    """A loaded Firefly tasks list resolves to its coordinator and child."""
    coordinator = fake_hass.data[DOMAIN][ENTRY]
    assert resolve_child(fake_hass, ENTITY) == (coordinator, CHILD)
    assert resolve_child(fake_hass, "sensor.other") is None


def test_resolve_child_needs_loaded_entry(fake_hass):
    """Before the entry is loaded (or without a change store) there's nothing to resolve to."""
    fake_hass.data[DOMAIN][ENTRY].change_store = None
    assert resolve_child(fake_hass, ENTITY) is None
    fake_hass.data[DOMAIN].clear()
    assert resolve_child(fake_hass, ENTITY) is None
