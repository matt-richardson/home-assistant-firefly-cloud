"""Websocket command for the dashboard cards: ``firefly_cloud/child_overview``."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from . import dates
from .child_lookup import firefly_todo_child, resolve_child
from .const import DOMAIN, WS_TYPE_CHILD_OVERVIEW
from .overview import build_overview

DATA_REGISTERED = f"{DOMAIN}_websocket_registered"
ERROR_NOT_FOUND = "not_found"
ERROR_NOT_READY = "not_ready"
ERROR_NEEDS_ATTENTION = "needs_attention"
NEEDS_ATTENTION_MESSAGE = (
    "Firefly Cloud needs attention (it may need you to log in again). Check Settings → Devices & services."
)
_FAILED_STATES = (ConfigEntryState.SETUP_ERROR, ConfigEntryState.MIGRATION_ERROR, ConfigEntryState.FAILED_UNLOAD)


# voluptuous keys, so older Home Assistant keeps working; newer HA's type hints expect probatio
@websocket_api.websocket_command(
    {vol.Required("type"): WS_TYPE_CHILD_OVERVIEW, vol.Required("entity_id"): str}  # type: ignore[dict-item]
)
@callback
def ws_child_overview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Send a child's open tasks and upcoming lessons, from coordinator data only."""
    resolved = resolve_child(hass, msg["entity_id"])
    if resolved is None:
        found = firefly_todo_child(hass, msg["entity_id"])
        if found is None:
            connection.send_error(msg["id"], ERROR_NOT_FOUND, "Not a Firefly Cloud tasks list")
        elif _needs_attention(hass, found[0]):
            connection.send_error(msg["id"], ERROR_NEEDS_ATTENTION, NEEDS_ATTENTION_MESSAGE)
        else:
            # A Firefly tasks list whose integration is still starting up or retrying
            connection.send_error(msg["id"], ERROR_NOT_READY, "Firefly data isn't loaded yet")
        return
    coordinator, child_guid = resolved
    child = coordinator.data.child(child_guid) if coordinator.data else None
    if child is None:
        connection.send_error(msg["id"], ERROR_NOT_READY, "Firefly data isn't loaded yet")
        return
    today = dates.get_offset_time().date()
    connection.send_result(msg["id"], build_overview(child, today))


def _needs_attention(hass: HomeAssistant, entry_id: str) -> bool:
    """Whether the Firefly entry can't load without the user (failed, disabled or needs logging in again)."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.disabled_by is not None or entry.state in _FAILED_STATES:
        return True
    return bool(entry.async_get_active_flows(hass, {SOURCE_REAUTH}))


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the websocket command once per Home Assistant instance."""
    if hass.data.get(DATA_REGISTERED):
        return
    websocket_api.async_register_command(hass, ws_child_overview)
    hass.data[DATA_REGISTERED] = True
