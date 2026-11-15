"""Read a config entry's children and settings."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import CONF_CHILDREN_GUIDS, CONF_USER_GUID


def child_guids(entry: ConfigEntry) -> list[str]:
    """Return the GUIDs to show: the account's children, or the account itself if it has none (a student)."""
    return list(entry.data.get(CONF_CHILDREN_GUIDS) or [entry.data[CONF_USER_GUID]])


def entry_option(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Return a setting from the entry's options, falling back to its setup data, then the default."""
    return entry.options.get(key, entry.data.get(key, default))
