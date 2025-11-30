"""Diagnostics support for Firefly Cloud."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SCHOOL_CODE,
    CONF_SCHOOL_NAME,
    CONF_SECRET,
    CONF_USER_GUID,
    DOMAIN,
)
from .coordinator import FireflyUpdateCoordinator


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Redact sensitive information
    redacted_data = {
        CONF_SCHOOL_CODE: entry.data[CONF_SCHOOL_CODE],
        CONF_SCHOOL_NAME: entry.data.get(CONF_SCHOOL_NAME, "Unknown"),
        CONF_HOST: entry.data.get(CONF_HOST, "Unknown"),
        CONF_DEVICE_ID: "**REDACTED**",
        CONF_SECRET: "**REDACTED**",
        CONF_USER_GUID: entry.data.get(CONF_USER_GUID, "Unknown"),
        CONF_CHILDREN_GUIDS: entry.data.get(CONF_CHILDREN_GUIDS, []),
    }

    # Extract last_updated with proper None handling
    last_updated = None
    if coordinator.data and "last_updated" in coordinator.data:
        last_updated_value = coordinator.data.get("last_updated")
        if last_updated_value is not None:
            last_updated = last_updated_value.isoformat()

    diagnostics_data = {
        "entry": {
            "title": entry.title,
            "data": redacted_data,
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "statistics": coordinator.statistics,
        },
        "data_summary": {
            "children_count": len(coordinator.data.get("children_guids", [])) if coordinator.data else 0,
            "has_user_info": "user_info" in (coordinator.data or {}),
            "last_updated": last_updated,
        },
    }

    return diagnostics_data
