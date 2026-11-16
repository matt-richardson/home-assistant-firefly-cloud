"""Tests for the child overview websocket command."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import make_child, make_data

from custom_components.firefly_cloud.const import WS_TYPE_CHILD_OVERVIEW
from custom_components.firefly_cloud.websocket_api import async_register_websocket_api, ws_child_overview

ENTITY = "todo.example_school_tasks_alex"
CHILD = "child-1"


@pytest.fixture
def coordinator():
    """A coordinator with data for one child."""
    coord = MagicMock()
    coord.api = AsyncMock()
    coord.task_lookahead_days = 7
    coord.data = make_data(make_child(CHILD, today=date(2026, 11, 14)))
    return coord


def _msg():
    return {"id": 5, "type": WS_TYPE_CHILD_OVERVIEW, "entity_id": ENTITY}


def test_overview_result(coordinator):
    """The command replies with the child's overview for today."""
    connection = MagicMock()
    with (
        patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=(coordinator, CHILD)),
        patch("custom_components.firefly_cloud.dates.get_offset_time") as now,
        patch("custom_components.firefly_cloud.websocket_api.build_overview", return_value={"ok": 1}) as build,
    ):
        now.return_value.date.return_value = date(2026, 11, 14)
        ws_child_overview(MagicMock(), connection, _msg())

    build.assert_called_once_with(coordinator.data.child(CHILD), date(2026, 11, 14))
    connection.send_result.assert_called_once_with(5, {"ok": 1})


def test_overview_unknown_entity():
    """An entity that isn't a Firefly todo list gets not_found."""
    connection = MagicMock()
    with (
        patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=None),
        patch("custom_components.firefly_cloud.websocket_api.firefly_todo_child", return_value=None),
    ):
        ws_child_overview(MagicMock(), connection, _msg())
    assert connection.send_error.call_args.args[:2] == (5, "not_found")
    connection.send_result.assert_not_called()


@pytest.mark.parametrize("data", [None, make_data()])
def test_overview_no_data_for_child(coordinator, data):
    """Before the first update, or for a child not yet returned, the reply is not_ready."""
    coordinator.data = data
    connection = MagicMock()
    with patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=(coordinator, CHILD)):
        ws_child_overview(MagicMock(), connection, _msg())
    assert connection.send_error.call_args.args[:2] == (5, "not_ready")


def test_overview_entry_not_loaded_is_not_ready():
    """A Firefly tasks list whose integration is still starting (or retrying) gets not_ready, not not_found."""
    connection = MagicMock()
    with (
        patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=None),
        patch("custom_components.firefly_cloud.websocket_api.firefly_todo_child", return_value=("entry", CHILD)),
    ):
        ws_child_overview(_hass_with_entry("SETUP_IN_PROGRESS"), connection, _msg())
    assert connection.send_error.call_args.args[:2] == (5, "not_ready")


def test_overview_does_not_call_api(coordinator):
    """Building the overview never calls Firefly."""
    with patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=(coordinator, CHILD)):
        ws_child_overview(MagicMock(), MagicMock(), _msg())
    assert coordinator.api.mock_calls == []


def test_registered_once():
    """The command is registered once per Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    with patch("custom_components.firefly_cloud.websocket_api.websocket_api.async_register_command") as register:
        async_register_websocket_api(hass)
        async_register_websocket_api(hass)
    register.assert_called_once_with(hass, ws_child_overview)


def _hass_with_entry(state, disabled_by=None, reauth=False):
    from homeassistant.config_entries import ConfigEntryState

    entry = MagicMock()
    entry.state = getattr(ConfigEntryState, state)
    entry.disabled_by = disabled_by
    entry.async_get_active_flows.return_value = [{"flow_id": "x"}] if reauth else []
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = entry
    return hass


@pytest.mark.parametrize(
    ("state", "disabled_by", "reauth", "code"),
    [
        ("SETUP_IN_PROGRESS", None, False, "not_ready"),
        ("SETUP_RETRY", None, False, "not_ready"),
        ("NOT_LOADED", None, False, "not_ready"),
        ("SETUP_ERROR", None, False, "needs_attention"),
        ("MIGRATION_ERROR", None, False, "needs_attention"),
        ("NOT_LOADED", "user", False, "needs_attention"),
        ("SETUP_ERROR", None, True, "needs_attention"),
        ("LOADED", None, True, "needs_attention"),
    ],
)
def test_overview_explains_an_entry_that_is_not_loaded(state, disabled_by, reauth, code):
    """Starting up or retrying is "not ready"; failed, disabled or needing re-login is "needs attention"."""
    connection = MagicMock()
    with (
        patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=None),
        patch("custom_components.firefly_cloud.websocket_api.firefly_todo_child", return_value=("entry", CHILD)),
    ):
        ws_child_overview(_hass_with_entry(state, disabled_by, reauth), connection, _msg())
    assert connection.send_error.call_args.args[:2] == (5, code)
    if code == "needs_attention":
        assert "Devices & services" in connection.send_error.call_args.args[2]


def test_overview_entry_gone_needs_attention():
    """A tasks list whose config entry no longer exists needs attention."""
    hass = MagicMock()
    hass.config_entries.async_get_entry.return_value = None
    connection = MagicMock()
    with (
        patch("custom_components.firefly_cloud.websocket_api.resolve_child", return_value=None),
        patch("custom_components.firefly_cloud.websocket_api.firefly_todo_child", return_value=("entry", CHILD)),
    ):
        ws_child_overview(hass, connection, _msg())
    assert connection.send_error.call_args.args[:2] == (5, "needs_attention")
